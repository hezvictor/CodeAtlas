import uuid

import pytest


def test_model_configuration_models_expose_user_scoped_fields():
    from app.models import ChatModel, EmbeddingConfig, ModelConnection

    assert "user_id" in ModelConnection.__table__.c
    assert "api_key_ciphertext" in ModelConnection.__table__.c
    assert "status" in ChatModel.__table__.c
    assert "verification_error" in ChatModel.__table__.c
    assert "user_id" in EmbeddingConfig.__table__.c
    assert "api_key_ciphertext" in EmbeddingConfig.__table__.c


def test_conversations_and_messages_can_snapshot_selected_model():
    from app.models import Conversation, Message

    assert "selected_chat_model_id" in Conversation.__table__.c
    assert "chat_model_id" in Message.__table__.c
    assert "model_name_snapshot" in Message.__table__.c


def test_document_scope_defaults_to_long_term_and_group_is_optional():
    from app.models import Document

    assert Document.__table__.c.group_id.nullable is True
    assert Document.__table__.c.scope.default.arg == "long_term"


def test_model_configuration_exposes_a_connection_scoped_model_list_route():
    from app.routers.model_connections import router

    routes = {(route.path, tuple(sorted(route.methods or []))) for route in router.routes}

    assert ("/model-connections/{connection_id}/models", ("GET",)) in routes


@pytest.mark.asyncio
async def test_available_models_query_requires_chat_verification_only():
    from sqlalchemy.dialects import postgresql

    from app.routers.model_connections import available_models

    statements = []
    class Session:
        async def get(self, *_args): return None
        async def execute(self, statement):
            statements.append(statement)
            return type("Rows", (), {"all": lambda self: []})()

    assert await available_models(user_id=uuid.uuid4(), session=Session()) == []
    sql = str(statements[0].whereclause.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    assert "chat_models.status = 'verified'" in sql
    assert "'chat'" in sql
    assert "'tool_calling'" not in sql
    assert "'tool_result'" not in sql


@pytest.mark.asyncio
async def test_chat_model_resolution_never_falls_back_to_environment_credentials(monkeypatch):
    from fastapi import HTTPException

    from app.routers import conversations as conversations_module

    class Session:
        async def get(self, _model, _id):
            return type("User", (), {"default_chat_model_id": None})()

    monkeypatch.setattr(
        conversations_module,
        "get_settings",
        lambda: type("Settings", (), {"chat_model": "env-model", "dashscope_api_key": "env-key"})(),
    )

    with pytest.raises(HTTPException, match="configure and verify") as error:
        await conversations_module.resolve_chat_model(
            Session(),
            type("Conversation", (), {"selected_chat_model_id": None})(),
            uuid.uuid4(),
            None,
        )

    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_embedding_requires_user_configuration_without_project_default():
    """没有用户 Embedding 配置时必须直接失败，不再回退到环境变量凭证。"""
    from app.providers.embedding import UserEmbeddingProvider

    class Session:
        async def scalar(self, _statement): return None

    with pytest.raises(RuntimeError, match="not configured"):
        await UserEmbeddingProvider(Session(), uuid.uuid4()).embed_query("query")
