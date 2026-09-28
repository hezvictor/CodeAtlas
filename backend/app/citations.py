import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Citation, Document, DocumentChunk, DocumentVersion, KnowledgeGroup, Message
from .retrieval import RankedChunk

_CITATION = re.compile(r"\[cite:([^\]]+)\]")


def validate_citations(text: str, allowed_ids: set[str]) -> tuple[str, list[str]]:
    valid: list[str] = []

    def replace(match: re.Match[str]) -> str:
        identifier = match.group(1)
        if identifier in allowed_ids:
            valid.append(identifier)
            return match.group(0)
        return ""

    return _CITATION.sub(replace, text), valid


async def persist_citations(session: AsyncSession, message_id: UUID, text: str, retrieved: list[RankedChunk]) -> tuple[str, list[Citation]]:
    cleaned, valid_ids = validate_citations(text, {str(item.chunk_id) for item in retrieved})
    by_id = {str(item.chunk_id): item for item in retrieved}
    records = []
    for rank, identifier in enumerate(dict.fromkeys(valid_ids), 1):
        item = by_id[identifier]
        # Hold a key-share lock until the caller commits so cleanup cannot
        # remove a chunk between this check and insertion of its citation.
        chunk_id = await session.scalar(select(DocumentChunk.id).where(DocumentChunk.id == item.chunk_id).with_for_update(read=True, key_share=True))
        record = Citation(message_id=message_id, chunk_id=chunk_id, chunk_id_snapshot=item.chunk_id, quote=item.content[:500], score=item.score, rank=rank, locator=item.locator or {}, is_valid=True)
        metadata = (await session.execute(select(DocumentVersion, Document, KnowledgeGroup).join(Document, DocumentVersion.document_id == Document.id).outerjoin(KnowledgeGroup, Document.group_id == KnowledgeGroup.id).where(DocumentVersion.id == item.document_version_id))).first() if item.document_version_id else None
        if metadata:
            version, document, group = metadata
            record.document_id_snapshot = document.id
            record.document_title_snapshot = document.title
            record.original_filename_snapshot = version.original_filename
            record.group_name_snapshot = group.name if group else None
            record.source_scope = document.scope
        records.append(record)
    session.add_all(records)
    return cleaned, records


async def citation_sources(
    session: AsyncSession,
    message_id: UUID,
    conversation_id: UUID,
    user_id: UUID,
) -> list[dict]:
    """Load citation rows with document metadata, enforcing user ownership.

    The join through Message and Conversation scope prevents a user from
    reading a citation by guessing either a message or chunk UUID.
    """
    from .models import Conversation

    stmt = (
        select(Citation, DocumentChunk, DocumentVersion, Document, KnowledgeGroup)
        .join(Message, Citation.message_id == Message.id)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .outerjoin(DocumentChunk, Citation.chunk_id == DocumentChunk.id)
        .outerjoin(DocumentVersion, DocumentChunk.document_version_id == DocumentVersion.id)
        .outerjoin(Document, DocumentVersion.document_id == Document.id)
        .outerjoin(KnowledgeGroup, Document.group_id == KnowledgeGroup.id)
        .where(
            Citation.message_id == message_id,
            Message.conversation_id == conversation_id,
            Conversation.user_id == user_id,
            Citation.is_valid.is_(True),
        )
        .order_by(Citation.rank, Citation.created_at)
    )
    rows = (await session.execute(stmt)).all()
    return [
        {
            "id": citation.id,
            "chunk_id": citation.chunk_id_snapshot or citation.chunk_id,
            "document_id": document.id if document else citation.document_id_snapshot,
            "document_title": document.title if document else citation.document_title_snapshot,
            "original_filename": version.original_filename if version else citation.original_filename_snapshot,
            "group_id": group.id if group else None,
            "group_name": group.name if group else citation.group_name_snapshot,
            "source_scope": document.scope if document else citation.source_scope,
            "source_deleted": document is None or document.deleted_at is not None,
            "quote": citation.quote,
            "score": citation.score,
            "rank": citation.rank,
            "locator": citation.locator or {},
            "citation_marker": f"[cite:{citation.chunk_id_snapshot or citation.chunk_id}]",
        }
        for citation, _chunk, version, document, group in rows
    ]
