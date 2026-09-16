import uuid

import pytest


def test_chat_request_defaults_to_none_but_infers_groups_for_legacy_payload():
    from app.schemas import ChatRequest

    assert ChatRequest(content="q").knowledge_scope == "none"
    gid = uuid.uuid4()
    request = ChatRequest(content="q", knowledge_group_ids=[gid])
    assert request.knowledge_scope == "groups"


def test_chat_request_rejects_groups_scope_without_groups():
    from app.schemas import ChatRequest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ChatRequest(content="q", knowledge_scope="groups")


def test_upload_policy_exposes_supported_extensions_and_size():
    from app.routers.knowledge_documents import upload_policy

    policy = upload_policy()
    assert ".pdf" in policy["extensions"]
    assert policy["max_size_bytes"] > 0
