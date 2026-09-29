import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from langsmith import tracing_context

from .budget import check_context_capacity
from .tools import TOOL_SCHEMAS, execute_tool


class ControlState(TypedDict, total=False):
    model_calls: int
    tool_calls: int
    tool_rounds: int
    has_tools: bool
    done: bool


@dataclass
class AgentRuntime:
    provider: object
    model: str
    load: Callable[[], Awaitable[dict]]
    save: Callable[[dict], Awaitable[None]]
    emit: Callable[[str, dict], Awaitable[None]]
    search: Callable[[str, int], Awaitable[dict]]
    read: Callable[[str, int], Awaitable[dict]]
    capacity: int | None = None
    stop_event: asyncio.Event = field(default_factory=asyncio.Event)
    max_models: int = 4
    max_tools: int = 4
    max_rounds: int = 2
    tool_timeout: int = 15
    reserve_model: Callable[[], Awaitable[int]] | None = None
    reserve_tool: Callable[[], Awaitable[int]] | None = None
    reserve_round: Callable[[], Awaitable[int]] | None = None
    counts: Callable[[], Awaitable[dict]] | None = None


async def model_node(state: ControlState, runtime: Runtime[AgentRuntime]):
    ctx = runtime.context
    if ctx.stop_event.is_set():
        raise asyncio.CancelledError
    context = await ctx.load()
    if ctx.counts:
        state = {**state, **await ctx.counts()}
    if state.get("model_calls", 0) >= ctx.max_models:
        context["answer"] = "已达到本次运行预算，现有资料不足以继续处理。"
        await ctx.save(context)
        return {"done": True, "has_tools": False}
    offer_tools = (state.get("tool_rounds", 0) < ctx.max_rounds
                   and state.get("tool_calls", 0) < ctx.max_tools
                   and state.get("model_calls", 0) < ctx.max_models - 1)
    tools = TOOL_SCHEMAS if offer_tools else []
    check_context_capacity(context["messages"], tools, ctx.capacity,
                           requires_full_text=bool(context.get("files")))
    calls = state.get("model_calls", 0)
    try:
        # Never export prompts or node arguments through external tracing.
        for attempt in range(2):
            calls = await ctx.reserve_model() if ctx.reserve_model else calls + 1
            await ctx.emit("model.started", {"step_id": f"model-{calls}", "title": "整理回答"})
            try:
                with tracing_context(enabled=False):
                    turn = await ctx.provider.complete(context["messages"], ctx.model,
                                                       tools=tools or None, stop_event=ctx.stop_event)
                break
            except Exception as error:
                from httpx import HTTPStatusError, TransportError
                transient = isinstance(error, (TransportError, TimeoutError, ConnectionError)) or (
                    isinstance(error, HTTPStatusError) and (error.response.status_code == 429 or error.response.status_code >= 500))
                if attempt or not transient or calls >= ctx.max_models:
                    raise
                # Last request must complete the answer, with no further tool round.
                if calls >= ctx.max_models - 1:
                    tools, offer_tools = [], False
                await ctx.emit("model.retrying", {"step_id": f"model-{calls}", "title": "重试模型请求"})
    except asyncio.CancelledError:
        raise
    except Exception:
        raise RuntimeError("MODEL_REQUEST_FAILED") from None
    if turn.tool_calls and not offer_tools:
        raise RuntimeError("MODEL_TOOL_PROTOCOL_ERROR")
    context["messages"].append(turn.message)
    context["pending_calls"] = turn.tool_calls
    if not turn.tool_calls:
        context["answer"] = str(turn.message.get("content") or "")
    await ctx.save(context)
    await ctx.emit("model.completed", {"step_id": f"model-{calls}", "title": "整理回答", "status": "ok"})
    return {"model_calls": calls, "has_tools": bool(turn.tool_calls), "done": not turn.tool_calls}


async def tools_node(state: ControlState, runtime: Runtime[AgentRuntime]):
    ctx = runtime.context
    context = await ctx.load()
    if ctx.counts:
        state = {**state, **await ctx.counts()}
    count = state.get("tool_calls", 0)
    rounds = await ctx.reserve_round() if ctx.reserve_round else state.get("tool_rounds", 0) + 1
    for call in context.get("pending_calls", []):
        if ctx.stop_event.is_set():
            raise asyncio.CancelledError
        if ctx.counts: count = (await ctx.counts())["tool_calls"]
        if count >= ctx.max_tools:
            result = {"status": "budget_exceeded", "evidence": []}
        else:
            count = await ctx.reserve_tool() if ctx.reserve_tool else count + 1
            result = await execute_tool(ctx, call, context)
        context["messages"].append({"role": "tool", "tool_call_id": call.get("id", "invalid"),
                                    "content": json.dumps(result, ensure_ascii=False)})
    context["pending_calls"] = []
    await ctx.save(context)
    if ctx.counts: count = (await ctx.counts())["tool_calls"]
    return {"tool_calls": count, "tool_rounds": rounds, "has_tools": False}


def build_graph(checkpointer):
    graph = StateGraph(ControlState, context_schema=AgentRuntime)
    graph.add_node("model", model_node)
    graph.add_node("tools", tools_node)
    graph.add_edge(START, "model")
    graph.add_conditional_edges("model", lambda state: "tools" if state.get("has_tools") else END)
    graph.add_edge("tools", "model")
    return graph.compile(checkpointer=checkpointer)
