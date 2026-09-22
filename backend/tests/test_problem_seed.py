from pathlib import Path


def test_problem_migration_contains_idempotent_seed_rows():
    source = Path(__file__).parents[1].joinpath("migrations/versions/0007_problem_acm_workflow.py").read_text(encoding="utf-8")

    for slug in ("hello-world", "a-plus-b", "basic-io", "branch-judgment", "simple-loop"):
        assert slug in source
    assert "ON CONFLICT" in source


def test_user_problem_copy_migration_clones_templates_for_existing_users():
    source = Path(__file__).parents[1].joinpath("migrations/versions/0011_user_owned_problem_copies.py").read_text(encoding="utf-8")

    assert "CROSS JOIN problems" in source
    assert "source_type = 'default'" in source
    assert "owner_user_id" in source
    assert "ON CONFLICT (slug) DO NOTHING" in source
