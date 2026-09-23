import uuid

import pytest


def test_problem_router_registers_list_and_detail_paths():
    from app.main import app

    paths = app.openapi()["paths"]
    assert "/api/v1/problems" in paths
    assert "/api/v1/problems/{problem_id}" in paths


def test_problem_visibility_filter_allows_only_current_user_rows():
    from app.services.problems import visible_problem_filter

    user_id = uuid.uuid4()
    expression = visible_problem_filter(user_id)

    assert expression is not None
    assert "owner_user_id" in str(expression)
    assert expression.right.value == user_id
    assert " OR " not in str(expression).upper()


def test_problem_schemas_normalize_fields_and_reject_blank_content():
    from pydantic import ValidationError

    from app.schemas import ProblemCreate, ProblemUpdate

    payload = ProblemCreate(
        title="  A+B  ",
        difficulty="简单",
        tags=[" 数学 ", "数学", ""],
        statement="  add two numbers  ",
        input_description=" input ",
        output_description=" output ",
        examples=[{"input": "1 2", "output": "3"}],
        constraints=" n > 0 ",
        supported_languages=["cpp", "cpp", "python"],
    )

    assert payload.title == "A+B"
    assert payload.tags == ["数学"]
    assert payload.supported_languages == ["cpp", "python"]
    assert ProblemUpdate(title=" New title ").title == "New title"
    with pytest.raises(ValidationError):
        ProblemCreate(
            title=" ",
            difficulty="简单",
            statement="题面",
            input_description="输入",
            output_description="输出",
            constraints="约束",
        )


@pytest.mark.asyncio
async def test_clone_system_problems_creates_user_owned_default_rows():
    from app.models import Problem
    from app.services.problems import clone_system_problems

    user_id = uuid.uuid4()
    template = Problem(
        id=uuid.uuid4(),
        owner_user_id=None,
        source_type="system",
        slug="a-plus-b",
        title="A+B",
        difficulty="入门",
        tags=["数学"],
        statement="题面",
        input_description="输入",
        output_description="输出",
        examples=[{"input": "1 2", "output": "3"}],
        constraints="约束",
        supported_languages=["cpp"],
    )

    class Result:
        def all(self):
            return [template]

    class Session:
        async def scalars(self, _statement):
            return Result()

        def add(self, problem):
            self.problem = problem

    session = Session()
    rows = await clone_system_problems(session, user_id)

    assert len(rows) == 1
    assert session.problem.owner_user_id == user_id
    assert session.problem.source_type == "default"
    assert session.problem.id != template.id
    assert session.problem.slug == f"default-a-plus-b-{user_id.hex}"


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
