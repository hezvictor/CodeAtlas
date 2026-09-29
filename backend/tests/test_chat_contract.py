import pytest
from pydantic import ValidationError

from app.schemas import ChatRequest, MessageResponse, RetryRequest


def test_message_content_is_nonempty_and_normalized():
    with pytest.raises(ValidationError): ChatRequest(content=" \n ")
    assert ChatRequest(content=" q ").content == "q"


def test_messages_keep_metrics_and_retry_contract():
    assert {"duration_ms", "first_token_latency_ms"}.issubset(MessageResponse.model_fields)
    assert RetryRequest(content="edited").content == "edited"
    assert ChatRequest(content="q", reuse_last_user=True).reuse_last_user
