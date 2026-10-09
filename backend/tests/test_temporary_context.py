from uuid import uuid4

import fakeredis.aioredis
import pytest


@pytest.mark.asyncio
async def test_full_text_is_session_scoped_and_survives_store_recreation():
    from app.temporary.context import TemporaryContextStore

    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    owner, other, conversation = str(uuid4()), str(uuid4()), str(uuid4())
    store = TemporaryContextStore(redis)
    await store.add(owner, conversation, "notes.md", "完整内容\n```cpp\nint main() {}\n```", ".md")
    restored = TemporaryContextStore(redis)
    files = await restored.files(owner, conversation)
    assert files[0]["text"] == "完整内容\n```cpp\nint main() {}\n```"
    assert await restored.files(other, conversation) == []
    assert "text" not in restored.public(files[0])


@pytest.mark.asyncio
async def test_activity_cannot_extend_absolute_file_deadline():
    from app.temporary.context import TemporaryContextStore

    now = [0.0]
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    store = TemporaryContextStore(redis, clock=lambda: now[0], idle_seconds=10, max_seconds=25)
    await store.add("u", "c", "a.txt", "full", ".txt")
    for instant in (8, 16, 24):
        now[0] = instant
        assert len(await store.files("u", "c")) == 1
    now[0] = 25
    assert await store.files("u", "c") == []


@pytest.mark.asyncio
async def test_idle_expiry_and_detach_remove_full_text():
    from app.temporary.context import TemporaryContextStore

    now = [0.0]
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    store = TemporaryContextStore(redis, clock=lambda: now[0], idle_seconds=10)
    item = await store.add("u", "c", "a.txt", "SECRET", ".txt")
    await store.remove("u", "c", item["id"])
    assert await store.files("u", "c") == []
    await store.add("u", "c", "a.txt", "SECRET", ".txt")
    now[0] = 10
    assert await store.files("u", "c") == []


def test_context_budget_rejects_oversized_whole_file_without_truncation():
    from app.agent.budget import check_context_capacity

    with pytest.raises(ValueError, match="CONTEXT_CAPACITY_EXCEEDED"):
        check_context_capacity([{"role": "user", "content": "全文" * 1000}], [], 1000)


def test_unknown_model_capacity_defers_full_text_limit_to_provider():
    from app.agent.budget import check_context_capacity

    check_context_capacity([{"role": "user", "content": "full"}], [], None, requires_full_text=True)


def test_answer_cannot_persist_full_file_or_file_metadata():
    from app.temporary.privacy import validate_answer

    files = [{"text": "secret document body", "filename": "private.txt"}]
    with pytest.raises(ValueError, match="TEMPORARY_CONTENT_PERSISTENCE"):
        validate_answer("secret document body", files, [])
    with pytest.raises(ValueError, match="TEMPORARY_METADATA_PERSISTENCE"):
        validate_answer("依据 private.txt", files, [])


def test_quote_budget_counts_previously_saved_answers():
    from app.temporary.privacy import validate_answer

    text = "abcdefghijklmnopqrstuvwxyz" * 10
    files = [{"text": text, "filename": "private.txt"}]
    with pytest.raises(ValueError, match="TEMPORARY_QUOTE_LIMIT"):
        validate_answer(text[30:50], files, [text[:20]])


def test_large_contiguous_copy_is_rejected_without_expensive_matching():
    from app.temporary.privacy import validate_answer

    with pytest.raises(ValueError, match="TEMPORARY_QUOTE_LIMIT"):
        validate_answer("b" + "a" * 1000, [{"text": "a" * 100_000, "filename": "sample.txt"}], [])


def test_large_contiguous_copy_is_rejected_even_when_match_starts_late():
    from app.temporary.privacy import validate_answer

    with pytest.raises(ValueError, match="TEMPORARY_QUOTE_LIMIT"):
        validate_answer("b" * 32 + "a" * 1000 + "c" * 32,
                        [{"text": "a" * 100_000, "filename": "sample.txt"}], [])


@pytest.mark.asyncio
async def test_temporary_content_check_yields_to_other_requests(monkeypatch):
    import asyncio
    import time

    from app.temporary import privacy

    monkeypatch.setattr(privacy, "validate_answer", lambda *_args: time.sleep(0.1))
    check = asyncio.create_task(privacy.validate_answer_async("answer", [], []))
    await asyncio.sleep(0.01)
    assert check.done() is False
    await check


@pytest.mark.asyncio
async def test_temporary_content_check_rejects_when_matching_exceeds_deadline(monkeypatch):
    import time

    from app.temporary import privacy

    monkeypatch.setattr(privacy, "_VALIDATION_TIMEOUT_SECONDS", 0.01, raising=False)
    monkeypatch.setattr(privacy, "validate_answer", lambda *_args: time.sleep(0.1))
    with pytest.raises(ValueError, match="TEMPORARY_QUOTE_LIMIT"):
        await privacy.validate_answer_async("answer", [], [])
