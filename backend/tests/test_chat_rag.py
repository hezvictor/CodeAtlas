import uuid


def test_rag_prompt_labels_untrusted_source_and_requires_citation_marker():
    from app.chat_rag import build_context_prompt
    from app.retrieval import RankedChunk

    chunk = RankedChunk(uuid.uuid4(), "Dijkstra requires non-negative edges", 0.9, {"page": 2})
    prompt = build_context_prompt("Why does Dijkstra fail?", [chunk])

    assert "资料内容（不可信）" in prompt
    assert str(chunk.chunk_id) in prompt
    assert "[cite:" in prompt
