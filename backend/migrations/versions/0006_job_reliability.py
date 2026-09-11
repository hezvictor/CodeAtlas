"""make document delivery durable and active jobs unique"""
from alembic import op
import sqlalchemy as sa


revision = "0006_job_reliability"
down_revision = "0005_embedding_dimensions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("document_jobs", sa.Column("dispatch_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("document_jobs", sa.Column("last_dispatch_at", sa.DateTime(timezone=True)))
    op.add_column("document_jobs", sa.Column("last_dispatch_error", sa.Text()))
    op.execute(
        """
        WITH ranked AS (
            SELECT id, row_number() OVER (
                PARTITION BY document_version_id
                ORDER BY created_at DESC, id DESC
            ) AS job_rank
            FROM document_jobs
            WHERE status IN ('queued', 'running')
        )
        UPDATE document_jobs AS job
        SET status = 'failed',
            error_message = 'Superseded by a newer active job',
            finished_at = now(),
            locked_at = NULL,
            locked_by = NULL
        FROM ranked
        WHERE job.id = ranked.id AND ranked.job_rank > 1
        """
    )
    op.create_index(
        "uq_document_jobs_active_version",
        "document_jobs",
        ["document_version_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running')"),
    )


def downgrade() -> None:
    op.drop_index("uq_document_jobs_active_version", table_name="document_jobs")
    op.drop_column("document_jobs", "last_dispatch_error")
    op.drop_column("document_jobs", "last_dispatch_at")
    op.drop_column("document_jobs", "dispatch_attempts")
