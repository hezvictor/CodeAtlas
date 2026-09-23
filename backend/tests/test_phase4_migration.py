import uuid
from pathlib import Path


def test_user_has_auth_version_default():
    from app.models import User

    user = User(email="a@example.com", password_hash="hash", nickname="A")
    assert user.auth_version == 1


def test_document_version_has_storage_cleanup_state():
    from app.models import DocumentVersion

    version = DocumentVersion(document_id=uuid.uuid4(), version_no=1, status="uploaded")
    assert version.storage_delete_attempts == 0
    assert version.storage_deleted_at is None


def test_migration_adds_phase4_columns():
    source = Path(__file__).parents[1].joinpath(
        "migrations/versions/0008_phase4_reliability_closure.py"
    ).read_text()
    assert "auth_version" in source
    assert "storage_deleted_at" in source
    assert "storage_delete_attempts" in source
