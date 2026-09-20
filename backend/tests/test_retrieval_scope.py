import uuid

import pytest


@pytest.mark.asyncio
async def test_empty_scope_skips_database_and_embedding():
    from app.services.retrieval_service import retrieve_chunks

    class ExplodingSession:
        async def execute(self, _statement):
            raise AssertionError("database must not be queried")

    class ExplodingProvider:
        async def embed_query(self, _query):
            raise AssertionError("embedding must not be called")

    assert (
        await retrieve_chunks(
            ExplodingSession(), uuid.uuid4(), uuid.uuid4(), "query", knowledge_scope="none", embedding_provider=ExplodingProvider()
        )
        == []
    )


def test_attachment_query_contains_conversation_filter():
    from app.services.retrieval_service import build_attachment_statement

    statement = build_attachment_statement(uuid.uuid4(), uuid.uuid4(), [uuid.uuid4()])
    assert "conversation_id" in str(statement)
