from app.parsers import parse_document
from app.chunking import chunk_document


def test_html_parser_removes_scripts_and_preserves_headings():
    parsed = parse_document("notes.html", "text/html", b"<h1>Graph</h1><script>alert(1)</script><p>Shortest path</p>")

    assert "Shortest path" in parsed.text
    assert "alert" not in parsed.text
    assert parsed.blocks[0].section_path == "Graph"


def test_python_parser_keeps_function_line_locations():
    parsed = parse_document("main.py", "text/x-python", b"def solve():\n    return 42\n")

    assert parsed.language == "python"
    assert parsed.blocks[0].line_start == 1
    assert parsed.blocks[0].line_end == 2


def test_chunker_preserves_source_locator_and_order():
    parsed = parse_document("main.py", "text/x-python", b"def solve():\n    return 42\n")
    chunks = chunk_document(parsed, max_chars=200)

    assert len(chunks) == 1
    assert chunks[0].ordinal == 0
    assert chunks[0].line_start == 1
    assert chunks[0].line_end == 2
