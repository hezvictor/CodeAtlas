import re
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from .models import Citation
from .retrieval import RankedChunk


_CITATION = re.compile(r"\[cite:([^\]]+)\]")


def validate_citations(text: str, allowed_ids: set[str]) -> tuple[str, list[str]]:
    valid: list[str] = []

    def replace(match: re.Match[str]) -> str:
        identifier = match.group(1)
        if identifier in allowed_ids:
            valid.append(identifier)
            return match.group(0)
        return ""

    return _CITATION.sub(replace, text), valid


async def persist_citations(session: AsyncSession, message_id: UUID, text: str, retrieved: list[RankedChunk]) -> tuple[str, list[Citation]]:
    cleaned, valid_ids = validate_citations(text, {str(item.chunk_id) for item in retrieved})
    by_id = {str(item.chunk_id): item for item in retrieved}
    records = []
    for rank, identifier in enumerate(dict.fromkeys(valid_ids), 1):
        item = by_id[identifier]
        records.append(Citation(message_id=message_id, chunk_id=item.chunk_id, quote=item.content[:500], score=item.score, rank=rank, locator=item.locator or {}, is_valid=True))
    session.add_all(records)
    return cleaned, records
