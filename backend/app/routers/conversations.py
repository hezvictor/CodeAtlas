import asyncio
import json
import logging
import time
from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import delete as sql_delete, func, select, update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession
from ..config import get_settings
from ..db import get_session, session_factory
from ..dependencies import current_user_id
from ..models import ChatModel, Citation, Conversation, EmbeddingConfig, Message, ModelConnection, User
from ..chat_rag import build_context_prompt
from ..citations import citation_sources, persist_citations
from ..acm_workflow import build_acm_prompt, sanitize_analysis_output
from ..code_validation import extract_solution_code, validate_solution_code
from ..services.problem_context import format_problem_context, message_context_metadata, resolve_problem_context, validate_chat_context
from ..services.retrieval_service import retrieve_chunks
from ..services.context_budget import trim_history, trim_retrieved_chunks
from ..services.run_state import RunLease, RunState
from ..schemas import BulkConversationRequest, ChatRequest, ConversationCreate, ConversationResponse, ConversationUpdate, MessagePage, MessageResponse, RetryRequest
from ..providers.openai_compatible import OpenAICompatibleChatProvider
from ..providers.embedding import UserEmbeddingProvider
from ..security.provider_credentials import decrypt_secret

router = APIRouter(prefix="/conversations", tags=["conversations"])
logger = logging.getLogger(__name__)
@dataclass
class RunHandle:
    stop_event: asyncio.Event = field(default_factory=asyncio.Event)
    last_activity: datetime = field(default_factory=lambda: datetime.now(UTC))
    lease: RunLease | None = None
    run_id: str = field(default_factory=lambda: str(UUID(int=0)))


@dataclass
class RunRecord:
    run_id: str
    conversation_id: str
    handle: RunHandle
    status: str = "generating"
    content: str = ""
    message_id: str | None = None
    events: list[tuple[str, dict]] = field(default_factory=list)
    subscribers: set[asyncio.Queue] = field(default_factory=set)
    task: asyncio.Task | None = None


class RunRegistry:
    def __init__(self, ttl_seconds: int = 900, state: RunState | None = None):
        self.ttl_seconds = ttl_seconds
        self.state = state
        self._runs: dict[str, tuple[asyncio.Lock, RunHandle]] = {}
        self._records: dict[str, RunRecord] = {}
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

    async def start(self, conversation_id: str, runner, message_id: str | None = None) -> str:
        """Start a process-owned generation task and return its reconnectable run id.

        ``runner`` may be an async iterable factory accepting the RunHandle, or an
        async callable. Events yielded as strings are exposed as ``message.delta``.
        """
        handle = await self.acquire(conversation_id)
        run_id = str(uuid4())
        handle.run_id = run_id
        record = RunRecord(run_id, conversation_id, handle, message_id=message_id)
        async with self._guard:
            self._records[run_id] = record
        record.events.append(("run.snapshot", self.snapshot(record)))

        async def execute():
            try:
                try:
                    result = runner(handle, record)
                except TypeError:
                    result = runner(handle)
                if hasattr(result, "__aiter__"):
                    async for delta in result:
                        if handle.stop_event.is_set():
                            break
                        if delta:
                            record.content += str(delta)
                            await self.publish(record, "message.delta", {"content": str(delta)})
                elif asyncio.iscoroutine(result):
                    await result
                record.status = "cancelled" if handle.stop_event.is_set() else "completed"
                await self.publish(record, "run.completed" if record.status == "completed" else "run.interrupted", {})
            except Exception:
                logger.exception("background run failed", extra={"conversation_id": conversation_id})
                record.status = "failed"
                await self.publish(record, "run.failed", {"code": "CHAT_PROVIDER_ERROR"})
            finally:
                await self.release(conversation_id, handle)

        record.task = asyncio.create_task(execute())
        return run_id

    @staticmethod
    def snapshot(record: RunRecord) -> dict:
        return {"run_id": record.run_id, "conversation_id": record.conversation_id, "message_id": record.message_id, "status": record.status, "content": record.content}

    async def publish(self, record: RunRecord, name: str, data: dict) -> None:
        record.events.append((name, data))
        for queue in list(record.subscribers):
            await queue.put((name, data))

    def get_record(self, conversation_id: str, run_id: str | None = None) -> RunRecord | None:
        records = [r for r in self._records.values() if r.conversation_id == conversation_id and (run_id is None or r.run_id == run_id)]
        return records[-1] if records else None

    async def subscribe(self, record: RunRecord) -> AsyncGenerator[str, None]:
        queue: asyncio.Queue[tuple[str, dict]] = asyncio.Queue(maxsize=128)
        record.subscribers.add(queue)
        try:
            yield event("run.snapshot", self.snapshot(record))
            if record.status != "generating":
                for name, payload in record.events[1:]:
                    yield event(name, payload)
                return
            while True:
                name, payload = await queue.get()
                yield event(name, payload)
                if name in {"run.completed", "run.interrupted", "run.failed"}:
                    return
        finally:
            record.subscribers.discard(queue)

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


