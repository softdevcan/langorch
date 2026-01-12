"""
SessionDocument model for LangOrch v0.4.1

Many-to-many relationship between conversation sessions and documents.
Enables document context management for chat sessions.
"""
from uuid import UUID
from datetime import datetime
from sqlalchemy import ForeignKey, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID

from app.models.base import Base


class SessionDocument(Base):
    """
    Session-Document association model

    Represents the many-to-many relationship between conversation sessions
    and documents. Enables:
    - Document context management per session
    - Active/inactive document toggling
    - Temporal tracking of document additions

    RLS Policy:
        Tenant isolation enforced through session relationship
    """
    __tablename__ = "session_documents"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        server_default="uuid_generate_v4()",
    )

    session_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("conversation_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    document_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="CURRENT_TIMESTAMP",
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        server_default="true",
        nullable=False,
        comment="Whether this document is active for the session"
    )

    # Relationships
    session: Mapped["ConversationSession"] = relationship(
        "ConversationSession",
        back_populates="session_documents"
    )

    document: Mapped["Document"] = relationship(
        "Document",
        lazy="joined"  # Eager load document details
    )

    def __repr__(self) -> str:
        return (
            f"<SessionDocument(id={self.id}, "
            f"session_id={self.session_id}, "
            f"document_id={self.document_id}, "
            f"is_active={self.is_active})>"
        )
