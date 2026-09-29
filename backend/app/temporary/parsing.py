from io import BytesIO
from pathlib import PurePosixPath
from zipfile import BadZipFile, ZipFile

from ..config import get_settings


def parse_temporary(filename, data):
    extension = PurePosixPath(filename).suffix.lower()
    settings = get_settings()
    if extension not in settings.allowed_document_extensions:
        raise ValueError("TEMPORARY_UNSUPPORTED_FORMAT")
    if extension == ".docx":
        try:
            with ZipFile(BytesIO(data)) as archive:
                if sum(item.file_size for item in archive.infolist()) > 100 * 1024 * 1024 or len(archive.infolist()) > 10000:
                    raise ValueError("TEMPORARY_DECOMPRESSED_SIZE_EXCEEDED")
                # Our text parser cannot interpret drawings, formulas or embedded objects.
                from lxml import etree
                for name in archive.namelist():
                    if name.startswith("word/") and name.endswith(".xml"):
                        root = etree.fromstring(archive.read(name), etree.XMLParser(resolve_entities=False, no_network=True))
                        if root.xpath("//*[local-name()='drawing' or local-name()='pict' or local-name()='object' or local-name()='oMath' or local-name()='altChunk']"):
                            raise ValueError("TEMPORARY_UNSUPPORTED_EMBEDDED_CONTENT")
            from ..parsers.docx import parse_docx
            text = parse_docx(data).text
        except (BadZipFile, KeyError):
            raise ValueError("TEMPORARY_INVALID_DOCUMENT") from None
    else:
        try: text = data.decode("utf-8-sig")
        except UnicodeDecodeError: raise ValueError("TEMPORARY_REQUIRES_UTF8") from None
        if extension in {".html", ".htm"}:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(text, "html.parser")
            for tag in soup(["script", "style", "noscript"]): tag.decompose()
            text = soup.get_text("\n", strip=False)
    if not text.strip(): raise ValueError("TEMPORARY_EMPTY_DOCUMENT")
    if len(text) > settings.max_extracted_text_chars:
        raise ValueError("TEMPORARY_TEXT_TOO_LARGE")
    return text
