import asyncio

import httpx


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

def test_openai_compatible_provider_discovers_and_tests_models(monkeypatch):
    from app.providers.openai_compatible import OpenAICompatibleChatProvider

    monkeypatch.setattr("app.providers.url_validation.socket.getaddrinfo",
                        lambda *_args, **_kwargs: [(2, 1, 6, "", ("93.184.216.34", 443))])

    client = _AsyncClient()
    monkeypatch.setattr("app.providers.openai_compatible.httpx.AsyncClient", lambda **_: client)
    provider = OpenAICompatibleChatProvider("https://provider.example/v1", "secret")

    async def run():
        return await provider.list_models(), await provider.test_model("model-a")

    candidates, result = asyncio.run(run())

    assert [item.name for item in candidates] == ["model-a", "model-b"]
    assert result.ok is True
    assert result.capabilities == {"chat": "verified"}
    assert client.requests[0][1].endswith("/models")
    assert client.requests[0][1].startswith("https://93.184.216.34/")
    assert client.requests[0][2]["headers"]["Host"] == "provider.example"
    assert client.requests[0][2]["extensions"]["sni_hostname"] == "provider.example"
    assert client.requests[1][2]["headers"]["Authorization"] == "Bearer secret"
    assert len(client.requests) == 2
    assert "tools" not in client.requests[1][2]["json"]
