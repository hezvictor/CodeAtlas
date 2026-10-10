from types import SimpleNamespace

import httpx
import pytest


class _Response:
    def __init__(self, status_code: int):
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=httpx.Request("POST", "http://test"), response=httpx.Response(self.status_code))

    def json(self):
        return {"data": [{"index": 0, "embedding": [0.1, 0.2]}]}


class _Client:
    statuses = [429, 200]
    calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False

    async def post(self, *_args, **_kwargs):
        self.calls += 1
        return _Response(self.statuses.pop(0))


@pytest.mark.asyncio
async def test_embedding_retries_429_then_succeeds(monkeypatch):
    import app.providers.embedding as module

    client = _Client()
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda **_: client)
    settings = SimpleNamespace(
        embedding_dimensions=2, embedding_max_retries=1,
        embedding_retry_base_delay_seconds=0, embedding_retry_max_delay_seconds=0,
    )
    assert await module.EmbeddingProvider()._embed_batches(
        ["q"], api_key="key", model="model", base_url="http://embedding", settings=settings,
    ) == [[0.1, 0.2]]
    assert client.calls == 2


@pytest.mark.asyncio
async def test_embedding_documents_batches_inputs_and_preserves_order(monkeypatch):
    import app.providers.embedding as module

    class BatchResponse:
        def raise_for_status(self):
            return None

        def __init__(self, count):
            self.count = count

        def json(self):
            return {"data": [{"index": index, "embedding": [float(index), 1.0]} for index in range(self.count)]}

    class BatchClient(_Client):
        def __init__(self):
            self.batch_sizes = []

        async def post(self, _url, *, headers, json):
            self.batch_sizes.append(len(json["input"]))
            return BatchResponse(len(json["input"]))

    client = BatchClient()
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda **_: client)
    settings = SimpleNamespace(embedding_dimensions=2, embedding_batch_size=2, embedding_max_retries=0)

    vectors = await module.EmbeddingProvider()._embed_batches(
        ["a", "b", "c", "d", "e"], api_key="key", model="model", base_url="http://embedding", settings=settings,
    )

    assert client.batch_sizes == [2, 2, 1]
    assert vectors == [[0.0, 1.0], [1.0, 1.0], [0.0, 1.0], [1.0, 1.0], [0.0, 1.0]]


@pytest.mark.asyncio
async def test_v3_never_exceeds_provider_batch_limit(monkeypatch):
    import app.providers.embedding as module

    sizes = []

    class Client(_Client):
        async def post(self, _url, *, headers, json):
            sizes.append(len(json["input"]))
            if len(json["input"]) > 10:
                return httpx.Response(400, json={"error": {"code": "InvalidParameter", "message": "batch too large"}}, request=httpx.Request("POST", "https://provider/embeddings"))
            return httpx.Response(200, json={"data": [{"index": i, "embedding": [float(value), 1.0]} for i, value in enumerate(json["input"])]}, request=httpx.Request("POST", "https://provider/embeddings"))

    monkeypatch.setattr(module.httpx, "AsyncClient", lambda **_: Client())
    settings = SimpleNamespace(embedding_dimensions=2, embedding_batch_size=16, embedding_max_retries=0)
    assert await module.EmbeddingProvider()._embed_batches(
        [str(i) for i in range(23)], api_key="key", model="text-embedding-v3",
        base_url="https://provider", settings=settings,
    ) == [[float(i), 1.0] for i in range(23)]
    assert sizes == [10, 10, 3]


def test_provider_failure_classification_preserves_safe_code_without_credentials():
    from app.providers.embedding import processing_error

    request = httpx.Request("POST", "https://provider/embeddings", headers={"Authorization": "Bearer secret"})
    error = httpx.HTTPStatusError("bad", request=request, response=httpx.Response(400, json={"error": {"code": "InvalidParameter", "message": "batch size must not exceed 10"}}))
    code, message, retryable = processing_error(error)
    assert code == "EMBEDDING_HTTP_400"
    assert "InvalidParameter" in message
    assert "secret" not in message
    assert retryable is False
    transient = httpx.HTTPStatusError("limited", request=request, response=httpx.Response(429))
    assert processing_error(transient)[2] is True
