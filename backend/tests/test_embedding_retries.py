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
    monkeypatch.setattr(module, "get_settings", lambda: SimpleNamespace(
        dashscope_api_key="key", embedding_model="model", embedding_dimensions=2,
        dashscope_base_url="http://embedding", embedding_max_retries=1,
        embedding_retry_base_delay_seconds=0, embedding_retry_max_delay_seconds=0,
    ))
    assert await module.EmbeddingProvider().embed_query("q") == [0.1, 0.2]
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
    monkeypatch.setattr(module, "get_settings", lambda: SimpleNamespace(
        dashscope_api_key="key", embedding_model="model", embedding_dimensions=2,
        embedding_batch_size=2, embedding_max_retries=0,
        dashscope_base_url="http://embedding",
    ))

    vectors = await module.EmbeddingProvider().embed_documents(["a", "b", "c", "d", "e"])

    assert client.batch_sizes == [2, 2, 1]
    assert vectors == [[0.0, 1.0], [1.0, 1.0], [0.0, 1.0], [1.0, 1.0], [0.0, 1.0]]
