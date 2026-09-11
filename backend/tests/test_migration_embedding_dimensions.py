from pathlib import Path


def test_embedding_dimension_migration_requeues_reset_versions():
    source = (Path(__file__).parents[1] / "migrations/versions/0005_embedding_dimensions.py").read_text(encoding="utf-8")

    assert "INSERT INTO document_jobs" in source
    assert "WHERE dv.status = 'uploaded'" in source


def test_job_reliability_migration_adds_outbox_fields_and_active_uniqueness():
    source = (Path(__file__).parents[1] / "migrations/versions/0006_job_reliability.py").read_text(encoding="utf-8")

    assert "dispatch_attempts" in source
    assert "last_dispatch_error" in source
    assert "uq_document_jobs_active_version" in source
