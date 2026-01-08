"""
Authentication service - Login, token generation
"""
from datetime import timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.core.config import settings
from app.core.security import security
from app.core.exceptions import AuthenticationException
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, TokenResponse

logger = structlog.get_logger()


class AuthService:
    """Authentication service"""

    @staticmethod
    async def authenticate_user(
        db: AsyncSession,
        email: str,
        password: str,
    ) -> Optional[User]:
        """
        Authenticate user with email and password

        Args:
            db: Database session
            email: User email
            password: User password

        Returns:
            User if authenticated, None otherwise
        """
        # Get user by email
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.warning("authentication_failed_user_not_found", email=email)
            return None

        if not user.is_active:
            logger.warning("authentication_failed_inactive_user", email=email, user_id=str(user.id))
            return None

        # Verify password
        if not security.verify_password(password, user.hashed_password):
            logger.warning("authentication_failed_wrong_password", email=email, user_id=str(user.id))
            return None

        # Log only on login, not on every authenticated request
        logger.info("user_logged_in", email=email, user_id=str(user.id), role=user.role.value)
        return user

    @staticmethod
    async def login(
        db: AsyncSession,
        login_data: LoginRequest,
    ) -> LoginResponse:
        """
        Login user and generate JWT token

        Args:
            db: Database session
            login_data: Login credentials

        Returns:
            LoginResponse with access token and user info

        Raises:
            AuthenticationException: If authentication fails
        """
        # Authenticate user
        user = await AuthService.authenticate_user(
            db,
            login_data.email,
            login_data.password,
        )

        if not user:
            raise AuthenticationException(
                "Authentication failed",
                detail="Incorrect email or password"
            )

        # Generate access token
        access_token = security.create_access_token(
            user_id=user.id,
            email=user.email,
            role=user.role,
            tenant_id=user.tenant_id,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        # Return login response
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
            user={
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value,
                "tenant_id": str(user.tenant_id) if user.tenant_id else None,
                "is_active": user.is_active,
            }
        )

    @staticmethod
    def create_token(
        user_id: str,
        email: str,
        role: str,
        tenant_id: Optional[str] = None,
    ) -> TokenResponse:
        """
        Create access token (used by other services)

        Args:
            user_id: User ID
            email: User email
            role: User role
            tenant_id: Tenant ID (optional)

        Returns:
            TokenResponse with access token
        """
        from uuid import UUID
        from app.models.user import UserRole

        access_token = security.create_access_token(
            user_id=UUID(user_id),
            email=email,
            role=UserRole(role),
            tenant_id=UUID(tenant_id) if tenant_id else None,
        )

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )


# Create singleton instance
auth_service = AuthService()
