import re

from .base import ParsedBlock, ParsedDocument

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_IMAGE_ONLY = re.compile(r"^\s*!\[[^\]]*\]\([^)]*\)\s*$")


def parse_markdown(data: bytes) -> ParsedDocument:
    source = data.decode("utf-8-sig", errors="replace")
    lines = source.splitlines(keepends=True)
    sections: list[str] = []
    blocks: list[ParsedBlock] = []
    current_lines: list[str] = []
    current_start = 1
    current_section: str | None = None
    fence = False
    offsets: list[int] = []
    cursor = 0
    for line in lines:
        offsets.append(cursor)
        cursor += len(line)

    def flush(end_line: int) -> None:
        if not current_lines:
            return
        content = "".join(current_lines).strip()
        if content:
            start_offset = offsets[current_start - 1]
            end_offset = offsets[end_line - 1] + len(lines[end_line - 1])
            blocks.append(
                ParsedBlock(
                    content,
                    section_path=current_section,
                    line_start=current_start,
                    line_end=end_line,
                    char_start=start_offset,
                    char_end=end_offset,
                )
            )

    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        heading = None if fence else _HEADING.match(line.rstrip("\r\n"))
        if heading:
            flush(number - 1)
            level = len(heading.group(1))
            sections[:] = sections[: level - 1]
            sections.append(heading.group(2).strip())
            current_section = " / ".join(sections)
            current_lines.clear()
            current_start = number
        if not (not fence and _IMAGE_ONLY.match(stripped)):
            current_lines.append(line)
        if stripped.startswith(("```", "~~~")):
            fence = not fence
    flush(len(lines))
    return ParsedDocument(text="".join(block.text for block in blocks), blocks=blocks, language="markdown")
