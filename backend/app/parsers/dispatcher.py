from pathlib import PurePath

from .base import ParsedDocument
from .markdown import parse_markdown


def parse_document(filename: str, mime_type: str, data: bytes) -> ParsedDocument:
    extension = PurePath(filename).suffix.lower()
    if extension in {".html", ".htm"} or mime_type == "text/html":
        from .html import parse_html

        return parse_html(data)
    if extension in {".md", ".markdown"} or mime_type in {"text/markdown", "text/x-markdown"}:
        return parse_markdown(data)
    if extension == ".pdf" or mime_type == "application/pdf":
        from .pdf import parse_pdf

        return parse_pdf(data)
    if extension == ".docx" or mime_type in {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}:
        from .docx import parse_docx

        return parse_docx(data)
    if extension in {".c", ".cc", ".cpp", ".h", ".hpp", ".java", ".py"}:
        from .code import parse_code

        return parse_code(data, extension)
    from .text import parse_text

    return parse_text(data)
