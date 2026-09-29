import re
from difflib import SequenceMatcher


def _normalized(value):
    return re.sub(r"\s+", "", value)


def _copied_characters(source, answer):
    return sum(block.size for block in SequenceMatcher(None, source, answer, autojunk=False).get_matching_blocks()
               if block.size >= 8)


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
        copied = _copied_characters(source, current)
        total += copied
        historical = sum(_copied_characters(source, _normalized(text)) for text in previous_answers)
        if copied + historical > len(source) * 0.1:
            raise ValueError("TEMPORARY_QUOTE_LIMIT")
    if total > 500:
        raise ValueError("TEMPORARY_QUOTE_LIMIT")
