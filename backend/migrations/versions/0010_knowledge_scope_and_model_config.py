"""add document scopes, durable citation metadata, and user model configuration"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0010_knowledge_scope_and_model_config"
down_revision = "0009_chat_session_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("scope", sa.String(20), nullable=False, server_default="long_term"))
    op.alter_column("documents", "scope", server_default=None)
    op.alter_column("documents", "group_id", nullable=True)
    op.create_index("ix_documents_user_scope_updated", "documents", ["user_id", "scope", "updated_at"])

    op.add_column("citations", sa.Column("source_scope", sa.String(20), nullable=False, server_default="long_term"))
    op.add_column("citations", sa.Column("document_title_snapshot", sa.String(200), nullable=True))
    op.add_column("citations", sa.Column("original_filename_snapshot", sa.String(255), nullable=True))
    op.alter_column("citations", "source_scope", server_default=None)

    op.add_column("users", sa.Column("default_chat_model_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("conversations", sa.Column("selected_chat_model_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_conversations_selected_chat_model_id", "conversations", ["selected_chat_model_id"])
    op.add_column("messages", sa.Column("chat_model_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("messages", sa.Column("model_name_snapshot", sa.String(200), nullable=True))
    op.create_index("ix_messages_chat_model_id", "messages", ["chat_model_id"])

    op.create_table(
        "model_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("api_key_ciphertext", sa.Text(), nullable=False),
        sa.Column("api_key_nonce", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_model_connections_user_id", "model_connections", ["user_id"])
    op.create_index("ix_model_connections_user_updated", "model_connections", ["user_id", "updated_at"])

    op.create_table(
        "chat_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("model_connections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("source", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(20), nullable=False, server_default="unverified"),
        sa.Column("verification_error", sa.Text(), nullable=True),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("connection_id", "name", name="uq_chat_models_connection_name"),
    )
    op.create_index("ix_chat_models_connection_status", "chat_models", ["connection_id", "status"])

    op.create_table(
        "embedding_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("api_key_ciphertext", sa.Text(), nullable=False),
        sa.Column("api_key_nonce", sa.String(100), nullable=False),
        sa.Column("model_name", sa.String(120), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="unverified"),
        sa.Column("verification_error", sa.Text(), nullable=True),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_embedding_configs_user_id"),
    )


def downgrade() -> None:
    op.drop_table("embedding_configs")
    op.drop_index("ix_chat_models_connection_status", table_name="chat_models")
    op.drop_table("chat_models")
    op.drop_index("ix_model_connections_user_updated", table_name="model_connections")
    op.drop_index("ix_model_connections_user_id", table_name="model_connections")
    op.drop_table("model_connections")
    op.drop_index("ix_messages_chat_model_id", table_name="messages")
    op.drop_column("messages", "model_name_snapshot")
    op.drop_column("messages", "chat_model_id")
    op.drop_index("ix_conversations_selected_chat_model_id", table_name="conversations")
    op.drop_column("conversations", "selected_chat_model_id")
    op.drop_column("users", "default_chat_model_id")
    op.alter_column("documents", "group_id", nullable=False)
    op.drop_index("ix_documents_user_scope_updated", table_name="documents")
    op.drop_column("documents", "scope")
    op.drop_column("citations", "original_filename_snapshot")
    op.drop_column("citations", "document_title_snapshot")
    op.drop_column("citations", "source_scope")
