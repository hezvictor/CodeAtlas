import uuid

import pytest


def test_problem_router_registers_list_and_detail_paths():
    from app.main import app

    paths = app.openapi()["paths"]
    assert "/api/v1/problems" in paths
    assert "/api/v1/problems/{problem_id}" in paths


def test_problem_visibility_filter_allows_system_or_owner_rows():
    from app.services.problems import visible_problem_filter

    user_id = uuid.uuid4()
    expression = visible_problem_filter(user_id)

    assert expression is not None
    assert "owner_user_id" in str(expression)


@pytest.mark.asyncio
async def test_problem_detail_uses_user_scoped_lookup(monkeypatch):
    from app.services import problems

    expected = object()

    async def fake_lookup(_session, problem_id, user_id):
        assert problem_id == uuid.UUID("11111111-1111-4111-8111-111111111111")
        assert user_id == uuid.UUID("22222222-2222-4222-8222-222222222222")
        return expected

    monkeypatch.setattr(problems, "get_owned_problem", fake_lookup)
    result = await problems.get_owned_problem(None, uuid.UUID("11111111-1111-4111-8111-111111111111"), uuid.UUID("22222222-2222-4222-8222-222222222222"))

    assert result is expected
