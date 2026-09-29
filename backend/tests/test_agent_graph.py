import json

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from app.providers.chat import ModelTurn


@pytest.mark.asyncio
async def test_tool_observation_returns_to_model_without_entering_checkpoint():
    from app.agent.graph import AgentRuntime, build_graph

    transcript = {"messages": [{"role": "user", "content": "PRIVATE FULL TEXT"}], "seen_calls": []}
    async def load():
        return transcript
    async def save(value):
        transcript.update(value)
    events = []
    async def emit(name, data):
        events.append((name, data))
    async def search(query, limit):
        return {"status": "ok", "evidence": [{"id": "e1", "content": "TOOL OBSERVATION"}]}
    async def read(identifier, radius):
        return {"status": "forbidden", "evidence": []}
    turns = []
    class Provider:
        async def complete(self, messages, model, **kwargs):
            turns.append(list(messages))
            if len(turns) == 1:
                return ModelTurn({"role": "assistant", "content": None, "tool_calls": [{
                    "id": "call-1", "type": "function", "function": {
                        "name": "search_knowledge", "arguments": '{"query":"PRIVATE FULL TEXT","limit":3}',
                    },
                }]})
            assert messages[-1]["role"] == "tool"
            assert messages[-1]["tool_call_id"] == "call-1"
            assert "TOOL OBSERVATION" in messages[-1]["content"]
            return ModelTurn({"role": "assistant", "content": "Grounded answer"})
    saver = InMemorySaver()
    runtime = AgentRuntime(Provider(), "m", load, save, emit, search, read)
    graph = build_graph(saver)
    config = {"configurable": {"thread_id": "r"}}
    await graph.ainvoke({"model_calls": 0, "tool_calls": 0, "tool_rounds": 0}, config, context=runtime)
    snapshots = [snapshot async for snapshot in graph.aget_state_history(config)]
    assert "PRIVATE FULL TEXT" not in json.dumps([s.values for s in snapshots])
    assert transcript["answer"] == "Grounded answer"
    assert [name for name, _ in events].count("tool.started") == 1
    assert [name for name, _ in events].count("tool.completed") == 1


@pytest.mark.asyncio
async def test_invalid_and_repeated_tools_are_bounded():
    from app.agent.graph import AgentRuntime, build_graph

    transcript = {"messages": [{"role": "user", "content": "q"}], "seen_calls": []}
    async def load():
        return transcript
    async def save(value):
        transcript.update(value)
    async def emit(*args):
        pass
    async def forbidden(*args):
        raise AssertionError("unknown tools must never execute")
    calls = []
    class Provider:
        async def complete(self, messages, model, **kwargs):
            calls.append(kwargs.get("tools"))
            if kwargs.get("tools"):
                return ModelTurn({"role": "assistant", "tool_calls": [{"id": str(len(calls)), "type": "function",
                    "function": {"name": "execute_code", "arguments": "{}"}}]})
            return ModelTurn({"role": "assistant", "content": "Insufficient evidence"})
    runtime = AgentRuntime(Provider(), "m", load, save, emit, forbidden, forbidden)
    state = await build_graph(InMemorySaver()).ainvoke(
        {"model_calls": 0, "tool_calls": 0, "tool_rounds": 0},
        {"configurable": {"thread_id": "bounded"}}, context=runtime,
    )
    assert len(calls) <= 4
    assert state["tool_calls"] <= 4
    assert transcript["answer"] == "Insufficient evidence"
