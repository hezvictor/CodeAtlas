import hashlib
import uuid
from pathlib import PurePath

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..dependencies import current_user_id
from ..models import Attachment, Conversation, Document, DocumentJob, DocumentVersion
from ..queue import dispatch_document_job
from ..schemas import AttachmentResponse
from ..storage.s3 import S3Storage, object_key_for
from .knowledge_documents import _validate_upload, read_limited_upload

router = APIRouter(prefix="/conversations/{conversation_id}/attachments", tags=["knowledge"])


async def owned_conversation(conversation_id: uuid.UUID, user_id: uuid.UUID, session: AsyncSession):
    item = await session.scalar(select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user_id))
    if not item:
        raise HTTPException(404, "Conversation not found")
    return item


@router.get("", response_model=list[AttachmentResponse])
async def list_attachments(conversation_id: uuid.UUID, user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    await owned_conversation(conversation_id, user_id, session)
    rows = await session.execute(
        select(Attachment, Document, DocumentVersion)
        .join(DocumentVersion, Attachment.document_version_id == DocumentVersion.id)
        .join(Document, DocumentVersion.document_id == Document.id)
        .where(Attachment.conversation_id == conversation_id, Attachment.user_id == user_id)
        .order_by(Attachment.created_at)
    )
    return [
        AttachmentResponse(
            id=attachment.id,
            conversation_id=attachment.conversation_id,
            document_version_id=attachment.document_version_id,
            document_id=document.id,
            title=document.title,
            original_filename=version.original_filename,
            extension=version.extension,
            status=version.status,
            scope=document.scope,
            created_at=attachment.created_at,
        )
        for attachment, document, version in rows.all()
    ]


@router.post("/upload", response_model=AttachmentResponse, status_code=202)
async def upload_attachment(
    conversation_id: uuid.UUID,
    title: str | None = Form(None),
    file: UploadFile = File(...),
    user_id=Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
):
    await owned_conversation(conversation_id, user_id, session)
    filename = PurePath(file.filename or "document").name
    data = await read_limited_upload(file)
    extension, mime_type = _validate_upload(filename, file.content_type, data)
    document = Document(
        user_id=user_id,
        group_id=None,
        scope="session",
        title=(title or PurePath(filename).stem).strip()[:200] or "Session file",
    )
    session.add(document)
    await session.flush()
    version = DocumentVersion(
        document_id=document.id,
        version_no=1,
        original_filename=filename,
        mime_type=mime_type,
        extension=extension,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        object_key=object_key_for(str(user_id), "session", str(document.id), 1, filename),
        status="uploaded",
    )
    session.add(version)
    await session.flush()
    document.current_version_id = version.id
    attachment = Attachment(user_id=user_id, conversation_id=conversation_id, document_version_id=version.id)
    session.add(attachment)
    job = DocumentJob(document_version_id=version.id, stage="parsing", status="queued", attempts=0)
    session.add(job)
    await S3Storage().put_bytes(version.object_key, data, mime_type)
    await session.commit()
    await session.refresh(attachment)
    try:
        await dispatch_document_job(str(job.id))
    except Exception:
        pass
    return AttachmentResponse(
        id=attachment.id,
        conversation_id=attachment.conversation_id,
        document_version_id=version.id,
        document_id=document.id,
        title=document.title,
        original_filename=version.original_filename,
        extension=version.extension,
        status=version.status,
        scope=document.scope,
        created_at=attachment.created_at,
    )


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
    document = await session.scalar(
        select(Document).join(DocumentVersion, DocumentVersion.document_id == Document.id).where(
            DocumentVersion.id == attachment.document_version_id,
            Document.user_id == user_id,
        )
    )
    await session.delete(attachment)
    if document and document.scope == "session":
        document.deleted_at = func.now()
    await session.commit()
