"""Small, dependency-free parser and validator for the internal RAG eval set."""

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class EvaluationCase:
    case_id: str
    title: str
    mode: str | None = None
    solution_language: str | None = None
    problem_id: str | None = None
    query: str | None = None
    turn_1: str | None = None
    turn_2: str | None = None
    expected_sources: list[str] = field(default_factory=list)
    must_retrieve_together: bool = False
    must_include: list[str] = field(default_factory=list)
    forbidden: list[str] = field(default_factory=list)
    citation_required: bool = False
    fixture: str | None = None
    expected_behavior: str | None = None


@dataclass(slots=True)
class RetrievalEvaluation:
    case_id: str
    top_k_hit: bool
    matched_sources: list[str] = field(default_factory=list)
    missing_sources: list[str] = field(default_factory=list)
    together_satisfied: bool = True


_CASE = re.compile(r"^###\s+(R\d+):\s*(.+?)\s*$")
_FIELD = re.compile(r"^-\s+([a-z_]+):\s*(.*?)\s*$")
_BACKTICK = re.compile(r"`([^`]+)`")
_WORD = re.compile(r"[a-zA-Z0-9_+#.-]+")
_CJK = re.compile(r"[\u3400-\u9fff]")


def _value(raw: str) -> str | None:
    value = raw.strip()
    if value.lower() == "none":
        return None
    leading_code = re.match(r"^`([^`]+)`", value)
    if leading_code:
        return leading_code.group(1)
    if value.startswith("`") and value.endswith("`"):
        return value[1:-1]
    return value


def _list_value(raw: str) -> list[str]:
    if raw.strip().lower() == "none":
        return []
    values = _BACKTICK.findall(raw)
    if values:
        return values
    return [item.strip() for item in raw.split(",") if item.strip()]


def _source_value(raw: str) -> str:
    values = _BACKTICK.findall(raw)
    return values[0] if values else (_value(raw) or raw.strip())


def load_evaluation_cases(path: str | Path) -> list[EvaluationCase]:
    lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    cases: list[EvaluationCase] = []
    current: EvaluationCase | None = None
    active_list: str | None = None
    for line in lines:
        heading = _CASE.match(line)
        if heading:
            current = EvaluationCase(heading.group(1), heading.group(2))
            cases.append(current)
            active_list = None
            continue
        if current is None:
            continue
        nested = re.match(r"^\s{2}-\s+(.+?)\s*$", line)
        if nested and active_list == "expected_sources":
            current.expected_sources.append(_source_value(nested.group(1)))
            continue
        field_match = _FIELD.match(line)
        if not field_match:
            continue
        name, raw = field_match.groups()
        if name == "expected_sources":
            active_list = name
            if raw.strip().lower() != "none":
                current.expected_sources.extend(_list_value(raw))
        elif name in {"must_include", "forbidden"}:
            setattr(current, name, _list_value(raw))
            active_list = None
        elif name == "must_retrieve_together":
            current.must_retrieve_together = raw.strip().lower() == "true"
            active_list = None
        elif name == "citation_required":
            current.citation_required = raw.strip().lower() == "true"
            active_list = None
        elif hasattr(current, name):
            setattr(current, name, _value(raw))
            active_list = None
        else:
            active_list = None
    return cases


def validate_evaluation_set(cases: list[EvaluationCase]) -> list[str]:
    errors: list[str] = []
    expected_ids = [f"R{index:02d}" for index in range(1, 21)]
    actual_ids = [case.case_id for case in cases]
    if actual_ids != expected_ids:
        errors.append(f"case ids must be {expected_ids}, got {actual_ids}")
    for case in cases:
        if case.mode not in {"normal", "acm_analysis", "acm_solution"}:
            errors.append(f"{case.case_id}: invalid mode")
        if not case.query and case.case_id != "R16":
            errors.append(f"{case.case_id}: query is required")
        if case.mode == "acm_solution" and not case.solution_language:
            errors.append(f"{case.case_id}: acm_solution requires solution_language")
        if case.case_id == "R20" and case.fixture != "source document exists but is not indexed yet":
            errors.append("R20: pending-index fixture is missing")
    return errors


def evaluate_retrieval_case(
    case: EvaluationCase,
    evidence: list[object],
    top_k: int = 5,
) -> RetrievalEvaluation:
    """Evaluate source-region recall without requiring a database connection.

    Evidence may be RankedChunk instances or dictionaries containing ``content``
    and a locator with ``section_path``. This intentionally measures grounding
    evidence, not answer quality or embedding similarity.
    """
    if case.fixture in {"retrieval provider unavailable", "source document exists but is not indexed yet"}:
        return RetrievalEvaluation(case.case_id, top_k_hit=not evidence, together_satisfied=not evidence)
    top = evidence[: max(0, top_k)]
    haystacks: list[str] = []
    for item in top:
        if isinstance(item, dict):
            locator = item.get("locator") or {}
            content = item.get("content") or ""
        else:
            locator = getattr(item, "locator", None) or {}
            content = getattr(item, "content", "")
        haystacks.append(f"{locator.get('section_path', '')}\n{content}".lower())
    matched: list[str] = []
    missing: list[str] = []
    for source in case.expected_sources:
        label = re.sub(r"[\W_]+", "", source.split(" (approximately", 1)[0].lower())
        if any(label and label in re.sub(r"[\W_]+", "", haystack) for haystack in haystacks):
            matched.append(source)
        else:
            missing.append(source)
    together = not case.must_retrieve_together or len(matched) >= min(2, len(case.expected_sources))
    return RetrievalEvaluation(case.case_id, bool(matched), matched, missing, together)


def _terms(text: str) -> set[str]:
    lowered = text.lower()
    terms = set(_WORD.findall(lowered))
    cjk = "".join(_CJK.findall(lowered))
    terms.update(cjk[index : index + 2] for index in range(max(0, len(cjk) - 1)))
    return {term for term in terms if term}


def lexical_retrieve(query: str, chunks: list[object], limit: int = 5) -> list[dict]:
    """Return a deterministic lexical baseline for offline RAG evaluation."""
    query_terms = _terms(query)
    ranked: list[tuple[float, int, dict]] = []
    for index, item in enumerate(chunks):
        if isinstance(item, dict):
            locator = item.get("locator") or {}
            content = item.get("content") or ""
        else:
            locator = getattr(item, "locator", None) or {}
            content = getattr(item, "content", "")
        section = str(locator.get("section_path") or "")
        terms = _terms(f"{section}\n{content}")
        overlap = len(query_terms & terms)
        section_overlap = len(_terms(section) & query_terms)
        score = overlap + section_overlap * 0.5
        if score:
            ranked.append((score, index, {"locator": locator, "content": content, "score": score}))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [item[2] for item in ranked[: max(0, limit)]]


def run_offline_evaluation(source_path: str | Path, evaluation_path: str | Path, top_k: int = 5) -> list[RetrievalEvaluation]:
    """Run the lexical baseline over the real source document and chunks."""
    from .chunking import chunk_document
    from .parsers import parse_document

    source = Path(source_path)
    parsed = parse_document(source.name, "text/markdown", source.read_bytes())
    chunks = chunk_document(parsed)
    cases = load_evaluation_cases(evaluation_path)
    results: list[RetrievalEvaluation] = []
    for case in cases:
        query = case.query or " ".join(value for value in (case.turn_1, case.turn_2) if value)
        evidence = [] if case.fixture in {"retrieval provider unavailable", "source document exists but is not indexed yet"} else lexical_retrieve(query, chunks, top_k)
        results.append(evaluate_retrieval_case(case, evidence, top_k))
    return results
