import uuid

import pytest


def test_conversation_model_has_pinned_and_message_retrieved_ids():
    from app.models import Conversation, Message

    assert "pinned" in Conversation.__table__.c
    assert "retrieved_chunk_ids" in Message.__table__.c


def test_conversation_update_allows_title_and_pinned_optional():
    from app.schemas import ConversationUpdate

    assert ConversationUpdate(title=" renamed ").title == "renamed"
    assert ConversationUpdate(pinned=True).pinned is True


def test_bulk_conversation_request_validates_action_and_ids():
    from app.schemas import BulkConversationRequest

    payload = BulkConversationRequest(conversation_ids=[uuid.uuid4()], action="pin")
    assert payload.action == "pin"
    with pytest.raises(ValueError):
        BulkConversationRequest(conversation_ids=[], action="delete")
