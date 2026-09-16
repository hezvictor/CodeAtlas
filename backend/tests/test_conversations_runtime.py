import uuid
import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import httpx
import pytest

from app.db import get_session
from app.dependencies import current_user_id
from app.main import app
from app.models import Conversation
from app.routers import conversations as conversations_module
from app.routers.conversations import RunRegistry


@pytest.mark.asyncio
async def test_registry_start_keeps_run_after_subscriber_disconnects():
    registry = RunRegistry()

    async def runner(_handle):
        yield "hello"
        yield " world"

    run_id = await registry.start("conversation-1", runner)
    await asyncio.sleep(0.01)
    record = registry.get_record("conversation-1", run_id)
    assert record is not None
    assert record.status == "completed"
    assert record.content == "hello world"


@pytest.mark.asyncio
async def test_registry_snapshot_contains_partial_content_for_reconnect():
    registry = RunRegistry()
    gate = asyncio.Event()

    async def runner(_handle):
        yield "partial"
        await gate.wait()

    run_id = await registry.start("conversation-2", runner)
    await asyncio.sleep(0.01)
    record = registry.get_record("conversation-2", run_id)
    assert record is not None
    assert registry.snapshot(record)["content"] == "partial"
    record.handle.stop_event.set()
    gate.set()
    await asyncio.sleep(0.01)


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

    assert registry.is_running("conversation-1")
    assert registry.get_stop_event("conversation-1").is_set()

    await registry.release("conversation-1", handle)
    assert not registry.is_running("conversation-1")
    assert registry.get_stop_event("conversation-1") is None


class _Rows:
    def __init__(self, rows=()):
        self._rows = list(rows)

    def all(self):
        return list(self._rows)


class _FakeSession:
    """只实现 stream 端点用到的会话接口，避免测试依赖真实数据库。"""

    def __init__(self, conversation=None):
        self.conversation = conversation
        self.added = []

    async def scalar(self, _statement):
        return self.conversation

    async def scalars(self, _statement):
        return _Rows()

    async def execute(self, _statement):
        return None

    async def flush(self):
        return None

    async def refresh(self, _instance):
        return None

    async def get(self, _model, _id):
        return None

    async def commit(self):
        return None

    async def rollback(self):
        return None

    async def close(self):
        return None

    def add(self, instance):
        self.added.append(instance)


class _AsyncSessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *_exc):
        return False


class _FakeSessionFactory:
    """模拟 `session_factory()` 的异步上下文管理器用法。"""

    def __init__(self, sessions):
        self.sessions = sessions

    def __call__(self):
        session = _FakeSession()
        self.sessions.append(session)
        return _AsyncSessionContext(session)


@pytest.mark.asyncio
async def test_stream_failure_records_metrics_and_persists_failed_message(monkeypatch):
    """聊天模型未配置时，SSE 必须回传 run.failed，并落库一条带耗时的失败助手消息。"""

    cid, uid = uuid.uuid4(), uuid.uuid4()
    request_session = _FakeSession(Conversation(id=cid, user_id=uid, title="新对话", mode="normal"))
    saved_sessions = []

    async def override_session():
        yield request_session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[current_user_id] = lambda: uid
    monkeypatch.setattr(conversations_module, "session_factory", _FakeSessionFactory(saved_sessions))
    monkeypatch.setattr(
        conversations_module,
        "get_settings",
        lambda: SimpleNamespace(dashscope_api_key="", chat_model="test-chat-model"),
    )

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                f"/api/v1/conversations/{cid}/messages/stream",
                json={"content": "这道题的最短路为什么超时？"},
            )

        assert response.status_code == 200
        body = response.text
        assert "event: run.started" in body
        assert "event: retrieval.completed" in body
        assert "event: run.failed" in body
        assert "CHAT_PROVIDER_ERROR" in body

        persisted = [message for session in saved_sessions for message in session.added]
        assert persisted, "失败路径必须落库一条助手消息"
        failed = persisted[-1]
        assert failed.role == "assistant"
        assert failed.status == "failed"
        assert failed.content == ""
        assert failed.first_token_latency_ms is None
        assert isinstance(failed.duration_ms, int)
        assert failed.problem_id is None
        assert failed.mode == "normal"
        assert failed.solution_language is None
        assert not conversations_module.runs.is_running(str(cid))
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_scoped_retrieval_failure_does_not_fall_back_to_chat(monkeypatch):
    cid, uid = uuid.uuid4(), uuid.uuid4()
    request_session = _FakeSession(Conversation(id=cid, user_id=uid, title="新对话", mode="normal"))
    saved_sessions = []

    async def override_session():
        yield request_session

    async def fail_retrieval(*_args, **_kwargs):
        raise RuntimeError("embedding service unavailable")

    async def unexpected_model_stream(*_args, **_kwargs):
        raise AssertionError("scoped retrieval failure must not call the chat model")
        yield "unreachable"

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[current_user_id] = lambda: uid
    monkeypatch.setattr(conversations_module, "session_factory", _FakeSessionFactory(saved_sessions))
    monkeypatch.setattr(conversations_module, "retrieve_chunks", fail_retrieval)
    monkeypatch.setattr(conversations_module, "model_stream", unexpected_model_stream)

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                f"/api/v1/conversations/{cid}/messages/stream",
                json={"content": "查询知识库", "knowledge_group_ids": [str(uuid.uuid4())]},
            )

        assert response.status_code == 200
        assert "event: retrieval.failed" in response.text
        assert "RETRIEVAL_FAILED" in response.text
        assert "event: run.failed" in response.text
    finally:
        app.dependency_overrides.clear()


def test_chat_request_rejects_whitespace_only_content_and_strips_content():
    from app.schemas import ChatRequest

    assert ChatRequest(content="  hello  ").content == "hello"
    with pytest.raises(ValueError):
        ChatRequest(content="   \n\t")


def test_message_response_exposes_generation_metrics():
    from app.schemas import MessageResponse

    assert "duration_ms" in MessageResponse.model_fields
    assert "first_token_latency_ms" in MessageResponse.model_fields


def test_retry_request_supports_editing_the_user_message():
    from app.schemas import RetryRequest

    assert RetryRequest(content=" updated prompt ").content == "updated prompt"


def test_chat_request_can_reuse_user_message_after_retry():
    from app.schemas import ChatRequest

    assert ChatRequest(content="retry", reuse_last_user=True).reuse_last_user is True
