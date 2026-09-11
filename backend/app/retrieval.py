from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True)
class RankedChunk:
    chunk_id: UUID
    content: str
    score: float
    locator: dict | None = None
    source_type: str = "knowledge"


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
    ranked_ids = sorted(scores, key=lambda chunk_id: (-scores[chunk_id], order[chunk_id]))[:limit]
    for chunk_id in ranked_ids:
        by_id[chunk_id].score = scores[chunk_id]
    return [by_id[chunk_id] for chunk_id in ranked_ids]
