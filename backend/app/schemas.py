import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    nickname: str = Field(min_length=1, max_length=80)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class LogoutRequest(BaseModel):
    refresh_token: str

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
    title: str = Field(min_length=1, max_length=200)
class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID; user_id: uuid.UUID; title: str; mode: str; created_at: datetime; updated_at: datetime
class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID; conversation_id: uuid.UUID; role: str; content: str; status: str; model: str | None; created_at: datetime
class ChatRequest(BaseModel):
    content: str = Field(min_length=1, max_length=20000)
    mode: str = Field(default="normal", pattern="^normal$")
    solution_language: str | None = Field(default=None, max_length=30)
    attachment_ids: list[uuid.UUID] = Field(default_factory=list, max_length=20)
    problem_id: uuid.UUID | None = None

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("content must not be blank")
        return value
