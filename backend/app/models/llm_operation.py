from decimal import Decimal
from sqlalchemy import Column, String, ForeignKey, Text, Integer, CheckConstraint, DECIMAL
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import BaseModel


class LLMOperation(BaseModel):
    __tablename__ = "llm_operations"

    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(PG_UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)
    operation_type = Column(Text, nullable=False)  # 'summarize', 'ask', 'transform'
    input_data = Column(JSONB, nullable=False)
    output_data = Column(JSONB, nullable=True)
    model_used = Column(Text, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    cost_estimate = Column(DECIMAL(10, 6), nullable=True)
    status = Column(Text, nullable=False, default="pending", server_default="pending")
    error_message = Column(Text, nullable=True)
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("operation_type IN ('summarize', 'ask', 'transform')", name="check_operation_type"),
        CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed')", name="check_operation_status"),
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="llm_operations")
    user = relationship("User", back_populates="llm_operations")
    document = relationship("Document", back_populates="llm_operations")
