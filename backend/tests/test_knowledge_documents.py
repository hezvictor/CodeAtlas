import pytest


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
