from pathlib import PurePath

from ..config import DOCUMENT_MIME_TYPES
from .base import ParsedDocument
from .markdown import parse_markdown


def parse_document(filename: str, mime_type: str, data: bytes) -> ParsedDocument:
    extension = PurePath(filename).suffix.lower()
    if extension not in DOCUMENT_MIME_TYPES:
        raise ValueError("Unsupported document type")
    expected = DOCUMENT_MIME_TYPES[extension]
    if mime_type and mime_type != "application/octet-stream" and mime_type != expected:
        if not (expected.startswith("text/") and mime_type.startswith("text/")):
            raise ValueError("MIME type does not match file extension")
    if extension in {".html", ".htm"}:
        from .html import parse_html

        return parse_html(data)
    if extension in {".md", ".markdown"}:
        return parse_markdown(data)
    if extension == ".docx":
        from .docx import parse_docx

        return parse_docx(data)
    if extension in {".c", ".cc", ".cpp", ".h", ".hpp", ".java", ".py"}:
        from .code import parse_code

        return parse_code(data, extension)
    from .text import parse_text

    return parse_text(data)
