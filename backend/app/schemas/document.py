"""
Document schemas for request/response validation
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import Field, field_validator

from app.models.document import DocumentStatus
from app.schemas import BaseSchema, TimestampSchema


class DocumentBase(BaseSchema):
    """Base document schema with common fields"""
    filename: str = Field(..., min_length=1, max_length=500, description="Original filename")
    file_type: str = Field(..., description="MIME type (e.g., 'application/pdf')")
    doc_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata (author, title, tags)")


class DocumentCreate(DocumentBase):
    """Schema for creating a document"""
    file_path: str = Field(..., description="Storage path")
    file_size: int = Field(..., gt=0, description="File size in bytes")
    content: Optional[str] = Field(None, description="Extracted text content")


class DocumentUpdate(BaseSchema):
    """Schema for updating a document"""
    status: Optional[DocumentStatus] = None
    content: Optional[str] = None
    chunk_count: Optional[int] = Field(None, ge=0)
    error_message: Optional[str] = None
    doc_metadata: Optional[Dict[str, Any]] = None


class DocumentResponse(DocumentBase, TimestampSchema):
    """Schema for document response"""
    tenant_id: UUID
    user_id: Optional[UUID]
    file_path: str
    file_size: int
    status: DocumentStatus
    content: Optional[str] = None
    chunk_count: int = 0
    error_message: Optional[str] = None

    # Don't expose embedding vector in response (too large)
    model_config = BaseSchema.model_config.copy()


class DocumentListResponse(BaseSchema):
    """Schema for paginated document list"""
    items: List[DocumentResponse]
    total: int
    page: int = 1
    page_size: int = 20


class DocumentSearchRequest(BaseSchema):
    """Schema for semantic search request"""
    query: str = Field(..., min_length=1, max_length=1000, description="Search query text")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of results")
    score_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Minimum similarity score")
    filter_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Filter by document metadata")


class SearchResult(BaseSchema):
    """Schema for a single search result"""
    chunk_id: UUID = Field(..., description="Document chunk ID")
    document_id: UUID = Field(..., description="Parent document ID")
    document_filename: str = Field(..., description="Document filename")
    content: str = Field(..., description="Chunk content")
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    chunk_index: int = Field(..., ge=0, description="Chunk index in document")
    chunk_metadata: Optional[Dict[str, Any]] = Field(None, description="Chunk metadata")
    doc_metadata: Optional[Dict[str, Any]] = Field(None, description="Document metadata")


class DocumentSearchResponse(BaseSchema):
    """Schema for search response"""
    query: str
    results: List[SearchResult]
    total_results: int
    search_time_ms: float = Field(..., description="Search execution time in milliseconds")


class DocumentUploadResponse(BaseSchema):
    """Schema for document upload response"""
    document_id: UUID
    filename: str
    file_size: int
    status: DocumentStatus
    message: str = "Document uploaded successfully and queued for processing"


class DocumentChunkResponse(BaseSchema):
    """Schema for document chunk response"""
    id: UUID
    document_id: UUID
    tenant_id: UUID
    chunk_index: int
    content: str
    token_count: int
    chunk_metadata: Optional[Dict[str, Any]]
    start_char: Optional[int]
    end_char: Optional[int]
    created_at: str
    updated_at: str

    # Don't expose embedding vector in response
    model_config = BaseSchema.model_config.copy()


class DocumentChunkListResponse(BaseSchema):
    """Schema for document chunks list"""
    items: List[DocumentChunkResponse]
    total: int
    document_id: UUID
