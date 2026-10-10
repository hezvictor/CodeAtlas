from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DOCUMENT_MIME_TYPES = {
    ".md": "text/markdown", ".markdown": "text/markdown", ".txt": "text/plain",
    ".html": "text/html", ".htm": "text/html", ".py": "text/x-python",
    ".java": "text/x-java-source", ".c": "text/x-c", ".cc": "text/x-c++src",
    ".cpp": "text/x-c++src", ".h": "text/x-c", ".hpp": "text/x-c++hdr",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


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
    ephemeral_redis_url: str = "redis://localhost:6380/0"
    agent_max_tool_rounds: int = 2
    agent_max_tool_calls: int = 4
    agent_max_model_calls: int = 4
    agent_tool_timeout_seconds: int = 15
    agent_active_timeout_seconds: int = 180
    agent_checkpoint_retention_seconds: int = 86400
    agent_context_wait_seconds: int = 604800
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
    # 模型凭证只能由用户在页面上配置，不存在项目级环境变量回退通道；
    # 这里只保留固定的向量维度，用于数据库列类型校验。
    embedding_dimensions: int = 1024
    embedding_batch_size: int = 10
    embedding_max_input_chars: int = 12_000
    reranker_base_url: str = ""
    reranker_api_key: str = ""
    reranker_model: str = ""
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
    allowed_document_extensions: set[str] = set(DOCUMENT_MIME_TYPES)
    frontend_url: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    @field_validator("allowed_document_extensions")
    @classmethod
    def validate_document_extensions(cls, value: set[str]) -> set[str]:
        unsupported = value - DOCUMENT_MIME_TYPES.keys()
        if unsupported:
            raise ValueError(f"Unsupported document extensions: {', '.join(sorted(unsupported))}")
        return value

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("JWT_SECRET_KEY must not be empty")
        return value

    @field_validator("agent_max_tool_rounds", "agent_max_tool_calls", "agent_max_model_calls", "agent_tool_timeout_seconds", "agent_active_timeout_seconds", "agent_checkpoint_retention_seconds", "agent_context_wait_seconds", "embedding_dimensions", "embedding_batch_size", "embedding_max_input_chars", "max_upload_size_bytes", "max_extracted_text_chars", "document_job_max_attempts", "document_job_timeout_seconds", "embedding_max_retries", "chat_history_max_messages", "chat_history_max_chars", "rag_context_max_chars", "avatar_max_size_bytes", "refresh_token_retention_days")
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
            or self.jwt_secret_key.startswith(("replace", "codeatlas-local"))
            or self.minio_root_password.startswith(("codeatlas-dev", "codeatlas-local"))
            or "localhost" in self.frontend_url.lower()
        ):
            raise ValueError("Production credentials and browser URLs must not use development defaults")
        if self.app_env.lower() in {"prod", "production"} and (
            len(self.model_credential_encryption_key) < 32
            or self.model_credential_encryption_key.startswith(("replace", "codeatlas-local"))
        ):
            raise ValueError("MODEL_CREDENTIAL_ENCRYPTION_KEY must have at least 32 characters in production")


@lru_cache
def get_settings() -> Settings:
    return Settings()
