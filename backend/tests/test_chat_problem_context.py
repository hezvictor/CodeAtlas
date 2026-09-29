import uuid
from types import SimpleNamespace

import pytest


def test_analysis_can_use_user_described_problem_without_problem_id():
    from app.services.problem_context import validate_chat_context

    assert validate_chat_context("acm_analysis", None, None) == (None, None)


def test_solution_requires_supported_language():
    from app.services.problem_context import validate_chat_context

    with pytest.raises(ValueError, match="language"):
        validate_chat_context("acm_solution", uuid.uuid4(), None)


def test_normal_mode_can_run_without_problem_or_language():
    from app.services.problem_context import validate_chat_context

    assert validate_chat_context("normal", None, None) == (None, None)


def test_message_context_metadata_preserves_retry_context():
    from app.services.problem_context import message_context_metadata

    problem_id = uuid.uuid4()
    message = SimpleNamespace(
        problem_id=problem_id,
        mode="acm_solution",
        solution_language="python",
    )

    assert message_context_metadata(message) == {
        "problem_id": problem_id,
        "mode": "acm_solution",
        "solution_language": "python",
    }
