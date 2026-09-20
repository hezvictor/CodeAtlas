import logging
import socket
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, update

from ..chunking import chunk_document
from ..config import get_settings
from ..db import session_factory
from ..models import Document, DocumentChunk, DocumentJob, DocumentVersion, EmbeddingConfig
from ..parsers import parse_document
from ..providers.embedding import UserEmbeddingProvider
from ..storage.s3 import S3Storage

logger = logging.getLogger(__name__)


async def cleanup_deleted_document_objects(_ctx=None) -> int:
    """Delete objects for soft-deleted documents; each attempt is durable and idempotent."""
    cleaned = 0
    async with session_factory() as session:
        versions = (await session.scalars(
            select(DocumentVersion)
            .join(Document, DocumentVersion.document_id == Document.id)
            .where(Document.deleted_at.is_not(None), DocumentVersion.storage_deleted_at.is_(None))
            .order_by(DocumentVersion.storage_delete_attempts, DocumentVersion.created_at)
            .limit(100)
        )).all()
        storage = S3Storage()
        for version in versions:
            version.storage_delete_attempts += 1
            try:
                await storage.delete(version.object_key)
                version.storage_deleted_at = datetime.now(UTC)
                version.storage_delete_error = None
                cleaned += 1
            except Exception as error:
                version.storage_delete_error = str(error)[:500]
        await session.commit()
    return cleaned


async def process_document(_ctx, job_id: str) -> dict:
    async with session_factory() as session:
        job = await session.scalar(select(DocumentJob).where(DocumentJob.id == job_id).with_for_update())
        if not job:
            return {"status": "missing", "job_id": job_id}
        now = datetime.now(UTC)
        if job.status != "queued":
            return {"status": "duplicate", "job_id": job_id, "job_status": job.status}
        if job.available_at and job.available_at > now:
            return {"status": "deferred", "job_id": job_id}
        job.status, job.stage, job.attempts = "running", "parsing", job.attempts + 1
        job.locked_at, job.locked_by = now, socket.gethostname()
        job.error_message, job.last_dispatch_error = None, None
        await session.commit()
        version = await session.get(DocumentVersion, job.document_version_id)
        if not version:
            job.status, job.finished_at = "failed", datetime.now(UTC)
            await session.commit()
            return {"status": "missing", "job_id": job_id}
        document = await session.get(Document, version.document_id)
        if not document:
            job.status, job.finished_at = "failed", datetime.now(UTC)
            await session.commit()
            return {"status": "missing", "job_id": job_id}
        embedding_config = await session.scalar(
            select(EmbeddingConfig).where(EmbeddingConfig.user_id == document.user_id)
        )
        if not embedding_config or embedding_config.status != "verified":
            version.status = "waiting_embedding"
            job.status, job.stage = "waiting_embedding", "embedding"
            job.locked_at, job.locked_by = None, None
            job.error_message = "Embedding configuration is not verified"
            await session.commit()
            return {"status": "waiting_embedding", "version_id": str(version.id), "job_id": job_id}
        try:
            version.status = "parsing"
            await session.commit()
            data = await S3Storage().get_bytes(version.object_key)
            parsed = parse_document(version.original_filename, version.mime_type, data)
            if len(parsed.text) > get_settings().max_extracted_text_chars:
                raise ValueError("Document text exceeds configured limit")
            version.extracted_text = parsed.text
            version.status = "chunking"
            await session.commit()
            chunks = chunk_document(parsed)
            await session.execute(delete(DocumentChunk).where(DocumentChunk.document_version_id == version.id))
            records = [DocumentChunk(document_version_id=version.id, ordinal=chunk.ordinal, content=chunk.content, content_hash=chunk.content_hash, token_count=chunk.token_count, page_start=chunk.page_start, page_end=chunk.page_end, line_start=chunk.line_start, line_end=chunk.line_end, section_path=chunk.section_path, char_start=chunk.char_start, char_end=chunk.char_end, locator=chunk.locator) for chunk in chunks]
            session.add_all(records)
            await session.flush()
            version.status = "embedding"
            await session.commit()
            vectors = await UserEmbeddingProvider(session, document.user_id).embed_documents([chunk.content for chunk in chunks]) if chunks else []
            for record, vector in zip(records, vectors, strict=True):
                record.embedding = vector
            await session.flush()
            await session.execute(update(DocumentChunk).where(DocumentChunk.document_version_id == version.id).values(search_vector=func.to_tsvector("simple", DocumentChunk.content)))
            version.status, version.indexed_at = "indexed", datetime.now(UTC)
            if job:
                job.status, job.stage, job.finished_at = "completed", "indexed", datetime.now(UTC)
                job.locked_at, job.locked_by = None, None
            await session.commit()
            return {"status": "indexed", "version_id": str(version.id), "job_id": job_id, "chunks": len(records)}
        except Exception as error:
            logger.exception("document processing failed", extra={"version_id": str(version.id), "job_id": job_id})
            message = str(error)[:500]
            version.error_code, version.error_message = "DOCUMENT_PROCESSING_FAILED", message
            if job.attempts < get_settings().document_job_max_attempts:
                job.status = "queued"
                job.available_at = datetime.now(UTC) + timedelta(seconds=min(300, 2 ** job.attempts * 5))
                job.last_dispatch_at, job.locked_at, job.locked_by = None, None, None
                job.error_message = message
                version.status = "uploaded"
            else:
                version.status = "failed"
                job.status, job.locked_at, job.locked_by, job.finished_at = "failed", None, None, datetime.now(UTC)
                job.error_message = message
            await session.commit()
            if job.status == "failed":
                raise
            return {"status": "retry_scheduled", "version_id": str(version.id), "job_id": job_id}
