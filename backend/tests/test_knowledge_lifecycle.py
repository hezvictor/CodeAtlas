"""PostgreSQL integration tests; each test owns a disposable schema.

Run with RUN_LIFECYCLE_INTEGRATION=1 in the backend-test compose service.
Only storage and provider HTTP boundaries are replaced; transactions are real.
"""
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings
from app.models import (
    Base,
    Citation,
    Conversation,
    Document,
    DocumentChunk,
    DocumentJob,
    DocumentVersion,
    Message,
    User,
)


def test_generations_can_stage_without_replacing_the_active_index():
    assert "active_index_job_id" in DocumentVersion.__table__.columns
    assert "index_job_id" in DocumentChunk.__table__.columns
    assert "completed_chunks" in DocumentJob.__table__.columns
    assert Citation.__table__.columns.chunk_id.nullable


@pytest.fixture
async def db(monkeypatch):
    if os.getenv("RUN_LIFECYCLE_INTEGRATION") != "1":
        pytest.skip("requires PostgreSQL integration service")
    import app.tasks.document_tasks as tasks

    schema = "lifecycle_" + uuid4().hex
    admin = create_async_engine(get_settings().database_url)
    async with admin.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_async_engine(get_settings().database_url, connect_args={"server_settings": {"search_path": f"{schema},public"}}, execution_options={"schema_translate_map": {None: schema}})
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(tasks, "session_factory", factory)
    monkeypatch.setattr(tasks, "project_embedding_is_configured", lambda: True)

    class Storage:
        deleted = []
        fail = False
        async def get_bytes(self, key):
            return b"" if key == "empty" else b"# Algorithms\n\nBinary search and sorting."
        async def delete(self, key):
            if self.fail:
                raise ConnectionError("storage offline")
            self.deleted.append(key)

    storage = Storage()
    monkeypatch.setattr(tasks, "S3Storage", lambda: storage)

    class Provider:
        async def embed_documents(self, values):
            return [[0.1] * get_settings().embedding_dimensions for _ in values]
    monkeypatch.setattr(tasks, "UserEmbeddingProvider", lambda *_: Provider())
    try:
        yield factory, tasks, storage
    finally:
        await engine.dispose()
        async with admin.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin.dispose()


async def seed(factory, *, existing=False, key="new"):
    async with factory() as session:
        user = User(email=f"{uuid4()}@test.invalid", password_hash="test", nickname="Test")
        session.add(user)
        await session.flush()
        doc = Document(user_id=user.id, title="notes", filename="notes.md")
        session.add(doc)
        await session.flush()
        old = None
        if existing:
            old = DocumentVersion(document_id=doc.id, version_no=1, original_filename="notes.md", extension=".md", sha256="0" * 64, object_key="old", status="indexed")
            session.add(old)
            await session.flush()
            doc.current_version_id = old.id
            chunk = DocumentChunk(document_version_id=old.id, ordinal=0, content="old text", content_hash="0" * 64, embedding=[0.1] * get_settings().embedding_dimensions)
            session.add(chunk)
            conversation = Conversation(user_id=user.id, title="history")
            session.add(conversation)
            await session.flush()
            message = Message(conversation_id=conversation.id, role="assistant", content="answer")
            session.add(message)
            await session.flush()
            session.add(Citation(message_id=message.id, chunk_id=chunk.id, quote="old text", locator={"line_start": 1}))
        version = DocumentVersion(document_id=doc.id, version_no=2 if existing else 1, original_filename="notes.md", extension=".md", mime_type="text/markdown", sha256="1" * 64, object_key=key, status="queued")
        session.add(version)
        await session.flush()
        job = DocumentJob(document_version_id=version.id, status="queued")
        session.add(job)
        await session.commit()
        return doc.id, version.id, job.id, old.id if old else None


@pytest.mark.asyncio
async def test_empty_document_is_failed_not_searchable(db):
    factory, tasks, _ = db
    doc_id, version_id, job_id, _ = await seed(factory, key="empty")
    result = await tasks.process_document(None, str(job_id))
    assert result["status"] == "failed"
    async with factory() as session:
        assert (await session.get(Document, doc_id)).current_version_id is None
        assert (await session.get(DocumentJob, job_id)).status == "failed"
        assert (await session.get(DocumentVersion, version_id)).status == "failed"


