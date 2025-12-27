from sqlalchemy import Column, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class LLMConversation(BaseModel):
    __tablename__ = "llm_conversations"

    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(PG_UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    title = Column(Text, nullable=True)
    conversation_metadata = Column("metadata", JSONB, default=dict, server_default="{}")

    # Relationships
    tenant = relationship("Tenant", back_populates="llm_conversations")
    user = relationship("User", back_populates="llm_conversations")
    document = relationship("Document", back_populates="llm_conversations")
    messages = relationship("LLMMessage", back_populates="conversation", cascade="all, delete-orphan")
