"""Schema definitions for API requests and responses"""
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime


# ===== Auth Schemas =====
class UserBase(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("A valid email address is required")
        return value


class UserCreate(UserBase):
    password: str

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be 72 bytes or fewer")
        return value


class UserResponse(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be 72 bytes or fewer")
        return value


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ===== Document Schemas =====
class DocumentBase(BaseModel):
    filename: str
    file_type: str
    file_size: int


class DocumentCreate(DocumentBase):
    pass


class DocumentResponse(DocumentBase):
    id: int
    user_id: int
    status: str
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    chunk_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    items: List[DocumentResponse]
    total: int
    skip: int
    limit: int


# ===== Summary Schemas =====
class SummaryResponse(BaseModel):
    id: int
    document_id: int
    summary_text: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class SummaryRequest(BaseModel):
    document_id: int


# ===== Chat Schemas =====
class MessageCreate(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    document_ids: List[int] = []


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: int
    user_id: int
    messages: List[MessageResponse] = []
    created_at: datetime
    
    class Config:
        from_attributes = True


class ConversationUpdate(BaseModel):
    title: str


class ChatRequest(BaseModel):
    question: str
    document_ids: List[int] = []
    conversation_id: Optional[int] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[dict] = []
    conversation_id: int
    message_id: int


# ===== Search Schemas =====
class SearchRequest(BaseModel):
    query: str
    document_ids: List[int] = []
    top_k: int = 3


class SearchResultItem(BaseModel):
    document_id: int
    filename: str
    page: Optional[int] = None
    text: str
    similarity_score: float


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResultItem]
    total: int


# ===== Entity Extraction Schemas =====
class EntityResponse(BaseModel):
    document_id: int
    emails: List[str] = []
    phone_numbers: List[str] = []
    dates: List[str] = []


# ===== Health Check =====
class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    vector_db: str


# ===== Error Response =====
class ErrorResponse(BaseModel):
    success: bool = False
    error: dict
