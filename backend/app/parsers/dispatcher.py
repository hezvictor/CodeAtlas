from pathlib import PurePath

from .base import ParsedBlock, ParsedDocument
from .code import parse_code
from .docx import parse_docx
from .html import parse_html
from .pdf import parse_pdf
from .text import parse_text


def parse_document(filename: str, mime_type: str, data: bytes) -> ParsedDocument:
    extension = PurePath(filename).suffix.lower()
    if extension in {".html", ".htm"} or mime_type == "text/html":
        return parse_html(data)
    if extension == ".pdf" or mime_type == "application/pdf":
        return parse_pdf(data)
    if extension == ".docx" or mime_type in {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}:
        return parse_docx(data)
    if extension in {".c", ".cc", ".cpp", ".h", ".hpp", ".java", ".py"}:
        return parse_code(data, extension)
    return parse_text(data)
