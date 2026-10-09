import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select, update

from ..chunking import chunk_document
from ..config import get_settings
from ..db import session_factory
from ..models import Document, DocumentChunk, DocumentJob, DocumentVersion, EmbeddingConfig
from ..parsers import parse_document
from ..providers.embedding import (
    UserEmbeddingProvider,
    processing_error,
    project_embedding_is_configured,
)
from ..services.document_lifecycle import lock_document, purge_chunks
from ..storage.s3 import S3Storage

logger = logging.getLogger(__name__)


class JobCancelled(Exception):
    pass


async def _checkpoint(session, document_id, job_id, lease):
    document = await lock_document(session, document_id)
    job = await session.scalar(select(DocumentJob).where(DocumentJob.id == job_id).with_for_update().execution_options(populate_existing=True))
    if not document or document.scope != "long_term" or document.deleted_at or not job or job.status != "running" or job.locked_by != lease:
        raise JobCancelled()
    job.locked_at = datetime.now(UTC)
    return document, job


def _stage(version, job, stage):
    job.stage = stage
    if version.status != "indexed":
        version.status = stage


async def cleanup_deleted_document_objects(_ctx=None) -> int:
    """Purge superseded/deleted content with durable, idempotent retries."""
    cleaned = 0
    async with session_factory() as session:
        ids = (await session.scalars(select(DocumentVersion.id).join(Document, DocumentVersion.document_id == Document.id).where(Document.scope == "long_term", DocumentVersion.cleanup_pending.is_(True)).order_by(DocumentVersion.storage_delete_attempts, DocumentVersion.created_at).limit(100))).all()
    for version_id in ids:
        async with session_factory() as session:
            version = await session.get(DocumentVersion, version_id)
            if not version:
                continue
            document = await lock_document(session, version.document_id)
            await session.refresh(version)
            if not document or not version.cleanup_pending or (not document.deleted_at and document.current_version_id == version.id):
                continue
            document.cleanup_status = "running"
            version.storage_delete_attempts += 1
            document_id = document.id
            try:
                await purge_chunks(session, DocumentChunk.document_version_id == version.id)
                version.extracted_text, version.active_index_job_id = None, None
                version.content_deleted_at = datetime.now(UTC)
                if not version.storage_deleted_at:
                    await S3Storage().delete(version.object_key)
                    version.storage_deleted_at = datetime.now(UTC)
                version.cleanup_pending, version.storage_delete_error = False, None
                version.status = "deleted" if document.deleted_at else "archived"
                cleaned += 1
            except Exception:
                logger.exception("document cleanup failed", extra={"version_id": str(version_id)})
                await session.rollback()
                document = await lock_document(session, document_id)
                version = await session.get(DocumentVersion, version_id, populate_existing=True)
                version.storage_delete_attempts += 1
                version.storage_delete_error = "原文件清理失败，系统将自动重试"
                document.cleanup_status, document.cleanup_error = "failed", version.storage_delete_error
            await session.commit()
            document = await lock_document(session, document.id)
            remaining = await session.scalar(select(func.count()).select_from(DocumentVersion).where(DocumentVersion.document_id == document.id, DocumentVersion.cleanup_pending.is_(True)))
            if not remaining:
                document.cleanup_status, document.cleanup_error = "completed", None
            elif document.cleanup_status != "failed":
                document.cleanup_status = "pending"
            await session.commit()
    return cleaned


