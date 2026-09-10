"""add generation timing fields to messages"""
from alembic import op
import sqlalchemy as sa

revision = "0003_message_generation_metrics"
down_revision = "0002_conversations_messages"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("messages", sa.Column("duration_ms", sa.Integer(), nullable=True))
    op.add_column("messages", sa.Column("first_token_latency_ms", sa.Integer(), nullable=True))

def downgrade():
    op.drop_column("messages", "first_token_latency_ms")
    op.drop_column("messages", "duration_ms")
