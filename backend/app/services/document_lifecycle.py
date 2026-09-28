"""Shared transactional boundaries for ingestion, activation and deletion."""
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select, update

from ..models import Citation, Document, DocumentChunk, DocumentJob, DocumentVersion, KnowledgeGroup

ACTIVE_JOB_STATES = ("queued", "running", "waiting_embedding")


async def lock_document(session, document_id: UUID) -> Document | None:
    return await session.scalar(select(Document).where(Document.id == document_id).with_for_update().execution_options(populate_existing=True))


async def archive_chunk_citations(session, chunk_filter) -> None:
    rows = (await session.execute(select(Citation, DocumentChunk, DocumentVersion, Document, KnowledgeGroup).join(DocumentChunk, Citation.chunk_id == DocumentChunk.id).join(DocumentVersion, DocumentChunk.document_version_id == DocumentVersion.id).join(Document, DocumentVersion.document_id == Document.id).outerjoin(KnowledgeGroup, Document.group_id == KnowledgeGroup.id).where(chunk_filter))).all()
    for citation, chunk, version, document, group in rows:
        citation.chunk_id_snapshot = chunk.id
        citation.document_id_snapshot = document.id
        citation.document_title_snapshot = document.title
        citation.original_filename_snapshot = version.original_filename
        citation.group_name_snapshot = group.name if group else None
        citation.source_scope = document.scope
    await session.flush()


async def purge_chunks(session, chunk_filter) -> None:
    await archive_chunk_citations(session, chunk_filter)
    await session.execute(delete(DocumentChunk).where(chunk_filter))


async def mark_document_deleted(session, document_id: UUID) -> None:
    document = await lock_document(session, document_id)
    if not document:
        return
    document.deleted_at = document.deleted_at or datetime.now(UTC)
    document.current_version_id = None
    document.cleanup_status, document.cleanup_error = "pending", None
    version_ids = select(DocumentVersion.id).where(DocumentVersion.document_id == document_id)
    await session.execute(update(DocumentVersion).where(DocumentVersion.document_id == document_id).values(cleanup_pending=True))
    await session.execute(update(DocumentJob).where(DocumentJob.document_version_id.in_(version_ids), DocumentJob.status.in_(ACTIVE_JOB_STATES)).values(status="cancelled", locked_at=None, locked_by=None, finished_at=datetime.now(UTC)))
    await session.commit()
