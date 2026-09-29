from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import delete as sql_delete
from sqlalchemy import func, select
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from ..chat_runtime.infrastructure import resources
from ..chat_runtime.service import (
    active_run,
    delete_run_data,
    resume_run,
    snapshot,
    start_run,
    stop_run,
    subscribe,
)
from ..citations import citation_sources
from ..config import get_settings
from ..db import get_session
from ..dependencies import current_user_id
from ..models import (
    ChatModel,
    ChatRun,
    Conversation,
    EmbeddingConfig,
    Message,
    ModelConnection,
    RerankerConfig,
    User,
)
from ..providers.embedding import project_embedding_is_configured
from ..schemas import (
    BulkConversationRequest,
    ChatRequest,
    ConversationCreate,
    ConversationResponse,
    ConversationUpdate,
    MessagePage,
    RetryRequest,
)
from ..security.provider_credentials import decrypt_secret
from ..services.problem_context import message_context_metadata
from ..temporary.privacy import validate_answer

router = APIRouter(prefix="/conversations", tags=["conversations"])

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
        from .model_connections import model_is_chat_ready
        if result and model_is_chat_ready(result[0]):
            return result[0], result[1]
        if requested_id or getattr(conversation, "selected_chat_model_id", None):
            raise HTTPException(409, "Selected chat model is unavailable")
    raise HTTPException(409, "Please configure and verify a chat model before sending")


def embedding_config_is_verified(config: EmbeddingConfig | None) -> bool:
    return config is not None and config.status == "verified"


def embedding_is_available(config: EmbeddingConfig | None) -> bool:
    return embedding_config_is_verified(config) or (config is None and project_embedding_is_configured(get_settings()))


async def _resolve_reranker(session: AsyncSession, user_id: UUID, config: RerankerConfig | None):
    settings = get_settings()
    if config and getattr(config, "status", None) == "verified":
        key = decrypt_secret(config.api_key_ciphertext, config.api_key_nonce)
        base_url, model = config.base_url, config.model_name
    elif settings.reranker_base_url and settings.reranker_api_key and settings.reranker_model:
        key, base_url, model = settings.reranker_api_key, settings.reranker_base_url, settings.reranker_model
    else:
        return None
    from ..providers.reranker import RerankerProvider
    provider = RerankerProvider(base_url, key, model)

    async def rerank(query, chunks):
        rows = await provider.rerank(query, [item.content for item in chunks])
        return [chunks[index] for index, _score in rows if 0 <= index < len(chunks)]

    return rerank


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
async def bulk_conversations(payload: BulkConversationRequest, request: Request, uid=Depends(current_user_id), session=Depends(get_session)):
    """Apply a bulk pin/unpin/delete operation, scoped to the authenticated user."""
    ids = list(dict.fromkeys(payload.conversation_ids))
    if payload.action == "delete":
        owned = (await session.scalars(select(Conversation.id).where(Conversation.user_id == uid, Conversation.id.in_(ids)))).all()
        for cid in owned:
            await delete_run_data(resources(request), session, cid, uid)
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
async def delete_conversation(cid: UUID, request: Request, uid=Depends(current_user_id), session=Depends(get_session)):
    item = await conversation(cid, uid, session)
    await delete_run_data(resources(request), session, cid, uid)
    await session.delete(item)
    await session.commit()

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
async def retry_message(cid: UUID, mid: UUID, payload: RetryRequest, request: Request, uid=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    await conversation(cid, uid, session)
    if await active_run(session, cid, uid):
        raise HTTPException(409, "A generation is already running for this conversation")
    target = await session.scalar(select(Message).where(Message.id == mid, Message.conversation_id == cid))
    if not target: raise HTTPException(404, "Message not found")
    content = payload.content.strip() if payload.content else target.content
    if payload.content is not None:
        files = await resources(request).temporary.files(uid, cid)
        previous = (await session.scalars(select(Message.content).where(Message.conversation_id == cid, Message.created_at < target.created_at))).all()
        try:
            validate_answer(content, files, previous)
        except ValueError as error:
            raise HTTPException(409, {"code": str(error), "message": "编辑内容包含不可持久化的临时资料，请减少原文引用"}) from None
    if target.role == "user":
        target.content = content
        await session.execute(Message.__table__.delete().where(Message.conversation_id == cid, Message.created_at > target.created_at))
        context_message = target
    elif target.role == "assistant":
        newer = await session.scalar(select(Message.id).where(Message.conversation_id == cid, Message.created_at > target.created_at).limit(1))
        if newer:
            raise HTTPException(409, "Only the latest assistant message can be retried")
        previous = await session.scalar(select(Message).where(Message.conversation_id == cid, Message.created_at < target.created_at).order_by(Message.created_at.desc()))
        if not previous or previous.role != "user": raise HTTPException(400, "Assistant message has no user prompt")
        content = previous.content
        await session.delete(target)
        context_message = previous
    else: raise HTTPException(400, "Only user or assistant messages can be retried")
    await session.commit()
    return {"content": content, **message_context_metadata(context_message)}


@router.post("/{cid}/messages/stream")
async def stream(cid: UUID, payload: ChatRequest, request: Request, uid=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    runtime = resources(request)
    run = await start_run(runtime, session, cid, uid, payload)
    return StreamingResponse(subscribe(runtime, cid, uid, run.id), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/{cid}/runs/active")
async def get_active_run(cid: UUID, uid=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    await conversation(cid, uid, session)
    run = await active_run(session, cid, uid)
    return snapshot(run, await session.get(Message, run.message_id)) if run else {}


@router.get("/{cid}/runs/{run_id}/stream")
async def reconnect_run(cid: UUID, run_id: UUID, request: Request, uid=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    await conversation(cid, uid, session)
    run = await session.scalar(select(ChatRun).where(ChatRun.id == run_id, ChatRun.conversation_id == cid, ChatRun.user_id == uid))
    if not run: raise HTTPException(404, "Generation run not found")
    return StreamingResponse(subscribe(resources(request), cid, uid, run_id), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/{cid}/run/stop", status_code=202)
async def stop(cid: UUID, request: Request, uid=Depends(current_user_id), session=Depends(get_session)):
    await conversation(cid, uid, session)
    await stop_run(resources(request), session, cid, uid)
    return {"status": "cancelled"}


@router.post("/{cid}/run/resume", status_code=202)
async def resume(cid: UUID, request: Request, uid=Depends(current_user_id), session=Depends(get_session)):
    await conversation(cid, uid, session)
    return await resume_run(resources(request), session, cid, uid)


@router.get("/{cid}/messages/{mid}/citations")
async def message_citations(cid: UUID, mid: UUID, uid=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    await conversation(cid, uid, session)
    rows = await citation_sources(session, mid, cid, uid)
    return [{**row, "file_name": row["original_filename"], "explicitly_cited": True} for row in rows]
