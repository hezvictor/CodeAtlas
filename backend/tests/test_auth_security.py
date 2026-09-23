import uuid

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials


def credentials_for(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


@pytest.mark.asyncio
async def test_old_access_token_is_rejected_after_auth_version_changes():
    from app.auth import create_access_token
    from app.dependencies import current_user_id
    from app.models import User

    user = User(
        id=uuid.uuid4(), email="a@example.com", password_hash="hash", nickname="A", auth_version=1
    )
    token = create_access_token(user.id, user.auth_version)
    user.auth_version = 2

    class FakeSession:
        async def get(self, model, user_id):
            return user if user_id == user.id else None

    with pytest.raises(HTTPException) as error:
        await current_user_id(credentials_for(token), session=FakeSession())
    assert error.value.status_code == 401


def test_access_token_contains_jti_and_auth_version():
    from app.auth import create_access_token
    from app.config import get_settings

    token = create_access_token(uuid.uuid4(), 3)
    claims = jwt.decode(token, get_settings().jwt_secret_key, algorithms=["HS256"])
    assert claims["auth_version"] == 3
    assert claims["jti"]


@pytest.mark.asyncio
async def test_malformed_auth_version_is_rejected_as_unauthorized():
    from app.config import get_settings
    from app.dependencies import current_user_id

    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "type": "access", "auth_version": []},
        get_settings().jwt_secret_key,
        algorithm="HS256",
    )

    class FakeSession:
        async def get(self, model, user_id):
            return type("User", (), {"auth_version": 1})()

    with pytest.raises(HTTPException) as error:
        await current_user_id(credentials_for(token), session=FakeSession())

    assert error.value.status_code == 401


def test_refresh_token_retention_defaults_to_expiry_window():
    from app.config import Settings

    settings = Settings(refresh_token_expire_days=17)
    assert settings.refresh_token_retention_days == 17


def test_logout_locks_refresh_token_row_before_revoking():
    from sqlalchemy import select

    from app.models import RefreshToken

    statement = select(RefreshToken).where(RefreshToken.token_hash == "hash").with_for_update()
    assert statement._for_update_arg is not None


@pytest.mark.asyncio
async def test_cleanup_refresh_tokens_uses_retention_window():
    from app.tasks.auth_tasks import cleanup_refresh_tokens

    class Result:
        rowcount = 3

    class Session:
        async def execute(self, statement):
            self.statement = statement
            return Result()

        async def commit(self):
            self.committed = True

    class Context:
        async def __aenter__(self):
            self.session = Session()
            return self.session

        async def __aexit__(self, *_):
            return False

    import app.tasks.auth_tasks as tasks

    tasks.session_factory = lambda: Context()
    assert await cleanup_refresh_tokens() == 3
