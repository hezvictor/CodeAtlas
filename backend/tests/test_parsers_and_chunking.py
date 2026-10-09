import pytest

from app.chunking import chunk_document
from app.parsers import parse_document


@pytest.mark.parametrize("filename,mime", [
    ("notes.pdf", "application/pdf"),
    ("notes.pdf", "text/plain"),
    ("notes.exe", "text/plain"),
])
def test_parser_rejects_unsupported_formats_before_reading_content(filename, mime):
    with pytest.raises(ValueError, match="Unsupported document type"):
        parse_document(filename, mime, b"This content could be mistaken for plain text")


def test_parser_rejects_unsupported_mime_for_a_supported_extension():
    with pytest.raises(ValueError, match="MIME type does not match"):
        parse_document("notes.txt", "application/pdf", b"Plain text")


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


def test_markdown_parser_preserves_heading_paths_and_fenced_code_blocks():
    parsed = parse_document(
        "notes.md",
        "text/markdown",
        b"# Graph\nintro\n## Dijkstra\nuse a heap\n```cpp\nint main() {}\n```\n## MST\nuse DSU\n",
    )

    assert [block.section_path for block in parsed.blocks] == ["Graph", "Graph / Dijkstra", "Graph / MST"]
    assert "```cpp\nint main() {}\n```" in parsed.blocks[1].text
    assert parsed.blocks[1].line_start == 3
    assert parsed.blocks[1].line_end == 7


def test_markdown_chunker_keeps_fenced_code_together_when_section_is_split():
    parsed = parse_document(
        "notes.md",
        "text/markdown",
        b"# Template\nintro paragraph\n\n```cpp\nint solve() { return 42; }\n```\n\nclosing explanation\n",
    )

    chunks = chunk_document(parsed, max_chars=60, overlap_chars=10)

    assert len(chunks) >= 2
    code_chunks = [chunk.content for chunk in chunks if "int solve()" in chunk.content]
    assert code_chunks == ["```cpp\nint solve() { return 42; }\n```"]


def test_chunker_assigns_stable_parent_id_to_chunks_from_one_section():
    parsed = parse_document(
        "notes.md",
        "text/markdown",
        b"# DSU\nA long explanation with enough words to split.\n\nMore explanation here.",
    )

    chunks = chunk_document(parsed, max_chars=45, overlap_chars=5)

    assert len(chunks) > 1
    parent_ids = {chunk.locator["parent_id"] for chunk in chunks}
    assert len(parent_ids) == 1
    assert all(chunk.locator["parent_id"] for chunk in chunks)
