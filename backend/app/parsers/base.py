from dataclasses import dataclass, field


@dataclass(slots=True)
class ParsedBlock:
    text: str
    section_path: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    line_start: int | None = None
    line_end: int | None = None
    char_start: int | None = None
    char_end: int | None = None


@dataclass(slots=True)
class ParsedDocument:
    text: str
    blocks: list[ParsedBlock] = field(default_factory=list)
    language: str | None = None
