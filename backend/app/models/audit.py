"""
Audit log model - Track all critical operations
"""
from sqlalchemy import String, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel


class AuditLog(BaseModel):
    """
    Audit log for tracking all critical operations

    Logs: user actions, tenant changes, security events
    Immutable records for compliance and security
    """
    __tablename__ = "audit_logs"

    # Who performed the action
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who performed the action (null if system)"
    )

    tenant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Tenant context (null for platform actions)"
    )

    # What action was performed
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Action type (e.g., 'user.created', 'document.deleted')"
    )

    resource_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Resource type (e.g., 'user', 'document', 'tenant')"
    )

    resource_id: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Resource ID that was affected"
    )

    # Additional context
    ip_address: Mapped[str] = mapped_column(
        String(45),
        nullable=True,
        comment="Client IP address (IPv4 or IPv6)"
    )

    user_agent: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        comment="Client user agent string"
    )

    details: Mapped[dict] = mapped_column(
        JSON,
        nullable=True,
        comment="Additional details (JSON)"
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, action={self.action}, "
            f"resource={self.resource_type}:{self.resource_id})>"
        )
