from app.code_validation import validate_solution_code


def test_python_solution_is_parsed_and_reported_valid():
    result = validate_solution_code("python", "import sys\nprint(1)\n")

    assert result["status"] == "valid"
    assert result["language"] == "python"


def test_python_solution_with_invalid_syntax_is_reported_invalid():
    result = validate_solution_code("python", "def broken(:\n")

    assert result["status"] == "invalid"
    assert "语法" in result["message"]


def test_cpp_and_java_require_main_and_balanced_delimiters():
    assert validate_solution_code("cpp", "int main() { return 0; }")["status"] == "valid"
    assert validate_solution_code("java", "class Main { public static void main(String[] a) {} }")["status"] == "valid"
    assert validate_solution_code("cpp", "int main() {")["status"] == "invalid"
