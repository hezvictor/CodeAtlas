import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .config import get_settings


class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    nickname: Mapped[str] = mapped_column(String(80))
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    auth_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
    default_chat_model_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __init__(self, **kwargs):
        kwargs.setdefault("auth_version", 1)
        super().__init__(**kwargs)

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), default="新对话")
    mode: Mapped[str] = mapped_column(String(30), default="normal")
    knowledge_scope: Mapped[str] = mapped_column(String(10), default="none", server_default=text("'none'"))
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    selected_chat_model_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String(20), default="completed")
    retrieved_chunk_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list, server_default=text("'[]'"))
    model: Mapped[str | None] = mapped_column(String(100))
    chat_model_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    model_name_snapshot: Mapped[str | None] = mapped_column(String(200))
    duration_ms: Mapped[int | None] = mapped_column()
    first_token_latency_ms: Mapped[int | None] = mapped_column()
    problem_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("problems.id", ondelete="SET NULL"), index=True)
    mode: Mapped[str] = mapped_column(String(30), default="normal")
    knowledge_scope: Mapped[str] = mapped_column(String(10), default="none", server_default=text("'none'"))
    solution_language: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Problem(Base):
    __tablename__ = "problems"
    __table_args__ = (
        Index("ix_problems_owner_id", "owner_user_id"),
        Index("ix_problems_source_difficulty", "source_type", "difficulty"),
        Index("ix_problems_search_vector", "search_vector", postgresql_using="gin"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, default="system")
    slug: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(30), nullable=False)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    input_description: Mapped[str] = mapped_column(Text, nullable=False)
    output_description: Mapped[str] = mapped_column(Text, nullable=False)
    examples: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    constraints: Mapped[str] = mapped_column(Text, nullable=False)
    supported_languages: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class KnowledgeGroup(Base):
    __tablename__ = "knowledge_groups"
    __table_args__ = (Index("ix_knowledge_groups_user_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_user_group_updated", "user_id", "group_id", "updated_at"),
        Index("ix_documents_user_scope_updated", "user_id", "scope", "updated_at"),
        Index("ix_documents_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    group_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("knowledge_groups.id", ondelete="SET NULL"), nullable=True)
    scope: Mapped[str] = mapped_column(String(20), nullable=False, default="long_term", server_default="long_term")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cleanup_status: Mapped[str | None] = mapped_column(String(20))
    cleanup_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        Index("ix_document_versions_document_id", "document_id"),
        Index("ix_document_versions_document_sha256", "document_id", "sha256"),
        Index("ix_document_versions_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False, default="application/octet-stream")
    extension: Mapped[str] = mapped_column(String(20), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    object_key: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="uploaded")
    error_code: Mapped[str | None] = mapped_column(String(80))
    error_message: Mapped[str | None] = mapped_column(Text)
    extracted_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    active_index_job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    upload_token: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), unique=True)
    cleanup_pending: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    content_deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    storage_deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    storage_delete_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    storage_delete_error: Mapped[str | None] = mapped_column(Text)

    def __init__(self, **kwargs):
        kwargs.setdefault("storage_delete_attempts", 0)
        super().__init__(**kwargs)


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        Index("ix_document_chunks_version_ordinal", "document_version_id", "index_job_id", "ordinal", unique=True),
        Index("ix_document_chunks_version_id", "document_version_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False)
    index_job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    page_start: Mapped[int | None] = mapped_column(Integer)
    page_end: Mapped[int | None] = mapped_column(Integer)
    line_start: Mapped[int | None] = mapped_column(Integer)
    line_end: Mapped[int | None] = mapped_column(Integer)
    section_path: Mapped[str | None] = mapped_column(Text)
    char_start: Mapped[int | None] = mapped_column(Integer)
    char_end: Mapped[int | None] = mapped_column(Integer)
    locator: Mapped[dict] = mapped_column(JSON, default=dict)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(get_settings().embedding_dimensions))
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR)


class Attachment(Base):
    __tablename__ = "attachments"
    __table_args__ = (Index("ix_attachments_conversation_id", "conversation_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    document_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Citation(Base):
    __tablename__ = "citations"
    __table_args__ = (Index("ix_citations_message_id", "message_id"), Index("uq_citations_message_chunk", "message_id", "chunk_id", unique=True))

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True)
    chunk_id_snapshot: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    document_id_snapshot: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    group_name_snapshot: Mapped[str | None] = mapped_column(String(100))
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    rank: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locator: Mapped[dict] = mapped_column(JSON, default=dict)
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    validation_error: Mapped[str | None] = mapped_column(String(120))
    source_scope: Mapped[str] = mapped_column(String(20), nullable=False, default="long_term", server_default="long_term")
    document_title_snapshot: Mapped[str | None] = mapped_column(String(200))
    original_filename_snapshot: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DocumentJob(Base):
    __tablename__ = "document_jobs"
    __table_args__ = (
        Index("ix_document_jobs_status_available", "status", "available_at"),
        Index(
            "uq_document_jobs_active_version",
            "document_version_id",
            unique=True,
            postgresql_where=text("status IN ('queued', 'running')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False)
    stage: Mapped[str] = mapped_column(String(20), nullable=False, default="parsing")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_chunks: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    completed_chunks: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    error_code: Mapped[str | None] = mapped_column(String(80))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    dispatch_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_dispatch_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_dispatch_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ModelConnection(Base):
    __tablename__ = "model_connections"
    __table_args__ = (Index("ix_model_connections_user_updated", "user_id", "updated_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    api_key_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    api_key_nonce: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", server_default="active")
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ChatModel(Base):
    __tablename__ = "chat_models"
    __table_args__ = (Index("ix_chat_models_connection_status", "connection_id", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("model_connections.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="unverified", server_default="unverified")
    verification_error: Mapped[str | None] = mapped_column(Text)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class EmbeddingConfig(Base):
    __tablename__ = "embedding_configs"
    __table_args__ = (Index("ix_embedding_configs_user_id", "user_id", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    api_key_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    api_key_nonce: Mapped[str] = mapped_column(String(100), nullable=False)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="unverified", server_default="unverified")
    verification_error: Mapped[str | None] = mapped_column(Text)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class RerankerConfig(Base):
    __tablename__ = "reranker_configs"
    __table_args__ = (Index("ix_reranker_configs_user_id", "user_id", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    api_key_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    api_key_nonce: Mapped[str] = mapped_column(String(100), nullable=False)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="unverified", server_default="unverified")
    verification_error: Mapped[str | None] = mapped_column(Text)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
