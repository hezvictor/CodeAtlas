from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas import ChatRequest, ConversationCreate


@pytest.mark.parametrize("field,value", [("knowledge_scope", "none"), ("attachment_ids", [])])
def test_chat_rejects_removed_controls(field, value):
    with pytest.raises(ValidationError):
        ChatRequest(content="q", **{field: value})


def test_conversation_rejects_removed_control():
    with pytest.raises(ValidationError):
        ConversationCreate(knowledge_scope="all")


@pytest.mark.asyncio
async def test_chat_verified_model_can_be_used_without_tool_capability():
    from app.routers.conversations import resolve_chat_model

    model = SimpleNamespace(status="verified", capabilities={"chat": "verified"})
    connection = SimpleNamespace()
    class Session:
        async def execute(self, statement):
            return SimpleNamespace(first=lambda: (model, connection))
    assert await resolve_chat_model(Session(), SimpleNamespace(selected_chat_model_id=None), uuid4(), uuid4()) == (model, connection)
