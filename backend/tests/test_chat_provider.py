import asyncio
import json

import httpx
import pytest


class _AsyncClient:
    def __init__(self, **_kwargs):
        self.requests = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False

    async def get(self, url, **kwargs):
        self.requests.append(("GET", url, kwargs))
        return httpx.Response(200, request=httpx.Request("GET", url), json={"data": [{"id": "model-a"}, {"id": "model-b"}]})

    async def post(self, url, **kwargs):
        self.requests.append(("POST", url, kwargs))
        return httpx.Response(200, request=httpx.Request("POST", url), json={"choices": [{"message": {"content": "ok"}}]})

    def stream(self, method, url, **kwargs):
        request = httpx.Request(method, url)
        chunks = [
            f"data: {json.dumps({'choices': [{'delta': {'content': 'hello'}}]})}\n\n",
            f"data: {json.dumps({'choices': [{'delta': {'content': ' world'}}]})}\n\n",
            "data: [DONE]\n\n",
        ]
        return httpx.MockTransport(lambda _request: httpx.Response(200, text="".join(chunks)))


def test_openai_compatible_provider_discovers_and_tests_models(monkeypatch):
    from app.providers.openai_compatible import OpenAICompatibleChatProvider

    client = _AsyncClient()
    monkeypatch.setattr("app.providers.openai_compatible.httpx.AsyncClient", lambda **_: client)
    provider = OpenAICompatibleChatProvider("https://provider.example/v1", "secret")

    async def run():
        return await provider.list_models(), await provider.test_model("model-a")

    candidates, result = asyncio.run(run())

    assert [item.name for item in candidates] == ["model-a", "model-b"]
    assert result.ok is True
    assert client.requests[0][1].endswith("/models")
    assert client.requests[1][2]["headers"]["Authorization"] == "Bearer secret"


def test_openai_compatible_provider_streams_text_deltas(monkeypatch):
    from app.providers.openai_compatible import OpenAICompatibleChatProvider

    class StreamResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        async def aiter_lines(self):
            yield 'data: {"choices":[{"delta":{"content":"hello"}}]}'
            yield 'data: {"choices":[{"delta":{"content":" world"}}]}'
            yield "data: [DONE]"

    class StreamContext:
        async def __aenter__(self):
            return StreamResponse()

        async def __aexit__(self, *_exc):
            return False

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_exc):
            return False

        def stream(self, *_args, **_kwargs):
            return StreamContext()

    monkeypatch.setattr("app.providers.openai_compatible.httpx.AsyncClient", lambda **_: Client())
    provider = OpenAICompatibleChatProvider("https://provider.example/v1", "secret")
    stop_event = asyncio.Event()

    async def run():
        return [delta async for delta in provider.stream_chat([{"role": "user", "content": "hi"}], "model-a", stop_event)]

    result = asyncio.run(run())

    assert result == ["hello", " world"]
