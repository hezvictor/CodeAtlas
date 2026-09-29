from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from ..models import Problem

ACM_MODES = {"acm_analysis", "acm_solution"}
SOLUTION_LANGUAGES = {"cpp", "java", "python"}


def message_context_metadata(message) -> dict:
    return {
        "problem_id": message.problem_id,
        "mode": message.mode or "normal",
        "solution_language": message.solution_language,
    }


def validate_chat_context(
    mode: str, problem_id: UUID | None, solution_language: str | None
) -> tuple[UUID | None, str | None]:
    if mode == "acm_analysis" and solution_language is not None:
        raise ValueError("ACM analysis mode does not accept a language")
    if mode == "acm_solution" and solution_language not in SOLUTION_LANGUAGES:
        raise ValueError("ACM solution mode requires a supported language")
    if mode == "normal" and solution_language is not None:
        raise ValueError("Normal mode does not accept a solution language")
    return problem_id, solution_language


async def resolve_problem_context(
    session: AsyncSession, problem_id: UUID | None, user_id: UUID
) -> "Problem | None":
    if problem_id is None:
        return None
    from .problems import get_owned_problem

    return await get_owned_problem(session, problem_id, user_id)


def format_problem_context(problem: "Problem | None") -> str:
    if problem is None:
        return ""
    examples = "\n".join(
        f"示例输入：{example.get('input', '')}\n示例输出：{example.get('output', '')}"
        for example in problem.examples
    )
    return (
        f"题库题目：{problem.title}\n"
        f"题目标签：{'、'.join(problem.tags)}\n"
        f"题目描述：{problem.statement}\n"
        f"输入描述：{problem.input_description}\n"
        f"输出描述：{problem.output_description}\n"
        f"约束条件：{problem.constraints}\n"
        f"样例：\n{examples}"
    )
