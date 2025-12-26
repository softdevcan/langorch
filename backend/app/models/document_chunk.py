"""
DocumentChunk model - Chunks from processed documents
"""
from sqlalchemy import String, Integer, ForeignKey, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
from typing import Optional

from app.models.base import BaseModel


class DocumentChunk(BaseModel):
    """
    DocumentChunk model

    Represents a chunk of text from a parent document.
    Each chunk has its own embedding for semantic search.

    Tenant isolation:
    - Inherits tenant_id from parent document
    - Row Level Security (RLS) enforced
    - Vector search filtered by tenant metadata
    """
    __tablename__ = "document_chunks"

    # Parent document relationship
    document_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent document ID"
    )

    # Tenant relationship (denormalized for faster queries and RLS)
    tenant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID (denormalized from document)"
    )

    # Chunk metadata
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Sequential index within the document (0-based)"
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Chunk text content"
    )

    # Token count for the chunk
    token_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Number of tokens in this chunk"
    )

    # Embedding vector
    embedding: Mapped[Vector] = mapped_column(
        Vector(1536),  # OpenAI ada-002/ada-003 dimension
        nullable=False,
        comment="Chunk embedding vector (1536 dimensions)"
    )

    # Chunk-specific metadata
    chunk_metadata: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        name="metadata",  # Column name in database
        nullable=True,
        comment="Chunk-specific metadata (page_number, section, etc.)"
    )

    # Character offsets in original document
    start_char: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Start character position in original document"
    )

    end_char: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="End character position in original document"
    )

    # Relationships
    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="chunks"
    )

    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="document_chunks"
    )

    # Indexes
    __table_args__ = (
        # Index for document's chunks (ordered by chunk_index)
        Index("ix_document_chunks_document_index", "document_id", "chunk_index"),
        # Index for tenant-based queries
        Index("ix_document_chunks_tenant_created", "tenant_id", "created_at"),
        # Composite index for tenant + document queries
        Index("ix_document_chunks_tenant_document", "tenant_id", "document_id"),
    )

    def __repr__(self) -> str:
        return f"<DocumentChunk(id={self.id}, document_id={self.document_id}, chunk_index={self.chunk_index})>"
