from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.schemas import RerankerConfigUpdate


@pytest.mark.asyncio
async def test_existing_reranker_can_change_model_without_replacing_secret(monkeypatch):
    from app.routers import model_connections

    config = SimpleNamespace(
        user_id=uuid4(), base_url="https://old.example/v1", model_name="old",
        api_key_ciphertext="saved-ciphertext", api_key_nonce="saved-nonce",
        status="verified", verification_error=None, last_tested_at=None,
    )

    class Session:
        async def scalar(self, _statement):
            return config

        async def commit(self):
            pass

        async def refresh(self, _value):
            pass

    monkeypatch.setattr(model_connections, "validate_provider_base_url", lambda value: value)
    monkeypatch.setattr(model_connections, "reranker_response", lambda value: value)
    payload = RerankerConfigUpdate(base_url="https://new.example/v1", model_name="new")
    result = await model_connections.update_reranker_config(payload, user_id=config.user_id, session=Session())
    assert result.api_key_ciphertext == "saved-ciphertext"
    assert result.api_key_nonce == "saved-nonce"
    assert result.model_name == "new"
    assert result.status == "unverified"


@pytest.mark.asyncio
async def test_new_reranker_requires_a_nonempty_key(monkeypatch):
    from app.routers import model_connections

    class Session:
        async def scalar(self, _statement):
            return None

    monkeypatch.setattr(model_connections, "validate_provider_base_url", lambda value: value)
    payload = RerankerConfigUpdate(base_url="https://new.example/v1", model_name="new")
    with pytest.raises(HTTPException) as error:
        await model_connections.update_reranker_config(payload, user_id=uuid4(), session=Session())
    assert error.value.status_code == 422

    with pytest.raises(ValidationError):
        RerankerConfigUpdate(base_url="https://new.example/v1", model_name="new", api_key="")

    with pytest.raises(ValidationError):
        RerankerConfigUpdate(base_url="https://new.example/v1", model_name="new", api_key="   ")


@pytest.mark.asyncio
async def test_existing_reranker_replaces_secret_when_new_key_is_provided(monkeypatch):
    from app.routers import model_connections

    config = SimpleNamespace(
        user_id=uuid4(), base_url="https://old.example/v1", model_name="old",
        api_key_ciphertext="old-ciphertext", api_key_nonce="old-nonce",
        status="verified", verification_error=None, last_tested_at=None,
    )

    class Session:
        async def scalar(self, _statement):
            return config

        async def commit(self):
            pass

        async def refresh(self, _value):
            pass

    monkeypatch.setattr(model_connections, "validate_provider_base_url", lambda value: value)
    monkeypatch.setattr(model_connections, "encrypt_secret", lambda value: SimpleNamespace(ciphertext=f"cipher:{value}", nonce="new-nonce"))
    monkeypatch.setattr(model_connections, "reranker_response", lambda value: value)
    payload = RerankerConfigUpdate(base_url="https://new.example/v1", model_name="new", api_key="new-key")
    result = await model_connections.update_reranker_config(payload, user_id=config.user_id, session=Session())
    assert result.api_key_ciphertext == "cipher:new-key"
    assert result.api_key_nonce == "new-nonce"