@pytest.mark.asyncio
async def test_permanent_embedding_failure_preserves_previous_version(db, monkeypatch):
    factory, tasks, _ = db
    doc_id, version_id, job_id, old_id = await seed(factory, existing=True)
    class Provider:
        async def embed_documents(self, _values):
            request = httpx.Request("POST", "https://provider/embeddings")
            raise httpx.HTTPStatusError("invalid", request=request, response=httpx.Response(400, json={"error": {"code": "InvalidParameter"}}))
    monkeypatch.setattr(tasks, "UserEmbeddingProvider", lambda *_: Provider())
    assert (await tasks.process_document(None, str(job_id)))["status"] == "failed"
    async with factory() as session:
        assert (await session.get(Document, doc_id)).current_version_id == old_id
        assert (await session.get(DocumentJob, job_id)).attempts == 1
        assert await session.scalar(select(func.count()).select_from(DocumentChunk).where(DocumentChunk.document_version_id == old_id)) == 1
        assert (await session.get(DocumentVersion, version_id)).error_code == "EMBEDDING_HTTP_400"


@pytest.mark.asyncio
async def test_success_activates_then_purges_old_content_and_keeps_citation(db):
    factory, tasks, storage = db
    doc_id, version_id, job_id, old_id = await seed(factory, existing=True)
    assert (await tasks.process_document(None, str(job_id)))["status"] == "indexed"
    async with factory() as session:
        assert (await session.get(Document, doc_id)).current_version_id == version_id
        assert (await session.get(DocumentVersion, version_id)).active_index_job_id == job_id
        job = await session.get(DocumentJob, job_id)
        assert job.completed_chunks == job.total_chunks > 0
    await tasks.cleanup_deleted_document_objects()
    async with factory() as session:
        assert await session.scalar(select(func.count()).select_from(DocumentChunk).where(DocumentChunk.document_version_id == old_id)) == 0
        assert (await session.get(DocumentVersion, old_id)).extracted_text is None
        citation = await session.scalar(select(Citation))
        assert citation.chunk_id is None
        assert citation.document_title_snapshot == "notes"
        assert citation.quote == "old text"
    assert storage.deleted == ["old"]


@pytest.mark.asyncio
async def test_delete_during_embedding_cannot_resurrect_index(db, monkeypatch):
    factory, tasks, _ = db
    doc_id, version_id, job_id, _ = await seed(factory)
    from app.services.document_lifecycle import mark_document_deleted
    class Provider:
        async def embed_documents(self, values):
            async with factory() as session:
                await mark_document_deleted(session, doc_id)
            return [[0.1] * get_settings().embedding_dimensions for _ in values]
    monkeypatch.setattr(tasks, "UserEmbeddingProvider", lambda *_: Provider())
    assert (await tasks.process_document(None, str(job_id)))["status"] == "cancelled"
    await tasks.cleanup_deleted_document_objects()
    async with factory() as session:
        doc = await session.get(Document, doc_id)
        assert doc.current_version_id is None
        assert doc.cleanup_status == "completed"
        assert await session.scalar(select(func.count()).select_from(DocumentChunk)) == 0


@pytest.mark.asyncio
async def test_cleanup_failure_stays_visible_and_retryable(db):
    factory, tasks, storage = db
    doc_id, _, _, _ = await seed(factory)
    from app.services.document_lifecycle import mark_document_deleted
    async with factory() as session:
        await mark_document_deleted(session, doc_id)
    storage.fail = True
    await tasks.cleanup_deleted_document_objects()
    async with factory() as session:
        assert (await session.get(Document, doc_id)).cleanup_status == "failed"
    storage.fail = False
    await tasks.cleanup_deleted_document_objects()
    async with factory() as session:
        assert (await session.get(Document, doc_id)).cleanup_status == "completed"


