import json

import httpx
import pytest

from app.providers.openai_compatible import OpenAICompatibleChatProvider


def install_transport(monkeypatch, handler):
    client_type = httpx.AsyncClient
    monkeypatch.setattr("app.providers.url_validation.socket.getaddrinfo",
                        lambda *_args, **_kwargs: [(2, 1, 6, "", ("93.184.216.34", 443))])
    monkeypatch.setattr(
        "app.providers.openai_compatible.httpx.AsyncClient",
        lambda **kwargs: client_type(transport=httpx.MockTransport(handler), **kwargs),
    )


@pytest.mark.asyncio
async def test_plain_chat_response_verifies_connection_without_tool_probe(monkeypatch):
    requests = []
    def handle(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": "OK"}}]})
    install_transport(monkeypatch, handle)
    result = await OpenAICompatibleChatProvider("https://example.test/v1", "secret").test_model("model")
    assert result.ok is True
    assert result.status == "verified"
    assert result.capabilities == {"chat": "verified"}
    assert len(requests) == 1
    assert "tools" not in requests[0]


@pytest.mark.asyncio
async def test_empty_chat_response_fails_connection_verification(monkeypatch):
    install_transport(monkeypatch, lambda request: httpx.Response(
        200, json={"choices": [{"message": {"role": "assistant", "content": ""}}]},
    ))
    result = await OpenAICompatibleChatProvider("https://example.test/v1", "secret").test_model("model")
    assert result.ok is False
    assert result.status == "failed"
    assert result.capabilities == {"chat": "failed"}


@pytest.mark.asyncio
async def test_rate_limit_is_incomplete_not_unsupported(monkeypatch):
    install_transport(monkeypatch, lambda request: httpx.Response(
        429, json={"error": {"message": "rate limited", "code": "rate_limit"}},
    ))
    result = await OpenAICompatibleChatProvider("https://example.test/v1", "secret").test_model("model")
    assert result.ok is False
    assert result.status == "incomplete"
    assert result.capabilities == {"chat": "unknown"}


@pytest.mark.asyncio
async def test_invalid_credentials_fail_connection_verification(monkeypatch):
    install_transport(monkeypatch, lambda request: httpx.Response(
        401, json={"error": {"message": "invalid key"}},
    ))
    result = await OpenAICompatibleChatProvider("https://example.test/v1", "secret").test_model("model")
    assert result.ok is False
    assert result.status == "failed"
    assert result.capabilities == {"chat": "failed"}


@pytest.mark.asyncio
async def test_provider_without_tools_can_pass_connection_verification(monkeypatch):
    def handle(request):
        if json.loads(request.content).get("tools"):
            return httpx.Response(400, json={"error": {
                "code": "unsupported_parameter", "param": "tools", "message": "tools are unsupported",
            }})
        return httpx.Response(200, json={"choices": [{"message": {"content": "OK"}}]})

    install_transport(monkeypatch, handle)
    result = await OpenAICompatibleChatProvider("https://example.test/v1", "secret").test_model("model")
    assert result.status == "verified"
    assert result.capabilities == {"chat": "verified"}


@pytest.mark.asyncio
@pytest.mark.parametrize("message", [
    {"role": "tool", "content": "wrong role"},
    {"role": "assistant", "content": None},
    {"role": "assistant", "content": {"text": "invalid content"}},
    {"role": "assistant", "tool_calls": {"id": "not a list"}},
    {"role": "assistant", "tool_calls": [{"id": "c", "type": "function", "function": {"name": "search_knowledge", "arguments": {"query": "q"}}}]},
])
async def test_malformed_native_protocol_is_rejected_before_next_model_turn(monkeypatch, message):
    install_transport(monkeypatch, lambda request: httpx.Response(200, json={"choices": [{"message": message}]}))
    with pytest.raises(ValueError):
        await OpenAICompatibleChatProvider("https://example.test/v1", "secret").complete([], "model")
