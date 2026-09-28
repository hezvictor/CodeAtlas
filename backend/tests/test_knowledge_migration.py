"""Run the actual upgrade against legacy records in a disposable schema."""
import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text
from test_knowledge_lifecycle import db as lifecycle_db

db = lifecycle_db


@pytest.mark.asyncio
async def test_legacy_upgrade_keeps_only_complete_indexes_and_snapshots(db):
    factory, _, _ = db
    # The fixture owns this schema. Other tests and application tables are untouched.
    async with factory() as session:
        schema = await session.scalar(text("SELECT current_schema()"))
        assert schema.startswith("lifecycle_")
        await session.execute(text(
            "DROP TABLE citations, document_chunks, document_jobs, document_versions, "
            "documents, knowledge_groups CASCADE"
        ))
        statements = [
            "CREATE TABLE knowledge_groups (id uuid PRIMARY KEY, name text)",
            "CREATE TABLE documents (id uuid PRIMARY KEY, title text, scope text, group_id uuid, current_version_id uuid, deleted_at timestamptz)",
            "CREATE TABLE document_versions (id uuid PRIMARY KEY, document_id uuid, original_filename text, version_no integer, status text, extension text, error_code text, error_message text)",
            "CREATE TABLE document_chunks (id uuid PRIMARY KEY, document_version_id uuid, ordinal integer, content text, embedding vector(1024), CONSTRAINT uq_document_chunks_version_ordinal UNIQUE(document_version_id, ordinal))",
            "CREATE UNIQUE INDEX ix_document_chunks_version_ordinal ON document_chunks(document_version_id, ordinal)",
            "CREATE TABLE document_jobs (id uuid PRIMARY KEY, document_version_id uuid, status text, finished_at timestamptz, locked_at timestamptz, locked_by text, error_message text)",
            "CREATE TABLE citations (id uuid PRIMARY KEY, chunk_id uuid NOT NULL CONSTRAINT citations_chunk_id_fkey REFERENCES document_chunks(id), quote text, document_title_snapshot text, original_filename_snapshot text, source_scope text)",
        ]
        for statement in statements:
            await session.execute(text(statement))
        complete, partial, empty, deleted, pdf = [uuid4() for _ in range(5)]
        versions = {doc: uuid4() for doc in (complete, partial, empty, deleted, pdf)}
        newer_failed, group, citation, old_chunk = [uuid4() for _ in range(4)]
        await session.execute(text("INSERT INTO knowledge_groups VALUES (:id, 'Algorithms')"), {"id": group})
        for doc, version in versions.items():
            await session.execute(text("INSERT INTO documents VALUES (:id, 'Legacy notes', 'user', :group, :version, CASE WHEN :deleted THEN now() ELSE NULL END)"), {"id": doc, "group": group, "version": newer_failed if doc == complete else version, "deleted": doc == deleted})
            await session.execute(text("INSERT INTO document_versions(id,document_id,original_filename,version_no,status,extension) VALUES (:id,:doc,'notes.md',1,:status,:extension)"), {"id": version, "doc": doc, "status": "queued" if doc == pdf else "indexed", "extension": ".pdf" if doc == pdf else ".md"})
        await session.execute(text("INSERT INTO document_versions(id,document_id,original_filename,version_no,status,extension) VALUES (:id,:doc,'notes.md',2,'failed','.md')"), {"id": newer_failed, "doc": complete})
        vector = "[" + ",".join(["0.1"] * 1024) + "]"
        for doc in (complete, partial, deleted):
            await session.execute(text("INSERT INTO document_chunks VALUES (:id,:version,0,'Legacy text',CAST(:embedding AS vector))"), {"id": old_chunk if doc == complete else uuid4(), "version": versions[doc], "embedding": vector})
        await session.execute(text("INSERT INTO document_chunks VALUES (:id,:version,1,'Missing vector',NULL)"), {"id": uuid4(), "version": versions[partial]})
        await session.execute(text("INSERT INTO citations(id,chunk_id,quote) VALUES (:id,:chunk,'Historical quote')"), {"id": citation, "chunk": old_chunk})
        for doc, status in ((complete, "completed"), (partial, "completed"), (empty, "completed"), (pdf, "queued")):
            await session.execute(text("INSERT INTO document_jobs(id,document_version_id,status) VALUES (:id,:version,:status)"), {"id": uuid4(), "version": versions[doc], "status": status})
        module_spec = importlib.util.spec_from_file_location("migration_0015", Path(__file__).parents[1] / "migrations/versions/0015_knowledge_lifecycle.py")
        revision = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(revision)

        def upgrade(connection):
            with Operations.context(MigrationContext.configure(connection)):
                revision.upgrade()

        connection = await session.connection()
        await connection.run_sync(upgrade)
        rows = (await session.execute(text("SELECT id,current_version_id,cleanup_status FROM documents"))).mappings().all()
        by_id = {row["id"]: row for row in rows}
        assert by_id[complete]["current_version_id"] == versions[complete]
        assert by_id[partial]["current_version_id"] is None
        assert by_id[empty]["current_version_id"] is None
        assert by_id[deleted]["current_version_id"] is None
        assert by_id[deleted]["cleanup_status"] == "pending"
        assert await session.scalar(text("SELECT status FROM document_versions WHERE id=:id"), {"id": versions[partial]}) == "failed"
        for doc in (partial, empty):
            assert await session.scalar(text("SELECT status FROM document_jobs WHERE document_version_id=:id"), {"id": versions[doc]}) == "failed"
        snapshot = (await session.execute(text("SELECT * FROM citations WHERE id=:id"), {"id": citation})).mappings().one()
        assert snapshot["document_id_snapshot"] == complete
        assert snapshot["document_title_snapshot"] == "Legacy notes"
        assert snapshot["group_name_snapshot"] == "Algorithms"
        assert snapshot["quote"] == "Historical quote"
        assert await session.scalar(text("SELECT acknowledged_at IS NOT NULL FROM document_jobs WHERE status='completed'"))
        assert await session.scalar(text("SELECT error_code FROM document_jobs WHERE document_version_id=:id"), {"id": versions[pdf]}) == "PDF_PROCESSING_DISABLED"
        await session.execute(text("DELETE FROM document_chunks WHERE id=:id"), {"id": old_chunk})
        assert await session.scalar(text("SELECT chunk_id FROM citations WHERE id=:id"), {"id": citation}) is None
