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
        records.append(Citation(message_id=message_id, chunk_id=item.chunk_id, quote=item.content[:500], score=item.score, rank=rank, locator=item.locator or {}, is_valid=True))
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
        .join(DocumentChunk, Citation.chunk_id == DocumentChunk.id)
        .join(DocumentVersion, DocumentChunk.document_version_id == DocumentVersion.id)
        .join(Document, DocumentVersion.document_id == Document.id)
        .outerjoin(KnowledgeGroup, Document.group_id == KnowledgeGroup.id)
        .where(
            Citation.message_id == message_id,
            Message.conversation_id == conversation_id,
            Conversation.user_id == user_id,
            Document.user_id == user_id,
            Citation.is_valid.is_(True),
        )
        .order_by(Citation.rank, Citation.created_at)
    )
    rows = (await session.execute(stmt)).all()
    return [
        {
            "id": citation.id,
            "chunk_id": citation.chunk_id,
            "document_id": document.id,
            "document_title": document.title,
            "original_filename": version.original_filename,
            "group_id": group.id if group else None,
            "group_name": group.name if group else None,
            "source_scope": document.scope,
            "quote": citation.quote,
            "score": citation.score,
            "rank": citation.rank,
            "locator": citation.locator or {},
            "citation_marker": f"[cite:{citation.chunk_id}]",
        }
        for citation, _chunk, version, document, group in rows
    ]
