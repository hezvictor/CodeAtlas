import uuid
from datetime import UTC, datetime

import pytest


@pytest.mark.asyncio
async def test_retry_rejects_an_active_generation(monkeypatch):
    import httpx

    from app.db import get_session
    from app.dependencies import current_user_id
    from app.main import app
    from app.models import Conversation
    from app.routers import conversations as module

    cid, mid, uid = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

    class Session:
        async def execute(self, *_args, **_kwargs):
            return None

        async def scalar(self, *_args, **_kwargs):
            return Conversation(id=cid, user_id=uid, title="active")

    async def override_session():
        yield Session()

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[current_user_id] = lambda: uid
    async def is_active(*args): return True
    monkeypatch.setattr(module, "active_run", is_active)
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(f"/api/v1/conversations/{cid}/messages/{mid}/retry", json={})
        assert response.status_code == 409
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_retry_rejects_older_assistant_message(monkeypatch):
    import httpx

    from app.db import get_session
    from app.dependencies import current_user_id
    from app.main import app
    from app.models import Conversation, Message
    from app.routers import conversations as module

    cid, mid, uid = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

    class Session:
        calls = 0

        async def execute(self, *_args, **_kwargs):
            return None

        async def scalar(self, *_args, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                return Conversation(id=cid, user_id=uid, title="active")
            if self.calls == 2:
                return Message(id=mid, conversation_id=cid, role="assistant", content="old answer", position=1, created_at=datetime.now(UTC))
            return uuid.uuid4()

    async def override_session():
        yield Session()

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[current_user_id] = lambda: uid
    async def is_active(*args): return None
    monkeypatch.setattr(module, "active_run", is_active)
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(f"/api/v1/conversations/{cid}/messages/{mid}/retry", json={})
        assert response.status_code == 409
    finally:
        app.dependency_overrides.clear()


def test_retry_request_rejects_blank_content():
    from app.schemas import RetryRequest

    with pytest.raises(ValueError):
        RetryRequest(content="   ")


def test_conversation_model_has_pinned_and_message_retrieved_ids():
    from app.models import Conversation, Message

    assert "pinned" in Conversation.__table__.c
    assert "retrieved_chunk_ids" in Message.__table__.c


def test_conversation_update_allows_title_and_pinned_optional():
    from app.schemas import ConversationUpdate

    assert ConversationUpdate(title=" renamed ").title == "renamed"
    assert ConversationUpdate(pinned=True).pinned is True


def test_conversation_titles_reject_whitespace_after_normalization():
    from app.schemas import ConversationCreate, ConversationUpdate

    with pytest.raises(ValueError):
        ConversationCreate(title="   ")
    with pytest.raises(ValueError):
        ConversationUpdate(title="   ")
    assert ConversationCreate(title="  题解  ").title == "题解"
    assert ConversationUpdate(title="  题解  ").title == "题解"


def test_bulk_conversation_request_validates_action_and_ids():
    from app.schemas import BulkConversationRequest

    payload = BulkConversationRequest(conversation_ids=[uuid.uuid4()], action="pin")
    assert payload.action == "pin"
    with pytest.raises(ValueError):
        BulkConversationRequest(conversation_ids=[], action="delete")
