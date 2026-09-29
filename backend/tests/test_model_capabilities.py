import json

import httpx
import pytest

from app.providers.openai_compatible import OpenAICompatibleChatProvider


def install_transport(monkeypatch, handler):
    client_type = httpx.AsyncClient
    monkeypatch.setattr(
        "app.providers.openai_compatible.httpx.AsyncClient",
        lambda **kwargs: client_type(transport=httpx.MockTransport(handler), **kwargs),
    )


@pytest.mark.asyncio
async def test_plain_text_cannot_pass_tool_capability_verification(monkeypatch):
    install_transport(monkeypatch, lambda request: httpx.Response(
        200, json={"choices": [{"message": {"role": "assistant", "content": "OK"}}]},
    ))
    result = await OpenAICompatibleChatProvider("https://example.test/v1", "secret").test_model("model")
    assert result.ok is False
    assert result.status == "failed"


@pytest.mark.asyncio
async def test_verification_requires_actual_tool_return_round_trip(monkeypatch):
    def handle(request):
        body = json.loads(request.content)
        messages = body["messages"]
        if messages[-1]["role"] == "tool":
            assert messages[-1]["tool_call_id"] == "probe-call"
            value = json.loads(messages[-1]["content"])["value"]
            return httpx.Response(200, json={"choices": [{"message": {"content": value}}]})
        if body.get("tools"):
            name = body["tools"][0]["function"]["name"]
            return httpx.Response(200, json={"choices": [{"message": {
                "role": "assistant", "content": None, "tool_calls": [{
                    "id": "probe-call", "type": "function",
                    "function": {"name": name, "arguments": '{"key":"probe"}'},
                }],
            }}]})
        return httpx.Response(200, json={"choices": [{"message": {"content": "OK"}}]})

    install_transport(monkeypatch, handle)
    result = await OpenAICompatibleChatProvider("https://example.test/v1", "secret").test_model("model")
    assert result.ok is True
    assert result.capabilities["tool_calling"] == "verified"
    assert result.capabilities["tool_result"] == "verified"


@pytest.mark.asyncio
async def test_rate_limit_is_incomplete_not_unsupported(monkeypatch):
    install_transport(monkeypatch, lambda request: httpx.Response(
        429, json={"error": {"message": "rate limited", "code": "rate_limit"}},
    ))
    result = await OpenAICompatibleChatProvider("https://example.test/v1", "secret").test_model("model")
    assert result.ok is False
    assert result.status == "incomplete"
    assert "unsupported" not in result.capabilities.values()


@pytest.mark.asyncio
async def test_explicit_unsupported_tools_is_classified_on_this_connection(monkeypatch):
    def handle(request):
        if json.loads(request.content).get("tools"):
            return httpx.Response(400, json={"error": {
                "code": "unsupported_parameter", "param": "tools", "message": "tools are unsupported",
            }})
        return httpx.Response(200, json={"choices": [{"message": {"content": "OK"}}]})

    install_transport(monkeypatch, handle)
    result = await OpenAICompatibleChatProvider("https://example.test/v1", "secret").test_model("model")
    assert result.status == "unsupported"
    assert result.capabilities["chat"] == "verified"
    assert result.capabilities["tool_calling"] == "unsupported"


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
