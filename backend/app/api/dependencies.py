"""
FastAPI dependencies for authentication and authorization
"""
from typing import Optional
from uuid import UUID
from fastapi import Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.core.database import get_db
from app.core.security import security
from app.core.exceptions import http_401_unauthorized, http_403_forbidden
from app.models.user import User, UserRole
from app.schemas.auth import TokenPayload

logger = structlog.get_logger()

# HTTP Bearer token scheme
security_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get current authenticated user from JWT token

    Args:
        credentials: HTTP Bearer token
        db: Database session

    Returns:
        Current user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    # Decode and validate token
    try:
        token_data: TokenPayload = security.decode_access_token(token)
    except Exception as e:
        logger.warning("invalid_token_in_request", error=str(e))
        raise http_401_unauthorized(detail="Invalid or expired token")

    # Get user from database
    result = await db.execute(
        select(User).where(User.id == token_data.sub)
    )
    user = result.scalar_one_or_none()

    if not user:
        logger.warning("user_not_found_for_token", user_id=str(token_data.sub))
        raise http_401_unauthorized(detail="User not found")

    if not user.is_active:
        logger.warning("inactive_user_attempted_access", user_id=str(user.id))
        raise http_401_unauthorized(detail="Inactive user")

    # Removed excessive logging - user_authenticated info log on every request
    # Only log on login (in auth_service.py) to reduce noise

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current active user (alias for get_current_user)

    Args:
        current_user: Current user from get_current_user

    Returns:
        Current active user
    """
    return current_user


def require_role(*allowed_roles: UserRole):
    """
    Dependency factory for role-based access control

    Usage:
        @app.get("/admin")
        async def admin_endpoint(
            user: User = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.TENANT_ADMIN))
        ):
            ...

    Args:
        *allowed_roles: Allowed user roles

    Returns:
        Dependency function
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            logger.warning(
                "unauthorized_role_access_attempt",
                user_id=str(current_user.id),
                user_role=current_user.role.value,
                required_roles=[role.value for role in allowed_roles],
            )
            raise http_403_forbidden(
                detail=f"Required role: {', '.join(role.value for role in allowed_roles)}"
            )
        return current_user

    return role_checker


def require_tenant_access(tenant_id: UUID):
    """
    Dependency factory for tenant isolation

    Ensures user can only access resources from their own tenant.
    Super admins can access all tenants.

    Usage:
        @app.get("/tenants/{tenant_id}/users")
        async def get_tenant_users(
            tenant_id: UUID,
            user: User = Depends(require_tenant_access(tenant_id))
        ):
            ...

    Args:
        tenant_id: Tenant ID to check access for

    Returns:
        Dependency function
    """
    async def tenant_checker(current_user: User = Depends(get_current_user)) -> User:
        # Super admin can access all tenants
        if current_user.role == UserRole.SUPER_ADMIN:
            return current_user

        # Check if user belongs to the tenant
        if current_user.tenant_id != tenant_id:
            logger.warning(
                "tenant_isolation_violation_attempt",
                user_id=str(current_user.id),
                user_tenant_id=str(current_user.tenant_id),
                requested_tenant_id=str(tenant_id),
            )
            raise http_403_forbidden(detail="Access denied to this tenant")

        return current_user

    return tenant_checker


async def get_current_tenant_id(
    current_user: User = Depends(get_current_user),
) -> Optional[UUID]:
    """
    Get current user's tenant ID

    Args:
        current_user: Current user

    Returns:
        Tenant ID or None for super_admin
    """
    return current_user.tenant_id
