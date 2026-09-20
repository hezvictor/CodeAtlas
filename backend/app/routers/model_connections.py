import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db import get_session
from ..dependencies import current_user_id
from ..models import ChatModel, Document, DocumentJob, DocumentVersion, EmbeddingConfig, ModelConnection, User
from ..providers.embedding import validate_embedding_vectors
from ..providers.openai_compatible import OpenAICompatibleChatProvider
from ..schemas import (
    ChatModelCreate,
    ChatModelResponse,
    EmbeddingConfigResponse,
    EmbeddingConfigUpdate,
    ModelConnectionCreate,
    ModelConnectionResponse,
    ModelConnectionUpdate,
)
from ..security.provider_credentials import decrypt_secret, encrypt_secret
from ..providers.url_validation import validate_provider_base_url

router = APIRouter(prefix="/model-connections", tags=["models"])
utility_router = APIRouter(prefix="/model-connections", tags=["models"])


async def owned_connection(connection_id: uuid.UUID, user_id: uuid.UUID, session: AsyncSession) -> ModelConnection:
    connection = await session.scalar(
        select(ModelConnection).where(
            ModelConnection.id == connection_id,
            ModelConnection.user_id == user_id,
            ModelConnection.status != "deleted",
        )
    )
    if not connection:
        raise HTTPException(404, "Model connection not found")
    return connection


async def owned_model(model_id: uuid.UUID, user_id: uuid.UUID, session: AsyncSession) -> tuple[ChatModel, ModelConnection]:
    row = await session.execute(
        select(ChatModel, ModelConnection)
        .join(ModelConnection, ChatModel.connection_id == ModelConnection.id)
        .where(ChatModel.id == model_id, ModelConnection.user_id == user_id, ModelConnection.status != "deleted")
    )
    item = row.first()
    if not item:
        raise HTTPException(404, "Chat model not found")
    return item[0], item[1]


def connection_response(item: ModelConnection) -> ModelConnectionResponse:
    return ModelConnectionResponse.model_validate(item)


def model_response(model: ChatModel, connection: ModelConnection | None = None, is_default: bool = False) -> ChatModelResponse:
    return ChatModelResponse(
        id=model.id,
        connection_id=model.connection_id,
        connection_name=connection.name if connection else None,
        name=model.name,
        source=model.source,
        status=model.status,
        verification_error=model.verification_error,
        last_tested_at=model.last_tested_at,
        is_default=is_default,
    )


