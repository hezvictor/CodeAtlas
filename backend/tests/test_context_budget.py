from uuid import uuid4


def test_history_budget_keeps_newest_complete_messages_without_partial_records():
    from app.services.context_budget import trim_history

    history = [
        {"role": "user", "content": "old message"},
        {"role": "assistant", "content": "middle"},
        {"role": "user", "content": "newest"},
    ]
    result = trim_history(history, max_chars=12, max_messages=3)
    assert result == history[1:]
    assert sum(len(item["content"]) for item in result) <= 12


def test_retrieved_budget_deduplicates_and_limits_content():
    from app.retrieval import RankedChunk
    from app.services.context_budget import trim_retrieved_chunks

    first = RankedChunk(uuid4(), "abc", 1.0)
    duplicate = RankedChunk(uuid4(), "abc", 0.9)
    third = RankedChunk(uuid4(), "defgh", 0.8)
    result = trim_retrieved_chunks([first, duplicate, third], max_chars=8, limit=10)
    assert result == [first, third]
    assert sum(len(item.content) for item in result) <= 8
