from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Problem
from ..schemas import ProblemPage


def visible_problem_filter(user_id: UUID):
    return or_(Problem.owner_user_id.is_(None), Problem.owner_user_id == user_id)


async def get_owned_problem(session: AsyncSession, problem_id: UUID, user_id: UUID) -> Problem:
    problem = await session.scalar(
        select(Problem).where(Problem.id == problem_id, visible_problem_filter(user_id))
    )
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    return problem


async def search_problems(
    session: AsyncSession,
    user_id: UUID,
    query: str | None = None,
    difficulty: str | None = None,
    tag: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> ProblemPage:
    page = max(page, 1)
    page_size = max(1, min(page_size, 100))
    filters = [visible_problem_filter(user_id)]
    if query and query.strip():
        pattern = f"%{query.strip()}%"
        filters.append(
            or_(
                Problem.title.ilike(pattern),
                Problem.slug.ilike(pattern),
                Problem.statement.ilike(pattern),
            )
        )
    if difficulty:
        filters.append(Problem.difficulty == difficulty)
    if tag:
        filters.append(Problem.tags.contains([tag]))

    total = int(await session.scalar(select(func.count()).select_from(Problem).where(*filters)) or 0)
    rows = (
        await session.scalars(
            select(Problem)
            .where(*filters)
            .order_by(Problem.updated_at.desc(), Problem.title.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return ProblemPage(items=list(rows), page=page, page_size=page_size, total=total)
