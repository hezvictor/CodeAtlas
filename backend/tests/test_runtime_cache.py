import asyncio
import json

import pytest
from fakeredis.aioredis import FakeRedis

from app.chat_runtime.infrastructure import RunCache, validate_ephemeral_redis


@pytest.mark.asyncio
async def test_cache_recovers_across_runtime_instances_without_durable_payload():
    redis = FakeRedis(decode_responses=True)
    cache = RunCache(redis)
    await cache.save("run", {"messages": [{"content": "PRIVATE"}], "files": []})
    await cache.emit("run", 1, "tool.started", {"step_id": "call", "title": "查询"})
    assert (await RunCache(redis).load("run"))["messages"][0]["content"] == "PRIVATE"
    events = await cache.events("run", 0)
    assert events[0]["sequence"] == 1
    assert "PRIVATE" not in json.dumps(events)
    await cache.clear("run")
    assert await cache.load("run") is None


@pytest.mark.asyncio
async def test_ephemeral_cache_fails_closed_for_persistent_or_unknown_config():
    class Redis:
        def __init__(self, config): self.config = config
        async def config_get(self, *names): return self.config
    for config in ({"appendonly": "yes", "save": ""}, {"appendonly": "no", "save": "900 1"}, {}):
        with pytest.raises(RuntimeError):
            await validate_ephemeral_redis(Redis(config))
    await validate_ephemeral_redis(Redis({"appendonly": "no", "save": ""}))


@pytest.mark.asyncio
async def test_stopped_run_cannot_recreate_private_context_after_cleanup():
    redis = FakeRedis(decode_responses=True)
    cache = RunCache(redis)
    await redis.set("codeatlas:ephemeral:stop:run", "1", ex=86400)
    with pytest.raises(asyncio.CancelledError):
        await cache.save("run", {"messages": [{"content": "PRIVATE"}], "files": []})
    assert await cache.load("run") is None
