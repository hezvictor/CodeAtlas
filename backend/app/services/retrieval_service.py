from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Document, DocumentChunk, DocumentVersion
from ..providers.embedding import EmbeddingProvider
from ..retrieval import RankedChunk, assemble_neighbor_context, rerank_chunks_async, rrf_merge


def authorized_chunks(user_id):
    return select(DocumentChunk).join(DocumentVersion, DocumentChunk.document_version_id == DocumentVersion.id).join(Document, DocumentVersion.document_id == Document.id).where(
        Document.user_id == user_id, Document.scope == "long_term", Document.deleted_at.is_(None),
        DocumentVersion.status == "indexed", Document.current_version_id == DocumentVersion.id,
        DocumentChunk.index_job_id.is_not_distinct_from(DocumentVersion.active_index_job_id),
    )


def ranked(row):
    return RankedChunk(row.id, row.content, 0.0, row.locator, "knowledge", row.document_version_id, row.ordinal)


async def read_context(session, user_id, evidence_id, radius=1):
    anchor = await session.scalar(authorized_chunks(user_id).where(DocumentChunk.id == UUID(evidence_id)))
    if not anchor:
        return []
    neighbors = list((await session.scalars(authorized_chunks(user_id).where(
        DocumentChunk.document_version_id == anchor.document_version_id,
        DocumentChunk.ordinal.between(max(0, anchor.ordinal - radius), anchor.ordinal + radius),
    ).order_by(DocumentChunk.ordinal))).all())
    result = ranked(anchor)
    result.context_content = assemble_neighbor_context(result, [ranked(row) for row in neighbors])
    return [result]


async def retrieve_chunks(session: AsyncSession, user_id: UUID, query: str, limit=10,
                          embedding_provider=None, queries=None, reranker=None):
    if not await session.scalar(authorized_chunks(user_id).limit(1)):
        return []
    keyword, vector = [], []
    provider = embedding_provider or EmbeddingProvider()
    for search_query in list(dict.fromkeys([query, *(queries or [])]))[:3]:
        tsquery = func.plainto_tsquery("simple", search_query)
        rows = (await session.scalars(authorized_chunks(user_id).where(
            DocumentChunk.search_vector.op("@@")(tsquery)
        ).order_by(func.ts_rank(DocumentChunk.search_vector, tsquery).desc()).limit(limit * 2))).all()
        keyword.extend(ranked(row) for row in rows)
        query_vector = await provider.embed_query(search_query)
        rows = (await session.scalars(authorized_chunks(user_id).where(DocumentChunk.embedding.is_not(None))
                                    .order_by(DocumentChunk.embedding.cosine_distance(query_vector)).limit(limit * 2))).all()
        vector.extend(ranked(row) for row in rows)
    selected = (await rerank_chunks_async(query, rrf_merge(keyword, vector, min(limit * 2, 20)), reranker))[:limit]
    for item in selected:
        neighbors = await read_context(session, user_id, str(item.chunk_id))
        if neighbors:
            item.context_content = neighbors[0].prompt_content
    return selected
