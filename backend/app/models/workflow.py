"""
Workflow model for LangGraph v0.4
"""
from uuid import UUID
from datetime import datetime
from sqlalchemy import Boolean, String, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID

from app.models.base import BaseModel


class Workflow(BaseModel):
    """
    Workflow definition model

    Stores LangGraph workflow configurations
    """
    __tablename__ = "workflows"

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

    name: Mapped[str] = mapped_column(Text, nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    workflow_config: Mapped[dict] = mapped_column(JSON, nullable=False)

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="workflows")
    user = relationship("User", back_populates="workflows")
    executions = relationship(
        "WorkflowExecution",
        back_populates="workflow",
        cascade="all, delete-orphan"
    )
    conversation_sessions = relationship(
        "ConversationSession",
        back_populates="workflow",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Workflow(id={self.id}, name={self.name}, tenant_id={self.tenant_id})>"
