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
from ..models import Conversation, Message
from ..schemas import ChatRequest, ConversationCreate, ConversationResponse, ConversationUpdate, MessageResponse

router = APIRouter(prefix="/conversations", tags=["conversations"])
logger = logging.getLogger(__name__)
@dataclass
class RunHandle:
    stop_event: asyncio.Event = field(default_factory=asyncio.Event)
    last_activity: datetime = field(default_factory=lambda: datetime.now(UTC))


class RunRegistry:
    def __init__(self, ttl_seconds: int = 900):
        self.ttl_seconds = ttl_seconds
        self._runs: dict[str, tuple[asyncio.Lock, RunHandle]] = {}
        self._guard = asyncio.Lock()

    async def acquire(self, cid: str) -> RunHandle:
        async with self._guard:
            lock, handle = self._runs.setdefault(cid, (asyncio.Lock(), RunHandle()))
            if lock.locked():
                raise HTTPException(409, "A response is already being generated")
            await lock.acquire()
            handle.last_activity = datetime.now(UTC)
            return handle

    async def release(self, cid: str, handle: RunHandle) -> None:
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

@router.get("/{cid}/messages", response_model=list[MessageResponse])
async def messages(cid, uid=Depends(current_user_id), session=Depends(get_session)):
    await conversation(cid, uid, session); return (await session.scalars(select(Message).where(Message.conversation_id == cid).order_by(Message.created_at))).all()

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
    handle = await runs.acquire(str(cid))
    started = time.monotonic()
    try:
        user = Message(conversation_id=cid, role="user", content=payload.content, status="completed")
        session.add(user); await session.commit()
        rows = (await session.scalars(select(Message).where(Message.conversation_id == cid, Message.id != user.id).order_by(Message.created_at))).all()
        history = [{"role": m.role, "content": m.content} for m in rows]
        await session.close()
    except Exception:
        await session.rollback(); await runs.release(str(cid), handle); raise

    async def generate():
        answer = ""
        try:
            yield event("run.started", {"conversation_id": str(cid)}); yield event("retrieval.completed", {"count": 0})
            async for delta in model_stream(payload.content, history, handle.stop_event):
                if await request.is_disconnected(): handle.stop_event.set(); break
                handle.last_activity = datetime.now(UTC)
                answer += delta; yield event("message.delta", {"content": delta}); yield event("ping", {})
            if answer:
                async with session_factory() as save_session:
                    save_session.add(Message(conversation_id=cid, role="assistant", content=answer, status="cancelled" if handle.stop_event.is_set() else "completed", model=get_settings().chat_model))
                    await save_session.execute(Conversation.__table__.update().where(Conversation.id == cid).values(updated_at=func.now()))
                    await save_session.commit()
            yield event("run.interrupted" if handle.stop_event.is_set() else "run.completed", {})
        except asyncio.CancelledError:
            handle.stop_event.set(); raise
        except Exception:
            logger.exception("chat stream failed", extra={"conversation_id": str(cid), "user_id": str(uid), "prompt_length": len(payload.content), "duration_ms": round((time.monotonic() - started) * 1000)})
            yield event("run.failed", {"code": "CHAT_PROVIDER_ERROR", "message": "生成回答失败，请稍后重试"})
        finally:
            await runs.release(str(cid), handle)
    return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@router.post("/{cid}/run/stop", status_code=202)
async def stop(cid, uid=Depends(current_user_id), session=Depends(get_session)):
    await conversation(cid, uid, session)
    if signal := runs.get_stop_event(str(cid)): signal.set()
    return {"status": "stopping"}

@router.post("/{cid}/run/resume", status_code=202)
async def resume(cid, uid=Depends(current_user_id), session=Depends(get_session)):
    await conversation(cid, uid, session); return {"status": "ready", "message": "Send the next request to resume from persisted messages"}
