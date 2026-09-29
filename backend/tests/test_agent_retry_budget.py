import json

import httpx
import pytest
from langgraph.checkpoint.memory import InMemorySaver

from app.agent.graph import AgentRuntime, build_graph
from app.config import Settings
from app.providers.chat import ModelTurn
from app.providers.embedding import UserEmbeddingProvider


@pytest.mark.asyncio
async def test_query_embedding_does_not_hide_extra_retries_from_tool_budget(monkeypatch):
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(429, json={"error": {"message": "limited"}})
    client = httpx.AsyncClient
    monkeypatch.setattr("app.providers.embedding.httpx.AsyncClient", lambda **kwargs: client(transport=httpx.MockTransport(handler), **kwargs))
    monkeypatch.setattr("app.providers.embedding.get_settings", lambda: Settings(dashscope_api_key="fake-only"))
    class Session:
        async def scalar(self, _): return None
    with pytest.raises(httpx.HTTPStatusError):
        await UserEmbeddingProvider(Session(), "test-user").embed_query("query")
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_transient_tool_retry_consumes_budget_before_other_calls():
    durable = {"model_calls": 0, "tool_calls": 0, "tool_rounds": 0}
    context = {"messages": [{"role": "user", "content": "q"}]}
    async def load(): return context
    async def save(value): context.update(value)
    async def emit(*args): pass
    async def counts(): return durable.copy()
    def reserve(key, maximum):
        async def increment():
            assert durable[key] < maximum
            durable[key] += 1
            return durable[key]
        return increment
    queries = []
    async def search(query, limit):
        queries.append(query)
        if len(queries) == 1: raise httpx.ConnectError("transient")
        return {"status": "no_hit", "evidence": []}
    class Provider:
        async def complete(self, messages, model, **kwargs):
            if not any(m["role"] == "tool" for m in messages):
                return ModelTurn({"role": "assistant", "tool_calls": [{"id": str(i), "type": "function",
                    "function": {"name": "search_knowledge", "arguments": json.dumps({"query": str(i)})}} for i in range(3)]})
            results = [json.loads(m["content"])["status"] for m in messages if m["role"] == "tool"]
            assert results == ["no_hit", "budget_exceeded", "budget_exceeded"]
            return ModelTurn({"role": "assistant", "content": "Insufficient evidence"})
    runtime = AgentRuntime(Provider(), "m", load, save, emit, search, search, max_tools=2,
        counts=counts, reserve_model=reserve("model_calls", 4), reserve_tool=reserve("tool_calls", 2), reserve_round=reserve("tool_rounds", 2))
    await build_graph(InMemorySaver()).ainvoke(durable.copy(), {"configurable": {"thread_id": "retry"}}, context=runtime)
    assert durable["tool_calls"] == 2 and queries == ["0", "0"]
    assert context["answer"] == "Insufficient evidence"
