from ..retrieval import RankedChunk


def trim_history(history: list[dict], max_chars: int, max_messages: int) -> list[dict]:
    result: list[dict] = []
    used = 0
    for item in reversed(history):
        content = str(item.get("content", ""))
        if len(result) >= max_messages or used + len(content) > max_chars:
            continue
        result.append(item)
        used += len(content)
    return list(reversed(result))


def trim_retrieved_chunks(chunks: list[RankedChunk], max_chars: int, limit: int) -> list[RankedChunk]:
    result: list[RankedChunk] = []
    seen: set[str] = set()
    used = 0
    for chunk in chunks:
        if len(result) >= limit or chunk.content in seen:
            continue
        content = chunk.prompt_content
        if used + len(content) > max_chars:
            continue
        result.append(chunk)
        seen.add(chunk.content)
        used += len(content)
    return result
