"""
Tenant context middleware for RLS (Row Level Security)
"""
from typing import Callable
from uuid import UUID
from fastapi import Request, Response
from sqlalchemy import text
import structlog

logger = structlog.get_logger()


async def set_tenant_context_middleware(
    request: Request,
    call_next: Callable,
) -> Response:
    """
    Middleware to set tenant context for RLS (Row Level Security)

    This middleware extracts the tenant_id from the authenticated user
    and sets it in the PostgreSQL session using SET LOCAL.
    This enables Row Level Security policies to filter data by tenant.

    Flow:
    1. Extract user from request.state (set by auth dependency)
    2. Get tenant_id from user
    3. Set app.current_tenant in PostgreSQL session
    4. Process request
    5. RLS policies automatically filter queries by tenant

    Args:
        request: FastAPI request
        call_next: Next middleware/endpoint

    Returns:
        Response from endpoint
    """
    # Get database session from request state (if available)
    db = getattr(request.state, "db", None)
    tenant_id = None

    # Get user from request state (set by get_current_user dependency)
    user = getattr(request.state, "user", None)

    if user and hasattr(user, "tenant_id") and user.tenant_id:
        tenant_id = user.tenant_id

        # Set tenant context in PostgreSQL session for RLS
        if db:
            try:
                await db.execute(
                    text(f"SET LOCAL app.current_tenant = '{str(tenant_id)}'")
                )
                logger.debug(
                    "tenant_context_set",
                    tenant_id=str(tenant_id),
                    path=request.url.path,
                )
            except Exception as e:
                logger.error(
                    "tenant_context_setting_failed",
                    tenant_id=str(tenant_id),
                    error=str(e),
                )

    # Process request
    response = await call_next(request)

    return response


async def inject_db_to_request(
    request: Request,
    call_next: Callable,
) -> Response:
    """
    Middleware to inject database session into request.state

    This allows other middleware (like tenant_context) to access
    the database session.

    Note: This should run BEFORE tenant_context_middleware

    Args:
        request: FastAPI request
        call_next: Next middleware/endpoint

    Returns:
        Response from endpoint
    """
    # Import here to avoid circular dependency
    from app.core.database import async_session_maker

    async with async_session_maker() as db:
        request.state.db = db
        response = await call_next(request)

    return response
