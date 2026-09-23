def test_query_rewrite_preserves_original_and_adds_recent_terms_for_short_followup():
    from app.services.query_rewrite import build_retrieval_queries

    queries = build_retrieval_queries("时间复杂度呢？", [{"role": "user", "content": "我在复习 Kruskal 和并查集"}])

    assert queries[0] == "时间复杂度呢？"
    assert any("Kruskal" in query and "并查集" in query for query in queries)
