import uuid
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from .config import get_settings

bearer = HTTPBearer(auto_error=False)

async def current_user_id(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> uuid.UUID:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        payload = jwt.decode(credentials.credentials, get_settings().jwt_secret_key, algorithms=["HS256"])
        if payload.get("type") != "access":
            raise ValueError
        return uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token") from None
