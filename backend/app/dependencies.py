import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .db import get_session
from .models import User

bearer = HTTPBearer(auto_error=False)

async def current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: AsyncSession = Depends(get_session),
) -> uuid.UUID:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        payload = jwt.decode(credentials.credentials, get_settings().jwt_secret_key, algorithms=["HS256"])
        if payload.get("type") != "access":
            raise ValueError
        user_id = uuid.UUID(payload["sub"])
        token_version = payload.get("auth_version")
        if token_version is None:
            raise ValueError
        user = await session.get(User, user_id)
        if not user or user.auth_version != int(token_version):
            raise ValueError
        return user_id
    except (jwt.PyJWTError, ValueError, TypeError, OverflowError, KeyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token") from None
