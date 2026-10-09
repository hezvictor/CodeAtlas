import pytest


@pytest.mark.asyncio
async def test_reranker_returns_document_scores_in_provider_order(monkeypatch):
    monkeypatch.setattr("app.providers.url_validation.socket.getaddrinfo",
                        lambda *_args, **_kwargs: [(2, 1, 6, "", ("93.184.216.34", 80))])
    from app.providers.reranker import RerankerProvider

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"results": [{"index": 1, "relevance_score": 0.9}, {"index": 0, "relevance_score": 0.2}]}

    class Client:
        async def __aenter__(self): return self
        async def __aexit__(self, *_args): return False
        async def post(self, *_args, **_kwargs): return Response()

    import app.providers.reranker as module
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda **_: Client())

    result = await RerankerProvider("http://rerank", "key", "model").rerank("query", ["a", "b"])
    assert result == [(1, 0.9), (0, 0.2)]
