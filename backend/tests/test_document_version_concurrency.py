import uuid

import pytest


class ScalarSession:
    def __init__(self, value):
        self.value = value
        self.statement = None

    async def scalar(self, statement):
        self.statement = statement
        return self.value


@pytest.mark.asyncio
async def test_version_upload_locks_owned_document_row():
    from app.models import Document
    from app.routers.knowledge_documents import _lock_document_for_version

    document = Document(
        id=uuid.uuid4(), user_id=uuid.uuid4(), group_id=uuid.uuid4(), title="notes"
    )
    session = ScalarSession(document)

    locked = await _lock_document_for_version(document, session)

    assert locked is document
    assert session.statement._for_update_arg is not None