async def resolve_chat_model(session: AsyncSession, conversation: Conversation, user_id: UUID, requested_id: UUID | None):
    model_id = requested_id or getattr(conversation, "selected_chat_model_id", None)
    if not model_id:
        user = await session.get(User, user_id)
        model_id = getattr(user, "default_chat_model_id", None) if user else None
    if model_id:
        row = await session.execute(
            select(ChatModel, ModelConnection)
            .join(ModelConnection, ChatModel.connection_id == ModelConnection.id)
            .where(
                ChatModel.id == model_id,
                ModelConnection.user_id == user_id,
                ModelConnection.status == "active",
                ChatModel.status == "verified",
            )
        )
        result = row.first() if row is not None else None
        if result:
            return result[0], result[1]
        if requested_id or getattr(conversation, "selected_chat_model_id", None):
            raise HTTPException(409, "Selected chat model is unavailable")
    raise HTTPException(409, "Please configure and verify a chat model before sending")


def embedding_config_is_verified(config: EmbeddingConfig | None) -> bool:
    return config is not None and config.status == "verified"

def event(name: str, data: dict) -> str: return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

@router.get("", response_model=list[ConversationResponse])
async def list_conversations(uid=Depends(current_user_id), session=Depends(get_session)):
    return (await session.scalars(select(Conversation).where(Conversation.user_id == uid).order_by(Conversation.pinned.desc(), Conversation.updated_at.desc()))).all()

@router.post("", response_model=ConversationResponse, status_code=201)
async def create_conversation(payload: ConversationCreate, uid=Depends(current_user_id), session=Depends(get_session)):
    item = Conversation(user_id=uid, title=payload.title.strip(), mode=payload.mode); session.add(item); await session.commit(); await session.refresh(item); return item

@router.get("/{cid}", response_model=ConversationResponse)
async def get_conversation(cid, uid=Depends(current_user_id), session=Depends(get_session)): return await conversation(cid, uid, session)

@router.patch("/{cid}", response_model=ConversationResponse)
async def update_conversation(cid, payload: ConversationUpdate, uid=Depends(current_user_id), session=Depends(get_session)):
    item = await conversation(cid, uid, session)
    changes = payload.model_dump(exclude_unset=True)
    if "title" in changes:
        item.title = changes["title"]
    if "pinned" in changes:
        item.pinned = changes["pinned"]
    await session.commit(); await session.refresh(item); return item

