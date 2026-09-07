import asyncio, json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from ..config import get_settings
from ..db import get_session
from ..dependencies import current_user_id
from ..models import Conversation, Message
from ..schemas import ChatRequest, ConversationCreate, ConversationResponse, ConversationUpdate, MessageResponse

router = APIRouter(prefix="/conversations", tags=["conversations"])
runs: dict[str, asyncio.Event] = {}
async def conversation(cid, uid, session):
    item = await session.scalar(select(Conversation).where(Conversation.id == cid, Conversation.user_id == uid))
    if not item: raise HTTPException(404, "Conversation not found")
    return item

def event(name, data): return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

@router.get("", response_model=list[ConversationResponse])
async def list_conversations(uid=Depends(current_user_id), session=Depends(get_session)):
    return (await session.scalars(select(Conversation).where(Conversation.user_id==uid).order_by(Conversation.updated_at.desc()))).all()
@router.post("", response_model=ConversationResponse, status_code=201)
async def create_conversation(payload: ConversationCreate, uid=Depends(current_user_id), session=Depends(get_session)):
    item=Conversation(user_id=uid,title=payload.title,mode=payload.mode); session.add(item); await session.commit(); await session.refresh(item); return item
@router.get("/{cid}", response_model=ConversationResponse)
async def get_conversation(cid, uid=Depends(current_user_id), session=Depends(get_session)): return await conversation(cid,uid,session)
@router.patch("/{cid}", response_model=ConversationResponse)
async def update_conversation(cid, payload: ConversationUpdate, uid=Depends(current_user_id), session=Depends(get_session)):
    item=await conversation(cid,uid,session); item.title=payload.title; await session.commit(); await session.refresh(item); return item
@router.delete("/{cid}", status_code=204)
async def delete_conversation(cid, uid=Depends(current_user_id), session=Depends(get_session)):
    item=await conversation(cid,uid,session); await session.delete(item); await session.commit()
@router.get("/{cid}/messages", response_model=list[MessageResponse])
async def messages(cid, uid=Depends(current_user_id), session=Depends(get_session)):
    await conversation(cid,uid,session); return (await session.scalars(select(Message).where(Message.conversation_id==cid).order_by(Message.created_at))).all()

async def model_stream(prompt: str, history: list[dict]) -> AsyncGenerator[str,None]:
    settings=get_settings()
    if not settings.dashscope_api_key or not settings.chat_model:
        raise RuntimeError("CHAT_MODEL and DASHSCOPE_API_KEY are required")
    import httpx
    body={"model":settings.chat_model,"messages":history+[ {"role":"user","content":prompt}],"stream":True}
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream("POST",settings.dashscope_base_url.rstrip("/")+"/chat/completions",headers={"Authorization":f"Bearer {settings.dashscope_api_key}"},json=body) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: ") and line[6:] != "[DONE]":
                    data=json.loads(line[6:]); delta=data["choices"][0].get("delta",{}).get("content","")
                    if delta: yield delta

@router.post("/{cid}/messages/stream")
async def stream(cid, payload: ChatRequest, uid=Depends(current_user_id), session: AsyncSession=Depends(get_session)):
    item=await conversation(cid,uid,session); user=Message(conversation_id=cid,role="user",content=payload.content,status="completed"); session.add(user); await session.commit()
    stop=asyncio.Event(); runs[str(cid)]=stop
    history=[{"role":m.role,"content":m.content} for m in (await session.scalars(select(Message).where(Message.conversation_id==cid).order_by(Message.created_at))).all()]
    async def generate():
        answer=""
        yield event("run.started",{"conversation_id":str(cid)})
        try:
            yield event("retrieval.completed",{"count":0})
            async for delta in model_stream(payload.content,history):
                if stop.is_set(): yield event("run.interrupted",{}); break
                answer+=delta; yield event("message.delta",{"content":delta})
            else:
                msg=Message(conversation_id=cid,role="assistant",content=answer,status="completed",model=get_settings().chat_model); session.add(msg); await session.commit(); yield event("run.completed",{"message_id":str(msg.id)})
        except Exception as exc:
            yield event("run.failed",{"message":str(exc)})
        finally: runs.pop(str(cid),None)
    return StreamingResponse(generate(),media_type="text/event-stream")
@router.post("/{cid}/run/stop", status_code=202)
async def stop(cid, uid=Depends(current_user_id), session=Depends(get_session)):
    await conversation(cid,uid,session); event= runs.get(str(cid));
    if event: event.set()
    return {"status":"stopping"}
@router.post("/{cid}/run/resume", status_code=202)
async def resume(cid, uid=Depends(current_user_id), session=Depends(get_session)):
    await conversation(cid,uid,session); return {"status":"ready","message":"Send the next request to resume from persisted messages"}
