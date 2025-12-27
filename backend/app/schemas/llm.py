from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


# ====== Conversation Schemas ======

class LLMConversationCreate(BaseModel):
    document_id: Optional[UUID] = None
    title: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LLMConversationResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    user_id: UUID
    document_id: Optional[UUID]
    title: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ====== Message Schemas ======

class LLMMessageCreate(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LLMMessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    metadata: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


# ====== Operation Schemas ======

class DocumentSummarizeRequest(BaseModel):
    document_id: UUID
    model: Optional[str] = "gpt-4"
    max_length: Optional[int] = 500


class DocumentSummarizeResponse(BaseModel):
    operation_id: UUID
    summary: str
    model_used: str
    tokens_used: int
    cost_estimate: Optional[Decimal]


class DocumentAskRequest(BaseModel):
    document_id: UUID
    question: str
    model: Optional[str] = "gpt-4"
    include_chunks: Optional[bool] = True
    max_chunks: Optional[int] = 5


class DocumentAskResponse(BaseModel):
    operation_id: UUID
    answer: str
    sources: List[Dict[str, Any]]
    model_used: str
    tokens_used: int
    cost_estimate: Optional[Decimal]


class DocumentTransformRequest(BaseModel):
    document_id: UUID
    instruction: str
    model: Optional[str] = "gpt-4"
    output_format: Optional[str] = "text"  # 'text', 'markdown', 'json'


class DocumentTransformResponse(BaseModel):
    operation_id: UUID
    transformed_content: str
    model_used: str
    tokens_used: int
    cost_estimate: Optional[Decimal]


class LLMOperationResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    user_id: UUID
    document_id: Optional[UUID]
    operation_type: str
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]]
    model_used: Optional[str]
    tokens_used: Optional[int]
    cost_estimate: Optional[Decimal]
    status: str
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True
