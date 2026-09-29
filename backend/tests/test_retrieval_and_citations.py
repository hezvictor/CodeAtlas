import uuid

import pytest


def test_rrf_merge_combines_keyword_and_vector_rankings_without_duplicates():
    from app.retrieval import RankedChunk, rrf_merge

    first, second, third = [uuid.uuid4() for _ in range(3)]
    keyword = [RankedChunk(first, "a", 0.9), RankedChunk(second, "b", 0.8)]
    vector = [RankedChunk(second, "b", 0.95), RankedChunk(third, "c", 0.7)]

    result = rrf_merge(keyword, vector, limit=3)

    assert [item.chunk_id for item in result] == [second, first, third]


def test_rrf_merge_populates_combined_score_for_citations():
    from app.retrieval import RankedChunk, rrf_merge

    chunk_id = uuid.uuid4()
    result = rrf_merge([RankedChunk(chunk_id, "a", 0.0)], [RankedChunk(chunk_id, "a", 0.0)])

    assert result[0].score > 0


def test_rerank_falls_back_to_rrf_when_provider_fails():
    from app.retrieval import RankedChunk, rerank_chunks

    first, second = uuid.uuid4(), uuid.uuid4()
    candidates = [RankedChunk(first, "first", 0.8), RankedChunk(second, "second", 0.7)]

    def failing(_query, _items):
        raise RuntimeError("reranker unavailable")

    assert rerank_chunks("query", candidates, failing) == candidates


def test_neighbor_context_keeps_anchor_first_and_deduplicates():
    from app.retrieval import RankedChunk, assemble_neighbor_context

    anchor = RankedChunk(uuid.uuid4(), "anchor", 1.0, ordinal=2)
    previous = RankedChunk(uuid.uuid4(), "previous", 0.2, ordinal=1)
    following = RankedChunk(uuid.uuid4(), "following", 0.1, ordinal=3)

    assert assemble_neighbor_context(anchor, [following, previous, anchor]) == "anchor\n\nprevious\n\nfollowing"


def test_citation_validator_removes_unknown_markers_and_returns_valid_ids():
    from app.citations import validate_citations

    allowed = {"abc", "def"}
    cleaned, valid = validate_citations("答案 [cite:abc] 和 [cite:unknown]", allowed)

    assert cleaned == "答案 [cite:abc] 和 "
    assert valid == ["abc"]


@pytest.mark.asyncio
async def test_retrieval_provider_failure_is_not_silently_converted_to_keyword_only():
    from app.services.retrieval_service import retrieve_chunks

    class EmptyResult:
        def scalars(self):
            return self

        def all(self):
            return []

    class Session:
        async def scalar(self, _statement): return True
        async def scalars(self, _statement):
            return EmptyResult()

        async def execute(self, _statement):
            return EmptyResult()

    class Provider:
        async def embed_query(self, _query):
            raise RuntimeError("embedding provider unavailable")

    with pytest.raises(RuntimeError, match="embedding provider unavailable"):
        await retrieve_chunks(Session(), uuid.uuid4(), "query", embedding_provider=Provider())
