"""
Conversation and Message schemas for LangGraph v0.4
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


# ============ Message Schemas ============

class MessageBase(BaseModel):
    """Base message schema"""
    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., min_length=1)
    message_metadata: Dict[str, Any] = Field(default_factory=dict)


class MessageCreate(MessageBase):
    """Schema for creating a message"""
    session_id: UUID


class MessageResponse(MessageBase):
    """Schema for message response"""
    id: UUID
    session_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ Conversation Session Schemas ============

class ConversationSessionBase(BaseModel):
    """Base conversation session schema"""
    title: Optional[str] = None
    session_metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationSessionCreate(ConversationSessionBase):
    """Schema for creating a conversation session"""
    workflow_id: Optional[UUID] = None


class ConversationSessionUpdate(BaseModel):
    """Schema for updating a conversation session"""
    title: Optional[str] = None
    session_metadata: Optional[Dict[str, Any]] = None


class ConversationSessionResponse(ConversationSessionBase):
    """Schema for conversation session response"""
    id: UUID
    tenant_id: UUID
    user_id: UUID
    workflow_id: Optional[UUID]
    thread_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationSessionWithMessages(ConversationSessionResponse):
    """Conversation session with messages"""
    messages: List[MessageResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ============ Chat Request/Response ============

class SendMessageRequest(BaseModel):
    """Request to send a message"""
    content: str = Field(..., min_length=1, description="Message content")


class ChatStreamEvent(BaseModel):
    """Server-Sent Event for chat streaming"""
    event_type: str = Field(..., description="Event type (message_start, content_delta, message_end, error)")
    session_id: str
    data: Optional[Dict[str, Any]] = None
