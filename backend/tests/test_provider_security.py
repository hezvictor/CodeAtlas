import pytest


def test_provider_secret_round_trip(monkeypatch):
    from app.security.provider_credentials import decrypt_secret, encrypt_secret

    monkeypatch.setenv("MODEL_CREDENTIAL_ENCRYPTION_KEY", "test-master-key-material")
    encrypted = encrypt_secret("sk-secret-value")

    assert encrypted.ciphertext != "sk-secret-value"
    assert decrypt_secret(encrypted.ciphertext, encrypted.nonce) == "sk-secret-value"


def test_provider_url_rejects_private_network(monkeypatch):
    from app.providers.url_validation import validate_provider_base_url

    monkeypatch.delenv("CODEATLAS_ALLOW_LOCAL_PROVIDER_URLS", raising=False)

    with pytest.raises(ValueError, match="private network"):
        validate_provider_base_url("http://127.0.0.1:11434/v1")


def test_provider_url_normalizes_openai_path(monkeypatch):
    from app.providers.url_validation import validate_provider_base_url

    monkeypatch.setenv("CODEATLAS_ALLOW_LOCAL_PROVIDER_URLS", "1")

    assert validate_provider_base_url("https://api.example.com/v1/") == "https://api.example.com/v1"
