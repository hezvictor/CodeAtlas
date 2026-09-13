from pathlib import Path


def test_problem_migration_contains_idempotent_seed_rows():
    source = Path(__file__).parents[1].joinpath("migrations/versions/0007_problem_acm_workflow.py").read_text(encoding="utf-8")

    for slug in ("hello-world", "a-plus-b", "basic-io", "branch-judgment", "simple-loop"):
        assert slug in source
    assert "ON CONFLICT" in source
