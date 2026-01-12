"""
HITLApproval model for LangGraph v0.4
"""
from uuid import UUID
from datetime import datetime
from enum import Enum
from sqlalchemy import String, ForeignKey, Text, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID

from app.models.base import Base


class ApprovalStatus(str, Enum):
    """HITL approval status enum"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class HITLApproval(Base):
    """
    Human-in-the-Loop approval model

    Tracks approval requests and responses during workflow execution
    """
    __tablename__ = "hitl_approvals"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        server_default="uuid_generate_v4()",
    )

    execution_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workflow_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    user_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    prompt: Mapped[str] = mapped_column(Text, nullable=False)

    context_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    status: Mapped[str] = mapped_column(
        Text,
        server_default="'pending'",
        nullable=False,
        index=True,
    )  # pending, approved, rejected

    user_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="CURRENT_TIMESTAMP",
        nullable=False,
    )

    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    execution = relationship("WorkflowExecution", back_populates="hitl_approvals")
    tenant = relationship("Tenant", back_populates="hitl_approvals")
    user = relationship("User", back_populates="hitl_approvals")

    def __repr__(self) -> str:
        return f"<HITLApproval(id={self.id}, status={self.status}, execution_id={self.execution_id})>"
