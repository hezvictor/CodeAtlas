import hashlib
from dataclasses import dataclass

from .parsers.base import ParsedDocument


@dataclass(slots=True)
class Chunk:
    ordinal: int
    content: str
    content_hash: str
    token_count: int
    page_start: int | None = None
    page_end: int | None = None
    line_start: int | None = None
    line_end: int | None = None
    section_path: str | None = None
    char_start: int | None = None
    char_end: int | None = None
    parent_id: str | None = None

    @property
    def locator(self) -> dict:
        return {key: value for key, value in {
            "page_start": self.page_start, "page_end": self.page_end,
            "line_start": self.line_start, "line_end": self.line_end,
            "section_path": self.section_path, "char_start": self.char_start,
            "char_end": self.char_end,
            "parent_id": self.parent_id,
        }.items() if value is not None}


def _make_chunk(number: int, text: str, source, start: int | None = None, end: int | None = None, parent_id: str | None = None) -> Chunk:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return Chunk(number, text, digest, max(1, len(text.split())), source.page_start, source.page_end, source.line_start, source.line_end, source.section_path, start if start is not None else source.char_start, end if end is not None else source.char_end, parent_id)


def _structured_units(text: str) -> list[tuple[str, int, int]]:
    """Split Markdown-like text at paragraph and fenced-code boundaries."""
    lines = text.splitlines(keepends=True)
    units: list[tuple[str, int, int]] = []
    current: list[str] = []
    start = 0
    cursor = 0
    fence = False

    def flush(end: int) -> None:
        nonlocal current, start
        content = "".join(current).strip()
        if content:
            leading = len("".join(current)) - len("".join(current).lstrip())
            units.append((content, start + leading, end))
        current = []

    for line in lines:
        stripped = line.strip()
        if not fence and not current and not stripped:
            cursor += len(line)
            start = cursor
            continue
        current.append(line)
        cursor += len(line)
        if stripped.startswith(("```", "~~~")):
            fence = not fence
            if not fence:
                flush(cursor)
        elif not fence and not stripped:
            flush(cursor)
            start = cursor
    flush(cursor)
    return units


def chunk_document(document: ParsedDocument, max_chars: int = 3200, overlap_chars: int = 300) -> list[Chunk]:
    chunks: list[Chunk] = []
    for block in document.blocks:
        text = block.text.strip()
        if not text:
            continue
        parent_id = hashlib.sha256(
            f"{block.section_path or ''}\0{block.text}".encode()
        ).hexdigest()[:24]
        if len(text) <= max_chars:
            chunks.append(_make_chunk(len(chunks), text, block, parent_id=parent_id))
            continue
        units = _structured_units(text)
        if len(units) <= 1:
            units = [(text, 0, len(text))]
        pending: list[tuple[str, int, int]] = []
        pending_chars = 0
        for unit, unit_start, unit_end in units:
            if len(unit) > max_chars:
                if pending:
                    piece = "\n\n".join(item[0] for item in pending).strip()
                    chunks.append(_make_chunk(len(chunks), piece, block, (block.char_start or 0) + pending[0][1], (block.char_start or 0) + pending[-1][2], parent_id))
                    pending, pending_chars = [], 0
                cursor = 0
                while cursor < len(unit):
                    end = min(len(unit), cursor + max_chars)
                    piece = unit[cursor:end].strip()
                    chunks.append(_make_chunk(len(chunks), piece, block, (block.char_start or 0) + unit_start + cursor, (block.char_start or 0) + unit_start + end, parent_id))
                    if end == len(unit):
                        break
                    cursor = max(cursor + 1, end - overlap_chars)
                continue
            if unit.lstrip().startswith(("```", "~~~")):
                if pending:
                    piece = "\n\n".join(item[0] for item in pending).strip()
                    chunks.append(_make_chunk(len(chunks), piece, block, (block.char_start or 0) + pending[0][1], (block.char_start or 0) + pending[-1][2], parent_id))
                    pending, pending_chars = [], 0
                chunks.append(_make_chunk(len(chunks), unit, block, (block.char_start or 0) + unit_start, (block.char_start or 0) + unit_end, parent_id))
                continue
            if pending and pending_chars + len(unit) + 2 > max_chars:
                piece = "\n\n".join(item[0] for item in pending).strip()
                chunks.append(_make_chunk(len(chunks), piece, block, (block.char_start or 0) + pending[0][1], (block.char_start or 0) + pending[-1][2], parent_id))
                pending, pending_chars = [], 0
            pending.append((unit, unit_start, unit_end))
            pending_chars += len(unit) + 2
        if pending:
            piece = "\n\n".join(item[0] for item in pending).strip()
            chunks.append(_make_chunk(len(chunks), piece, block, (block.char_start or 0) + pending[0][1], (block.char_start or 0) + pending[-1][2], parent_id))
    return chunks
