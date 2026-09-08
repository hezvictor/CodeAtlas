from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://codeatlas:codeatlas-dev-password@localhost:5432/codeatlas"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret_key: str = "replace-me"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30
    s3_endpoint: str = "http://localhost:9000"
    s3_bucket: str = "codeatlas-documents"
    s3_region: str = "us-east-1"
    minio_root_user: str = "codeatlas"
    minio_root_password: str = "codeatlas-dev-password"
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    chat_model: str = ""
    embedding_model: str = ""
    frontend_url: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("JWT_SECRET_KEY must not be empty")
        return value

    def model_post_init(self, __context) -> None:
        if self.app_env.lower() in {"prod", "production"} and (
            len(self.jwt_secret_key) < 32 or self.jwt_secret_key.startswith("replace")
        ):
            raise ValueError("A strong JWT_SECRET_KEY is required in production")


@lru_cache
def get_settings() -> Settings:
    return Settings()
