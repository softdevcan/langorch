"""
Authentication endpoints
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db
from app.core.exceptions import AuthenticationException, http_401_unauthorized
from app.api.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, LogoutResponse
from app.services.auth_service import auth_service

logger = structlog.get_logger()

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Login",
    description="Authenticate user and return JWT access token",
)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Login endpoint

    - **email**: User email address
    - **password**: User password

    Returns JWT access token and user information
    """
    try:
        result = await auth_service.login(db, login_data)
        logger.info("user_logged_in", email=login_data.email)
        return result
    except AuthenticationException as e:
        logger.warning("login_failed", email=login_data.email, error=str(e))
        raise http_401_unauthorized(detail=e.detail or e.message)


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout",
    description="Logout current user (client-side token removal)",
)
async def logout(
    current_user: User = Depends(get_current_user),
):
    """
    Logout endpoint

    Note: JWT tokens are stateless, so logout is handled client-side.
    This endpoint is mainly for logging purposes and future token blacklisting.
    """
    logger.info("user_logged_out", user_id=str(current_user.id), email=current_user.email)
    return LogoutResponse(message="Successfully logged out")


@router.get(
    "/me",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description="Get current authenticated user information",
)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """
    Get current user information

    Returns the currently authenticated user's details
    """
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role.value,
        "tenant_id": str(current_user.tenant_id) if current_user.tenant_id else None,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat(),
    }