@router.get("", response_model=list[ModelConnectionResponse])
async def list_connections(user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    rows = await session.scalars(
        select(ModelConnection)
        .where(ModelConnection.user_id == user_id, ModelConnection.status != "deleted")
        .order_by(ModelConnection.updated_at.desc())
    )
    return [connection_response(item) for item in rows]


@router.post("", response_model=ModelConnectionResponse, status_code=201)
async def create_connection(payload: ModelConnectionCreate, user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    try:
        base_url = validate_provider_base_url(payload.base_url)
        secret = encrypt_secret(payload.api_key)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    connection = ModelConnection(
        user_id=user_id,
        name=payload.name,
        base_url=base_url,
        api_key_ciphertext=secret.ciphertext,
        api_key_nonce=secret.nonce,
    )
    session.add(connection)
    await session.commit()
    await session.refresh(connection)
    return connection_response(connection)


@router.patch("/{connection_id}", response_model=ModelConnectionResponse)
async def update_connection(connection_id: uuid.UUID, payload: ModelConnectionUpdate, user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    connection = await owned_connection(connection_id, user_id, session)
    changes = payload.model_dump(exclude_unset=True)
    credentials_changed = False
    if "name" in changes:
        connection.name = changes["name"]
    if "base_url" in changes:
        try:
            connection.base_url = validate_provider_base_url(changes["base_url"])
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        credentials_changed = True
    if "api_key" in changes:
        secret = encrypt_secret(changes["api_key"])
        connection.api_key_ciphertext = secret.ciphertext
        connection.api_key_nonce = secret.nonce
        credentials_changed = True
    if credentials_changed:
        connection.status = "active"
        connection.last_error = None
        await session.execute(
            update(ChatModel)
            .where(ChatModel.connection_id == connection.id)
            .values(status="unverified", verification_error="Connection credentials changed", last_tested_at=None)
        )
    await session.commit()
    await session.refresh(connection)
    return connection_response(connection)


@router.delete("/{connection_id}", status_code=204)
async def delete_connection(connection_id: uuid.UUID, user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    connection = await owned_connection(connection_id, user_id, session)
    connection.status = "deleted"
    await session.execute(
        update(ChatModel)
        .where(ChatModel.connection_id == connection.id)
        .values(status="invalid", verification_error="Connection deleted")
    )
    user = await session.get(User, user_id)
    if user and user.default_chat_model_id:
        selected = await session.scalar(select(ChatModel.id).where(ChatModel.id == user.default_chat_model_id, ChatModel.connection_id == connection.id))
        if selected:
            user.default_chat_model_id = None
    await session.commit()


@router.post("/{connection_id}/discover-models")
async def discover_models(connection_id: uuid.UUID, user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    connection = await owned_connection(connection_id, user_id, session)
    try:
        key = decrypt_secret(connection.api_key_ciphertext, connection.api_key_nonce)
        candidates = await OpenAICompatibleChatProvider(connection.base_url, key).list_models()
    except Exception as error:
        connection.last_error = str(error)
        await session.commit()
        return {"items": [], "error": "无法自动获取模型列表，可手动添加模型"}
    items = []
    for candidate in candidates:
        existing = await session.scalar(select(ChatModel).where(ChatModel.connection_id == connection.id, ChatModel.name == candidate.name))
        if not existing:
            existing = ChatModel(connection_id=connection.id, name=candidate.name, source="discovered")
            session.add(existing)
        items.append(existing)
    connection.last_error = None
    await session.commit()
    return {"items": [model_response(item, connection) for item in items], "error": None}


@router.post("/{connection_id}/models", response_model=ChatModelResponse, status_code=201)
async def add_model(connection_id: uuid.UUID, payload: ChatModelCreate, user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    connection = await owned_connection(connection_id, user_id, session)
    existing = await session.scalar(select(ChatModel).where(ChatModel.connection_id == connection.id, ChatModel.name == payload.name))
    if existing:
        return model_response(existing, connection)
    model = ChatModel(connection_id=connection.id, name=payload.name, source="manual")
    session.add(model)
    await session.commit()
    await session.refresh(model)
    return model_response(model, connection)


@router.get("/{connection_id}/models", response_model=list[ChatModelResponse])
async def list_connection_models(connection_id: uuid.UUID, user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    connection = await owned_connection(connection_id, user_id, session)
    user = await session.get(User, user_id)
    rows = await session.scalars(
        select(ChatModel)
        .where(ChatModel.connection_id == connection.id)
        .order_by(ChatModel.name)
    )
    return [model_response(model, connection, model.id == getattr(user, "default_chat_model_id", None)) for model in rows]


@router.post("/{connection_id}/models/{model_id}/test", response_model=ChatModelResponse)
async def test_model(connection_id: uuid.UUID, model_id: uuid.UUID, user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    model, connection = await owned_model(model_id, user_id, session)
    if model.connection_id != connection_id:
        raise HTTPException(404, "Chat model not found")
    try:
        key = decrypt_secret(connection.api_key_ciphertext, connection.api_key_nonce)
        result = await OpenAICompatibleChatProvider(connection.base_url, key).test_model(model.name)
    except Exception as error:
        result = type("ProviderResult", (), {"ok": False, "error": str(error)})()
    model.last_tested_at = datetime.now(UTC)
    model.status = "verified" if result.ok else "invalid"
    model.verification_error = None if result.ok else result.error or "Model test failed"
    await session.commit()
    await session.refresh(model)
    return model_response(model, connection)


@router.patch("/{connection_id}/models/{model_id}/default", response_model=ChatModelResponse)
async def set_default_model(connection_id: uuid.UUID, model_id: uuid.UUID, user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    model, connection = await owned_model(model_id, user_id, session)
    if model.connection_id != connection_id or model.status != "verified":
        raise HTTPException(409, "Only a verified model can be the default")
    user = await session.get(User, user_id)
    user.default_chat_model_id = model.id
    await session.commit()
    return model_response(model, connection, True)


@utility_router.get("/available", response_model=list[ChatModelResponse])
async def available_models(user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    user = await session.get(User, user_id)
    rows = await session.execute(
        select(ChatModel, ModelConnection)
        .join(ModelConnection, ChatModel.connection_id == ModelConnection.id)
        .where(ModelConnection.user_id == user_id, ModelConnection.status == "active", ChatModel.status == "verified")
        .order_by(ModelConnection.name, ChatModel.name)
    )
    return [model_response(model, connection, model.id == getattr(user, "default_chat_model_id", None)) for model, connection in rows.all()]


def embedding_response(config: EmbeddingConfig | None) -> EmbeddingConfigResponse:
    settings = get_settings()
    return EmbeddingConfigResponse(
        model_name=config.model_name if config else settings.embedding_model,
        status=config.status if config else "unconfigured",
        verification_error=config.verification_error if config else None,
        last_tested_at=config.last_tested_at if config else None,
        configured=config is not None,
    )


@utility_router.get("/embedding-config", response_model=EmbeddingConfigResponse)
async def get_embedding_config(user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    return embedding_response(await session.scalar(select(EmbeddingConfig).where(EmbeddingConfig.user_id == user_id)))


@utility_router.patch("/embedding-config", response_model=EmbeddingConfigResponse)
async def update_embedding_config(payload: EmbeddingConfigUpdate, user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    settings = get_settings()
    secret = encrypt_secret(payload.api_key)
    config = await session.scalar(select(EmbeddingConfig).where(EmbeddingConfig.user_id == user_id))
    if not config:
        config = EmbeddingConfig(user_id=user_id, model_name=settings.embedding_model, api_key_ciphertext=secret.ciphertext, api_key_nonce=secret.nonce)
        session.add(config)
    else:
        config.api_key_ciphertext = secret.ciphertext
        config.api_key_nonce = secret.nonce
        config.status = "unverified"
        config.verification_error = None
        config.last_tested_at = None
    await session.commit()
    await session.refresh(config)
    return embedding_response(config)


@utility_router.post("/embedding-config/test", response_model=EmbeddingConfigResponse)
async def test_embedding_config(user_id=Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    from ..providers.embedding import UserEmbeddingProvider

    config = await session.scalar(select(EmbeddingConfig).where(EmbeddingConfig.user_id == user_id))
    if not config:
        raise HTTPException(409, "Embedding API key is not configured")
    try:
        await UserEmbeddingProvider(session, user_id).embed_query("connection test")
        config.status, config.verification_error = "verified", None
    except Exception as error:
        config.status, config.verification_error = "invalid", str(error)
    config.last_tested_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(config)
    if config.status == "verified":
        pending_jobs = (
            await session.scalars(
                select(DocumentJob)
                .join(DocumentVersion, DocumentJob.document_version_id == DocumentVersion.id)
                .join(Document, DocumentVersion.document_id == Document.id)
                .where(Document.user_id == user_id, DocumentJob.status == "waiting_embedding")
            )
        ).all()
        for job in pending_jobs:
            job.status, job.stage = "queued", "parsing"
            job.available_at = datetime.now(UTC)
            job.error_message = None
            version = await session.get(DocumentVersion, job.document_version_id)
            if version:
                version.status = "uploaded"
        await session.commit()
        from ..queue import dispatch_document_job

        for job in pending_jobs:
            try:
                await dispatch_document_job(str(job.id))
            except Exception:
                # The durable dispatcher will retry queued jobs; connection validation remains successful.
                pass
    return embedding_response(config)
