import uuid

import pytest


def test_chat_request_defaults_to_all_long_term_documents():
    from app.schemas import ChatRequest

    assert ChatRequest(content="q").knowledge_scope == "all"


def test_chat_request_ignores_legacy_group_ids_and_uses_all_long_term_documents():
    from app.schemas import ChatRequest

    gid = uuid.uuid4()
    request = ChatRequest(content="q", knowledge_group_ids=[gid])
    assert request.knowledge_scope == "all"


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
