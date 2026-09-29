from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
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
async def test_ordinary_verified_model_cannot_bypass_agent_admission():
    from app.routers.conversations import resolve_chat_model

    model = SimpleNamespace(status="verified", capabilities={})
    class Session:
        async def execute(self, statement):
            return SimpleNamespace(first=lambda: (model, SimpleNamespace()))
    with pytest.raises(HTTPException):
        await resolve_chat_model(Session(), SimpleNamespace(selected_chat_model_id=None), uuid4(), uuid4())
