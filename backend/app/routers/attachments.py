import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..dependencies import current_user_id
from ..models import Attachment, Conversation, Document, DocumentVersion
from ..schemas import AttachmentResponse

router = APIRouter(prefix="/conversations/{conversation_id}/attachments", tags=["knowledge"])


async def owned_conversation(conversation_id: uuid.UUID, user_id: uuid.UUID, session: AsyncSession):
    item = await session.scalar(select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user_id))
    if not item:
        raise HTTPException(404, "Conversation not found")
    return item


@router.get("", response_model=list[AttachmentResponse])
async def list_attachments(conversation_id: uuid.UUID, user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    await owned_conversation(conversation_id, user_id, session)
    return (await session.scalars(select(Attachment).where(Attachment.conversation_id == conversation_id, Attachment.user_id == user_id).order_by(Attachment.created_at))).all()


@router.post("/{document_version_id}", response_model=AttachmentResponse, status_code=201)
async def attach_document(conversation_id: uuid.UUID, document_version_id: uuid.UUID, user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    await owned_conversation(conversation_id, user_id, session)
    version = await session.scalar(select(DocumentVersion).join(Document, DocumentVersion.document_id == Document.id).where(DocumentVersion.id == document_version_id, Document.user_id == user_id, DocumentVersion.status == "indexed"))
    if not version:
        raise HTTPException(404, "Indexed document version not found")
    existing = await session.scalar(select(Attachment).where(Attachment.conversation_id == conversation_id, Attachment.document_version_id == document_version_id))
    if existing:
        return existing
    attachment = Attachment(user_id=user_id, conversation_id=conversation_id, document_version_id=document_version_id)
    session.add(attachment)
    await session.commit()
    await session.refresh(attachment)
    return attachment


@router.delete("/{attachment_id}", status_code=204)
async def detach_document(conversation_id: uuid.UUID, attachment_id: uuid.UUID, user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    await owned_conversation(conversation_id, user_id, session)
    attachment = await session.scalar(select(Attachment).where(Attachment.id == attachment_id, Attachment.conversation_id == conversation_id, Attachment.user_id == user_id))
    if not attachment:
        raise HTTPException(404, "Attachment not found")
    await session.delete(attachment)
    await session.commit()
