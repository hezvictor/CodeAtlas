from datetime import datetime
from pathlib import PurePosixPath

from sqlalchemy import func, select

from ..models import Document, DocumentVersion


def timestamp_filename(filename: str, now: datetime, sequence: int = 0) -> str:
    path = PurePosixPath(filename.replace("\\", "/"))
    suffix = f" ({sequence})" if sequence else ""
    return f"{path.stem[:170]} · {now:%Y-%m-%d %H:%M}{suffix}{path.suffix}"


async def conflict_candidates(session, user_id, group_id, filename, sha256):
    newest = select(func.max(DocumentVersion.version_no)).where(DocumentVersion.document_id == Document.id).correlate(Document).scalar_subquery()
    rows = (await session.execute(select(Document, DocumentVersion).join(DocumentVersion, DocumentVersion.document_id == Document.id).where(Document.user_id == user_id, Document.group_id == group_id, Document.scope == "long_term", Document.deleted_at.is_(None), Document.filename == filename, DocumentVersion.version_no == newest))).all()
    return [{"document_id": document.id, "title": document.title, "filename": version.original_filename, "same_content": version.sha256 == sha256} for document, version in rows]
