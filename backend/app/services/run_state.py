import uuid
from dataclasses import dataclass

from fastapi import HTTPException


@dataclass
class RunLease:
    state: "RunState"
    conversation_id: str
    owner: str

    async def stop_requested(self) -> bool:
        return bool(await self.state.redis.get(self.state.stop_key(self.conversation_id)))

    async def refresh(self) -> bool:
        """Extend this lease only while it is still owned by this generator."""
        key = self.state.lease_key(self.conversation_id)
        evaluator = getattr(self.state.redis, "eval", None)
        if evaluator is not None:
            result = await evaluator(
                "if redis.call('get', KEYS[1]) == ARGV[1] then "
                "return redis.call('expire', KEYS[1], ARGV[2]) else return 0 end",
                1,
                key,
                self.owner,
                str(self.state.lease_ttl_seconds),
            )
            return bool(result)
        current = await self.state.redis.get(key)
        if isinstance(current, bytes):
            current = current.decode()
        if current != self.owner:
            return False
        expire = getattr(self.state.redis, "expire", None)
        if expire is None:
            return True
        return bool(await expire(key, self.state.lease_ttl_seconds))

    async def release(self) -> None:
        key = self.state.lease_key(self.conversation_id)
        # Redis eval makes owner verification and deletion one atomic operation,
        # preventing an expired lease from being replaced and then deleted here.
        evaluator = getattr(self.state.redis, "eval", None)
        if evaluator is not None:
            await evaluator(
                "if redis.call('get', KEYS[1]) == ARGV[1] then "
                "return redis.call('del', KEYS[1]) else return 0 end",
                1,
                key,
                self.owner,
            )
            return
        # Lightweight in-memory adapters used by unit tests may not implement eval.
        current = await self.state.redis.get(key)
        if isinstance(current, bytes):
            current = current.decode()
        if current == self.owner:
            await self.state.redis.delete(key)


class RunState:
    def __init__(self, redis, lease_ttl_seconds: int = 900, stop_ttl_seconds: int = 120):
        self.redis = redis
        self.lease_ttl_seconds = lease_ttl_seconds
        self.stop_ttl_seconds = stop_ttl_seconds

    @staticmethod
    def lease_key(conversation_id: str) -> str:
        return f"codeatlas:run:lease:{conversation_id}"

    @staticmethod
    def stop_key(conversation_id: str) -> str:
        return f"codeatlas:run:stop:{conversation_id}"

    async def acquire(self, conversation_id: str) -> RunLease:
        owner = str(uuid.uuid4())
        acquired = await self.redis.set(
            self.lease_key(conversation_id), owner, ex=self.lease_ttl_seconds, nx=True
        )
        if not acquired:
            raise HTTPException(409, "A response is already being generated")
        await self.redis.delete(self.stop_key(conversation_id))
        return RunLease(self, conversation_id, owner)

    async def request_stop(self, conversation_id: str) -> None:
        await self.redis.set(self.stop_key(conversation_id), "1", ex=self.stop_ttl_seconds)
