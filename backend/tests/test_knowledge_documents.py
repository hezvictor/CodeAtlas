import pytest
from fastapi import HTTPException


def test_pdf_upload_is_rejected_as_an_unsupported_format():
    from app.routers.knowledge_documents import _validate_upload, upload_policy

    with pytest.raises(HTTPException) as error:
        _validate_upload("notes.pdf", "application/pdf", b"%PDF-1.7")
    assert error.value.status_code == 400
    assert error.value.detail["code"] == "UNSUPPORTED_EXTENSION"
    assert ".pdf" not in upload_policy()["extensions"]


@pytest.mark.asyncio
@pytest.mark.parametrize("extension", [".pdf", ".exe"])
async def test_unsupported_existing_versions_cannot_be_retried(monkeypatch, extension):
    from types import SimpleNamespace
    from uuid import uuid4

    from app.routers import knowledge_documents as documents

    document = SimpleNamespace(id=uuid4(), current_version_id=None)
    version = SimpleNamespace(id=uuid4(), extension=extension, status="failed", storage_deleted_at=None, cleanup_pending=False)

    class Session:
        async def scalar(self, _statement):
            return None

        def add(self, _job):
            pass

        async def commit(self):
            pass

    async def owned(*_args):
        return document

    async def latest(*_args):
        return version

    monkeypatch.setattr(documents, "owned_document", owned)
    monkeypatch.setattr(documents, "_lock_document_for_version", owned)
    monkeypatch.setattr(documents, "latest_version", latest)

    async def dispatch(_job_id):
        pass

    monkeypatch.setattr(documents, "dispatch_document_job", dispatch)

    with pytest.raises(HTTPException) as error:
        await documents._reset_latest(document.id, uuid4(), Session())
    assert error.value.status_code == 409


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


@pytest.mark.asyncio
@pytest.mark.parametrize("committed, lookup_fails, should_delete", [(False, False, True), (True, False, False), (False, True, False)])
async def test_upload_compensation_deletes_only_proven_orphans(committed, lookup_fails, should_delete):
    from uuid import uuid4

    from app.routers.knowledge_documents import _discard_uncommitted_upload

    version_id = uuid4()

    class Session:
        rolled_back = False

        async def rollback(self):
            self.rolled_back = True

        async def scalar(self, _query):
            if lookup_fails:
                raise ConnectionError("database unavailable")
            return version_id if committed else None

    class Storage:
        def __init__(self):
            self.deleted = []

        async def delete(self, key):
            self.deleted.append(key)

    session, storage = Session(), Storage()
    await _discard_uncommitted_upload(session, storage, "unique-object-key", version_id)
    assert session.rolled_back
    assert storage.deleted == (["unique-object-key"] if should_delete else [])