@router.post("/bulk")
async def bulk_conversations(payload: BulkConversationRequest, uid=Depends(current_user_id), session=Depends(get_session)):
    """Apply a bulk pin/unpin/delete operation, scoped to the authenticated user."""
    ids = list(dict.fromkeys(payload.conversation_ids))
    if payload.action == "delete":
        result = await session.execute(
            sql_delete(Conversation).where(Conversation.user_id == uid, Conversation.id.in_(ids))
        )
    else:
        result = await session.execute(
            sql_update(Conversation)
            .where(Conversation.user_id == uid, Conversation.id.in_(ids))
            .values(pinned=payload.action == "pin", updated_at=func.now())
        )
    await session.commit()
    return {"action": payload.action, "affected": int(getattr(result, "rowcount", 0) or 0)}

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
async def stream(cid: UUID, payload: ChatRequest, uid=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    """Start a process-owned generation and subscribe this connection to it.

    The work is deliberately not performed by the response generator: closing a
    browser tab only removes one subscriber and does not stop the model run.
    """
    conversation_item = await conversation(cid, uid, session)
    selected_chat_model, selected_connection = await resolve_chat_model(session, conversation_item, uid, payload.chat_model_id)
    try:
        validate_chat_context(payload.mode, payload.problem_id, payload.solution_language)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    problem = await resolve_problem_context(session, payload.problem_id, uid)
    started = time.monotonic()
    embedding_config = await session.scalar(select(EmbeddingConfig).where(EmbeddingConfig.user_id == uid))
    retrieval_requested = embedding_config_is_verified(embedding_config) and (
        payload.knowledge_scope != "none" or bool(payload.attachment_ids)
    )
    retrieved = []
    retrieval_error: Exception | None = None
    if payload.reuse_last_user:
        user = await session.scalar(select(Message).where(Message.conversation_id == cid, Message.role == "user").order_by(Message.created_at.desc()).limit(1))
        if not user:
            raise HTTPException(400, "No user message available to retry")
        user.content = payload.content
        user.problem_id = problem.id if problem else None
        user.mode = payload.mode
        user.solution_language = payload.solution_language
    else:
        user = Message(conversation_id=cid, role="user", content=payload.content, status="completed", problem_id=problem.id if problem else None, mode=payload.mode, solution_language=payload.solution_language)
        session.add(user)
    await session.flush()
    rows = (await session.scalars(select(Message).where(Message.conversation_id == cid, Message.id != user.id).order_by(Message.created_at))).all()
    history = trim_history([{"role": item.role, "content": item.content} for item in rows], getattr(get_settings(), "chat_history_max_chars", 60_000), getattr(get_settings(), "chat_history_max_messages", 30))
    try:
        if retrieval_requested:
            retrieved = await retrieve_chunks(
                session,
                uid,
                cid,
                payload.content,
                payload.knowledge_group_ids,
                payload.attachment_ids,
                knowledge_scope=payload.knowledge_scope,
                embedding_provider=UserEmbeddingProvider(session, uid),
            )
            retrieved = trim_retrieved_chunks(
                retrieved, getattr(get_settings(), "rag_context_max_chars", 40_000), 10
            )
    except Exception as error:
        logger.exception("retrieval failed", extra={"conversation_id": str(cid), "user_id": str(uid)})
        retrieval_error = error
    selected_model_name = selected_chat_model.name
    if selected_chat_model.id != getattr(conversation_item, "selected_chat_model_id", None):
        conversation_item.selected_chat_model_id = selected_chat_model.id
    assistant = Message(conversation_id=cid, role="assistant", content="", status="generating", model=selected_model_name, chat_model_id=selected_chat_model.id, model_name_snapshot=selected_model_name, problem_id=problem.id if problem else None, mode=payload.mode, solution_language=payload.solution_language, retrieved_chunk_ids=[str(item.chunk_id) for item in retrieved])
    session.add(assistant)
    await session.commit()
    await session.refresh(assistant)
    assistant_id = assistant.id

    async def persist(status: str, content: str, first_token_ms: int | None):
        async with session_factory() as save_session:
            target = await save_session.get(Message, assistant_id)
            if not target:
                return
            target.status = status
            target.content = content
            target.duration_ms = round((time.monotonic() - started) * 1000)
            target.first_token_latency_ms = first_token_ms
            target.retrieved_chunk_ids = [str(item.chunk_id) for item in retrieved]
            await save_session.execute(Conversation.__table__.update().where(Conversation.id == cid).values(updated_at=func.now()))
            await save_session.commit()

    async def generate(handle: RunHandle, record: RunRecord):
        answer = ""
        first_token_ms: int | None = None
        record.message_id = str(assistant_id)
        await runs.publish(record, "run.started", {"conversation_id": str(cid), "message_id": str(assistant_id)})
        await runs.publish(record, "retrieval.completed", {"status": "failed" if retrieval_error else "ok", "count": len(retrieved), "items": [{"chunk_id": str(item.chunk_id), "score": item.score, "locator": item.locator or {}} for item in retrieved]})
        if retrieval_error and retrieval_requested:
            await persist("failed", "", None)
            record.status = "failed"
            await runs.publish(record, "run.failed", {"code": "RETRIEVAL_FAILED", "message": "知识库检索失败，请稍后重试", "message_id": str(assistant_id)})
            return
        try:
            knowledge_context = "\n\n".join(f"来源切片：{item.chunk_id}\n{item.content}" for item in retrieved)
            if payload.mode == "normal":
                base_prompt = payload.content if not problem else f"{format_problem_context(problem)}\n\n用户问题：{payload.content}"
                prompt = build_context_prompt(base_prompt, retrieved)
            else:
                prompt = build_acm_prompt(problem, payload.content, payload.mode, payload.solution_language, knowledge_context)
            key = decrypt_secret(selected_connection.api_key_ciphertext, selected_connection.api_key_nonce)
            provider_stream = OpenAICompatibleChatProvider(selected_connection.base_url, key).stream_chat(
                history + [{"role": "user", "content": prompt}], selected_chat_model.name, handle.stop_event
            )
            async for delta in provider_stream:
                if handle.lease and (not await handle.lease.refresh() or await handle.lease.stop_requested()):
                    handle.stop_event.set()
                    break
                handle.last_activity = datetime.now(UTC)
                answer += delta
                if first_token_ms is None:
                    first_token_ms = round((time.monotonic() - started) * 1000)
                    await runs.publish(record, "run.first_token", {"latency_ms": first_token_ms})
                yield delta
            cleaned = sanitize_analysis_output(answer) if payload.mode == "acm_analysis" else answer
            final_status = "cancelled" if handle.stop_event.is_set() else "completed"
            await persist(final_status, cleaned, first_token_ms)
            if final_status == "completed":
                async with session_factory() as save_session:
                    cleaned, citations = await persist_citations(save_session, assistant_id, cleaned, retrieved)
                    target = await save_session.get(Message, assistant_id)
                    if target:
                        target.content = cleaned
                    await save_session.commit()
                await runs.publish(record, "citations.validated", {"items": [{"chunk_id": str(item.chunk_id), "quote": item.quote, "score": item.score, "locator": item.locator} for item in citations]})
            record.content = cleaned
            record.status = final_status
            await runs.publish(record, "message.final", {"content": cleaned, "message_id": str(assistant_id), "mode": payload.mode, "problem_id": str(problem.id) if problem else None, "solution_language": payload.solution_language})
        except Exception:
            logger.exception("chat background task failed", extra={"conversation_id": str(cid), "user_id": str(uid)})
            await persist("failed", "", first_token_ms)
            record.status = "failed"
            await runs.publish(record, "run.failed", {"code": "CHAT_PROVIDER_ERROR", "message": "生成回答失败，请稍后重试", "message_id": str(assistant_id)})

    run_id = await runs.start(str(cid), generate, message_id=str(assistant_id))
    record = runs.get_record(str(cid), run_id)
    return StreamingResponse(runs.subscribe(record), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/{cid}/runs/active")
async def active_run(cid: UUID, uid=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    await conversation(cid, uid, session)
    record = runs.get_record(str(cid))
    return runs.snapshot(record) if record else {}


@router.get("/{cid}/runs/{run_id}/stream")
async def reconnect_run(cid: UUID, run_id: str, uid=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    await conversation(cid, uid, session)
    record = runs.get_record(str(cid), run_id)
    if not record:
        raise HTTPException(404, "Generation run not found")
    return StreamingResponse(runs.subscribe(record), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

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
    """Return validated citations with the document metadata the UI renders.

    The payload is deliberately richer than the raw citation rows: the answer
    panel needs the document title, group name and filename for every source.
    """
    await conversation(cid, uid, session)
    rows = await citation_sources(session, mid, cid, uid)
    return [{**row, "original_filename": row["original_filename"], "file_name": row["original_filename"], "explicitly_cited": True} for row in rows]
