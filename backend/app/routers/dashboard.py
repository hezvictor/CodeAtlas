from datetime import UTC, datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..dependencies import current_user_id
from ..models import Conversation
from ..schemas import DashboardResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def beijing_day_utc_bounds(now_utc: datetime) -> tuple[datetime, datetime]:
    local = now_utc.astimezone(timezone(timedelta(hours=8)))
    start_local = local.replace(hour=0, minute=0, second=0, microsecond=0)
    return start_local.astimezone(UTC), (start_local + timedelta(days=1)).astimezone(UTC)


@router.get("", response_model=DashboardResponse)
async def dashboard(user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    day_start, day_end = beijing_day_utc_bounds(datetime.now(UTC))
    base_filter = Conversation.user_id == user_id
    today_count = int(
        await session.scalar(
            select(func.count()).select_from(Conversation).where(
                base_filter, Conversation.created_at >= day_start, Conversation.created_at < day_end
            )
        )
        or 0
    )
    recent = list(
        (
            await session.scalars(
                select(Conversation).where(base_filter).order_by(Conversation.updated_at.desc()).limit(5)
            )
        ).all()
    )
    return DashboardResponse(
        today_conversation_count=today_count,
        recent_conversations=recent,
        latest_conversation=recent[0] if recent else None,
    )