@pytest.mark.asyncio
async def test_transient_failure_records_retry_and_later_completes(db, monkeypatch):
    factory, tasks, _ = db
    doc_id, _, job_id, _ = await seed(factory)
    class Provider:
        async def embed_documents(self, values):
            raise httpx.ReadTimeout("test timeout")
    monkeypatch.setattr(tasks, "UserEmbeddingProvider", lambda *_: Provider())
    assert (await tasks.process_document(None, str(job_id)))["status"] == "retry_scheduled"
    async with factory() as session:
        job = await session.get(DocumentJob, job_id)
        assert job.status == "queued" and job.available_at > datetime.now(UTC)
        assert job.error_code == "SERVICE_UNAVAILABLE"
        assert (await session.get(Document, doc_id)).current_version_id is None
        job.available_at = datetime.now(UTC) - timedelta(seconds=1)
        await session.commit()
    class Healthy:
        async def embed_documents(self, values):
            return [[0.1] * get_settings().embedding_dimensions for _ in values]
    monkeypatch.setattr(tasks, "UserEmbeddingProvider", lambda *_: Healthy())
    assert (await tasks.process_document(None, str(job_id)))["status"] == "indexed"


@pytest.mark.asyncio
async def test_reindex_staging_is_invisible_until_activation(db, monkeypatch):
    factory, tasks, _ = db
    doc_id, version_id, job_id, _ = await seed(factory)
    await tasks.process_document(None, str(job_id))
    async with factory() as session:
        doc = await session.get(Document, doc_id)
        user_id = doc.user_id
        new_job = DocumentJob(document_version_id=version_id, status="queued")
        session.add(new_job)
        await session.commit()
        retry_id = new_job.id
    class QueryProvider:
        async def embed_query(self, _):
            return [0.1] * get_settings().embedding_dimensions
    class Provider:
        async def embed_documents(self, values):
            from app.services.retrieval_service import retrieve_chunks
            async with factory() as session:
                old_chunk_ids = set((await session.scalars(select(DocumentChunk.id).where(DocumentChunk.index_job_id == job_id))).all())
                hits = await retrieve_chunks(session, user_id, uuid4(), "Algorithms", embedding_provider=QueryProvider())
                assert hits and all(hit.chunk_id in old_chunk_ids for hit in hits)
                assert (await session.get(DocumentVersion, version_id)).status == "indexed"
                assert (await session.get(DocumentJob, retry_id)).total_chunks > 0
            return [[0.1] * get_settings().embedding_dimensions for _ in values]
    monkeypatch.setattr(tasks, "UserEmbeddingProvider", lambda *_: Provider())
    assert (await tasks.process_document(None, str(retry_id)))["status"] == "indexed"
    async with factory() as session:
        assert (await session.get(DocumentVersion, version_id)).active_index_job_id == retry_id
        assert await session.scalar(select(func.count()).select_from(DocumentChunk).where(DocumentChunk.index_job_id == job_id)) == 0


@pytest.mark.asyncio
async def test_unconfigured_embedding_keeps_source_but_no_index(db, monkeypatch):
    factory, tasks, storage = db
    doc_id, version_id, job_id, _ = await seed(factory)
    monkeypatch.setattr(tasks, "project_embedding_is_configured", lambda: False)
    assert (await tasks.process_document(None, str(job_id)))["status"] == "waiting_embedding"
    async with factory() as session:
        assert (await session.get(Document, doc_id)).current_version_id is None
        assert (await session.get(DocumentVersion, version_id)).status == "waiting_embedding"
        assert await session.scalar(select(func.count()).select_from(DocumentChunk)) == 0
    assert not storage.deleted


@pytest.mark.asyncio
async def test_citation_saved_after_source_cleanup_keeps_snapshot_without_missing_fk(db):
    from app.citations import persist_citations
    from app.retrieval import RankedChunk

    factory, tasks, _ = db
    doc_id, _, job_id, old_id = await seed(factory, existing=True)
    async with factory() as session:
        chunk = await session.scalar(select(DocumentChunk).where(DocumentChunk.document_version_id == old_id))
        message_id = await session.scalar(select(Message.id))
        hit = RankedChunk(chunk.id, "old text", 0.5, locator={"line_start": 1}, document_version_id=old_id)
    await tasks.process_document(None, str(job_id))
    await tasks.cleanup_deleted_document_objects()
    async with factory() as session:
        cleaned, citations = await persist_citations(session, message_id, f"answer [cite:{hit.chunk_id}]", [hit])
        await session.commit()
        assert cleaned == f"answer [cite:{hit.chunk_id}]"
        assert citations[0].chunk_id is None
        assert citations[0].chunk_id_snapshot == hit.chunk_id
        assert citations[0].document_id_snapshot == doc_id
        assert citations[0].document_title_snapshot == "notes"
        assert citations[0].quote == "old text"
        assert citations[0].locator == {"line_start": 1}
