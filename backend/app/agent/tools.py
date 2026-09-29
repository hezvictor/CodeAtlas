import asyncio
import json

from httpx import HTTPStatusError, TransportError
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class SearchArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=10)


class ReadArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_id: str = Field(min_length=1, max_length=80)
    radius: int = Field(default=1, ge=0, le=2)


TOOL_TYPES = {"search_knowledge": SearchArguments, "read_knowledge_context": ReadArguments}
TOOL_TITLES = {"search_knowledge": "补充检索知识库", "read_knowledge_context": "补充读取相关段落"}
TOOL_SCHEMAS = [{"type": "function", "function": {"name": name, "description": description,
                  "parameters": model.model_json_schema()}}
                for name, model, description in (
                    ("search_knowledge", SearchArguments, "Search the current user's long-term knowledge for evidence."),
                    ("read_knowledge_context", ReadArguments, "Read nearby text for an evidence ID already returned in this run."),
                )]


async def execute_tool(runtime, call, context):
    function = call.get("function") or {}
    name = function.get("name")
    if name not in TOOL_TYPES or call.get("type") != "function" or not call.get("id"):
        return {"status": "invalid_parameters", "evidence": [], "error": "UNKNOWN_TOOL"}
    try:
        args = TOOL_TYPES[name].model_validate_json(function.get("arguments", ""))
    except (ValidationError, TypeError):
        return {"status": "invalid_parameters", "evidence": [], "error": "INVALID_ARGUMENTS"}
    signature = json.dumps([name, args.model_dump()], sort_keys=True, ensure_ascii=False)
    if signature in context.setdefault("seen_calls", []):
        return {"status": "no_progress", "evidence": [], "error": "REPEATED_CALL"}
    context["seen_calls"].append(signature)
    if name == "read_knowledge_context" and args.evidence_id not in context.get("evidence_ids", []):
        return {"status": "forbidden", "evidence": [], "error": "UNAUTHORIZED_EVIDENCE"}
    if name == "search_knowledge":
        compact = "".join(args.query.split())
        for file in context.get("files", []):
            full = "".join(file["text"].split())
            if full and full in compact:
                return {"status": "invalid_parameters", "evidence": [], "error": "FULL_FILE_IS_NOT_A_SEARCH_QUERY"}
    await runtime.emit("tool.started", {"step_id": call["id"], "tool": name, "title": TOOL_TITLES[name]})
    try:
        async with asyncio.timeout(runtime.tool_timeout):
            for attempt in range(2):
                try:
                    if name == "search_knowledge":
                        result = await runtime.search(args.query, args.limit)
                    else:
                        result = await runtime.read(args.evidence_id, args.radius)
                    break
                except (ConnectionError, TimeoutError, TransportError, HTTPStatusError) as error:
                    transient = not isinstance(error, HTTPStatusError) or error.response.status_code == 429 or error.response.status_code >= 500
                    if attempt or not transient:
                        raise
                    if runtime.reserve_tool:
                        await runtime.reserve_tool()
                    await runtime.emit("tool.retrying", {"step_id": call["id"], "title": TOOL_TITLES[name]})
        context.setdefault("chunks", {}).update(result.pop("_chunks", {}))
        ids = context.setdefault("evidence_ids", [])
        for item in result.get("evidence", []):
            if item["id"] not in ids:
                ids.append(item["id"])
    except TimeoutError:
        result = {"status": "timeout", "evidence": [], "error": "TOOL_TIMEOUT"}
    except Exception:
        result = {"status": "unavailable", "evidence": [], "error": "TOOL_UNAVAILABLE"}
    await runtime.emit("tool.completed", {"step_id": call["id"], "tool": name, "title": TOOL_TITLES[name],
                                           "status": result["status"], "count": len(result.get("evidence", []))})
    return result
