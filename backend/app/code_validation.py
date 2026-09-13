import ast
import re

_CODE_BLOCK = re.compile(r"```(?:cpp|c\+\+|java|python|py)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_solution_code(text: str) -> str:
    match = _CODE_BLOCK.search(text)
    return match.group(1).strip() if match else ""


def _balanced(code: str) -> bool:
    pairs = {"}": "{", "]": "[", ")": "("}
    stack: list[str] = []
    for char in code:
        if char in "{[(":
            stack.append(char)
        elif char in pairs:
            if not stack or stack.pop() != pairs[char]:
                return False
    return not stack


def validate_solution_code(language: str, code: str) -> dict[str, str]:
    if not code.strip():
        return {"status": "invalid", "language": language, "message": "代码为空"}
    if language == "python":
        try:
            ast.parse(code)
        except SyntaxError as error:
            return {"status": "invalid", "language": language, "message": f"Python 语法错误：{error.msg}"}
    elif language in {"cpp", "java"}:
        has_main = bool(re.search(r"\bmain\s*\(", code))
        if not has_main or not _balanced(code):
            return {"status": "invalid", "language": language, "message": "缺少 main 函数或括号不匹配"}
    else:
        return {"status": "invalid", "language": language, "message": "不支持的语言"}
    return {"status": "valid", "language": language, "message": "已完成基础静态检查，未进行在线评测"}
