from io import BytesIO

from docx import Document as WordDocument

from .base import ParsedBlock, ParsedDocument


def parse_docx(data: bytes) -> ParsedDocument:
    document = WordDocument(BytesIO(data))
    blocks = []
    section = None
    for paragraph in document.paragraphs:
        value = paragraph.text.strip()
        if not value:
            continue
        if paragraph.style.name.lower().startswith("heading"):
            section = value
        else:
            blocks.append(ParsedBlock(value, section_path=section))
    return ParsedDocument(text="\n\n".join(b.text for b in blocks), blocks=blocks)
