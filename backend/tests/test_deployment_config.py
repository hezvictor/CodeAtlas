import os
from pathlib import Path

import pytest


def compose_file() -> Path:
    configured = os.environ.get("CODEATLAS_COMPOSE_FILE")
    return Path(configured) if configured else Path(__file__).parents[2].joinpath("docker-compose.yml")


def test_production_rejects_default_credentials():
    from app.config import Settings

    with pytest.raises(ValueError):
        Settings(app_env="production", jwt_secret_key="replace-with-a-long-random-secret")


def test_production_requires_model_credential_encryption_key():
    from app.config import Settings

    with pytest.raises(ValueError, match="MODEL_CREDENTIAL_ENCRYPTION_KEY"):
        Settings(
            app_env="production",
            jwt_secret_key="j" * 32,
            minio_root_password="m" * 32,
            frontend_url="https://codeatlas.example.com",
            model_credential_encryption_key="",
        )


def test_compose_does_not_hardcode_service_credentials():
    compose = compose_file().read_text(encoding="utf-8")
    assert "POSTGRES_PASSWORD: codeatlas-dev-password" not in compose
    assert "MINIO_ROOT_PASSWORD: codeatlas-dev-password" not in compose


def test_compose_uses_environment_for_browser_url_and_database_healthcheck():
    compose = compose_file().read_text(encoding="utf-8")
    assert "FRONTEND_URL: ${FRONTEND_URL:-http://localhost:3000}" in compose
    assert 'pg_isready -U ${POSTGRES_USER:-codeatlas} -d ${POSTGRES_DB:-codeatlas}' in compose


def test_compose_boots_without_a_local_env_file():
    """`git clone` 之后直接 `docker compose up -d --build` 必须可用，无需手工创建 .env。"""
    compose = compose_file().read_text(encoding="utf-8")
    assert ":?" not in compose, "compose 不能再声明必填变量"
    assert "required: false" in compose
    required = ("${POSTGRES_USER}", "${POSTGRES_PASSWORD}", "${POSTGRES_DB}",
                "${MINIO_ROOT_USER}", "${MINIO_ROOT_PASSWORD}", "${JWT_SECRET_KEY}", "${S3_BUCKET}")
    for line in compose.splitlines():
        if any(token in line for token in required):
            raise AssertionError(f"变量缺少默认值: {line.strip()}")


def test_compose_exposes_no_model_credential_environment_channel():
    """模型凭证只走页面配置，compose 不再下发任何模型环境变量。"""
    compose = compose_file().read_text(encoding="utf-8")
    assert "DASHSCOPE_API_KEY" not in compose
    assert "CHAT_MODEL" not in compose
    assert "EMBEDDING_MODEL" not in compose
