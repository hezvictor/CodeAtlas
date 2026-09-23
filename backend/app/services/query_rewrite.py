import re

_TERM = re.compile(r"[A-Za-z][A-Za-z0-9_+#.-]{2,}|[\u4e00-\u9fff]{2,}")


def build_retrieval_queries(query: str, history: list[dict] | None = None, max_history_messages: int = 3) -> list[str]:
    original = query.strip()
    if not original:
        return []
    queries = [original]
    if len(original) <= 24 and history:
        recent = " ".join(str(item.get("content", "")) for item in history[-max_history_messages:])
        terms: list[str] = []
        for term in _TERM.findall(recent):
            if term not in terms:
                terms.append(term)
        if terms:
            queries.append(f"{original} {' '.join(terms[:12])}")
    return queries
