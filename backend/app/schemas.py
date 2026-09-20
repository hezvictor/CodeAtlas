import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator, model_validator

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    nickname: str = Field(min_length=1, max_length=80)

    @field_validator("nickname")
    @classmethod
    def normalize_nickname(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("nickname must not be blank")
        return value

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class LogoutRequest(BaseModel):
    refresh_token: str

class UserUpdate(BaseModel):
    nickname: str | None = Field(default=None, min_length=1, max_length=80)
    email: EmailStr | None = None

    @field_validator("nickname")
    @classmethod
    def normalize_nickname(cls, value: str) -> str:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("nickname must not be blank")
        return value

class PasswordUpdate(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: EmailStr
    nickname: str
    avatar_url: str | None
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse

class ConversationCreate(BaseModel):
    title: str = Field(default="新对话", min_length=1, max_length=200)
    mode: str = Field(default="normal", pattern="^normal$")
class ConversationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    pinned: bool | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value):
        return value.strip() if value is not None else value

    @model_validator(mode="after")
    def has_changes(self):
        if self.title is None and self.pinned is None:
            raise ValueError("at least one field is required")
        return self

class BulkConversationRequest(BaseModel):
    conversation_ids: list[uuid.UUID] = Field(min_length=1, max_length=100)
    action: Literal["pin", "unpin", "delete"]

class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID; user_id: uuid.UUID; title: str; mode: str; pinned: bool; selected_chat_model_id: uuid.UUID | None = None; created_at: datetime; updated_at: datetime


class DashboardResponse(BaseModel):
    today_conversation_count: int
    recent_conversations: list[ConversationResponse]
    latest_conversation: ConversationResponse | None


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID; conversation_id: uuid.UUID; role: str; content: str; status: str; model: str | None; chat_model_id: uuid.UUID | None = None; model_name_snapshot: str | None = None; retrieved_chunk_ids: list[uuid.UUID]
    duration_ms: int | None; first_token_latency_ms: int | None; problem_id: uuid.UUID | None
    mode: str; solution_language: str | None; created_at: datetime
class MessagePage(BaseModel):
    items: list[MessageResponse]
    has_more: bool
    next_before: datetime | None
class ChatRequest(BaseModel):
    content: str = Field(min_length=1, max_length=20000)
    mode: str = Field(default="normal", pattern="^(normal|acm_analysis|acm_solution)$")
    solution_language: str | None = Field(default=None, pattern="^(cpp|java|python)$")
    chat_model_id: uuid.UUID | None = None
    attachment_ids: list[uuid.UUID] = Field(default_factory=list, max_length=20)
    knowledge_group_ids: list[uuid.UUID] = Field(default_factory=list, max_length=20)
    knowledge_scope: Literal["none", "all", "groups"] = "all"
    reuse_last_user: bool = False
    problem_id: uuid.UUID | None = None

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("content must not be blank")
        return value

    @model_validator(mode="after")
    def normalize_knowledge_scope(self):
        # Older clients only supplied group IDs. Keep that request shape working.
        if self.knowledge_scope == "none" and self.knowledge_group_ids:
            self.knowledge_scope = "groups"
        if self.knowledge_scope == "groups" and not self.knowledge_group_ids:
            raise ValueError("knowledge_group_ids is required when knowledge_scope is groups")
        return self


class ProblemSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    slug: str
    title: str
    difficulty: str
    tags: list[str]
    supported_languages: list[str]


class ProblemResponse(ProblemSummary):
    owner_user_id: uuid.UUID | None
    source_type: str
    statement: str
    input_description: str
    output_description: str
    examples: list[dict]
    constraints: str
    created_at: datetime
    updated_at: datetime


class ProblemPage(BaseModel):
    items: list[ProblemSummary]
    page: int
    page_size: int
    total: int
class RetryRequest(BaseModel):
    content: str | None = Field(default=None, min_length=1, max_length=20000)

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value):
        return value.strip() if value is not None else value


class KnowledgeGroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("name", "description")
    @classmethod
    def normalize_text(cls, value):
        return value.strip() if value is not None else value


class KnowledgeGroupUpdate(KnowledgeGroupCreate):
    pass


class KnowledgeGroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class DocumentVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    document_id: uuid.UUID
    version_no: int
    original_filename: str
    mime_type: str
    extension: str
    size_bytes: int
    sha256: str
    status: str
    error_code: str | None
    error_message: str | None
    created_at: datetime
    indexed_at: datetime | None


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    user_id: uuid.UUID
    group_id: uuid.UUID | None
    scope: str = "long_term"
    title: str
    created_at: datetime
    updated_at: datetime
    latest_version: DocumentVersionResponse | None = None


class DocumentPreviewResponse(BaseModel):
    document: DocumentResponse
    version: DocumentVersionResponse
    text: str


class CitationSourceResponse(BaseModel):
    id: uuid.UUID
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    original_filename: str
    group_id: uuid.UUID | None
    group_name: str | None
    source_scope: str
    quote: str
    score: float
    rank: int
    locator: dict
    citation_marker: str


class DocumentUploadPolicyResponse(BaseModel):
    extensions: list[str]
    max_size_bytes: int
    format_description: str


class AttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    conversation_id: uuid.UUID
    document_version_id: uuid.UUID
    document_id: uuid.UUID | None = None
    title: str | None = None
    original_filename: str | None = None
    extension: str | None = None
    status: str | None = None
    scope: str | None = None
    created_at: datetime


class ModelConnectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    base_url: str = Field(min_length=1, max_length=500)
    api_key: str = Field(min_length=1, max_length=500)

    @field_validator("name", "base_url", "api_key")
    @classmethod
    def normalize_connection_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value


class ModelConnectionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    base_url: str | None = Field(default=None, min_length=1, max_length=500)
    api_key: str | None = Field(default=None, min_length=1, max_length=500)

    @field_validator("name", "base_url", "api_key")
    @classmethod
    def normalize_optional_connection_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value


class ChatModelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)

    @field_validator("name")
    @classmethod
    def normalize_model_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("model name must not be blank")
        return value


class ModelConnectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    base_url: str
    status: str
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class ChatModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    connection_id: uuid.UUID
    connection_name: str | None = None
    name: str
    source: str
    status: str
    verification_error: str | None
    last_tested_at: datetime | None
    is_default: bool = False


class EmbeddingConfigUpdate(BaseModel):
    api_key: str = Field(min_length=1, max_length=500)

    @field_validator("api_key")
    @classmethod
    def normalize_embedding_key(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("api_key must not be blank")
        return value


class EmbeddingConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    model_name: str
    status: str
    verification_error: str | None
    last_tested_at: datetime | None
    configured: bool
