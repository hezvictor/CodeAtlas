import uuid


def test_knowledge_schemas_normalize_group_and_expose_document_status():
    from app.schemas import DocumentVersionResponse, KnowledgeGroupCreate

    group = KnowledgeGroupCreate(name="  算法模板  ", description=" notes ")
    assert group.name == "算法模板"
    assert group.description == "notes"
    version = DocumentVersionResponse(
        id=uuid.uuid4(), document_id=uuid.uuid4(), version_no=1,
        original_filename="notes.html", mime_type="text/html", extension=".html",
        size_bytes=10, sha256="a" * 64, status="uploaded", error_code=None,
        error_message=None, created_at="2026-01-01T00:00:00Z", indexed_at=None,
    )
    assert version.status == "uploaded"
