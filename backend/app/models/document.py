"""
Document model - Documents uploaded by tenants
"""
from enum import Enum as PyEnum
from sqlalchemy import String, Integer, ForeignKey, Enum, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
from typing import List, Optional

from app.models.base import BaseModel


class DocumentStatus(str, PyEnum):
    """Document processing status enumeration"""
    UPLOADING = "uploading"  # File is being uploaded
    PROCESSING = "processing"  # Being chunked and embedded
    COMPLETED = "completed"  # Processing completed successfully
    FAILED = "failed"  # Processing failed
    DELETED = "deleted"  # Soft deleted


class Document(BaseModel):
    """
    Document model

    Each document belongs to a tenant and user.
    Tenant isolation is enforced at multiple layers:
    - Row Level Security (RLS) at database level
    - Application-level filtering in services
    - Vector store metadata filtering
    """
    __tablename__ = "documents"

    # Tenant relationship
    tenant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID for multi-tenant isolation"
    )

    # User relationship (uploader)
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who uploaded the document"
    )

    # Document metadata
    filename: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Original filename"
    )

    file_path: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        comment="Storage path (S3, local filesystem, etc.)"
    )

    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="File size in bytes"
    )

    file_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="MIME type (e.g., 'application/pdf', 'text/plain')"
    )

    # Processing status
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, native_enum=False),
        default=DocumentStatus.UPLOADING,
        nullable=False,
        index=True,
        comment="Document processing status"
    )

    # Content and embeddings
    content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Extracted text content (for full-text search)"
    )

    embedding: Mapped[Optional[Vector]] = mapped_column(
        Vector(1536),  # OpenAI ada-002/ada-003 dimension
        nullable=True,
        comment="Document-level embedding vector (1536 dimensions)"
    )

    # Metadata
    doc_metadata: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        name="metadata",  # Column name in database
        nullable=True,
        comment="Additional metadata (author, title, tags, etc.)"
    )

    # Processing information
    chunk_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of chunks created from this document"
    )

    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if processing failed"
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="documents"
    )

    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="documents"
    )

    chunks: Mapped[List["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan"
    )

    llm_conversations: Mapped[List["LLMConversation"]] = relationship(
        "LLMConversation",
        back_populates="document"
    )

    llm_operations: Mapped[List["LLMOperation"]] = relationship(
        "LLMOperation",
        back_populates="document"
    )

    # Indexes
    __table_args__ = (
        # Index for tenant-based queries
        Index("ix_documents_tenant_status", "tenant_id", "status"),
        # Index for user's documents
        Index("ix_documents_user_created", "user_id", "created_at"),
        # Full-text search index (if using PostgreSQL full-text search)
        # Index("ix_documents_content_fts", text("to_tsvector('english', content)"), postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, filename={self.filename}, status={self.status})>"
