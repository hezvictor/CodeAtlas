import pytest
from fastapi import HTTPException


def test_document_upload_validation_accepts_html_and_rejects_unknown_extension():
    from app.routers.knowledge_documents import _validate_upload

    extension, mime = _validate_upload("notes.html", "text/html", b"<html><body>notes</body></html>")
    assert extension == ".html"
    assert mime == "text/html"
    with pytest.raises(Exception, match="Unsupported document type"):
        _validate_upload("notes.exe", "application/octet-stream", b"MZ")


def test_document_upload_validation_rejects_mismatched_mime_type():
    from app.routers.knowledge_documents import _validate_upload

    with pytest.raises(Exception, match="MIME type does not match"):
        _validate_upload("notes.html", "application/pdf", b"<html><body>notes</body></html>")


@pytest.mark.asyncio
async def test_upload_reader_limits_bytes_before_loading_a_session_file(monkeypatch):
    from types import SimpleNamespace

    from app.routers import knowledge_documents

    class File:
        def __init__(self):
            self.requested = None

        async def read(self, size):
            self.requested = size
            return b"12345"

    monkeypatch.setattr(knowledge_documents, "get_settings", lambda: SimpleNamespace(max_upload_size_bytes=4))
    file = File()

    with pytest.raises(HTTPException) as error:
        await knowledge_documents.read_limited_upload(file)

    assert file.requested == 5
    assert error.value.status_code == 413
