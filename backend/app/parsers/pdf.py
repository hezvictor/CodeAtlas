from io import BytesIO

from pypdf import PdfReader

from .base import ParsedBlock, ParsedDocument


def parse_pdf(data: bytes) -> ParsedDocument:
    reader = PdfReader(BytesIO(data))
    blocks = []
    pages = []
    for number, page in enumerate(reader.pages, 1):
        value = (page.extract_text() or "").strip()
        if value:
            pages.append(value)
            blocks.append(ParsedBlock(value, page_start=number, page_end=number))
    return ParsedDocument(text="\n\n".join(pages), blocks=blocks)
