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

    @property
    def locator(self) -> dict:
        return {key: value for key, value in {
            "page_start": self.page_start, "page_end": self.page_end,
            "line_start": self.line_start, "line_end": self.line_end,
            "section_path": self.section_path, "char_start": self.char_start,
            "char_end": self.char_end,
        }.items() if value is not None}


def _make_chunk(number: int, text: str, source, start: int | None = None, end: int | None = None) -> Chunk:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return Chunk(number, text, digest, max(1, len(text.split())), source.page_start, source.page_end, source.line_start, source.line_end, source.section_path, start if start is not None else source.char_start, end if end is not None else source.char_end)


def chunk_document(document: ParsedDocument, max_chars: int = 3200, overlap_chars: int = 300) -> list[Chunk]:
    chunks: list[Chunk] = []
    for block in document.blocks:
        text = block.text.strip()
        if not text:
            continue
        if len(text) <= max_chars:
            chunks.append(_make_chunk(len(chunks), text, block))
            continue
        cursor = 0
        while cursor < len(text):
            end = min(len(text), cursor + max_chars)
            piece = text[cursor:end].strip()
            chunks.append(_make_chunk(len(chunks), piece, block, (block.char_start or 0) + cursor, (block.char_start or 0) + end))
            if end == len(text):
                break
            cursor = max(cursor + 1, end - overlap_chars)
    return chunks
