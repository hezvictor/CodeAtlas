import pytest
from fastapi import HTTPException


class FakeRedis:
    def __init__(self):
        self.values = {}

    async def set(self, key, value, ex=None, nx=False):
        if nx and key in self.values:
            return False
        self.values[key] = value
        return True

    async def get(self, key):
        return self.values.get(key)

    async def delete(self, key):
        self.values.pop(key, None)


class EvalOnlyRedis(FakeRedis):
    async def get(self, key):
        raise AssertionError("release must use an atomic owner check")

    async def eval(self, script, numkeys, key, owner, *args):
        if self.values.get(key) == owner:
            if "expire" in script:
                return 1
            self.values.pop(key, None)
            return 1
        return 0

    async def expire(self, key, ttl):
        return key in self.values


@pytest.mark.asyncio
async def test_second_instance_cannot_acquire_same_conversation():
    from app.services.run_state import RunState

    redis = FakeRedis()
    first = RunState(redis)
    second = RunState(redis)
    lease = await first.acquire("conversation-1")
    with pytest.raises(HTTPException) as error:
        await second.acquire("conversation-1")
    assert error.value.status_code == 409
    await lease.release()


@pytest.mark.asyncio
async def test_stop_signal_is_visible_and_release_is_idempotent():
    from app.services.run_state import RunState

    redis = FakeRedis()
    state = RunState(redis)
    lease = await state.acquire("conversation-1")
    assert not await lease.stop_requested()
    await state.request_stop("conversation-1")
    assert await lease.stop_requested()
    await lease.release()
    await lease.release()


@pytest.mark.asyncio
async def test_release_uses_atomic_owner_check():
    from app.services.run_state import RunState

    redis = EvalOnlyRedis()
    state = RunState(redis)
    lease = await state.acquire("conversation-atomic")
    await lease.release()
    assert redis.values == {}


@pytest.mark.asyncio
async def test_lease_refresh_uses_owner_check():
    from app.services.run_state import RunState

    redis = EvalOnlyRedis()
    state = RunState(redis, lease_ttl_seconds=42)
    lease = await state.acquire("conversation-refresh")
    refreshed = await lease.refresh()
    assert refreshed is True
    assert redis.values
