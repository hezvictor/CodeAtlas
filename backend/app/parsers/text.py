from .base import ParsedBlock, ParsedDocument


def parse_text(data: bytes) -> ParsedDocument:
    text = data.decode("utf-8-sig", errors="replace")
    block = ParsedBlock(text=text, line_start=1 if text else None, line_end=text.count("\n") + 1 if text else None, char_start=0, char_end=len(text))
    return ParsedDocument(text=text, blocks=[block] if text.strip() else [])
