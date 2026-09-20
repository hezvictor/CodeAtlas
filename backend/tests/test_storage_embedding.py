from app.providers.embedding import validate_embedding_vectors
from app.storage.s3 import object_key_for


def test_object_key_contains_scope_document_and_version_without_path_traversal():
    key = object_key_for("u", "g", "d", 2, "../../notes.md")

    assert key.startswith("users/u/scopes/g/documents/d/versions/2/")
    assert ".." not in key
    assert key.endswith("notes.md")


def test_embedding_vectors_require_expected_count_and_dimension():
    assert validate_embedding_vectors([[0.1, 0.2]], expected_count=1, dimensions=2) == [[0.1, 0.2]]
    try:
        validate_embedding_vectors([[0.1]], expected_count=1, dimensions=2)
    except ValueError as error:
        assert "dimension" in str(error)
    else:
        raise AssertionError("dimension mismatch must fail")
