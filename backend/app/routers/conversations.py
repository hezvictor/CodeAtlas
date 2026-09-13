import asyncio
import json
import logging
import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from ..config import get_settings
from ..db import get_session, session_factory
from ..dependencies import current_user_id
from ..models import Citation, Conversation, Message
from ..chat_rag import build_context_prompt
from ..citations import persist_citations
from ..acm_workflow import build_acm_prompt, sanitize_analysis_output
from ..code_validation import extract_solution_code, validate_solution_code
from ..services.problem_context import format_problem_context, message_context_metadata, resolve_problem_context, validate_chat_context
from ..services.retrieval_service import retrieve_chunks
from ..services.context_budget import trim_history, trim_retrieved_chunks
from ..services.run_state import RunLease, RunState
from ..schemas import ChatRequest, ConversationCreate, ConversationResponse, ConversationUpdate, MessagePage, MessageResponse, RetryRequest

router = APIRouter(prefix="/conversations", tags=["conversations"])
logger = logging.getLogger(__name__)
@dataclass
class RunHandle:
    stop_event: asyncio.Event = field(default_factory=asyncio.Event)
    last_activity: datetime = field(default_factory=lambda: datetime.now(UTC))
    lease: RunLease | None = None


class RunRegistry:
    def __init__(self, ttl_seconds: int = 900, state: RunState | None = None):
        self.ttl_seconds = ttl_seconds
        self.state = state
        self._runs: dict[str, tuple[asyncio.Lock, RunHandle]] = {}
        self._guard = asyncio.Lock()

    async def acquire(self, cid: str) -> RunHandle:
        if self.state:
            lease = await self.state.acquire(cid)
            handle = RunHandle(lease=lease)
            async with self._guard:
                self._runs[cid] = (asyncio.Lock(), handle)
                await self._runs[cid][0].acquire()
            return handle
        async with self._guard:
            lock, handle = self._runs.setdefault(cid, (asyncio.Lock(), RunHandle()))
            if lock.locked():
                raise HTTPException(409, "A response is already being generated")
            await lock.acquire()
            handle.last_activity = datetime.now(UTC)
            return handle

    async def release(self, cid: str, handle: RunHandle) -> None:
        if handle.lease:
            await handle.lease.release()
        async with self._guard:
            entry = self._runs.get(cid)
            if entry and entry[1] is handle:
                if entry[0].locked():
                    entry[0].release()
                self._runs.pop(cid, None)

    def get_stop_event(self, cid: str) -> asyncio.Event | None:
        entry = self._runs.get(cid)
        return entry[1].stop_event if entry else None

    def is_running(self, cid: str) -> bool:
        entry = self._runs.get(cid)
        return bool(entry and entry[0].locked())

    async def cleanup(self) -> None:
        cutoff = datetime.now(UTC).timestamp() - self.ttl_seconds
        async with self._guard:
            for cid, (lock, handle) in list(self._runs.items()):
                if lock.locked() and handle.last_activity.timestamp() < cutoff:
                    handle.stop_event.set()


runs = RunRegistry()


def configure_run_state(redis) -> None:
    runs.state = RunState(redis)

async def conversation(cid: UUID, uid: UUID, session: AsyncSession):
    item = await session.scalar(select(Conversation).where(Conversation.id == cid, Conversation.user_id == uid))
    if not item: raise HTTPException(404, "Conversation not found")
    return item

def event(name: str, data: dict) -> str: return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

@router.get("", response_model=list[ConversationResponse])
async def list_conversations(uid=Depends(current_user_id), session=Depends(get_session)):
    return (await session.scalars(select(Conversation).where(Conversation.user_id == uid).order_by(Conversation.updated_at.desc()))).all()

@router.post("", response_model=ConversationResponse, status_code=201)
async def create_conversation(payload: ConversationCreate, uid=Depends(current_user_id), session=Depends(get_session)):
    item = Conversation(user_id=uid, title=payload.title.strip(), mode=payload.mode); session.add(item); await session.commit(); await session.refresh(item); return item

