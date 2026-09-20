from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


def validate_embedding_dimension(configured: int, database_type: str) -> None:
    expected = f"vector({configured})"
    actual = database_type.strip().lower()
    if actual != expected:
        raise RuntimeError(
            f"Embedding dimension mismatch: configuration requires {expected}, database column is {actual}"
        )


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://codeatlas:codeatlas-dev-password@localhost:5432/codeatlas"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret_key: str = "replace-me"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30
    refresh_token_retention_days: int | None = None
    s3_endpoint: str = "http://localhost:9000"
    s3_bucket: str = "codeatlas-documents"
    avatar_bucket: str = "codeatlas-avatars"
    browser_s3_endpoint: str = "http://localhost:9000"
    s3_region: str = "us-east-1"
    minio_root_user: str = "codeatlas"
    minio_root_password: str = "codeatlas-dev-password"
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    chat_model: str = ""
    embedding_model: str = "text-embedding-v3"
    embedding_dimensions: int = 1024
    model_credential_encryption_key: str = ""
    max_upload_size_bytes: int = 20 * 1024 * 1024
    max_extracted_text_chars: int = 2_000_000
    document_job_max_attempts: int = 3
    document_job_timeout_seconds: int = 300
    embedding_max_retries: int = 2
    embedding_retry_base_delay_seconds: float = 0.5
    embedding_retry_max_delay_seconds: float = 8.0
    chat_history_max_messages: int = 30
    chat_history_max_chars: int = 60_000
    rag_context_max_chars: int = 40_000
    avatar_max_size_bytes: int = 2 * 1024 * 1024
    allowed_document_extensions: set[str] = {
        ".md", ".markdown", ".pdf", ".docx", ".txt", ".c", ".cc", ".cpp", ".h", ".hpp",
        ".java", ".py", ".html", ".htm",
    }
    frontend_url: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("JWT_SECRET_KEY must not be empty")
        return value

    @field_validator("embedding_dimensions", "max_upload_size_bytes", "max_extracted_text_chars", "document_job_max_attempts", "document_job_timeout_seconds", "embedding_max_retries", "chat_history_max_messages", "chat_history_max_chars", "rag_context_max_chars", "avatar_max_size_bytes", "refresh_token_retention_days")
    @classmethod
    def validate_positive_limits(cls, value: int, info) -> int:
        if value is None:
            return value
        if value <= 0:
            raise ValueError(f"{info.field_name.upper()} must be positive")
        return value

    def model_post_init(self, __context) -> None:
        if self.refresh_token_retention_days is None:
            self.refresh_token_retention_days = self.refresh_token_expire_days
        if self.app_env.lower() in {"prod", "production"} and (
            len(self.jwt_secret_key) < 32
            or self.jwt_secret_key.startswith("replace")
            or self.minio_root_password.startswith("codeatlas-dev")
            or "localhost" in self.frontend_url.lower()
        ):
            raise ValueError("Production credentials and browser URLs must not use development defaults")


@lru_cache
def get_settings() -> Settings:
    return Settings()
