"""
Tenant model - Multi-tenant organization
"""
from sqlalchemy import String, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from typing import List, Optional

from app.models.base import BaseModel


class Tenant(BaseModel):
    """
    Tenant model for multi-tenant architecture

    Each tenant represents a separate organization/company.
    All data is isolated by tenant_id.
    """
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Organization/company name"
    )

    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="URL-friendly identifier (e.g., 'acme-corp')"
    )

    domain: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        comment="Custom domain (e.g., 'acme.example.com')"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Tenant status (active/suspended)"
    )

    settings: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        comment="Tenant-specific settings (JSON)"
    )

    embedding_provider: Mapped[str] = mapped_column(
        String(50),
        default="openai",
        nullable=False,
        index=True,
        comment="Embedding provider type (openai, ollama, claude, gemini)"
    )

    embedding_config: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Provider-specific configuration (API keys, URLs, model settings)"
    )

    # Relationships
    users: Mapped[List["User"]] = relationship(
        "User",
        back_populates="tenant",
        cascade="all, delete-orphan"
    )

    documents: Mapped[List["Document"]] = relationship(
        "Document",
        back_populates="tenant",
        cascade="all, delete-orphan"
    )

    document_chunks: Mapped[List["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="tenant",
        cascade="all, delete-orphan"
    )

    llm_conversations: Mapped[List["LLMConversation"]] = relationship(
        "LLMConversation",
        back_populates="tenant",
        cascade="all, delete-orphan"
    )

    llm_operations: Mapped[List["LLMOperation"]] = relationship(
        "LLMOperation",
        back_populates="tenant",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name={self.name}, slug={self.slug})>"
