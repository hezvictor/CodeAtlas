from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Attachment, Document, DocumentChunk, DocumentVersion
from ..providers.embedding import EmbeddingProvider
from ..retrieval import RankedChunk, assemble_neighbor_context, rerank_chunks_async, rrf_merge


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
    attachment_ids: list[UUID] | None = None,
    limit: int = 10,
    embedding_provider: EmbeddingProvider | None = None,
    knowledge_scope: str | None = None,
    queries: list[str] | None = None,
    reranker=None,
) -> list[RankedChunk]:
    attachment_ids = list(dict.fromkeys(attachment_ids or []))
    scope = knowledge_scope or "all"
    if scope not in {"none", "all"}:
        raise ValueError("knowledge_scope must be one of: none, all")
    if scope == "none":
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
    filters = [Document.user_id == user_id, Document.deleted_at.is_(None), DocumentVersion.status == "indexed", Document.current_version_id == DocumentVersion.id, DocumentChunk.index_job_id.is_not_distinct_from(DocumentVersion.active_index_job_id)]
    scope_filters = []
    if scope == "all":
        scope_filters.append(Document.scope == "long_term")
    if attachment_ids:
        scope_filters.append(
            DocumentVersion.id.in_(
                build_attachment_statement(user_id, conversation_id, attachment_ids)
            )
        )
    if scope_filters:
        filters.append(or_(*scope_filters))
    search_queries = list(dict.fromkeys([query, *(queries or [])]))
    keyword: list[RankedChunk] = []
    vector: list[RankedChunk] = []
    provider = embedding_provider or EmbeddingProvider()
    for search_query in search_queries:
        keyword_rows = (await session.execute(
            select(DocumentChunk, Document.scope).join(DocumentVersion, DocumentChunk.document_version_id == DocumentVersion.id).join(Document, DocumentVersion.document_id == Document.id)
            .where(*filters, DocumentChunk.search_vector.op("@@")(func.plainto_tsquery("simple", search_query)))
            .order_by(func.ts_rank(DocumentChunk.search_vector, func.plainto_tsquery("simple", search_query)).desc())
            .limit(limit * 2)
        )).all()
        keyword.extend(
            RankedChunk(
                row.id, row.content, 0.0, row.locator,
                "session" if source_scope == "session" else "knowledge",
                row.document_version_id, row.ordinal,
            )
            for row, source_scope in keyword_rows
        )
        query_vector = await provider.embed_query(search_query)
        vector_rows = (await session.execute(
            select(DocumentChunk, Document.scope).join(DocumentVersion, DocumentChunk.document_version_id == DocumentVersion.id).join(Document, DocumentVersion.document_id == Document.id)
            .where(*filters, DocumentChunk.embedding.is_not(None))
            .order_by(DocumentChunk.embedding.cosine_distance(query_vector))
            .limit(limit * 2)
        )).all()
        vector.extend(
            RankedChunk(
                row.id, row.content, 0.0, row.locator,
                "session" if source_scope == "session" else "knowledge",
                row.document_version_id, row.ordinal,
            )
            for row, source_scope in vector_rows
        )
    merged = rrf_merge(keyword, vector, limit=min(limit * 2, 20))
    selected = (await rerank_chunks_async(query, merged, reranker))[:limit]
    if not selected:
        return []
    version_ids = {item.document_version_id for item in selected if item.document_version_id}
    if not version_ids:
        return selected
    for item in selected:
        if item.document_version_id is None or item.ordinal is None:
            continue
        neighbors = (await session.scalars(
            select(DocumentChunk)
            .where(
                DocumentChunk.document_version_id == item.document_version_id,
                DocumentChunk.index_job_id.is_not_distinct_from(select(DocumentVersion.active_index_job_id).where(DocumentVersion.id == item.document_version_id).scalar_subquery()),
                DocumentChunk.ordinal.between(max(0, item.ordinal - 1), item.ordinal + 1),
                DocumentChunk.id != item.chunk_id,
            )
            .order_by(DocumentChunk.ordinal)
        )).all()
        item.context_content = assemble_neighbor_context(
            item,
            [
                RankedChunk(
                    row.id, row.content, 0.0, row.locator,
                    item.source_type, row.document_version_id, row.ordinal,
                )
                for row in neighbors
            ],
        )
    return selected
