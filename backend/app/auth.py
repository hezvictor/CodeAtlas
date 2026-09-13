import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
import jwt
from argon2 import PasswordHasher
from .config import get_settings

password_hasher = PasswordHasher()

def hash_password(password: str) -> str:
    return password_hasher.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except Exception:
        return False

def create_access_token(user_id: uuid.UUID, auth_version: int = 1) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "type": "access",
        "auth_version": auth_version,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(claims, settings.jwt_secret_key, algorithm="HS256")

def create_refresh_token() -> tuple[str, str, datetime]:
    expires = datetime.now(UTC) + timedelta(days=get_settings().refresh_token_expire_days)
    raw = secrets.token_urlsafe(48)
    return raw, hashlib.sha256(raw.encode()).hexdigest(), expires

def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
