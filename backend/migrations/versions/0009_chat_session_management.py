"""add conversation pinning and persisted retrieval ids"""
from alembic import op
import sqlalchemy as sa

revision = "0009_chat_session_management"
down_revision = "0008_phase4_reliability_closure"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("conversations", sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("messages", sa.Column("retrieved_chunk_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    op.alter_column("conversations", "pinned", server_default=None)
    op.alter_column("messages", "retrieved_chunk_ids", server_default=None)

def downgrade() -> None:
    op.drop_column("messages", "retrieved_chunk_ids")
    op.drop_column("conversations", "pinned")
