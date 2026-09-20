from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Attachment, Document, DocumentChunk, DocumentVersion
from ..providers.embedding import EmbeddingProvider
from ..retrieval import RankedChunk, rrf_merge


def build_attachment_statement(
    user_id: UUID, conversation_id: UUID, attachment_ids: list[UUID]
):
    return select(Attachment.document_version_id).where(
        Attachment.id.in_(attachment_ids),
        Attachment.user_id == user_id,
        Attachment.conversation_id == conversation_id,
    )


async def retrieve_chunks(
    session: AsyncSession,
    user_id: UUID,
    conversation_id: UUID,
    query: str,
    group_ids: list[UUID] | None = None,
    attachment_ids: list[UUID] | None = None,
    limit: int = 10,
    embedding_provider: EmbeddingProvider | None = None,
    knowledge_scope: str | None = None,
) -> list[RankedChunk]:
    group_ids = list(dict.fromkeys(group_ids or []))
    attachment_ids = list(dict.fromkeys(attachment_ids or []))
    scope = knowledge_scope or "all"
    if scope not in {"none", "all", "groups"}:
        raise ValueError("knowledge_scope must be one of: none, all, groups")
    if scope == "none" and not attachment_ids:
        return []
    if not attachment_ids:
        attachment_ids = list(
            (await session.scalars(
                select(Attachment.id).where(
                    Attachment.user_id == user_id,
                    Attachment.conversation_id == conversation_id,
                )
            )).all()
        )
    if scope == "groups" and not group_ids and not attachment_ids:
        raise ValueError("knowledge_group_ids is required when knowledge_scope is groups")

    filters = [Document.user_id == user_id, Document.deleted_at.is_(None), DocumentVersion.status == "indexed"]
    scope_filters = []
    if scope == "all":
        scope_filters.append(Document.scope == "long_term")
    elif scope == "groups" and group_ids:
        scope_filters.append(Document.group_id.in_(group_ids))
    if attachment_ids:
        scope_filters.append(
            DocumentVersion.id.in_(
                build_attachment_statement(user_id, conversation_id, attachment_ids)
            )
        )
    if scope_filters:
        filters.append(or_(*scope_filters))
    keyword_rows = (await session.execute(
        select(DocumentChunk, Document.scope).join(DocumentVersion, DocumentChunk.document_version_id == DocumentVersion.id).join(Document, DocumentVersion.document_id == Document.id)
        .where(*filters, DocumentChunk.search_vector.op("@@")(func.plainto_tsquery("simple", query)))
        .order_by(func.ts_rank(DocumentChunk.search_vector, func.plainto_tsquery("simple", query)).desc())
        .limit(limit * 2)
    )).all()
    keyword = [RankedChunk(row.id, row.content, 0.0, row.locator, scope) for row, scope in keyword_rows]
    provider = embedding_provider or EmbeddingProvider()
    query_vector = await provider.embed_query(query)
    vector_rows = (await session.execute(
        select(DocumentChunk, Document.scope).join(DocumentVersion, DocumentChunk.document_version_id == DocumentVersion.id).join(Document, DocumentVersion.document_id == Document.id)
        .where(*filters, DocumentChunk.embedding.is_not(None))
        .order_by(DocumentChunk.embedding.cosine_distance(query_vector))
        .limit(limit * 2)
    )).all()
    vector = [RankedChunk(row.id, row.content, 0.0, row.locator, scope) for row, scope in vector_rows]
    return rrf_merge(keyword, vector, limit=limit)
