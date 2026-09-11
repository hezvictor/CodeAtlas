from bs4 import BeautifulSoup

from .base import ParsedBlock, ParsedDocument


def parse_html(data: bytes) -> ParsedDocument:
    soup = BeautifulSoup(data, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer"]):
        tag.decompose()
    blocks: list[ParsedBlock] = []
    section = None
    for element in soup.find_all(["h1", "h2", "h3", "p", "li", "pre"]):
        value = " ".join(element.get_text(" ", strip=True).split())
        if not value:
            continue
        if element.name in {"h1", "h2", "h3"}:
            section = value
        elif element.name in {"p", "li", "pre"}:
            blocks.append(ParsedBlock(value, section_path=section))
    text = "\n\n".join((b.section_path + "\n" if b.section_path else "") + b.text for b in blocks)
    return ParsedDocument(text=text, blocks=blocks)
