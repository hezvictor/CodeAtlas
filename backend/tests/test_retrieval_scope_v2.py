
import pytest


def test_chat_request_defaults_to_no_knowledge_retrieval():
    from app.schemas import ChatRequest

    assert ChatRequest(content="q").knowledge_scope == "none"


def test_chat_request_does_not_expose_group_filtering():
    from app.schemas import ChatRequest

    assert "knowledge_group_ids" not in ChatRequest.model_fields


def test_chat_request_rejects_legacy_groups_scope():
    from pydantic import ValidationError

    from app.schemas import ChatRequest

    with pytest.raises(ValidationError):
        ChatRequest(content="q", knowledge_scope="groups")


def test_acm_analysis_does_not_require_problem_or_language():
    from app.services.problem_context import validate_chat_context

    validate_chat_context("acm_analysis", None, None)


def test_upload_policy_exposes_supported_extensions_and_size():
    from app.routers.knowledge_documents import upload_policy

    policy = upload_policy()
    assert ".pdf" not in policy["extensions"]
    assert policy["max_size_bytes"] > 0
