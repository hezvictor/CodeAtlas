import hashlib
import logging
import mimetypes
import uuid
from datetime import UTC, datetime
from pathlib import PurePath

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db import get_session
from ..dependencies import current_user_id
from ..models import Document, DocumentJob, DocumentVersion, KnowledgeGroup
from ..queue import dispatch_document_job
from ..schemas import DocumentPreviewResponse, DocumentResponse, DocumentVersionResponse
from ..storage.s3 import S3Storage, object_key_for

router = APIRouter(prefix="/knowledge/documents", tags=["knowledge"])
logger = logging.getLogger(__name__)

_MIME_BY_EXTENSION = {
    ".md": "text/markdown", ".markdown": "text/markdown", ".txt": "text/plain",
    ".html": "text/html", ".htm": "text/html", ".py": "text/x-python",
    ".java": "text/x-java-source", ".c": "text/x-c", ".cc": "text/x-c++src",
    ".cpp": "text/x-c++src", ".h": "text/x-c", ".hpp": "text/x-c++hdr",
    ".pdf": "application/pdf", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


async def owned_document(document_id: uuid.UUID, user_id: uuid.UUID, session: AsyncSession) -> Document:
    item = await session.scalar(select(Document).where(Document.id == document_id, Document.user_id == user_id, Document.deleted_at.is_(None)))
    if not item:
        raise HTTPException(404, "Document not found")
    return item


async def latest_version(document: Document, session: AsyncSession) -> DocumentVersion | None:
    return await session.scalar(select(DocumentVersion).where(DocumentVersion.document_id == document.id).order_by(DocumentVersion.version_no.desc()).limit(1))


def document_response(document: Document, version: DocumentVersion | None) -> DocumentResponse:
    return DocumentResponse(
        id=document.id, user_id=document.user_id, group_id=document.group_id, title=document.title,
        created_at=document.created_at, updated_at=document.updated_at,
        latest_version=DocumentVersionResponse.model_validate(version) if version else None,
    )


def _validate_upload(filename: str, content_type: str | None, data: bytes) -> tuple[str, str]:
    extension = PurePath(filename).suffix.lower()
    settings = get_settings()
    if extension not in settings.allowed_document_extensions:
        raise HTTPException(400, "Unsupported document type")
    if len(data) > settings.max_upload_size_bytes:
        raise HTTPException(413, "Document is too large")
    declared = content_type or "application/octet-stream"
    expected = _MIME_BY_EXTENSION.get(extension, declared)
    if declared != "application/octet-stream" and declared != expected:
        if not (expected.startswith("text/") and declared.startswith("text/")):
            raise HTTPException(400, "MIME type does not match file extension")
    if extension == ".pdf" and not data.startswith(b"%PDF"):
        raise HTTPException(400, "Uploaded file is not a valid PDF")
    if extension == ".docx" and not data.startswith(b"PK"):
        raise HTTPException(400, "Uploaded file is not a valid DOCX")
    if extension in {".html", ".htm"} and b"<" not in data[:4096]:
        raise HTTPException(400, "Uploaded file is not a valid HTML document")
    return extension, expected


@router.get("", response_model=list[DocumentResponse])
async def list_documents(group_id: uuid.UUID | None = None, user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    query = select(Document).where(Document.user_id == user_id, Document.deleted_at.is_(None)).order_by(Document.updated_at.desc())
    if group_id:
        query = query.where(Document.group_id == group_id)
    documents = (await session.scalars(query)).all()
    return [document_response(document, await latest_version(document, session)) for document in documents]


@router.post("", response_model=DocumentResponse, status_code=202)
async def upload_document(
    group_id: uuid.UUID = Form(...), title: str | None = Form(None), file: UploadFile = File(...),
    user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session),
):
    group = await session.scalar(select(KnowledgeGroup).where(KnowledgeGroup.id == group_id, KnowledgeGroup.user_id == user_id))
    if not group:
        raise HTTPException(404, "Knowledge group not found")
    filename = PurePath(file.filename or "document").name
    data = await file.read(get_settings().max_upload_size_bytes + 1)
    extension, mime_type = _validate_upload(filename, file.content_type, data)
    document = Document(user_id=user_id, group_id=group_id, title=(title or PurePath(filename).stem).strip()[:200] or "Untitled document")
    session.add(document)
    await session.flush()
    max_version = await session.scalar(select(func.max(DocumentVersion.version_no)).where(DocumentVersion.document_id == document.id)) or 0
    version_no = int(max_version) + 1
    key = object_key_for(str(user_id), str(group_id), str(document.id), version_no, filename)
    version = DocumentVersion(
        document_id=document.id, version_no=version_no, original_filename=filename,
        mime_type=mime_type, extension=extension, size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(), object_key=key, status="uploaded",
    )
    session.add(version)
    await session.flush()
    document.current_version_id = version.id
    job = DocumentJob(document_version_id=version.id, stage="parsing", status="queued", attempts=0)
    session.add(job)
    storage = S3Storage()
    await storage.put_bytes(key, data, mime_type)
    await session.commit()
    await session.refresh(document)
    try:
        await dispatch_document_job(str(job.id))
    except Exception:
        logger.exception("document job dispatch failed after upload", extra={"job_id": str(job.id), "version_id": str(version.id)})
    return document_response(document, version)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: uuid.UUID, user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    document = await owned_document(document_id, user_id, session)
    return document_response(document, await latest_version(document, session))


@router.get("/{document_id}/status", response_model=DocumentVersionResponse)
async def document_status(document_id: uuid.UUID, user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    document = await owned_document(document_id, user_id, session)
    version = await latest_version(document, session)
    if not version:
        raise HTTPException(404, "Document version not found")
    return version


@router.get("/{document_id}/preview", response_model=DocumentPreviewResponse)
async def preview_document(document_id: uuid.UUID, user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    document = await owned_document(document_id, user_id, session)
    version = await latest_version(document, session)
    if not version:
        raise HTTPException(404, "Document version not found")
    return DocumentPreviewResponse(document=document_response(document, version), version=version, text=version.extracted_text or "")


@router.get("/{document_id}/download")
async def download_document(document_id: uuid.UUID, user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    document = await owned_document(document_id, user_id, session)
    version = await latest_version(document, session)
    if not version:
        raise HTTPException(404, "Document version not found")
    return {"url": await S3Storage().presigned_get(version.object_key), "expires_in": 300}


@router.delete("/{document_id}", status_code=204)
async def delete_document(document_id: uuid.UUID, user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    document = await owned_document(document_id, user_id, session)
    document.deleted_at = func.now()
    await session.commit()


async def _reset_latest(document_id: uuid.UUID, user_id: uuid.UUID, session: AsyncSession) -> DocumentVersion:
    document = await owned_document(document_id, user_id, session)
    version = await session.scalar(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document.id)
        .order_by(DocumentVersion.version_no.desc())
        .limit(1)
        .with_for_update()
    )
    if not version:
        raise HTTPException(404, "Document version not found")
    version.status, version.error_code, version.error_message = "uploaded", None, None
    job = await session.scalar(
        select(DocumentJob)
        .where(DocumentJob.document_version_id == version.id, DocumentJob.status.in_(("queued", "running")))
        .order_by(DocumentJob.created_at.desc())
        .limit(1)
    )
    if job and job.status == "running":
        raise HTTPException(409, "Document job is already running")
    if job:
        job.attempts = 0
        job.available_at = datetime.now(UTC)
        job.last_dispatch_at = None
        job.last_dispatch_error = None
    else:
        job = DocumentJob(document_version_id=version.id, stage="parsing", status="queued", attempts=0)
        session.add(job)
    await session.commit()
    try:
        await dispatch_document_job(str(job.id))
    except Exception:
        logger.exception("document job dispatch failed after reset", extra={"job_id": str(job.id), "version_id": str(version.id)})
    return version


@router.post("/{document_id}/retry", response_model=DocumentVersionResponse, status_code=202)
async def retry_document(document_id: uuid.UUID, user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    return await _reset_latest(document_id, user_id, session)


@router.post("/{document_id}/reindex", response_model=DocumentVersionResponse, status_code=202)
async def reindex_document(document_id: uuid.UUID, user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    return await _reset_latest(document_id, user_id, session)
