import hashlib
import logging
import uuid
from datetime import UTC, datetime, timedelta, timezone
from pathlib import PurePath

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db import get_session
from ..dependencies import current_user_id
from ..models import Document, DocumentJob, DocumentVersion, KnowledgeGroup
from ..queue import dispatch_document_job
from ..schemas import (
    DocumentJobResponse,
    DocumentPreviewResponse,
    DocumentResponse,
    DocumentVersionResponse,
)
from ..services.document_lifecycle import ACTIVE_JOB_STATES, mark_document_deleted
from ..services.document_upload import conflict_candidates, timestamp_filename
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

_FORMAT_DESCRIPTION = "支持 Markdown、DOCX、TXT、C/C++、Java、Python、HTML 文件"


def upload_policy() -> dict:
    """Return the effective upload policy used by server-side validation."""
    settings = get_settings()
    return {
        "extensions": sorted(settings.allowed_document_extensions - {".pdf"}),
        "max_size_bytes": settings.max_upload_size_bytes,
        "format_description": _FORMAT_DESCRIPTION,
    }


def _upload_error(status_code: int, code: str, message: str, english: str) -> HTTPException:
    # Keep a stable machine-readable code while retaining a useful message for
    # existing clients that displayed the old English detail string.
    return HTTPException(status_code, {"code": code, "message": f"{english}：{message}"})


async def owned_document(document_id: uuid.UUID, user_id: uuid.UUID, session: AsyncSession) -> Document:
    item = await session.scalar(select(Document).where(Document.id == document_id, Document.user_id == user_id, Document.deleted_at.is_(None)))
    if not item:
        raise HTTPException(404, "Document not found")
    return item


async def latest_version(document: Document, session: AsyncSession) -> DocumentVersion | None:
    return await session.scalar(select(DocumentVersion).where(DocumentVersion.document_id == document.id).order_by(DocumentVersion.version_no.desc()).limit(1))


