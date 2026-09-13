from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..dependencies import current_user_id
from ..schemas import ProblemPage, ProblemResponse
from ..services.problems import get_owned_problem, search_problems


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
