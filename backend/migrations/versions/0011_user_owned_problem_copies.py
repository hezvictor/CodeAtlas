"""copy system problem templates into each user's private problem set"""

from alembic import op
import sqlalchemy as sa


revision = "0011_user_owned_problem_copies"
down_revision = "0010_knowledge_scope_model_cfg"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO problems (
                id, owner_user_id, source_type, slug, title, difficulty, tags, statement,
                input_description, output_description, examples, constraints,
                supported_languages, search_vector
            )
            SELECT
                md5(u.id::text || p.id::text)::uuid,
                u.id,
                'default',
                'default-' || p.slug || '-' || replace(u.id::text, '-', ''),
                p.title,
                p.difficulty,
                p.tags,
                p.statement,
                p.input_description,
                p.output_description,
                p.examples,
                p.constraints,
                p.supported_languages,
                p.search_vector
            FROM users AS u
            CROSS JOIN problems AS p
            WHERE p.owner_user_id IS NULL AND p.source_type = 'system'
            ON CONFLICT (slug) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM problems WHERE source_type = 'default'"))
