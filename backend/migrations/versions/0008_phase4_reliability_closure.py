"""add auth version and storage cleanup state"""

from alembic import op
import sqlalchemy as sa

revision = "0008_phase4_reliability_closure"
down_revision = "0007_problem_acm_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("auth_version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("document_versions", sa.Column("storage_deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("document_versions", sa.Column("storage_delete_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("document_versions", sa.Column("storage_delete_error", sa.Text(), nullable=True))
    op.alter_column("users", "auth_version", server_default=None)
    op.alter_column("document_versions", "storage_delete_attempts", server_default=None)


def downgrade() -> None:
    op.drop_column("document_versions", "storage_delete_error")
    op.drop_column("document_versions", "storage_delete_attempts")
    op.drop_column("document_versions", "storage_deleted_at")
    op.drop_column("users", "auth_version")
