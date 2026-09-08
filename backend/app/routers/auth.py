from datetime import UTC, datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from ..auth import create_access_token, create_refresh_token, hash_password, hash_refresh_token, verify_password
from ..db import get_session
from ..dependencies import current_user_id
from ..models import RefreshToken, User
from ..schemas import LoginRequest, LogoutRequest, RefreshRequest, RegisterRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])

def token_response(user: User, refresh: str) -> TokenResponse:
    return TokenResponse(access_token=create_access_token(user.id), refresh_token=refresh, user=UserResponse.model_validate(user))

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(payload: RegisterRequest, session: AsyncSession = Depends(get_session)):
    email = str(payload.email).lower()
    if await session.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(email=email, nickname=payload.nickname, password_hash=hash_password(payload.password))
    raw, token_hash, expires = create_refresh_token()
    session.add(user)
    await session.flush()
    session.add(RefreshToken(user_id=user.id, token_hash=token_hash, expires_at=expires))
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Email already registered") from None
    await session.refresh(user)
    return token_response(user, raw)

@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_session)):
    user = await session.scalar(select(User).where(User.email == str(payload.email).lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    raw, token_hash, expires = create_refresh_token()
    session.add(RefreshToken(user_id=user.id, token_hash=token_hash, expires_at=expires))
    await session.commit()
    return token_response(user, raw)

@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, session: AsyncSession = Depends(get_session)):
    record = await session.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(payload.refresh_token)).with_for_update())
    if not record or record.revoked_at or record.expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    record.revoked_at = datetime.now(UTC)
    user = await session.get(User, record.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    raw, token_hash, expires = create_refresh_token()
    session.add(RefreshToken(user_id=record.user_id, token_hash=token_hash, expires_at=expires))
    await session.commit()
    return token_response(user, raw)

@router.post("/logout", status_code=204)
async def logout(payload: LogoutRequest, user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    record = await session.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(payload.refresh_token), RefreshToken.user_id == user_id))
    if record and not record.revoked_at:
        record.revoked_at = datetime.now(UTC)
        await session.commit()

@router.get("/me", response_model=UserResponse)
async def me(user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