async def _lock_document_for_version(document: Document, session: AsyncSession) -> Document:
    """Serialize version allocation for a document across concurrent uploads."""
    locked = await session.scalar(
        select(Document)
        .where(
            Document.id == document.id,
            Document.user_id == document.user_id,
            Document.deleted_at.is_(None),
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not locked:
        raise HTTPException(404, "Document not found")
    return locked


def document_response(document: Document, version: DocumentVersion | None, active=None, operation=None) -> DocumentResponse:
    return DocumentResponse(
        id=document.id, user_id=document.user_id, group_id=document.group_id, scope=document.scope, title=document.title,
        created_at=document.created_at, updated_at=document.updated_at,
        latest_version=DocumentVersionResponse.model_validate(version) if version else None,
        active_version=DocumentVersionResponse.model_validate(active) if active else None,
        operation=DocumentJobResponse.model_validate(operation) if operation else None,
        cleanup_status=document.cleanup_status, cleanup_error=document.cleanup_error, deleted_at=document.deleted_at,
    )


async def responses(session, documents):
    if not documents:
        return []
    ids = [doc.id for doc in documents]
    versions = (await session.scalars(select(DocumentVersion).where(DocumentVersion.document_id.in_(ids)).order_by(DocumentVersion.version_no.desc()))).all()
    by_id = {version.id: version for version in versions}
    newest = {}
    for version in versions:
        newest.setdefault(version.document_id, version)
    jobs = (await session.scalars(select(DocumentJob).where(DocumentJob.document_version_id.in_(by_id)).order_by(DocumentJob.created_at.desc()))).all() if by_id else []
    operations = {}
    for job in jobs:
        operations.setdefault(by_id[job.document_version_id].document_id, job)
    return [document_response(doc, newest.get(doc.id), by_id.get(doc.current_version_id), operations.get(doc.id)) for doc in documents]


async def response_for(session, document):
    return (await responses(session, [document]))[0]


class PreflightRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    group_id: uuid.UUID | None = None


class JobAcknowledgement(BaseModel):
    job_ids: list[uuid.UUID] = Field(max_length=1000)


@router.post("/preflight")
async def preflight(payload: PreflightRequest, user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    if payload.group_id and not await session.scalar(select(KnowledgeGroup.id).where(KnowledgeGroup.id == payload.group_id, KnowledgeGroup.user_id == user_id)):
        raise HTTPException(404, "分组不存在")
    return {"conflicts": await conflict_candidates(session, user_id, payload.group_id, payload.filename, payload.sha256)}


@router.get("/summary")
async def knowledge_summary(user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    items = await list_documents(user_id=user_id, session=session)
    result = {"processing": 0, "waiting": 0, "failed": 0, "completed": 0, "ready": 0, "completed_job_ids": []}
    for item in items:
        if item.deleted_at:
            result["failed" if item.cleanup_status == "failed" else "processing"] += 1
            continue
        if item.active_version:
            result["ready"] += 1
        if item.cleanup_status == "failed":
            result["failed"] += 1
        elif item.cleanup_status in {"pending", "running"}:
            result["processing"] += 1
        job = item.operation
        if not job:
            continue
        if job.status in {"queued", "running"}:
            if item.cleanup_status not in {"pending", "running"}:
                result["processing"] += 1
        elif job.status == "waiting_embedding":
            result["waiting"] += 1
        elif job.status == "failed":
            if item.cleanup_status != "failed":
                result["failed"] += 1
        elif job.status == "completed" and not job.acknowledged_at:
            result["completed"] += 1
            result["completed_job_ids"].append(str(job.id))
    return result


@router.post("/acknowledge", status_code=204)
async def acknowledge_jobs(payload: JobAcknowledgement, user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    owned_versions = select(DocumentVersion.id).join(Document, DocumentVersion.document_id == Document.id).where(Document.user_id == user_id, Document.scope == "long_term")
    await session.execute(update(DocumentJob).where(DocumentJob.id.in_(payload.job_ids), DocumentJob.document_version_id.in_(owned_versions), DocumentJob.status == "completed").values(acknowledged_at=datetime.now(UTC)))
    await session.commit()


def _validate_upload(filename: str, content_type: str | None, data: bytes) -> tuple[str, str]:
    extension = PurePath(filename).suffix.lower()
    settings = get_settings()
    if extension == ".pdf" or extension not in settings.allowed_document_extensions:
        raise _upload_error(400, "UNSUPPORTED_EXTENSION", f"不支持 {extension or '该'} 文件格式", "Unsupported document type")
    if len(data) > settings.max_upload_size_bytes:
        raise _upload_error(413, "FILE_TOO_LARGE", f"文件大小不能超过 {settings.max_upload_size_bytes} 字节", "Document is too large")
    declared = content_type or "application/octet-stream"
    expected = _MIME_BY_EXTENSION.get(extension, declared)
    if declared != "application/octet-stream" and declared != expected:
        if not (expected.startswith("text/") and declared.startswith("text/")):
            raise _upload_error(400, "MIME_MISMATCH", "文件类型与扩展名不匹配", "MIME type does not match file extension")
    if extension == ".pdf" and not data.startswith(b"%PDF"):
        raise _upload_error(400, "INVALID_FILE_HEADER", "文件头不是有效的 PDF", "Uploaded file is not a valid PDF")
    if extension == ".docx" and not data.startswith(b"PK"):
        raise _upload_error(400, "INVALID_FILE_HEADER", "文件头不是有效的 DOCX", "Uploaded file is not a valid DOCX")
    if extension in {".html", ".htm"} and b"<" not in data[:4096]:
        raise _upload_error(400, "INVALID_FILE_HEADER", "文件内容不是有效的 HTML 文档", "Uploaded file is not a valid HTML document")
    return extension, expected


async def read_limited_upload(file: UploadFile) -> bytes:
    limit = get_settings().max_upload_size_bytes
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise _upload_error(413, "FILE_TOO_LARGE", f"文件大小不能超过 {limit} 字节", "Document is too large")
    return data


@router.get("/policy")
async def get_upload_policy():
    return upload_policy()


@router.get("", response_model=list[DocumentResponse])
async def list_documents(group_id: uuid.UUID | None = None, user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    query = select(Document).where(Document.user_id == user_id, Document.scope == "long_term", or_(Document.deleted_at.is_(None), Document.cleanup_status != "completed")).order_by(Document.updated_at.desc())
    if group_id:
        query = query.where(Document.group_id == group_id)
    documents = (await session.scalars(query)).all()
    return await responses(session, documents)


@router.post("", response_model=DocumentResponse, status_code=202)
async def upload_document(
    group_id: uuid.UUID | None = Form(None), title: str | None = Form(None), file: UploadFile = File(...),
    conflict_action: str | None = Form(None), target_document_id: uuid.UUID | None = Form(None), upload_token: uuid.UUID | None = Form(None),
    user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session),
):
    group = None
    if group_id:
        group = await session.scalar(select(KnowledgeGroup).where(KnowledgeGroup.id == group_id, KnowledgeGroup.user_id == user_id))
        if not group:
            raise HTTPException(404, "Knowledge group not found")
    if upload_token:
        previous = await session.scalar(select(DocumentVersion).where(DocumentVersion.upload_token == upload_token))
        if previous:
            document = await owned_document(previous.document_id, user_id, session)
            return await response_for(session, document)
    filename = PurePath((file.filename or "document").replace("\\", "/")).name
    data = await read_limited_upload(file)
    extension, mime_type = _validate_upload(filename, file.content_type, data)
    # Serialize conflict decisions within one user's destination group.
    await session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:scope, 0))"), {"scope": f"{user_id}:{group_id}"})
    if upload_token:
        previous = await session.scalar(select(DocumentVersion).where(DocumentVersion.upload_token == upload_token))
        if previous:
            return await response_for(session, await owned_document(previous.document_id, user_id, session))
    digest = hashlib.sha256(data).hexdigest()
    conflicts = await conflict_candidates(session, user_id, group_id, filename, digest)
    if conflicts and conflict_action != "independent":
        target = next((c for c in conflicts if c["document_id"] == target_document_id), conflicts[0] if len(conflicts) == 1 and not target_document_id else None)
        if target and target["same_content"] and conflict_action != "new_version":
            return await response_for(session, await owned_document(target["document_id"], user_id, session))
        if conflict_action != "new_version" or not target:
            raise HTTPException(409, {"code": "NAME_CONFLICT", "message": "同分组存在同名文件，请选择新版本或独立文档", "conflicts": [{**c, "document_id": str(c["document_id"])} for c in conflicts]})
        document = await owned_document(target["document_id"], user_id, session)
        await _upload_version(document, file, title, session, data=data, upload_token=upload_token)
        return await response_for(session, document)
    if conflicts and conflict_action == "independent":
        now = datetime.now(timezone(timedelta(hours=8)))
        renamed = timestamp_filename(filename, now)
        sequence = 1
        while await conflict_candidates(session, user_id, group_id, renamed, digest):
            sequence += 1
            renamed = timestamp_filename(filename, now, sequence)
        filename = renamed
    document = Document(user_id=user_id, group_id=group_id, scope="long_term", filename=filename, title=(title or PurePath(filename).stem).strip()[:200] or "Untitled document")
    session.add(document)
    await session.flush()
    max_version = await session.scalar(select(func.max(DocumentVersion.version_no)).where(DocumentVersion.document_id == document.id)) or 0
    version_no = int(max_version) + 1
    key = object_key_for(str(user_id), str(group_id) if group_id else None, str(document.id), version_no, filename)
    version = DocumentVersion(
        document_id=document.id, version_no=version_no, original_filename=filename,
        mime_type=mime_type, extension=extension, size_bytes=len(data),
        sha256=digest, object_key=key, status="queued", upload_token=upload_token,
    )
    session.add(version)
    await session.flush()
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
    return await response_for(session, document)


async def _upload_version(document: Document, file: UploadFile, title: str | None, session: AsyncSession, *, data=None, upload_token=None) -> DocumentVersion:
    document = await _lock_document_for_version(document, session)
    if upload_token:
        previous = await session.scalar(select(DocumentVersion).where(DocumentVersion.upload_token == upload_token, DocumentVersion.document_id == document.id))
        if previous:
            return previous
    active = await session.scalar(select(DocumentJob.id).join(DocumentVersion, DocumentJob.document_version_id == DocumentVersion.id).where(DocumentVersion.document_id == document.id, DocumentJob.status.in_(ACTIVE_JOB_STATES)))
    if active:
        raise HTTPException(409, "此文档仍有处理任务，请等待完成或删除文档")
    filename = PurePath((file.filename or "document").replace("\\", "/")).name
    data = data if data is not None else await read_limited_upload(file)
    extension, mime_type = _validate_upload(filename, file.content_type, data)
    max_version = await session.scalar(
        select(func.max(DocumentVersion.version_no)).where(DocumentVersion.document_id == document.id)
    ) or 0
    version_no = int(max_version) + 1
    key = object_key_for(str(document.user_id), str(document.group_id) if document.group_id else None, str(document.id), version_no, filename)
    version = DocumentVersion(
        document_id=document.id, version_no=version_no, original_filename=filename,
        mime_type=mime_type, extension=extension, size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(), object_key=key, status="queued", upload_token=upload_token,
    )
    session.add(version)
    await session.flush()
    job = DocumentJob(document_version_id=version.id, stage="parsing", status="queued", attempts=0)
    session.add(job)
    document.filename = filename
    await S3Storage().put_bytes(key, data, mime_type)
    if title and title.strip():
        document.title = title.strip()[:200]
    await session.commit()
    try:
        await dispatch_document_job(str(job.id))
    except Exception:
        logger.exception("document version job dispatch failed", extra={"job_id": str(job.id)})
    return version


@router.post("/{document_id}/versions", response_model=DocumentVersionResponse, status_code=202)
async def upload_document_version(
    document_id: uuid.UUID, file: UploadFile = File(...), title: str | None = Form(None),
    upload_token: uuid.UUID | None = Form(None),
    user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session),
):
    document = await owned_document(document_id, user_id, session)
    return await _upload_version(document, file, title, session, upload_token=upload_token)


@router.get("/{document_id}/versions", response_model=list[DocumentVersionResponse])
async def list_document_versions(document_id: uuid.UUID, user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    document = await owned_document(document_id, user_id, session)
    return (await session.scalars(select(DocumentVersion).where(DocumentVersion.document_id == document.id).order_by(DocumentVersion.version_no.desc()))).all()


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: uuid.UUID, user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    document = await owned_document(document_id, user_id, session)
    return await response_for(session, document)


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
    version = await session.get(DocumentVersion, document.current_version_id) if document.current_version_id else await latest_version(document, session)
    if not version:
        raise HTTPException(404, "Document version not found")
    return DocumentPreviewResponse(document=await response_for(session, document), version=version, text=version.extracted_text or "")


@router.get("/{document_id}/download")
async def download_document(document_id: uuid.UUID, user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    document = await owned_document(document_id, user_id, session)
    version = await session.get(DocumentVersion, document.current_version_id) if document.current_version_id else await latest_version(document, session)
    if not version:
        raise HTTPException(404, "Document version not found")
    if version.storage_deleted_at:
        raise HTTPException(410, "原文件已清理，无法下载")
    return {"url": await S3Storage().presigned_get(version.object_key, filename=version.original_filename), "expires_in": 300}


@router.delete("/{document_id}", status_code=204)
async def delete_document(document_id: uuid.UUID, user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    document = await owned_document(document_id, user_id, session)
    await mark_document_deleted(session, document.id)


async def _reset_latest(document_id: uuid.UUID, user_id: uuid.UUID, session: AsyncSession, *, use_current=False) -> DocumentVersion:
    document = await owned_document(document_id, user_id, session)
    document = await _lock_document_for_version(document, session)
    version = await session.get(DocumentVersion, document.current_version_id) if use_current and document.current_version_id else await latest_version(document, session)
    if not version:
        raise HTTPException(404, "Document version not found")
    if version.extension == ".pdf" or version.storage_deleted_at or version.cleanup_pending:
        raise HTTPException(409, "当前文件不支持重新处理")
    if version.status != "indexed":
        version.status = "queued"
    version.error_code, version.error_message = None, None
    job = await session.scalar(
        select(DocumentJob).join(DocumentVersion, DocumentJob.document_version_id == DocumentVersion.id)
        .where(DocumentVersion.document_id == document.id, DocumentJob.status.in_(ACTIVE_JOB_STATES))
        .order_by(DocumentJob.created_at.desc())
        .limit(1)
    )
    if job:
        raise HTTPException(409, "Document job is already running")
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
    return await _reset_latest(document_id, user_id, session, use_current=True)
