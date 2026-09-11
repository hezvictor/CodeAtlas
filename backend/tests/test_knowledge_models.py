import uuid


def test_knowledge_models_define_user_scoped_documents_and_chunks():
    from app.models import Document, DocumentChunk, DocumentVersion, KnowledgeGroup

    group = KnowledgeGroup(user_id=uuid.uuid4(), name="算法模板")
    document = Document(user_id=group.user_id, group_id=group.id, title="最短路")
    version = DocumentVersion(document_id=document.id, version_no=1, status="uploaded")
    chunk = DocumentChunk(document_version_id=version.id, ordinal=0, content="Bellman-Ford")

    assert group.__tablename__ == "knowledge_groups"
    assert document.group_id == group.id
    assert version.document_id == document.id
    assert chunk.document_version_id == version.id


def test_knowledge_tables_expose_ownership_and_search_indexes():
    from app.models import Document, DocumentChunk, KnowledgeGroup

    group_indexes = {index.name for index in KnowledgeGroup.__table__.indexes}
    document_indexes = {index.name for index in Document.__table__.indexes}
    chunk_indexes = {index.name for index in DocumentChunk.__table__.indexes}

    assert "ix_knowledge_groups_user_id" in group_indexes
    assert "ix_documents_user_group_updated" in document_indexes
    assert "ix_document_chunks_version_ordinal" in chunk_indexes
