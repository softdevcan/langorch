"""
WorkflowExecution model for LangGraph v0.4
"""
from uuid import UUID
from datetime import datetime
from enum import Enum
from sqlalchemy import String, ForeignKey, Text, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID

from app.models.base import Base


class ExecutionStatus(str, Enum):
    """Workflow execution status enum"""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class WorkflowExecution(Base):
    """
    Workflow execution tracking model

    Tracks individual workflow runs with state and results
    """
    __tablename__ = "workflow_executions"

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
    )

    workflow_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="SET NULL"),
        nullable=True,
    )

    thread_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)

    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        index=True,
    )  # running, completed, failed, interrupted

    input_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    output_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="CURRENT_TIMESTAMP",
        nullable=False,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="workflow_executions")
    user = relationship("User", back_populates="workflow_executions")
    workflow = relationship("Workflow", back_populates="executions")
    hitl_approvals = relationship(
        "HITLApproval",
        back_populates="execution",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<WorkflowExecution(id={self.id}, status={self.status}, thread_id={self.thread_id})>"
