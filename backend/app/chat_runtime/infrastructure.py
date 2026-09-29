import asyncio
import json
import sys
import time

from arq.connections import RedisSettings, create_pool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from redis.asyncio import from_url
from redis.exceptions import WatchError

from ..config import get_settings
from ..temporary.context import TemporaryContextStore


async def validate_ephemeral_redis(redis):
    try:
        config = await redis.config_get("appendonly", "save")
    except Exception:
        raise RuntimeError("EPHEMERAL_REDIS_CONFIG_UNVERIFIABLE") from None
    if config.get("appendonly") != "no" or config.get("save") != "":
        raise RuntimeError("EPHEMERAL_REDIS_MUST_NOT_PERSIST")


class RunCache:
    def __init__(self, redis): self.redis = redis

    @staticmethod
    def key(run_id, suffix="context"):
        return f"codeatlas:ephemeral:run:{run_id}:{suffix}"

    async def load(self, run_id):
        value = await self.redis.get(self.key(run_id))
        return json.loads(value) if value else None

    async def save(self, run_id, context):
        ttl = 86400
        if context.get("files"):
            ttl = min(ttl, int(min(f["created_at"] + 259200 for f in context["files"]) - time.time()))
        if ttl <= 0:
            raise RuntimeError("TEMPORARY_CONTEXT_LOST")
        stop_key = f"codeatlas:ephemeral:stop:{run_id}"
        for _ in range(8):
            async with self.redis.pipeline(transaction=True) as pipe:
                try:
                    await pipe.watch(stop_key)
                    if await pipe.exists(stop_key): raise asyncio.CancelledError
                    pipe.multi()
                    pipe.set(self.key(run_id), json.dumps(context, ensure_ascii=False), ex=ttl)
                    await pipe.execute()
                    return
                except WatchError:
                    continue
        raise RuntimeError("TEMPORARY_CONTEXT_BUSY")

    async def emit(self, run_id, sequence, name, data):
        key = self.key(run_id, "events")
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.rpush(key, json.dumps({"sequence": sequence, "name": name, "data": data}, ensure_ascii=False))
            pipe.ltrim(key, -128, -1)
            pipe.expire(key, 86400)
            await pipe.execute()

    async def events(self, run_id, after):
        return [item for raw in await self.redis.lrange(self.key(run_id, "events"), 0, -1)
                if (item := json.loads(raw))["sequence"] > after]

    async def clear(self, run_id):
        await self.redis.delete(self.key(run_id), self.key(run_id, "events"))


class RuntimeResources:
    async def open(self):
        if sys.platform == "win32" and isinstance(asyncio.get_running_loop(), asyncio.ProactorEventLoop):
            raise RuntimeError("PostgreSQL checkpoints require Windows SelectorEventLoop; use app.api_runner or app.worker_runner")
        settings = get_settings()
        # An independent server is required, not another logical DB on the queue Redis.
        from urllib.parse import urlsplit
        persistent, ephemeral = urlsplit(settings.redis_url), urlsplit(settings.ephemeral_redis_url)
        if (persistent.hostname, persistent.port or 6379) == (ephemeral.hostname, ephemeral.port or 6379):
            raise RuntimeError("EPHEMERAL_REDIS_REQUIRES_SEPARATE_SERVER")
        self.ephemeral = from_url(settings.ephemeral_redis_url, decode_responses=True)
        await validate_ephemeral_redis(self.ephemeral)
        self.temporary = TemporaryContextStore(self.ephemeral)
        self.cache = RunCache(self.ephemeral)
        self.queue = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        self.pool = AsyncConnectionPool(settings.database_url.replace("postgresql+asyncpg://", "postgresql://"),
                                        open=False, kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row})
        await self.pool.open()
        await self.pool.wait()
        self.checkpointer = AsyncPostgresSaver(self.pool)
        # Schema is owned by reviewed Alembic migrations; never call saver.setup() here.
        async with self.pool.connection() as conn:
            await conn.execute("SELECT 1 FROM checkpoint_migrations LIMIT 1")
        return self

    async def close(self):
        if hasattr(self, "queue"): await self.queue.aclose()
        if hasattr(self, "pool"): await self.pool.close()
        if hasattr(self, "ephemeral"): await self.ephemeral.aclose()


def resources(request):
    return request.app.state.runtime
