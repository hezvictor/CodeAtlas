"""Durable ingestion generations, progress and content cleanup."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0015_knowledge_lifecycle"
down_revision = "0014_group_delete_set_null"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("documents", sa.Column("filename", sa.String(255), nullable=False, server_default=""))
    op.add_column("documents", sa.Column("cleanup_status", sa.String(20)))
    op.add_column("documents", sa.Column("cleanup_error", sa.Text()))
    op.add_column("document_versions", sa.Column("active_index_job_id", pg.UUID(as_uuid=True)))
    op.add_column("document_versions", sa.Column("upload_token", pg.UUID(as_uuid=True)))
    op.create_unique_constraint("uq_document_version_upload_token", "document_versions", ["upload_token"])
    op.add_column("document_versions", sa.Column("cleanup_pending", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("document_versions", sa.Column("content_deleted_at", sa.DateTime(timezone=True)))
    op.add_column("document_chunks", sa.Column("index_job_id", pg.UUID(as_uuid=True)))
    op.drop_constraint("uq_document_chunks_version_ordinal", "document_chunks", type_="unique")
    op.drop_index("ix_document_chunks_version_ordinal", "document_chunks")
    op.create_index("ix_document_chunks_version_ordinal", "document_chunks", ["document_version_id", "index_job_id", "ordinal"], unique=True)
    op.create_index("ix_document_chunks_index_job_id", "document_chunks", ["index_job_id"])
    for name in ("total_chunks", "completed_chunks"):
        op.add_column("document_jobs", sa.Column(name, sa.Integer(), nullable=False, server_default="0"))
    op.add_column("document_jobs", sa.Column("error_code", sa.String(80)))
    op.add_column("document_jobs", sa.Column("acknowledged_at", sa.DateTime(timezone=True)))
    for name in ("chunk_id_snapshot", "document_id_snapshot"):
        op.add_column("citations", sa.Column(name, pg.UUID(as_uuid=True)))
    op.add_column("citations", sa.Column("group_name_snapshot", sa.String(100)))
    op.execute("""UPDATE citations c SET chunk_id_snapshot=c.chunk_id, document_id_snapshot=d.id,
        document_title_snapshot=d.title, original_filename_snapshot=v.original_filename,
        source_scope=d.scope, group_name_snapshot=g.name
        FROM document_chunks ch JOIN document_versions v ON v.id=ch.document_version_id
        JOIN documents d ON d.id=v.document_id LEFT JOIN knowledge_groups g ON g.id=d.group_id
        WHERE ch.id=c.chunk_id""")
    op.drop_constraint("citations_chunk_id_fkey", "citations", type_="foreignkey")
    op.alter_column("citations", "chunk_id", nullable=True)
    op.create_foreign_key("citations_chunk_id_fkey", "citations", "document_chunks", ["chunk_id"], ["id"], ondelete="SET NULL")
    op.execute("""UPDATE documents d SET filename=COALESCE((SELECT original_filename FROM document_versions v WHERE v.document_id=d.id ORDER BY version_no DESC LIMIT 1),d.title),
        current_version_id=CASE WHEN d.deleted_at IS NULL THEN (SELECT id FROM document_versions v WHERE v.document_id=d.id AND v.status='indexed' AND EXISTS (SELECT 1 FROM document_chunks ch WHERE ch.document_version_id=v.id) AND NOT EXISTS (SELECT 1 FROM document_chunks ch WHERE ch.document_version_id=v.id AND (ch.embedding IS NULL OR NULLIF(btrim(ch.content),'') IS NULL)) ORDER BY version_no DESC LIMIT 1) ELSE NULL END,
        cleanup_status=CASE WHEN d.deleted_at IS NOT NULL THEN 'pending' ELSE NULL END""")
    op.execute("UPDATE document_versions SET cleanup_pending=true WHERE document_id IN (SELECT id FROM documents WHERE deleted_at IS NOT NULL)")
    op.execute("""UPDATE document_jobs j SET status='failed', error_code='PDF_PROCESSING_DISABLED', error_message='此文件暂不支持处理，可下载原文件或删除', finished_at=now(), locked_at=NULL, locked_by=NULL
        FROM document_versions v WHERE j.document_version_id=v.id AND v.extension='.pdf' AND j.status IN ('queued','running','waiting_embedding')""")
    op.execute("""UPDATE document_versions SET status='failed', error_code='EMPTY_LEGACY_INDEX', error_message='原索引没有有效文本块，请重试处理'
        WHERE status='indexed' AND NOT EXISTS (SELECT 1 FROM document_chunks ch WHERE ch.document_version_id=document_versions.id AND ch.embedding IS NOT NULL)""")
    op.execute("""UPDATE document_versions SET status='failed', error_code='INCOMPLETE_LEGACY_INDEX', error_message='原索引未完整生成，请重试处理'
        WHERE status='indexed' AND EXISTS (SELECT 1 FROM document_chunks ch WHERE ch.document_version_id=document_versions.id AND (ch.embedding IS NULL OR NULLIF(btrim(ch.content),'') IS NULL))""")
    op.execute("""UPDATE document_jobs j SET status='failed', error_code=v.error_code, error_message=v.error_message, finished_at=COALESCE(j.finished_at,now()), locked_at=NULL, locked_by=NULL
        FROM document_versions v WHERE j.document_version_id=v.id AND v.error_code IN ('EMPTY_LEGACY_INDEX','INCOMPLETE_LEGACY_INDEX') AND j.status IN ('completed','queued','running','waiting_embedding')""")
    op.execute("UPDATE document_jobs SET acknowledged_at=now() WHERE status='completed'")


def downgrade():
    # Deleted file content is intentionally irreversible; backup before rollback.
    op.execute("DELETE FROM citations WHERE chunk_id IS NULL")
    op.drop_constraint("citations_chunk_id_fkey", "citations", type_="foreignkey")
    op.alter_column("citations", "chunk_id", nullable=False)
    op.create_foreign_key("citations_chunk_id_fkey", "citations", "document_chunks", ["chunk_id"], ["id"], ondelete="CASCADE")
    for name in ("group_name_snapshot", "document_id_snapshot", "chunk_id_snapshot"):
        op.drop_column("citations", name)
    op.execute("DELETE FROM document_chunks ch USING document_versions v WHERE ch.document_version_id=v.id AND ch.index_job_id IS DISTINCT FROM v.active_index_job_id")
    op.drop_index("ix_document_chunks_version_ordinal", "document_chunks")
    op.drop_index("ix_document_chunks_index_job_id", "document_chunks")
    op.drop_column("document_chunks", "index_job_id")
    op.create_unique_constraint("uq_document_chunks_version_ordinal", "document_chunks", ["document_version_id", "ordinal"])
    op.create_index("ix_document_chunks_version_ordinal", "document_chunks", ["document_version_id", "ordinal"], unique=True)
    for name in ("acknowledged_at", "error_code", "completed_chunks", "total_chunks"):
        op.drop_column("document_jobs", name)
    for name in ("content_deleted_at", "cleanup_pending", "upload_token", "active_index_job_id"):
        op.drop_column("document_versions", name)
    for name in ("cleanup_error", "cleanup_status", "filename"):
        op.drop_column("documents", name)
