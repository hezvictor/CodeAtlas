"""add optional per-user reranker configuration"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0013_reranker_config"
down_revision = "0012_rag_chat_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reranker_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("api_key_ciphertext", sa.Text(), nullable=False),
        sa.Column("api_key_nonce", sa.String(100), nullable=False),
        sa.Column("model_name", sa.String(120), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="unverified"),
        sa.Column("verification_error", sa.Text()),
        sa.Column("last_tested_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", name="uq_reranker_configs_user_id"),
    )


def downgrade() -> None:
    op.drop_table("reranker_configs")
