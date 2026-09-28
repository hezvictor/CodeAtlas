from datetime import datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from test_knowledge_lifecycle import db as lifecycle_db
from test_knowledge_lifecycle import seed

from app.models import Document, DocumentJob, DocumentVersion, KnowledgeGroup, User

db = lifecycle_db


def test_timestamped_name_preserves_unicode_and_extension():
    from app.services.document_upload import timestamp_filename
    assert timestamp_filename("算法笔记.md", datetime(2026, 9, 23, 16, 30)) == "算法笔记 · 2026-09-23 16:30.md"
    assert timestamp_filename("算法笔记.md", datetime(2026, 9, 23, 16, 30), 2) == "算法笔记 · 2026-09-23 16:30 (2).md"


@pytest.mark.asyncio
async def test_same_name_conflicts_are_user_and_group_scoped(db):
    factory, _, _ = db
    from app.services.document_upload import conflict_candidates
    doc_id, _, _, _ = await seed(factory)
    async with factory() as session:
        doc = await session.get(Document, doc_id)
        group = KnowledgeGroup(user_id=doc.user_id, name="Other")
        session.add(group)
        await session.flush()
        assert len(await conflict_candidates(session, doc.user_id, None, "notes.md", "1" * 64)) == 1
        assert await conflict_candidates(session, doc.user_id, group.id, "notes.md", "1" * 64) == []
        assert await conflict_candidates(session, uuid4(), None, "notes.md", "1" * 64) == []


@pytest.mark.asyncio
async def test_delete_keeps_visible_row_until_cleanup_and_summary_ack_is_scoped(db):
    factory, tasks, _ = db
    from app.routers.knowledge_documents import (
        JobAcknowledgement,
        acknowledge_jobs,
        knowledge_summary,
        list_documents,
    )
    from app.services.document_lifecycle import mark_document_deleted
    doc_id, _, job_id, _ = await seed(factory)
    await tasks.process_document(None, str(job_id))
    async with factory() as session:
        user_id = (await session.get(Document, doc_id)).user_id
        summary = await knowledge_summary(user_id=user_id, session=session)
        assert summary["completed"] == 1
        await acknowledge_jobs(JobAcknowledgement(job_ids=[job_id]), user_id=uuid4(), session=session)
        assert (await knowledge_summary(user_id=user_id, session=session))["completed"] == 1
        await acknowledge_jobs(JobAcknowledgement(job_ids=[job_id]), user_id=user_id, session=session)
        assert (await knowledge_summary(user_id=user_id, session=session))["completed"] == 0
        await mark_document_deleted(session, doc_id)
        assert len(await list_documents(user_id=user_id, session=session)) == 1
    await tasks.cleanup_deleted_document_objects()
    async with factory() as session:
        assert await list_documents(user_id=user_id, session=session) == []


@pytest.mark.asyncio
async def test_upload_idempotency_and_explicit_conflict_choices(db, monkeypatch):
    from io import BytesIO

    from starlette.datastructures import UploadFile

    import app.routers.knowledge_documents as routes
    factory, _, storage = db
    stored = []
    async def put(key, data, mime):
        stored.append((key, data))
    storage.put_bytes = put
    monkeypatch.setattr(routes, "S3Storage", lambda: storage)
    async def dispatch(_):
        return None
    monkeypatch.setattr(routes, "dispatch_document_job", dispatch)
    async with factory() as session:
        user = User(email=f"{uuid4()}@test.invalid", password_hash="test", nickname="test")
        session.add(user)
        await session.commit()
        token = uuid4()
        async def upload(**kwargs):
            return await routes.upload_document(file=UploadFile(BytesIO(b"hello"), filename="算法笔记.md"), group_id=None, title=None, upload_token=kwargs.pop("upload_token", None), conflict_action=kwargs.pop("conflict_action", None), target_document_id=None, user_id=user.id, session=session, **kwargs)
        first = await upload(upload_token=token)
        same = await upload(upload_token=token)
        assert same.id == first.id
        assert len(stored) == 1
        duplicate = await upload()
        assert duplicate.id == first.id
        assert len(stored) == 1
        independent = await upload(conflict_action="independent")
        assert independent.id != first.id
        assert " · " in independent.latest_version.original_filename
        assert stored[-1][0].endswith(independent.latest_version.original_filename)
        assert (await session.get(Document, first.id)).current_version_id is None


