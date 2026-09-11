"""align embedding vectors with text-embedding-v3 deployment"""
from alembic import op
import sqlalchemy as sa

revision = "0005_embedding_dimensions"
down_revision = "0004_knowledge_rag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    # Existing vectors were created with the failed 1536-dimension configuration.
    # Clear them and requeue indexed versions so no incompatible vector survives.
    op.execute("UPDATE document_chunks SET embedding = NULL")
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(1024)")
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw")
    op.execute("CREATE INDEX ix_document_chunks_embedding_hnsw ON document_chunks USING hnsw (embedding vector_cosine_ops)")
    op.execute("UPDATE document_versions SET status = 'uploaded', indexed_at = NULL WHERE status = 'indexed'")
    op.execute(
        """
        INSERT INTO document_jobs (id, document_version_id, stage, status, attempts, available_at)
        SELECT gen_random_uuid(), dv.id, 'parsing', 'queued', 0, now()
        FROM document_versions dv
        WHERE dv.status = 'uploaded'
          AND NOT EXISTS (
              SELECT 1 FROM document_jobs dj
              WHERE dj.document_version_id = dv.id AND dj.status IN ('queued', 'running')
          )
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw")
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(1536)")
    op.execute("CREATE INDEX ix_document_chunks_embedding_hnsw ON document_chunks USING hnsw (embedding vector_cosine_ops)")
