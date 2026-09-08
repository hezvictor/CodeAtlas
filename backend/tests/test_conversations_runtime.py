import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app.routers.conversations import RunRegistry


@pytest.mark.asyncio
async def test_registry_removes_released_run_and_lock():
    registry = RunRegistry(ttl_seconds=60)
    handle = await registry.acquire("conversation-1")

    assert registry.is_running("conversation-1")

    await registry.release("conversation-1", handle)

    assert not registry.is_running("conversation-1")
    assert registry.get_stop_event("conversation-1") is None


@pytest.mark.asyncio
async def test_registry_expires_stale_run():
    registry = RunRegistry(ttl_seconds=1)
    handle = await registry.acquire("conversation-1")
    handle.last_activity = datetime.now(UTC) - timedelta(seconds=2)

    await registry.cleanup()

    assert not registry.is_running("conversation-1")
    assert registry.get_stop_event("conversation-1") is None


def test_chat_request_rejects_whitespace_only_content_and_strips_content():
    from app.schemas import ChatRequest

    assert ChatRequest(content="  hello  ").content == "hello"
    with pytest.raises(ValueError):
        ChatRequest(content="   \n\t")
