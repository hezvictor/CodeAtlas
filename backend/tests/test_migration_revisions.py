import re
from pathlib import Path


def test_migration_revisions_fit_alembic_default_version_column():
    migrations_dir = Path(__file__).parents[1] / "migrations" / "versions"
    revision_pattern = re.compile(r'^revision\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)

    revisions = []
    for migration in migrations_dir.glob("*.py"):
        match = revision_pattern.search(migration.read_text(encoding="utf-8"))
        if match:
            revisions.append(match.group(1))

    assert revisions
    assert all(len(revision) <= 32 for revision in revisions)
