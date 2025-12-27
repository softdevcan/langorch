"""
Security utilities: JWT, password hashing, etc.
"""
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
import bcrypt
import jwt
from jwt.exceptions import InvalidTokenError
import structlog

from app.core.config import settings
from app.core.exceptions import AuthenticationException
from app.schemas.auth import TokenPayload
from app.models.user import UserRole

logger = structlog.get_logger()


class SecurityManager:
    """Security manager for password hashing and JWT operations"""

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt

        Args:
            password: Plain text password

        Returns:
            Hashed password
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against a hash

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password

        Returns:
            True if password matches, False otherwise
        """
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                hashed_password.encode("utf-8")
            )
        except Exception as e:
            logger.error("password_verification_error", error=str(e))
            return False

    @staticmethod
    def create_access_token(
        user_id: UUID,
        email: str,
        role: UserRole,
        tenant_id: Optional[UUID] = None,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Create a JWT access token

        Args:
            user_id: User ID
            email: User email
            role: User role
            tenant_id: Tenant ID (optional, null for super_admin)
            expires_delta: Token expiration time (optional)

        Returns:
            JWT token string
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )

        issued_at = datetime.utcnow()

        payload = {
            "sub": str(user_id),
            "email": email,
            "role": role.value if isinstance(role, UserRole) else role,
            "tenant_id": str(tenant_id) if tenant_id else None,
            "exp": int(expire.timestamp()),
            "iat": int(issued_at.timestamp()),
        }

        token = jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

        logger.info(
            "access_token_created",
            user_id=str(user_id),
            email=email,
            expires_at=expire.isoformat(),
        )

        return token

    @staticmethod
    def decode_access_token(token: str) -> TokenPayload:
        """
        Decode and validate a JWT access token

        Args:
            token: JWT token string

        Returns:
            TokenPayload with decoded data

        Raises:
            AuthenticationException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )

            # Convert tenant_id back to UUID if present
            tenant_id = payload.get("tenant_id")
            if tenant_id:
                tenant_id = UUID(tenant_id)

            token_data = TokenPayload(
                sub=UUID(payload["sub"]),
                email=payload["email"],
                role=UserRole(payload["role"]),
                tenant_id=tenant_id,
                exp=payload["exp"],
                iat=payload["iat"],
            )

            return token_data

        except InvalidTokenError as e:
            logger.warning("invalid_token", error=str(e))
            raise AuthenticationException(
                "Could not validate credentials",
                detail="Invalid or expired token"
            )
        except Exception as e:
            logger.error("token_decode_error", error=str(e))
            raise AuthenticationException(
                "Could not validate credentials",
                detail=str(e)
            )


# Create singleton instance
security = SecurityManager()

# Export commonly used functions for backward compatibility
verify_password = security.verify_password
get_password_hash = security.hash_password
create_access_token = security.create_access_token
decode_access_token = security.decode_access_token
