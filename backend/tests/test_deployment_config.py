from pathlib import Path
import os

import pytest


def compose_file() -> Path:
    configured = os.environ.get("CODEATLAS_COMPOSE_FILE")
    return Path(configured) if configured else Path(__file__).parents[2].joinpath("docker-compose.yml")


def test_production_rejects_default_credentials():
    from app.config import Settings

    with pytest.raises(ValueError):
        Settings(app_env="production", jwt_secret_key="replace-with-a-long-random-secret")


def test_compose_does_not_hardcode_service_credentials():
    compose = compose_file().read_text(encoding="utf-8")
    assert "POSTGRES_PASSWORD: codeatlas-dev-password" not in compose
    assert "MINIO_ROOT_PASSWORD: codeatlas-dev-password" not in compose


def test_compose_uses_environment_for_browser_url_and_database_healthcheck():
    compose = compose_file().read_text(encoding="utf-8")
    assert "FRONTEND_URL: ${FRONTEND_URL:-http://localhost:3000}" in compose
    assert 'pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}' in compose
