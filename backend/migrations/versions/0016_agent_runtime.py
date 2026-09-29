"""Bounded agent runs; keep old document content as an inactive archive."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0016_agent_runtime"
down_revision = "0015_knowledge_lifecycle"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("chat_models", sa.Column("capabilities", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("chat_models", sa.Column("context_window_tokens", sa.Integer(), nullable=True))
    op.drop_column("conversations", "knowledge_scope")
    op.drop_column("messages", "knowledge_scope")
    # Archive only. No original, extracted text, chunk, object or citation is deleted.
    op.rename_table("attachments", "legacy_chat_associations")
    op.execute("""UPDATE document_jobs j SET status='cancelled', locked_at=NULL, locked_by=NULL,
        finished_at=COALESCE(j.finished_at, now()), error_code='LEGACY_SESSION_ARCHIVED'
        FROM document_versions v JOIN documents d ON d.id=v.document_id
        WHERE j.document_version_id=v.id AND d.scope='session'
          AND j.status IN ('queued','running','waiting_embedding')""")
    op.create_table("chat_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conversation_id", UUID(as_uuid=True), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message_id", UUID(as_uuid=True), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_message_id", UUID(as_uuid=True), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chat_model_id", UUID(as_uuid=True), sa.ForeignKey("chat_models.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="queued"),
        sa.Column("owner", UUID(as_uuid=True)),
        *[sa.Column(name, sa.DateTime(timezone=True)) for name in ("locked_at", "waiting_at", "finished_at")],
        sa.Column("context_required", sa.Boolean(), nullable=False, server_default="false"),
        *[sa.Column(name, sa.Integer(), nullable=False, server_default="0") for name in
          ("model_calls", "tool_calls", "tool_rounds", "active_ms", "event_sequence")],
        sa.Column("error_code", sa.String(80)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("uq_chat_runs_active_conversation", "chat_runs", ["conversation_id"], unique=True,
                    postgresql_where=sa.text("status IN ('queued','running','waiting_context')"))
    op.create_index("ix_chat_runs_status_locked", "chat_runs", ["status", "locked_at"])
    # Static schema for langgraph-checkpoint-postgres 3.1.2. No runtime DDL.
    op.execute("CREATE TABLE checkpoint_migrations (v INTEGER PRIMARY KEY)")
    op.execute("""CREATE TABLE checkpoints (
        thread_id TEXT NOT NULL, checkpoint_ns TEXT NOT NULL DEFAULT '', checkpoint_id TEXT NOT NULL,
        parent_checkpoint_id TEXT, type TEXT, checkpoint JSONB NOT NULL, metadata JSONB NOT NULL DEFAULT '{}',
        PRIMARY KEY(thread_id, checkpoint_ns, checkpoint_id))""")
    op.execute("""CREATE TABLE checkpoint_blobs (
        thread_id TEXT NOT NULL, checkpoint_ns TEXT NOT NULL DEFAULT '', channel TEXT NOT NULL,
        version TEXT NOT NULL, type TEXT NOT NULL, blob BYTEA,
        PRIMARY KEY(thread_id, checkpoint_ns, channel, version))""")
    op.execute("""CREATE TABLE checkpoint_writes (
        thread_id TEXT NOT NULL, checkpoint_ns TEXT NOT NULL DEFAULT '', checkpoint_id TEXT NOT NULL,
        task_id TEXT NOT NULL, idx INTEGER NOT NULL, channel TEXT NOT NULL, type TEXT, blob BYTEA NOT NULL,
        task_path TEXT NOT NULL DEFAULT '', PRIMARY KEY(thread_id, checkpoint_ns, checkpoint_id, task_id, idx))""")
    for table in ("checkpoints", "checkpoint_blobs", "checkpoint_writes"):
        op.create_index(f"{table}_thread_id_idx", table, ["thread_id"])
    op.execute("INSERT INTO checkpoint_migrations(v) SELECT generate_series(0,9)")


def downgrade():
    for table in ("checkpoint_writes", "checkpoint_blobs", "checkpoints", "checkpoint_migrations", "chat_runs"):
        op.drop_table(table)
    op.rename_table("legacy_chat_associations", "attachments")
    for table in ("conversations", "messages"):
        op.add_column(table, sa.Column("knowledge_scope", sa.String(20), nullable=False, server_default="none"))
    op.drop_column("chat_models", "context_window_tokens")
    op.drop_column("chat_models", "capabilities")
