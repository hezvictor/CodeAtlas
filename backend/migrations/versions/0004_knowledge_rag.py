"""add private knowledge base and rag tables"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

revision = "0004_knowledge_rag"
down_revision = "0003_message_generation_metrics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "knowledge_groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "name", name="uq_knowledge_groups_user_name"),
    )
    op.create_index("ix_knowledge_groups_user_id", "knowledge_groups", ["user_id"])
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("knowledge_groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("current_version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_documents_user_group_updated", "documents", ["user_id", "group_id", "updated_at"])
    op.create_index("ix_documents_user_id", "documents", ["user_id"])
    op.create_table(
        "document_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(120), nullable=False),
        sa.Column("extension", sa.String(20), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_code", sa.String(80)),
        sa.Column("error_message", sa.Text()),
        sa.Column("extracted_text", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("document_id", "version_no", name="uq_document_versions_document_version"),
    )
    op.create_index("ix_document_versions_document_id", "document_versions", ["document_id"])
    op.create_index("ix_document_versions_document_sha256", "document_versions", ["document_id", "sha256"])
    op.create_index("ix_document_versions_status", "document_versions", ["status"])
    op.create_foreign_key("fk_documents_current_version", "documents", "document_versions", ["current_version_id"], ["id"], ondelete="SET NULL")
    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("page_start", sa.Integer()),
        sa.Column("page_end", sa.Integer()),
        sa.Column("line_start", sa.Integer()),
        sa.Column("line_end", sa.Integer()),
        sa.Column("section_path", sa.Text()),
        sa.Column("char_start", sa.Integer()),
        sa.Column("char_end", sa.Integer()),
        sa.Column("locator", postgresql.JSONB(), nullable=False),
        sa.Column("embedding", Vector(1024), nullable=True),
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True),
        sa.UniqueConstraint("document_version_id", "ordinal", name="uq_document_chunks_version_ordinal"),
    )
    op.create_index("ix_document_chunks_version_ordinal", "document_chunks", ["document_version_id", "ordinal"], unique=True)
    op.create_index("ix_document_chunks_version_id", "document_chunks", ["document_version_id"])
    op.create_index("ix_document_chunks_search_vector", "document_chunks", ["search_vector"], postgresql_using="gin")
    op.execute("CREATE INDEX ix_document_chunks_embedding_hnsw ON document_chunks USING hnsw (embedding vector_cosine_ops)")
    op.create_table(
        "attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_attachments_conversation_id", "attachments", ["conversation_id"])
    op.create_table(
        "citations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("locator", postgresql.JSONB(), nullable=False),
        sa.Column("is_valid", sa.Boolean(), nullable=False),
        sa.Column("validation_error", sa.String(120)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("message_id", "chunk_id", name="uq_citations_message_chunk"),
    )
    op.create_index("ix_citations_message_id", "citations", ["message_id"])
    op.create_table(
        "document_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True)),
        sa.Column("locked_by", sa.String(100)),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_document_jobs_status_available", "document_jobs", ["status", "available_at"])


def downgrade() -> None:
    op.drop_index("ix_document_jobs_status_available", table_name="document_jobs")
    op.drop_table("document_jobs")
    op.drop_index("ix_citations_message_id", table_name="citations")
    op.drop_table("citations")
    op.drop_index("ix_attachments_conversation_id", table_name="attachments")
    op.drop_table("attachments")
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw")
    op.drop_index("ix_document_chunks_search_vector", table_name="document_chunks")
    op.drop_index("ix_document_chunks_version_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_version_ordinal", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_constraint("fk_documents_current_version", "documents", type_="foreignkey")
    op.drop_index("ix_document_versions_status", table_name="document_versions")
    op.drop_index("ix_document_versions_document_sha256", table_name="document_versions")
    op.drop_index("ix_document_versions_document_id", table_name="document_versions")
    op.drop_table("document_versions")
    op.drop_index("ix_documents_user_id", table_name="documents")
    op.drop_index("ix_documents_user_group_updated", table_name="documents")
    op.drop_table("documents")
    op.drop_index("ix_knowledge_groups_user_id", table_name="knowledge_groups")
    op.drop_table("knowledge_groups")
