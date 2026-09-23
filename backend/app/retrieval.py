from collections.abc import Callable
from dataclasses import dataclass
from inspect import isawaitable
from uuid import UUID


@dataclass(slots=True)
class RankedChunk:
    chunk_id: UUID
    content: str
    score: float
    locator: dict | None = None
    source_type: str = "knowledge"
    document_version_id: UUID | None = None
    ordinal: int | None = None
    context_content: str | None = None

    @property
    def prompt_content(self) -> str:
        return self.context_content or self.content


def assemble_neighbor_context(anchor: RankedChunk, neighbors: list[RankedChunk]) -> str:
    """Combine an anchor with nearby chunks while keeping the anchor first."""
    ordered = [anchor, *sorted(neighbors, key=lambda item: item.ordinal if item.ordinal is not None else 0)]
    seen: set[UUID] = set()
    parts: list[str] = []
    for item in ordered:
        if item.chunk_id in seen:
            continue
        seen.add(item.chunk_id)
        parts.append(item.content)
    return "\n\n".join(parts)


def rerank_chunks(
    query: str,
    chunks: list[RankedChunk],
    provider: Callable[[str, list[RankedChunk]], list[RankedChunk]] | None = None,
) -> list[RankedChunk]:
    """Apply an optional reranker while keeping RRF as the failure-safe result."""
    if not provider or not chunks:
        return chunks
    try:
        reranked = provider(query, chunks)
        return reranked if reranked else chunks
    except Exception:
        return chunks


async def rerank_chunks_async(query: str, chunks: list[RankedChunk], provider=None) -> list[RankedChunk]:
    if not provider or not chunks:
        return chunks
    try:
        result = provider(query, chunks)
        if isawaitable(result):
            result = await result
        return result if result else chunks
    except Exception:
        return chunks
def rrf_merge(keyword: list[RankedChunk], vector: list[RankedChunk], limit: int = 10, k: int = 60) -> list[RankedChunk]:
    by_id: dict[UUID, RankedChunk] = {}
    scores: dict[UUID, float] = {}
    for rank, item in enumerate(keyword, 1):
        by_id.setdefault(item.chunk_id, item)
        scores[item.chunk_id] = scores.get(item.chunk_id, 0) + 1 / (k + rank)
    for rank, item in enumerate(vector, 1):
        by_id.setdefault(item.chunk_id, item)
        scores[item.chunk_id] = scores.get(item.chunk_id, 0) + 1 / (k + rank)
    order = {chunk_id: index for index, chunk_id in enumerate(by_id)}
    ranked_ids = sorted(
        scores,
        key=lambda chunk_id: (
            -scores[chunk_id]
            - (1 / (k * k) if by_id[chunk_id].source_type == "session" else 0),
            order[chunk_id],
        ),
    )[:limit]
    for chunk_id in ranked_ids:
        by_id[chunk_id].score = scores[chunk_id]
    return [by_id[chunk_id] for chunk_id in ranked_ids]
