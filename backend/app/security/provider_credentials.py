import base64
import hashlib
import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


@dataclass(frozen=True, slots=True)
class EncryptedSecret:
    ciphertext: str
    nonce: str


def _master_key() -> bytes:
    configured = os.getenv("MODEL_CREDENTIAL_ENCRYPTION_KEY", "").strip()
    if not configured:
        raise RuntimeError("MODEL_CREDENTIAL_ENCRYPTION_KEY is not configured")
    return hashlib.sha256(configured.encode("utf-8")).digest()


def encrypt_secret(value: str) -> EncryptedSecret:
    if not value:
        raise ValueError("secret must not be empty")
    nonce = os.urandom(12)
    ciphertext = AESGCM(_master_key()).encrypt(nonce, value.encode("utf-8"), None)
    encoder = base64.urlsafe_b64encode
    return EncryptedSecret(encoder(ciphertext).decode("ascii"), encoder(nonce).decode("ascii"))


def decrypt_secret(ciphertext: str, nonce: str) -> str:
    decoder = base64.urlsafe_b64decode
    plaintext = AESGCM(_master_key()).decrypt(decoder(nonce), decoder(ciphertext), None)
    return plaintext.decode("utf-8")
