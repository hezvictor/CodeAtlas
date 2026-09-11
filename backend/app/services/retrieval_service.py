from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Attachment, Document, DocumentChunk, DocumentVersion
from ..providers.embedding import EmbeddingProvider
from ..retrieval import RankedChunk, rrf_merge


async def retrieve_chunks(
    session: AsyncSession,
    user_id: UUID,
    query: str,
    group_ids: list[UUID] | None = None,
    attachment_ids: list[UUID] | None = None,
    limit: int = 10,
    embedding_provider: EmbeddingProvider | None = None,
) -> list[RankedChunk]:
    filters = [Document.user_id == user_id, Document.deleted_at.is_(None), DocumentVersion.status == "indexed"]
    if group_ids:
        filters.append(Document.group_id.in_(group_ids))
    if attachment_ids:
        filters.append(DocumentVersion.id.in_(select(Attachment.document_version_id).where(Attachment.id.in_(attachment_ids), Attachment.user_id == user_id)))
    keyword_rows = (await session.execute(
        select(DocumentChunk).join(DocumentVersion, DocumentChunk.document_version_id == DocumentVersion.id).join(Document, DocumentVersion.document_id == Document.id)
        .where(*filters, DocumentChunk.search_vector.op("@@")(func.plainto_tsquery("simple", query)))
        .order_by(func.ts_rank(DocumentChunk.search_vector, func.plainto_tsquery("simple", query)).desc())
        .limit(limit * 2)
    )).scalars().all()
    keyword = [RankedChunk(row.id, row.content, 0.0, row.locator) for row in keyword_rows]
    provider = embedding_provider or EmbeddingProvider()
    query_vector = await provider.embed_query(query)
    vector_rows = (await session.execute(
        select(DocumentChunk).join(DocumentVersion, DocumentChunk.document_version_id == DocumentVersion.id).join(Document, DocumentVersion.document_id == Document.id)
        .where(*filters, DocumentChunk.embedding.is_not(None))
        .order_by(DocumentChunk.embedding.cosine_distance(query_vector))
        .limit(limit * 2)
    )).scalars().all()
    vector = [RankedChunk(row.id, row.content, 0.0, row.locator) for row in vector_rows]
    return rrf_merge(keyword, vector, limit=limit)
