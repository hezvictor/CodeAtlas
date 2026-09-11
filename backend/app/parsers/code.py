import re

from .base import ParsedBlock, ParsedDocument


_LANGUAGES = {".py": "python", ".java": "java", ".c": "c", ".cc": "cpp", ".cpp": "cpp", ".h": "c", ".hpp": "cpp"}


def parse_code(data: bytes, extension: str) -> ParsedDocument:
    text = data.decode("utf-8-sig", errors="replace")
    lines = text.splitlines()
    blocks: list[ParsedBlock] = []
    starts: list[int] = []
    pattern = re.compile(r"^\s*(?:def|class|async\s+def)\s+\w+|^\s*(?:class|struct|void|int|long|bool|public|private|protected)\b.*\(" )
    for index, line in enumerate(lines, 1):
        if pattern.search(line):
            starts.append(index)
    if not starts and lines:
        starts = [1]
    for position, start in enumerate(starts):
        end = (starts[position + 1] - 1) if position + 1 < len(starts) else len(lines)
        content = "\n".join(lines[start - 1 : end]).strip()
        if content:
            char_start = sum(len(line) + 1 for line in lines[: start - 1])
            blocks.append(ParsedBlock(content, line_start=start, line_end=end, char_start=char_start, char_end=char_start + len(content)))
    return ParsedDocument(text=text, blocks=blocks, language=_LANGUAGES.get(extension))
