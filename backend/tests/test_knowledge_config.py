from app.config import Settings


def test_knowledge_settings_expose_embedding_and_upload_defaults():
    settings = Settings(
        embedding_model="text-embedding-v3",
        embedding_dimensions=1024,
    )

    assert settings.embedding_dimensions == 1024
    assert settings.max_upload_size_bytes == 20 * 1024 * 1024
    assert ".html" in settings.allowed_document_extensions
    assert Settings().embedding_dimensions == 1024
    assert Settings().embedding_batch_size == 16
    assert Settings().embedding_max_input_chars == 12000


def test_knowledge_settings_reject_non_positive_embedding_dimension():
    try:
        Settings(embedding_dimensions=0)
    except ValueError as error:
        assert "EMBEDDING_DIMENSIONS" in str(error)
    else:
        raise AssertionError("embedding dimension must be positive")


def test_embedding_dimension_validation_rejects_database_mismatch():
    from app.config import validate_embedding_dimension

    validate_embedding_dimension(1024, "vector(1024)")
    try:
        validate_embedding_dimension(1536, "vector(1024)")
    except RuntimeError as error:
        assert "1536" in str(error)
        assert "1024" in str(error)
    else:
        raise AssertionError("database and configured embedding dimensions must match")


def test_project_embedding_defaults_require_key_and_model():
    from app.providers.embedding import project_embedding_is_configured

    assert project_embedding_is_configured(type("Settings", (), {"dashscope_api_key": "key", "embedding_model": "text-embedding-v3"})()) is True
    assert project_embedding_is_configured(type("Settings", (), {"dashscope_api_key": "", "embedding_model": "text-embedding-v3"})()) is False
