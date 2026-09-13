from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, or_, and_

from ..config import get_settings
from ..db import session_factory
from ..models import RefreshToken


async def cleanup_refresh_tokens(_ctx=None) -> int:
    """Remove refresh-token rows that have been unusable for the retention window."""
    settings = get_settings()
    cutoff = datetime.now(UTC) - timedelta(days=settings.refresh_token_retention_days)
    statement = delete(RefreshToken).where(
        or_(
            RefreshToken.expires_at < cutoff,
            and_(RefreshToken.revoked_at.is_not(None), RefreshToken.revoked_at < cutoff),
        )
    )
    async with session_factory() as session:
        result = await session.execute(statement)
        await session.commit()
        return int(result.rowcount or 0)
