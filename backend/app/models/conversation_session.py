"""
ConversationSession model for LangGraph v0.4
"""
from uuid import UUID
from datetime import datetime
from sqlalchemy import ForeignKey, Text, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID

from app.models.base import Base


class ConversationSession(Base):
    """
    Conversation session model

    Represents a chat session with message history
    """
    __tablename__ = "conversation_sessions"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        server_default="uuid_generate_v4()",
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    workflow_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="SET NULL"),
        nullable=True,
    )

    thread_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
        index=True,
    )

    title: Mapped[str | None] = mapped_column(Text, nullable=True)

    session_metadata: Mapped[dict] = mapped_column(
        JSON,
        server_default="'{}'",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="CURRENT_TIMESTAMP",
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="CURRENT_TIMESTAMP",
        nullable=False,
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="conversation_sessions")
    user = relationship("User", back_populates="conversation_sessions")
    workflow = relationship("Workflow", back_populates="conversation_sessions")
    messages = relationship(
        "Message",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.created_at"
    )
    session_documents = relationship(
        "SessionDocument",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin"  # Eager load for session context
    )

    def __repr__(self) -> str:
        return f"<ConversationSession(id={self.id}, thread_id={self.thread_id}, title={self.title})>"
