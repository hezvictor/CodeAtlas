from pathlib import Path

EVALUATION_FILE = Path(__file__).parents[2] / "docs" / "rag-evaluation" / "hzvictory-template-v1.md"


def test_internal_rag_evaluation_set_contains_twenty_valid_cases():
    from app.evaluation import load_evaluation_cases, validate_evaluation_set

    cases = load_evaluation_cases(EVALUATION_FILE)
    errors = validate_evaluation_set(cases)

    assert not errors, errors
    assert [case.case_id for case in cases] == [f"R{index:02d}" for index in range(1, 21)]


def test_evaluation_contract_covers_disabled_pending_and_acm_constraints():
    from app.evaluation import load_evaluation_cases

    cases = {case.case_id: case for case in load_evaluation_cases(EVALUATION_FILE)}

    assert cases["R19"].knowledge_scope == "none"
    assert cases["R19"].citation_required is False
    assert cases["R20"].fixture == "source document exists but is not indexed yet"
    assert cases["R14"].mode == "acm_solution"
    assert cases["R14"].solution_language == "cpp"
    assert cases["R02"].mode == "acm_analysis"
    assert "complete submit-ready program" in cases["R02"].forbidden


def test_evaluation_result_checks_expected_sections_and_disabled_scope():
    from app.evaluation import evaluate_retrieval_case, load_evaluation_cases

    cases = {case.case_id: case for case in load_evaluation_cases(EVALUATION_FILE)}
    first_source = cases["R08"].expected_sources[1].split(" (approximately", 1)[0]
    second_source = cases["R08"].expected_sources[2].split(" (approximately", 1)[0]
    evidence = [
        {"locator": {"section_path": first_source}, "content": "Kruskal DSU"},
        {"locator": {"section_path": second_source}, "content": "find union"},
    ]

    result = evaluate_retrieval_case(cases["R08"], evidence)
    assert result.top_k_hit is True
    assert result.matched_sources
    assert evaluate_retrieval_case(cases["R19"], evidence).top_k_hit is False


def test_lexical_retrieval_ranks_matching_section_above_unrelated_text():
    from app.evaluation import lexical_retrieve

    chunks = [
        {"locator": {"section_path": "Kruskal 模板"}, "content": "排序边并使用 DSU 合并连通分量"},
        {"locator": {"section_path": "字符串算法"}, "content": "KMP 前缀函数"},
    ]

    result = lexical_retrieve("Kruskal DSU 合并", chunks)

    assert result[0]["locator"]["section_path"] == "Kruskal 模板"
