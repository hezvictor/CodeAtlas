"""Keep documents when their knowledge group is deleted."""

from alembic import op

revision = "0014_group_delete_set_null"
down_revision = "0013_reranker_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("documents_group_id_fkey", "documents", type_="foreignkey")
    op.create_foreign_key("documents_group_id_fkey", "documents", "knowledge_groups", ["group_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint("documents_group_id_fkey", "documents", type_="foreignkey")
    op.create_foreign_key("documents_group_id_fkey", "documents", "knowledge_groups", ["group_id"], ["id"], ondelete="CASCADE")
