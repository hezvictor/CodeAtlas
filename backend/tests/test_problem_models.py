import pytest


def test_problem_model_exposes_search_and_ownership_fields():
    from app.models import Problem

    problem = Problem(title="A+B", source_type="system", difficulty="入门", tags=["基础输入输出"])

    assert problem.owner_user_id is None
    assert problem.tags == ["基础输入输出"]
    assert "ix_problems_search_vector" in {index.name for index in Problem.__table__.indexes}


def test_chat_request_accepts_acm_modes_and_rejects_unknown_mode():
    from pydantic import ValidationError

    from app.schemas import ChatRequest

    assert ChatRequest(content="分析", mode="acm_analysis").mode == "acm_analysis"
    assert ChatRequest(content="解题", mode="acm_solution", solution_language="python").solution_language == "python"
    with pytest.raises(ValidationError):
        ChatRequest(content="x", mode="other")
