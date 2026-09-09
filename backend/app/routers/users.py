import asyncio
import uuid
from functools import partial
import boto3
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from ..auth import hash_password, verify_password
from ..dependencies import current_user_id
from ..db import get_session
from ..models import RefreshToken, User
from ..schemas import PasswordUpdate, UserResponse, UserUpdate
from ..config import get_settings

router = APIRouter(prefix="/users", tags=["users"])

async def get_user(uid, session):
    user = await session.get(User, uid)
    if not user:
        raise HTTPException(404, "User not found")
    return user

@router.get("/me", response_model=UserResponse)
async def me(uid=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    return await get_user(uid, session)

@router.patch("/me", response_model=UserResponse)
async def update_me(payload: UserUpdate, uid=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    user = await get_user(uid, session)
    existing = await session.scalar(select(User).where(User.email == str(payload.email).lower(), User.id != uid))
    if existing:
        raise HTTPException(409, "Email already registered")
    user.nickname = payload.nickname.strip()
    user.email = str(payload.email).lower()
    await session.commit()
    await session.refresh(user)
    return user

@router.patch("/me/password", status_code=204)
async def update_password(payload: PasswordUpdate, uid=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    user = await get_user(uid, session)
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    user.password_hash = hash_password(payload.new_password)
    await session.execute(update(RefreshToken).where(RefreshToken.user_id == uid, RefreshToken.revoked_at.is_(None)).values(revoked_at=func.now()))
    await session.commit()

@router.post("/me/avatar", response_model=UserResponse)
async def upload_avatar(file: UploadFile = File(...), uid=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(400, "Only JPEG, PNG, and WebP images are supported")
    data = await file.read()
    if len(data) > 2 * 1024 * 1024:
        raise HTTPException(413, "Avatar must be 2 MB or smaller")
    settings = get_settings()
    signatures = {"image/jpeg": b"\xff\xd8\xff", "image/png": b"\x89PNG\r\n\x1a\n", "image/webp": b"RIFF"}
    if not data.startswith(signatures[file.content_type]):
        raise HTTPException(400, "Uploaded file is not a valid image")
    object_key = f"avatars/{uid}/{uuid.uuid4()}.{file.content_type.split('/')[-1]}"
    client = boto3.client("s3", endpoint_url=settings.s3_endpoint, aws_access_key_id=settings.minio_root_user, aws_secret_access_key=settings.minio_root_password, region_name=settings.s3_region)
    try:
        await asyncio.to_thread(partial(client.head_bucket, Bucket=settings.avatar_bucket))
    except client.exceptions.ClientError:
        await asyncio.to_thread(partial(client.create_bucket, Bucket=settings.avatar_bucket))
    await asyncio.to_thread(partial(client.put_object, Bucket=settings.avatar_bucket, Key=object_key, Body=data, ContentType=file.content_type))
    user = await get_user(uid, session)
    policy = '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":["*"]},"Action":["s3:GetObject"],"Resource":["arn:aws:s3:::%s/*"]}]}' % settings.avatar_bucket
    await asyncio.to_thread(partial(client.put_bucket_policy, Bucket=settings.avatar_bucket, Policy=policy))
    user.avatar_url = f"{settings.browser_s3_endpoint.rstrip('/')}/{settings.avatar_bucket}/{object_key}"
    await session.commit()
    await session.refresh(user)
    return user
