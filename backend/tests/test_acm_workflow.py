from types import SimpleNamespace


def _problem():
    return SimpleNamespace(
        title="A+B",
        tags=["基础输入输出"],
        statement="给定两个整数，输出它们的和。",
        input_description="输入 A 和 B。",
        output_description="输出 A+B。",
        constraints="-10^9 <= A, B <= 10^9。",
        examples=[{"input": "1 2", "output": "3"}],
    )


def test_analysis_prompt_requires_explanation_without_complete_code():
    from app.acm_workflow import build_acm_prompt

    prompt = build_acm_prompt(_problem(), "怎么做", "acm_analysis", None, "")

    assert "不得输出完整代码" in prompt
    assert "时间复杂度" in prompt
    assert "输入描述" in prompt


def test_solution_prompt_includes_selected_language_and_code_requirement():
    from app.acm_workflow import build_acm_prompt

    prompt = build_acm_prompt(_problem(), "请给出解法", "acm_solution", "cpp", "模板资料")

    assert "cpp" in prompt
    assert "完整代码" in prompt
    assert "模板资料" in prompt


def test_analysis_output_removes_fenced_complete_code():
    from app.acm_workflow import sanitize_analysis_output

    result = sanitize_analysis_output("思路如下。\n```cpp\nint main() {}\n```")

    assert "int main" not in result
    assert "分析模式不输出完整代码" in result