@pytest.mark.asyncio
async def test_different_content_requires_choice_and_version_preserves_active_pointer(db, monkeypatch):
    from io import BytesIO

    from starlette.datastructures import UploadFile

    import app.routers.knowledge_documents as routes
    factory, tasks, storage = db
    doc_id, version_id, job_id, _ = await seed(factory)
    await tasks.process_document(None, str(job_id))
    async def put(*_):
        pass
    async def dispatch(_):
        pass
    storage.put_bytes = put
    monkeypatch.setattr(routes, "S3Storage", lambda: storage)
    monkeypatch.setattr(routes, "dispatch_document_job", dispatch)
    async with factory() as session:
        document = await session.get(Document, doc_id)
        async def upload(action=None, target=None):
            return await routes.upload_document(file=UploadFile(BytesIO(b"changed"), filename="notes.md"), group_id=None, title=None, upload_token=None, conflict_action=action, target_document_id=target, user_id=document.user_id, session=session)
        with pytest.raises(HTTPException) as conflict:
            await upload()
        assert conflict.value.status_code == 409
        with pytest.raises(HTTPException):
            await upload("new_version", uuid4())
        result = await upload("new_version", doc_id)
        assert result.active_version.id == version_id
        assert result.latest_version.version_no == 2
        assert result.operation.status == "queued"
        assert (await session.get(Document, doc_id)).current_version_id == version_id


@pytest.mark.asyncio
async def test_storage_error_does_not_acknowledge_upload(db, monkeypatch):
    from io import BytesIO

    from starlette.datastructures import UploadFile

    import app.routers.knowledge_documents as routes
    factory, _, storage = db
    async def put(*_):
        raise ConnectionError("storage offline")
    storage.put_bytes = put
    monkeypatch.setattr(routes, "S3Storage", lambda: storage)
    async with factory() as session:
        user = User(email=f"{uuid4()}@test.invalid", nickname="test", password_hash="test")
        session.add(user)
        await session.commit()
        with pytest.raises(ConnectionError):
            await routes.upload_document(group_id=None, title=None, file=UploadFile(BytesIO(b"hello"), filename="notes.md"), conflict_action=None, target_document_id=None, upload_token=None, user_id=user.id, session=session)
        await session.rollback()
        assert not (await session.scalars(select(Document))).all()
        assert not (await session.scalars(select(DocumentJob))).all()
        assert not (await session.scalars(select(DocumentVersion))).all()


@pytest.mark.asyncio
async def test_completion_after_summary_snapshot_is_not_acknowledged(db):
    from app.routers.knowledge_documents import (
        JobAcknowledgement,
        acknowledge_jobs,
        knowledge_summary,
        reindex_document,
    )

    factory, tasks, _ = db
    doc_id, _, first_job_id, _ = await seed(factory)
    await tasks.process_document(None, str(first_job_id))
    async with factory() as session:
        user_id = (await session.get(Document, doc_id)).user_id
        observed = await knowledge_summary(user_id=user_id, session=session)
        await reindex_document(doc_id, user_id=user_id, session=session)
        next_job = await session.scalar(select(DocumentJob).where(DocumentJob.id != first_job_id))
        next_job_id = next_job.id
    await tasks.process_document(None, str(next_job_id))
    async with factory() as session:
        await acknowledge_jobs(
            JobAcknowledgement(job_ids=observed["completed_job_ids"]),
            user_id=user_id,
            session=session,
        )
        remaining = await knowledge_summary(user_id=user_id, session=session)
        assert remaining["completed"] == 1
        assert remaining["completed_job_ids"] == [str(next_job_id)]
        assert (await session.get(DocumentJob, next_job_id)).acknowledged_at is None
