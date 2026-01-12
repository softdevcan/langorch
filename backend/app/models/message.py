"""
Message model for LangGraph v0.4
"""
from uuid import UUID
from datetime import datetime
from enum import Enum
from sqlalchemy import String, ForeignKey, Text, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID

from app.models.base import Base


class MessageRole(str, Enum):
    """Message role enum"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(Base):
    """
    Chat message model

    Represents individual messages in a conversation
    """
    __tablename__ = "messages"

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

    role: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )  # user, assistant, system

    content: Mapped[str] = mapped_column(Text, nullable=False)

    message_metadata: Mapped[dict] = mapped_column(
        JSON,
        server_default="'{}'",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="CURRENT_TIMESTAMP",
        nullable=False,
        index=True,
    )

    # Relationships
    session = relationship("ConversationSession", back_populates="messages")

    def __repr__(self) -> str:
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<Message(id={self.id}, role={self.role}, content='{preview}')>"
