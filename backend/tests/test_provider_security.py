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
    import socket

    from app.providers.url_validation import validate_provider_base_url

    monkeypatch.setenv("CODEATLAS_ALLOW_LOCAL_PROVIDER_URLS", "1")
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))])

    assert validate_provider_base_url("https://api.example.com/v1/") == "https://api.example.com/v1"


def test_provider_url_rejects_domain_resolving_to_private_address(monkeypatch):
    import socket

    from app.providers.url_validation import validate_provider_base_url

    monkeypatch.delenv("CODEATLAS_ALLOW_LOCAL_PROVIDER_URLS", raising=False)
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.8", 443))])
    with pytest.raises(ValueError, match="private network"):
        validate_provider_base_url("https://model.example/v1")


def test_production_provider_url_requires_https(monkeypatch):
    from app.providers.url_validation import validate_provider_base_url

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("CODEATLAS_ALLOW_LOCAL_PROVIDER_URLS", raising=False)
    with pytest.raises(ValueError, match="https"):
        validate_provider_base_url("http://model.example/v1")
