from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..dependencies import current_user_id
from ..schemas import ProblemCreate, ProblemPage, ProblemResponse, ProblemUpdate
from ..services.problems import (
    create_problem,
    delete_problem,
    get_owned_problem,
    search_problems,
    update_problem,
)


router = APIRouter(prefix="/problems", tags=["problems"])


@router.get("", response_model=ProblemPage)
async def list_problems(
    query: str | None = Query(default=None, max_length=200),
    difficulty: str | None = Query(default=None, max_length=30),
    tag: str | None = Query(default=None, max_length=50),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user_id=Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
):
    return await search_problems(session, user_id, query, difficulty, tag, page, page_size)


@router.get("/{problem_id}", response_model=ProblemResponse)
async def problem_detail(
    problem_id: UUID,
    user_id=Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
):
    return await get_owned_problem(session, problem_id, user_id)


@router.post("", response_model=ProblemResponse, status_code=status.HTTP_201_CREATED)
async def create_problem_route(
    payload: ProblemCreate,
    user_id=Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
):
    problem = await create_problem(session, user_id, payload)
    await session.commit()
    await session.refresh(problem)
    return problem


@router.patch("/{problem_id}", response_model=ProblemResponse)
async def update_problem_route(
    problem_id: UUID,
    payload: ProblemUpdate,
    user_id=Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
):
    problem = await update_problem(session, problem_id, user_id, payload)
    await session.commit()
    await session.refresh(problem)
    return problem


@router.delete("/{problem_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_problem_route(
    problem_id: UUID,
    user_id=Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
):
    await delete_problem(session, problem_id, user_id)
    await session.commit()
