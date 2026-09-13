"""add problems and chat workflow metadata"""

import json

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0007_problem_acm_workflow"
down_revision = "0006_job_reliability"
branch_labels = None
depends_on = None


_SYSTEM_PROBLEMS = [
    {
        "id": "1c2d3e4f-5061-47a8-9b0c-1d2e3f405061",
        "slug": "hello-world",
        "title": "Hello World",
        "difficulty": "入门",
        "tags": ["基础输出"],
        "statement": "输出一行 Hello World。",
        "input_description": "本题没有输入。",
        "output_description": "输出 Hello World。",
        "examples": [{"input": "", "output": "Hello World"}],
        "constraints": "无。",
    },
    {
        "id": "2d3e4f50-6172-48b9-ac1d-2e3f40506172",
        "slug": "a-plus-b",
        "title": "A+B",
        "difficulty": "入门",
        "tags": ["基础输入输出", "数学"],
        "statement": "给定两个整数 A 和 B，输出它们的和。",
        "input_description": "一行包含两个整数 A 和 B。",
        "output_description": "输出 A+B。",
        "examples": [{"input": "1 2", "output": "3"}],
        "constraints": "-10^9 <= A, B <= 10^9。",
    },
    {
        "id": "3e4f5061-7283-49ca-bd2e-3f4050617283",
        "slug": "basic-io",
        "title": "基础输入输出",
        "difficulty": "入门",
        "tags": ["基础输入输出"],
        "statement": "读取一个整数和一个实数，并按指定顺序输出。",
        "input_description": "一行包含整数 n 和实数 x。",
        "output_description": "输出 n 和 x，中间用空格分隔。",
        "examples": [{"input": "7 3.5", "output": "7 3.5"}],
        "constraints": "n 为 32 位有符号整数，x 为有限实数。",
    },
    {
        "id": "4f506172-8394-4adb-ce3f-405061728394",
        "slug": "branch-judgment",
        "title": "分支判断",
        "difficulty": "入门",
        "tags": ["分支判断", "条件处理"],
        "statement": "给定整数 n，判断它是正数、负数还是零。",
        "input_description": "输入一个整数 n。",
        "output_description": "正数输出 positive，负数输出 negative，零输出 zero。",
        "examples": [{"input": "-2", "output": "negative"}],
        "constraints": "-10^9 <= n <= 10^9。",
    },
    {
        "id": "50617283-94ab-4bec-df40-5061728394ab",
        "slug": "simple-loop",
        "title": "简单循环",
        "difficulty": "入门",
        "tags": ["循环", "基础数学"],
        "statement": "给定 n，计算 1 到 n 的整数之和。",
        "input_description": "输入一个正整数 n。",
        "output_description": "输出 1+2+...+n 的结果。",
        "examples": [{"input": "5", "output": "15"}],
        "constraints": "1 <= n <= 100000。",
    },
]


def _seed_system_problems() -> None:
    bind = op.get_bind()
    statement = sa.text(
        """
        INSERT INTO problems (
            id, owner_user_id, source_type, slug, title, difficulty, tags, statement,
            input_description, output_description, examples, constraints,
            supported_languages, search_vector
        ) VALUES (
            CAST(:id AS uuid), NULL, 'system', :slug, :title, :difficulty,
            CAST(:tags AS jsonb), :statement, :input_description, :output_description,
            CAST(:examples AS jsonb), :constraints, CAST(:supported_languages AS jsonb),
            to_tsvector('simple', :search_text)
        )
        ON CONFLICT (slug) DO NOTHING
        """
    )
    rows = []
    for problem in _SYSTEM_PROBLEMS:
        rows.append(
            {
                **problem,
                "tags": json.dumps(problem["tags"], ensure_ascii=False),
                "examples": json.dumps(problem["examples"], ensure_ascii=False),
                "supported_languages": json.dumps(["cpp", "java", "python"]),
                "search_text": " ".join(
                    [problem["title"], problem["slug"], *problem["tags"], problem["statement"]]
                ),
            }
        )
    bind.execute(statement, rows)


def upgrade() -> None:
    op.create_table(
        "problems",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("source_type", sa.String(20), nullable=False, server_default="system"),
        sa.Column("slug", sa.String(160), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("difficulty", sa.String(30), nullable=False),
        sa.Column("tags", postgresql.JSONB(), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("input_description", sa.Text(), nullable=False),
        sa.Column("output_description", sa.Text(), nullable=False),
        sa.Column("examples", postgresql.JSONB(), nullable=False),
        sa.Column("constraints", sa.Text(), nullable=False),
        sa.Column("supported_languages", postgresql.JSONB(), nullable=False),
        sa.Column("search_vector", postgresql.TSVECTOR()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("slug", name="uq_problems_slug"),
    )
    op.create_index("ix_problems_owner_id", "problems", ["owner_user_id"])
    op.create_index("ix_problems_source_difficulty", "problems", ["source_type", "difficulty"])
    op.create_index("ix_problems_search_vector", "problems", ["search_vector"], postgresql_using="gin")
    op.add_column("messages", sa.Column("problem_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("messages", sa.Column("mode", sa.String(30), nullable=False, server_default="normal"))
    op.add_column("messages", sa.Column("solution_language", sa.String(20), nullable=True))
    op.create_index("ix_messages_problem_id", "messages", ["problem_id"])
    op.create_foreign_key("fk_messages_problem_id", "messages", "problems", ["problem_id"], ["id"], ondelete="SET NULL")
    _seed_system_problems()


def downgrade() -> None:
    op.drop_constraint("fk_messages_problem_id", "messages", type_="foreignkey")
    op.drop_index("ix_messages_problem_id", table_name="messages")
    op.drop_column("messages", "solution_language")
    op.drop_column("messages", "mode")
    op.drop_column("messages", "problem_id")
    op.drop_index("ix_problems_search_vector", table_name="problems")
    op.drop_index("ix_problems_source_difficulty", table_name="problems")
    op.drop_index("ix_problems_owner_id", table_name="problems")
    op.drop_table("problems")
