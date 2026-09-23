"""persist per-conversation and per-message RAG state"""

from alembic import op
import sqlalchemy as sa


revision = "0012_rag_chat_state"
down_revision = "0011_user_owned_problem_copies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("knowledge_scope", sa.String(10), nullable=False, server_default="none"),
    )
    op.alter_column("conversations", "knowledge_scope", server_default=None)
    op.add_column(
        "messages",
        sa.Column("knowledge_scope", sa.String(10), nullable=False, server_default="none"),
    )
    op.alter_column("messages", "knowledge_scope", server_default=None)


def downgrade() -> None:
    op.drop_column("messages", "knowledge_scope")
    op.drop_column("conversations", "knowledge_scope")
