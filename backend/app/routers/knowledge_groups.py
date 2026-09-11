import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..dependencies import current_user_id
from ..models import KnowledgeGroup
from ..schemas import KnowledgeGroupCreate, KnowledgeGroupResponse, KnowledgeGroupUpdate

router = APIRouter(prefix="/knowledge/groups", tags=["knowledge"])


async def owned_group(group_id: uuid.UUID, user_id: uuid.UUID, session: AsyncSession) -> KnowledgeGroup:
    group = await session.scalar(select(KnowledgeGroup).where(KnowledgeGroup.id == group_id, KnowledgeGroup.user_id == user_id))
    if not group:
        raise HTTPException(404, "Knowledge group not found")
    return group


@router.get("", response_model=list[KnowledgeGroupResponse])
async def list_groups(user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    return (await session.scalars(select(KnowledgeGroup).where(KnowledgeGroup.user_id == user_id).order_by(KnowledgeGroup.updated_at.desc()))).all()


@router.post("", response_model=KnowledgeGroupResponse, status_code=201)
async def create_group(payload: KnowledgeGroupCreate, user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    group = KnowledgeGroup(user_id=user_id, name=payload.name, description=payload.description)
    session.add(group)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(409, "A knowledge group with this name already exists") from None
    await session.refresh(group)
    return group


@router.patch("/{group_id}", response_model=KnowledgeGroupResponse)
async def update_group(group_id: uuid.UUID, payload: KnowledgeGroupUpdate, user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    group = await owned_group(group_id, user_id, session)
    group.name, group.description = payload.name, payload.description
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(409, "A knowledge group with this name already exists") from None
    await session.refresh(group)
    return group


@router.delete("/{group_id}", status_code=204)
async def delete_group(group_id: uuid.UUID, user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    group = await owned_group(group_id, user_id, session)
    await session.delete(group)
    await session.commit()
