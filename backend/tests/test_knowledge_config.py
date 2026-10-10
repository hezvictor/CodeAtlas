import pytest

from app.config import Settings


def test_upload_configuration_cannot_enable_formats_without_a_parser():
    with pytest.raises(ValueError, match="Unsupported document extensions"):
        Settings(allowed_document_extensions={".md", ".pdf"})


def test_knowledge_settings_expose_embedding_and_upload_defaults():
    settings = Settings(embedding_dimensions=1024)

    assert settings.embedding_dimensions == 1024
    assert settings.max_upload_size_bytes == 20 * 1024 * 1024
    assert ".html" in settings.allowed_document_extensions
    assert Settings().embedding_dimensions == 1024
    assert Settings().embedding_batch_size == 10
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


def test_settings_expose_no_project_level_model_credentials():
    """模型凭证只能由用户在页面上配置；环境变量不再提供任何回退通道。"""
    settings = Settings()

    assert not hasattr(settings, "dashscope_api_key")
    assert not hasattr(settings, "dashscope_base_url")
    assert not hasattr(settings, "embedding_model")
    assert not hasattr(settings, "chat_model")
    assert settings.embedding_dimensions == 1024