@router.get("/{cid}", response_model=ConversationResponse)
async def get_conversation(cid, uid=Depends(current_user_id), session=Depends(get_session)): return await conversation(cid, uid, session)

@router.patch("/{cid}", response_model=ConversationResponse)
async def update_conversation(cid, payload: ConversationUpdate, uid=Depends(current_user_id), session=Depends(get_session)):
    item = await conversation(cid, uid, session); item.title = payload.title.strip(); await session.commit(); await session.refresh(item); return item

@router.delete("/{cid}", status_code=204)
async def delete_conversation(cid, uid=Depends(current_user_id), session=Depends(get_session)):
    item = await conversation(cid, uid, session); await session.delete(item); await session.commit()

@router.get("/{cid}/messages", response_model=MessagePage)
async def messages(cid, limit: int = 30, before: datetime | None = None, uid=Depends(current_user_id), session=Depends(get_session)):
    await conversation(cid, uid, session)
    limit = max(1, min(limit, 100))
    query = select(Message).where(Message.conversation_id == cid)
    if before:
        query = query.where(Message.created_at < before)
    rows = list((await session.scalars(query.order_by(Message.created_at.desc()).limit(limit + 1))).all())
    has_more = len(rows) > limit
    items = list(reversed(rows[:limit]))
    return MessagePage(items=items, has_more=has_more, next_before=items[0].created_at if has_more else None)

@router.post("/{cid}/messages/{mid}/retry")
async def retry_message(cid: UUID, mid: UUID, payload: RetryRequest, uid=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    await conversation(cid, uid, session)
    target = await session.scalar(select(Message).where(Message.id == mid, Message.conversation_id == cid))
    if not target: raise HTTPException(404, "Message not found")
    content = payload.content.strip() if payload.content else target.content
    if target.role == "user":
        target.content = content
        await session.execute(Message.__table__.delete().where(Message.conversation_id == cid, Message.created_at > target.created_at))
        context_message = target
    elif target.role == "assistant":
        previous = await session.scalar(select(Message).where(Message.conversation_id == cid, Message.created_at < target.created_at).order_by(Message.created_at.desc()))
        if not previous or previous.role != "user": raise HTTPException(400, "Assistant message has no user prompt")
        content = previous.content
        await session.delete(target)
        context_message = previous
    else: raise HTTPException(400, "Only user or assistant messages can be retried")
    await session.commit()
    return {"content": content, **message_context_metadata(context_message)}

async def model_stream(prompt: str, history: list[dict], stop_event: asyncio.Event) -> AsyncGenerator[str, None]:
    settings = get_settings()
    if not settings.dashscope_api_key or not settings.chat_model: raise RuntimeError("chat provider is not configured")
    body = {"model": settings.chat_model, "messages": history + [{"role": "user", "content": prompt}], "stream": True}
    async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=10)) as client:
        async with client.stream("POST", settings.dashscope_base_url.rstrip("/") + "/chat/completions", headers={"Authorization": f"Bearer {settings.dashscope_api_key}"}, json=body) as response:
            response.raise_for_status()
            lines = response.aiter_lines().__aiter__()
            while not stop_event.is_set():
                next_line = asyncio.create_task(lines.__anext__())
                stopped = asyncio.create_task(stop_event.wait())
                done, pending = await asyncio.wait({next_line, stopped}, return_when=asyncio.FIRST_COMPLETED)
                for task in pending: task.cancel()
                if stopped in done:
                    await response.aclose()
                    break
                try: line = next_line.result()
                except StopAsyncIteration: break
                if line.startswith("data: ") and line[6:] != "[DONE]":
                    choices = (json.loads(line[6:]).get("choices") or [])
                    if choices:
                        delta = (choices[0].get("delta") or {}).get("content") or ""
                        if isinstance(delta, list): delta = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in delta)
                        if delta: yield delta

