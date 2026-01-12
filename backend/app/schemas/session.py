"""
Session schemas for request/response validation

LangOrch v0.4.1 - Session document management and routing
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import Field

from app.schemas import BaseSchema, TimestampSchema
from app.core.enums import SessionMode


class SessionDocumentCreate(BaseSchema):
    """Schema for adding a document to a session"""
    document_id: UUID = Field(..., description="Document UUID to add to session")


class SessionDocumentResponse(BaseSchema):
    """Schema for session document response"""
    id: UUID
    session_id: UUID
    document_id: UUID
    added_at: datetime
    is_active: bool


class SessionDocumentWithDetails(SessionDocumentResponse):
    """Schema for session document with full document details"""
    document_filename: str = Field(..., description="Original filename")
    document_status: str = Field(..., description="Document processing status")
    document_chunk_count: int = Field(..., description="Number of chunks")


class SessionContextResponse(BaseSchema):
    """
    Schema for session context response

    Provides full context about session's document state and routing preferences.
    """
    mode: SessionMode = Field(..., description="Current session mode")
    active_documents: List[UUID] = Field(..., description="List of active document IDs")
    total_documents: int = Field(..., description="Total number of documents in session")
    total_chunks: int = Field(..., description="Total chunks across all documents")
    routing_preferences: Dict[str, Any] = Field(
        default_factory=lambda: {
            "auto_route": True,
            "prefer_rag_when_available": True
        },
        description="Routing preferences"
    )


class SessionModeUpdate(BaseSchema):
    """Schema for updating session mode"""
    mode: SessionMode = Field(..., description="New session mode")


class DocumentContextMetadata(BaseSchema):
    """Schema for document context metadata structure"""
    active_document_ids: List[UUID] = Field(default_factory=list)
    last_upload_at: Optional[datetime] = None
    total_documents: int = 0
    total_chunks: int = 0


class RoutingPreferences(BaseSchema):
    """Schema for routing preferences structure"""
    auto_route: bool = True
    prefer_rag_when_available: bool = True


class ConversationSummary(BaseSchema):
    """Schema for conversation summary metadata"""
    topics: List[str] = Field(default_factory=list)
    last_summary: Optional[str] = None
    message_count_at_summary: int = 0


class SessionMetadata(BaseSchema):
    """
    Schema for complete session metadata structure

    This represents the standardized structure of the session_metadata JSONB field.
    """
    mode: SessionMode = SessionMode.AUTO
    document_context: DocumentContextMetadata = Field(default_factory=DocumentContextMetadata)
    routing_preferences: RoutingPreferences = Field(default_factory=RoutingPreferences)
    conversation_summary: ConversationSummary = Field(default_factory=ConversationSummary)


class SessionDocumentListResponse(BaseSchema):
    """Schema for paginated session document list"""
    items: List[SessionDocumentWithDetails]
    total: int
    session_id: UUID


class SessionDocumentAddResponse(BaseSchema):
    """Schema for successful document addition"""
    session_document: SessionDocumentResponse
    message: str = "Document added to session successfully"


class SessionDocumentRemoveResponse(BaseSchema):
    """Schema for successful document removal"""
    message: str = "Document removed from session successfully"
    removed_document_id: UUID
