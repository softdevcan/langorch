"""
User model - Users within tenants
"""
from enum import Enum as PyEnum
from sqlalchemy import String, Boolean, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from typing import List

from app.models.base import BaseModel


class UserRole(str, PyEnum):
    """User role enumeration"""
    SUPER_ADMIN = "super_admin"  # Platform admin (manages all tenants)
    TENANT_ADMIN = "tenant_admin"  # Tenant admin (manages tenant)
    USER = "user"  # Regular user
    VIEWER = "viewer"  # Read-only user


class User(BaseModel):
    """
    User model

    Each user belongs to a tenant (except super_admin).
    Tenant isolation is enforced at multiple layers.
    """
    __tablename__ = "users"

    # Tenant relationship
    tenant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,  # Nullable for super_admin
        index=True,
        comment="Tenant ID (null for super_admin)"
    )

    # User credentials
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="User email (unique across platform)"
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Bcrypt hashed password"
    )

    # User profile
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="User full name"
    )

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False),
        default=UserRole.USER,
        nullable=False,
        index=True,
        comment="User role (super_admin, tenant_admin, user, viewer)"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="User account status"
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="users"
    )

    documents: Mapped[List["Document"]] = relationship(
        "Document",
        back_populates="user"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