async def process_document(_ctx, job_id: str) -> dict:
    async with session_factory() as session:
        job = await session.scalar(select(DocumentJob).where(DocumentJob.id == job_id))
        if not job:
            return {"status": "missing", "job_id": job_id}
        if job.status != "queued":
            return {"status": "duplicate", "job_id": job_id, "job_status": job.status}
        version = await session.get(DocumentVersion, job.document_version_id)
        if not version:
            return {"status": "missing", "job_id": job_id}
        document = await lock_document(session, version.document_id)
        await session.refresh(job, with_for_update=True)
        if not document or document.scope != "long_term" or document.deleted_at:
            job.status = "cancelled"
            await session.commit()
            return {"status": "cancelled", "job_id": job_id}
        if job.status != "queued" or (job.available_at and job.available_at > datetime.now(UTC)):
            return {"status": "deferred", "job_id": job_id}
        lease = str(uuid4())
        job.status, job.stage, job.attempts = "running", "parsing", job.attempts + 1
        job.locked_at, job.locked_by = datetime.now(UTC), lease
        job.error_message, job.error_code = None, None
        job.completed_chunks, job.total_chunks = 0, 0
        supported = version.extension in get_settings().allowed_document_extensions
        config = await session.scalar(select(EmbeddingConfig).where(EmbeddingConfig.user_id == document.user_id))
        if supported and ((config and config.status != "verified") or (not config and not project_embedding_is_configured())):
            _stage(version, job, "waiting_embedding")
            job.status, job.locked_at, job.locked_by = "waiting_embedding", None, None
            job.attempts -= 1
            job.error_message = "原文件已保存，等待配置 Embedding；目前不可检索"
            await session.commit()
            return {"status": "waiting_embedding", "job_id": job_id}
        _stage(version, job, "parsing")
        await session.commit()
        document_id, version_id, actual_job_id = document.id, version.id, job.id
        try:
            if not supported:
                raise ValueError("此文件格式不支持处理，可下载原文件或删除")
            data = await S3Storage().get_bytes(version.object_key)
            parsed = parse_document(version.original_filename, version.mime_type, data)
            if len(parsed.text) > get_settings().max_extracted_text_chars:
                raise ValueError("提取文本超出处理长度限制")
            document, job = await _checkpoint(session, document_id, actual_job_id, lease)
            _stage(version, job, "chunking")
            await session.commit()
            chunks = chunk_document(parsed)
            if not chunks or any(not chunk.content.strip() for chunk in chunks):
                raise ValueError("无法提取可索引文本，请检查文件内容")
            document, job = await _checkpoint(session, document_id, actual_job_id, lease)
            await purge_chunks(session, (DocumentChunk.document_version_id == version_id) & (DocumentChunk.index_job_id == job.id))
            records = [DocumentChunk(document_version_id=version_id, index_job_id=job.id, ordinal=c.ordinal, content=c.content, content_hash=c.content_hash, token_count=c.token_count, page_start=c.page_start, page_end=c.page_end, line_start=c.line_start, line_end=c.line_end, section_path=c.section_path, char_start=c.char_start, char_end=c.char_end, locator=c.locator) for c in chunks]
            session.add_all(records)
            job.total_chunks = len(records)
            if document.current_version_id != version_id:
                version.extracted_text = parsed.text
            _stage(version, job, "embedding")
            await session.commit()
            provider = UserEmbeddingProvider(session, document.user_id)
            size = max(1, min(10, get_settings().embedding_batch_size))
            for offset in range(0, len(records), size):
                vectors = await provider.embed_documents([c.content for c in chunks[offset:offset + size]])
                document, job = await _checkpoint(session, document_id, actual_job_id, lease)
                for record, vector in zip(records[offset:offset + size], vectors, strict=True):
                    record.embedding = vector
                job.completed_chunks = offset + len(vectors)
                await session.commit()
            document, job = await _checkpoint(session, document_id, actual_job_id, lease)
            _stage(version, job, "committing")
            await session.commit()
            document, job = await _checkpoint(session, document_id, actual_job_id, lease)
            count = await session.scalar(select(func.count()).select_from(DocumentChunk).where(DocumentChunk.index_job_id == job.id, DocumentChunk.embedding.is_not(None)))
            if count != len(records):
                raise ValueError("向量数据不完整，索引未启用")
            await session.execute(update(DocumentChunk).where(DocumentChunk.index_job_id == job.id).values(search_vector=func.to_tsvector("simple", DocumentChunk.content)))
            version.active_index_job_id = job.id
            version.extracted_text = parsed.text
            version.status, version.indexed_at = "indexed", datetime.now(UTC)
            version.error_code, version.error_message = None, None
            document.current_version_id, document.filename = version_id, version.original_filename
            document.updated_at = datetime.now(UTC)
            await session.execute(update(DocumentVersion).where(DocumentVersion.document_id == document_id, DocumentVersion.id != version_id).values(cleanup_pending=True, status="archived"))
            if await session.scalar(select(DocumentVersion.id).where(DocumentVersion.document_id == document_id, DocumentVersion.cleanup_pending.is_(True)).limit(1)):
                document.cleanup_status, document.cleanup_error = "pending", None
            await purge_chunks(session, (DocumentChunk.document_version_id == version_id) & DocumentChunk.index_job_id.is_distinct_from(job.id))
            job.status, job.stage, job.finished_at = "completed", "indexed", datetime.now(UTC)
            job.locked_at, job.locked_by = None, None
            await session.commit()
            return {"status": "indexed", "version_id": str(version_id), "job_id": job_id, "chunks": len(records)}
        except JobCancelled:
            await session.rollback()
            return {"status": "cancelled", "job_id": job_id}
        except Exception as error:
            await session.rollback()
            try:
                document, job = await _checkpoint(session, document_id, actual_job_id, lease)
            except JobCancelled:
                return {"status": "cancelled", "job_id": job_id}
            version = await session.get(DocumentVersion, version_id, populate_existing=True)
            code, message, retryable = processing_error(error)
            logger.warning("document processing failed", extra={"job_id": job_id, "error_code": code})
            job.error_code, job.error_message = code, message
            version.error_code, version.error_message = code, message
            await purge_chunks(session, DocumentChunk.index_job_id == job.id)
            job.locked_at, job.locked_by = None, None
            if retryable and job.attempts < get_settings().document_job_max_attempts:
                job.status = "queued"
                job.available_at = datetime.now(UTC) + timedelta(seconds=min(300, 2 ** job.attempts * 5))
                job.last_dispatch_at = None
                if document.current_version_id != version_id:
                    version.status = "retry_wait"
                result = "retry_scheduled"
            else:
                job.status, job.finished_at = "failed", datetime.now(UTC)
                if document.current_version_id != version_id:
                    version.status = "failed"
                result = "failed"
            await session.commit()
            return {"status": result, "job_id": job_id, "version_id": str(version_id)}
