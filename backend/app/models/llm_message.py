from sqlalchemy import Column, ForeignKey, Text, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class LLMMessage(BaseModel):
    __tablename__ = "llm_messages"

    conversation_id = Column(PG_UUID(as_uuid=True), ForeignKey("llm_conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(Text, nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    message_metadata = Column("metadata", JSONB, default=dict, server_default="{}")

    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant', 'system')", name="check_message_role"),
    )

    # Relationships
    conversation = relationship("LLMConversation", back_populates="messages")