@router.post("/{cid}/messages/stream")
async def stream(cid: UUID, payload: ChatRequest, request: Request, uid=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    await conversation(cid, uid, session)
    try:
        validate_chat_context(payload.mode, payload.problem_id, payload.solution_language)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    problem = await resolve_problem_context(session, payload.problem_id, uid)
    handle = await runs.acquire(str(cid))
    started = time.monotonic(); first_token_ms = None
    retrieved = []
    retrieval_error = None
    retrieval_requested = bool(payload.knowledge_group_ids or payload.attachment_ids)
    try:
        if payload.reuse_last_user:
            user = await session.scalar(select(Message).where(Message.conversation_id == cid, Message.role == "user").order_by(Message.created_at.desc()).limit(1))
            if not user:
                raise HTTPException(400, "No user message available to retry")
            if user.content != payload.content:
                user.content = payload.content
            user.problem_id = problem.id if problem else None
            user.mode = payload.mode
            user.solution_language = payload.solution_language
            await session.commit()
        else:
            user = Message(
                conversation_id=cid,
                role="user",
                content=payload.content,
                status="completed",
                problem_id=problem.id if problem else None,
                mode=payload.mode,
                solution_language=payload.solution_language,
            )
            session.add(user); await session.commit()
        rows = (await session.scalars(select(Message).where(Message.conversation_id == cid, Message.id != user.id).order_by(Message.created_at))).all()
        history = trim_history(
            [{"role": m.role, "content": m.content} for m in rows],
            getattr(get_settings(), "chat_history_max_chars", 60_000),
            getattr(get_settings(), "chat_history_max_messages", 30),
        )
        try:
            retrieved = await retrieve_chunks(session, uid, cid, payload.content, payload.knowledge_group_ids, payload.attachment_ids)
            retrieved = trim_retrieved_chunks(retrieved, getattr(get_settings(), "rag_context_max_chars", 40_000), 10)
        except Exception as error:
            logger.exception("retrieval failed", extra={"conversation_id": str(cid), "user_id": str(uid)})
            retrieval_error = error
            retrieved = []
        await session.close()
    except Exception:
        await session.rollback(); await runs.release(str(cid), handle); raise

    async def generate():
        answer = ""
        first_token_ms = None
        try:
            yield event("run.started", {"conversation_id": str(cid)})
            if retrieval_error:
                yield event("retrieval.failed", {"code": "RETRIEVAL_FAILED", "message": "知识库检索失败，请稍后重试"})
                if retrieval_requested:
                    async with session_factory() as save_session:
                        save_session.add(Message(conversation_id=cid, role="assistant", content="", status="failed", model=get_settings().chat_model, duration_ms=round((time.monotonic() - started) * 1000), problem_id=problem.id if problem else None, mode=payload.mode, solution_language=payload.solution_language))
                        await save_session.commit()
                    yield event("run.failed", {"code": "RETRIEVAL_FAILED", "message": "知识库检索失败，请稍后重试"})
                    return
            yield event("context.resolved", {
                "mode": payload.mode,
                "problem": {"id": str(problem.id), "title": problem.title, "tags": problem.tags} if problem else None,
                "knowledge_requested": retrieval_requested,
            })
            yield event("retrieval.completed", {"status": "failed" if retrieval_error else "ok", "count": len(retrieved), "items": [{"chunk_id": str(item.chunk_id), "score": item.score, "locator": item.locator or {}} for item in retrieved]})
            knowledge_context = "\n\n".join(
                f"来源切片：{item.chunk_id}\n{item.content}" for item in retrieved
            )
            if payload.mode == "normal":
                base_prompt = payload.content
                if problem:
                    base_prompt = f"{format_problem_context(problem)}\n\n用户问题：{payload.content}"
                prompt = build_context_prompt(base_prompt, retrieved)
            else:
                prompt = build_acm_prompt(problem, payload.content, payload.mode, payload.solution_language, knowledge_context)
            async for delta in model_stream(prompt, history, handle.stop_event):
                if await request.is_disconnected(): handle.stop_event.set(); break
                if handle.lease:
                    if not await handle.lease.refresh() or await handle.lease.stop_requested():
                        handle.stop_event.set()
                        break
                handle.last_activity = datetime.now(UTC)
                answer += delta
                if first_token_ms is None:
                    first_token_ms = round((time.monotonic() - started) * 1000)
                    yield event("run.first_token", {"latency_ms": first_token_ms})
                yield event("message.delta", {"content": delta}); yield event("ping", {})
            if answer:
                async with session_factory() as save_session:
                    cleaned_answer = sanitize_analysis_output(answer) if payload.mode == "acm_analysis" else answer
                    assistant = Message(conversation_id=cid, role="assistant", content=cleaned_answer, status="cancelled" if handle.stop_event.is_set() else "completed", model=get_settings().chat_model, duration_ms=round((time.monotonic() - started) * 1000), first_token_latency_ms=first_token_ms, problem_id=problem.id if problem else None, mode=payload.mode, solution_language=payload.solution_language)
                    save_session.add(assistant)
                    await save_session.flush()
                    cleaned, citations = await persist_citations(save_session, assistant.id, cleaned_answer, retrieved)
                    assistant.content = cleaned
                    await save_session.execute(Conversation.__table__.update().where(Conversation.id == cid).values(updated_at=func.now()))
                    await save_session.commit()
                    yield event("citations.validated", {"items": [{"chunk_id": str(c.chunk_id), "quote": c.quote, "score": c.score, "locator": c.locator} for c in citations]})
                    if payload.mode == "acm_solution":
                        code = extract_solution_code(cleaned)
                        if code:
                            yield event("solution.validated", validate_solution_code(payload.solution_language or "", code))
                    yield event("message.final", {"content": cleaned, "message_id": str(assistant.id), "mode": payload.mode, "problem_id": str(problem.id) if problem else None, "solution_language": payload.solution_language})
            yield event("run.interrupted" if handle.stop_event.is_set() else "run.completed", {})
        except asyncio.CancelledError:
            handle.stop_event.set(); raise
        except Exception:
            logger.exception("chat stream failed", extra={"conversation_id": str(cid), "user_id": str(uid), "prompt_length": len(payload.content), "duration_ms": round((time.monotonic() - started) * 1000)})
            async with session_factory() as save_session:
                save_session.add(Message(conversation_id=cid, role="assistant", content="", status="failed", model=get_settings().chat_model, duration_ms=round((time.monotonic() - started) * 1000), first_token_latency_ms=first_token_ms, problem_id=problem.id if problem else None, mode=payload.mode, solution_language=payload.solution_language))
                await save_session.commit()
            yield event("run.failed", {"code": "CHAT_PROVIDER_ERROR", "message": "生成回答失败，请稍后重试"})
        finally:
            await runs.release(str(cid), handle)
    return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@router.post("/{cid}/run/stop", status_code=202)
async def stop(cid, uid=Depends(current_user_id), session=Depends(get_session)):
    await conversation(cid, uid, session)
    if signal := runs.get_stop_event(str(cid)): signal.set()
    if runs.state:
        await runs.state.request_stop(str(cid))
    return {"status": "stopping"}

@router.post("/{cid}/run/resume", status_code=202)
async def resume(cid, uid=Depends(current_user_id), session=Depends(get_session)):
    await conversation(cid, uid, session); return {"status": "ready", "message": "Send the next request to resume from persisted messages"}


@router.get("/{cid}/messages/{mid}/citations")
async def message_citations(cid: UUID, mid: UUID, uid=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    await conversation(cid, uid, session)
    rows = (await session.scalars(select(Citation).join(Message, Citation.message_id == Message.id).where(Message.id == mid, Message.conversation_id == cid, Citation.is_valid.is_(True)).order_by(Citation.rank))).all()
    return [{"id": str(row.id), "chunk_id": str(row.chunk_id), "quote": row.quote, "score": row.score, "rank": row.rank, "locator": row.locator} for row in rows]
