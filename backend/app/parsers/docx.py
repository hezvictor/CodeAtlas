from io import BytesIO

from docx import Document as WordDocument
from docx.table import Table

from .base import ParsedBlock, ParsedDocument


def parse_docx(data: bytes) -> ParsedDocument:
    document = WordDocument(BytesIO(data))
    blocks = []
    section = None
    for element in document.iter_inner_content():
        if isinstance(element, Table):
            value = "\n".join("\t".join(cell.text for cell in row.cells) for row in element.rows)
            if value.strip(): blocks.append(ParsedBlock(value, section_path=section))
            continue
        paragraph = element
        value = paragraph.text
        if not value:
            continue
        if paragraph.style.name.lower().startswith("heading"):
            section = value
        blocks.append(ParsedBlock(value, section_path=section))
    return ParsedDocument(text="\n\n".join(b.text for b in blocks), blocks=blocks)
