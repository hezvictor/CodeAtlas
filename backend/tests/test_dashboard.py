import asyncio
from datetime import UTC, datetime
from uuid import UUID


def test_dashboard_router_registers_authenticated_endpoint():
    from app.main import app

    assert "/api/v1/dashboard" in app.openapi()["paths"]


def test_beijing_today_starts_before_utc_midnight():
    from app.routers.dashboard import beijing_day_utc_bounds

    assert beijing_day_utc_bounds(datetime(2026, 10, 7, 15, 59, 59, tzinfo=UTC)) == (
        datetime(2026, 10, 6, 16, tzinfo=UTC),
        datetime(2026, 10, 7, 16, tzinfo=UTC),
    )


def test_beijing_today_rolls_over_at_1600_utc():
    from app.routers.dashboard import beijing_day_utc_bounds

    assert beijing_day_utc_bounds(datetime(2026, 10, 7, 16, tzinfo=UTC)) == (
        datetime(2026, 10, 7, 16, tzinfo=UTC),
        datetime(2026, 10, 8, 16, tzinfo=UTC),
    )


def test_dashboard_queries_current_user_with_half_open_beijing_day(monkeypatch):
    from app.routers import dashboard as module

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 7, 16, tzinfo=tz)

    class RecentRows:
        def all(self):
            return []

    class Session:
        def __init__(self):
            self.queries = []

        async def scalar(self, query):
            self.queries.append(query)
            return 3

        async def scalars(self, query):
            self.queries.append(query)
            return RecentRows()

    monkeypatch.setattr(module, "datetime", FixedDateTime)
    user_id = UUID("00000000-0000-0000-0000-000000000001")
    session = Session()
    result = asyncio.run(module.dashboard(user_id=user_id, session=session))

    count_query, recent_query = session.queries
    count_sql = str(count_query)
    assert "conversations.user_id =" in count_sql
    assert "conversations.created_at >=" in count_sql
    assert "conversations.created_at <" in count_sql
    assert set(count_query.compile().params.values()) == {
        user_id, datetime(2026, 10, 7, 16, tzinfo=UTC), datetime(2026, 10, 8, 16, tzinfo=UTC),
    }
    assert "conversations.user_id =" in str(recent_query)
    assert "ORDER BY conversations.updated_at DESC" in str(recent_query)
    assert result.today_conversation_count == 3
