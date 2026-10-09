import asyncio
import re
from difflib import SequenceMatcher
from threading import BoundedSemaphore

_VALIDATION_SLOTS = BoundedSemaphore(4)
_VALIDATION_TIMEOUT_SECONDS = 2.0


def _normalized(value):
    return re.sub(r"\s+", "", value)


def _has_common_block(source, answer, size=8):
    if len(source) < size or len(answer) < size:
        return False
    answer_blocks = {answer[index:index + size] for index in range(len(answer) - size + 1)}
    pattern = "|".join(re.escape(block) for block in answer_blocks)
    return re.search(pattern, source) is not None


def _copied_characters(source, answer):
    if not _has_common_block(source, answer):
        return 0
    return sum(block.size for block in SequenceMatcher(None, source, answer, autojunk=False).get_matching_blocks()
               if block.size >= 8)


def _obvious_over_limit_copy(source, answer):
    # A single matching block above either quota is sufficient to reject. Search
    # every possible answer offset with str.find(), whose implementation avoids
    # SequenceMatcher's repeated-text worst case. The second pass catches many
    # smaller, ordered excerpts while requiring disjoint source windows, so it
    # cannot count one source span repeatedly.
    limit = min(500, int(len(source) * 0.1))
    width = max(8, limit + 1)
    if not _has_common_block(source, answer):
        return False
    if len(answer) >= width and any(source.find(answer[start:start + width]) >= 0
                                    for start in range(len(answer) - width + 1)):
        return True

    matched = 0
    source_cursor = 0
    answer_cursor = 0
    while answer_cursor + 8 <= len(answer):
        position = source.find(answer[answer_cursor:answer_cursor + 8], source_cursor)
        if position < 0:
            answer_cursor += 1
            continue
        matched += 8
        if matched > limit:
            return True
        source_cursor = position + 8
        answer_cursor += 8
    return False


def validate_answer(answer: str, files: list[dict], previous_answers: list[str]) -> None:
    """Gate direct excerpts without writing file identities or fingerprints."""
    current = _normalized(answer)
    total = 0
    for file in files:
        for value in (file.get("filename"), file.get("id")):
            if value and value in answer:
                raise ValueError("TEMPORARY_METADATA_PERSISTENCE")
        source = _normalized(file["text"])
        if source and source in current:
            raise ValueError("TEMPORARY_CONTENT_PERSISTENCE")
        if _obvious_over_limit_copy(source, current):
            raise ValueError("TEMPORARY_QUOTE_LIMIT")
        copied = _copied_characters(source, current)
        total += copied
        historical = sum(_copied_characters(source, _normalized(text)) for text in previous_answers)
        if copied + historical > len(source) * 0.1:
            raise ValueError("TEMPORARY_QUOTE_LIMIT")
    if total > 500:
        raise ValueError("TEMPORARY_QUOTE_LIMIT")


async def validate_answer_async(answer: str, files: list[dict], previous_answers: list[str]) -> None:
    def run():
        with _VALIDATION_SLOTS:
            validate_answer(answer, files, previous_answers)

    try:
        await asyncio.wait_for(asyncio.to_thread(run), timeout=_VALIDATION_TIMEOUT_SECONDS)
    except TimeoutError:
        # Never allow a slow matcher to bypass the privacy gate. The worker
        # remains bounded by _VALIDATION_SLOTS and may finish in the background
        # after the caller receives this safe rejection.
        raise ValueError("TEMPORARY_QUOTE_LIMIT") from None
