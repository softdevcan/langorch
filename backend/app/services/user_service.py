"""
User service - CRUD operations for users
"""
from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
import structlog

from app.core.security import security
from app.core.exceptions import (
    NotFoundException,
    ConflictException,
    ValidationException,
)
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate, UserResponse

logger = structlog.get_logger()


class UserService:
    """User service for CRUD operations"""

    @staticmethod
    async def create_user(
        db: AsyncSession,
        user_data: UserCreate,
    ) -> User:
        """
        Create a new user

        Args:
            db: Database session
            user_data: User creation data

        Returns:
            Created user

        Raises:
            ConflictException: If email already exists
            ValidationException: If validation fails
        """
        # Check if email already exists
        result = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise ConflictException(
                "User already exists",
                detail=f"Email {user_data.email} is already registered"
            )

        # Validate tenant_id for non-super_admin users
        if user_data.role != UserRole.SUPER_ADMIN and not user_data.tenant_id:
            raise ValidationException(
                "Tenant ID required",
                detail="Non-super_admin users must belong to a tenant"
            )

        # Hash password
        hashed_password = security.hash_password(user_data.password)

        # Create user
        user = User(
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            role=user_data.role,
            tenant_id=user_data.tenant_id,
            is_active=user_data.is_active,
        )

        try:
            db.add(user)
            await db.commit()
            await db.refresh(user)

            logger.info(
                "user_created",
                user_id=str(user.id),
                email=user.email,
                role=user.role.value,
                tenant_id=str(user.tenant_id) if user.tenant_id else None,
            )

            return user

        except IntegrityError as e:
            await db.rollback()
            logger.error("user_creation_failed", error=str(e))
            raise ConflictException(
                "User creation failed",
                detail="Database constraint violation"
            )

    @staticmethod
    async def get_user(
        db: AsyncSession,
        user_id: UUID,
        current_user: Optional[User] = None,
    ) -> User:
        """
        Get user by ID

        Args:
            db: Database session
            user_id: User ID
            current_user: Current user (for tenant filtering)

        Returns:
            User

        Raises:
            NotFoundException: If user not found
        """
        query = select(User).where(User.id == user_id)

        # Apply tenant filtering (unless super_admin)
        if current_user and current_user.role != UserRole.SUPER_ADMIN:
            query = query.where(User.tenant_id == current_user.tenant_id)

        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise NotFoundException(
                "User not found",
                detail=f"User with ID {user_id} not found"
            )

        return user

    @staticmethod
    async def list_users(
        db: AsyncSession,
        current_user: Optional[User] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[User], int]:
        """
        List users with pagination and tenant filtering

        Args:
            db: Database session
            current_user: Current user (for tenant filtering)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (users list, total count)
        """
        query = select(User)

        # Apply tenant filtering (unless super_admin)
        if current_user and current_user.role != UserRole.SUPER_ADMIN:
            query = query.where(User.tenant_id == current_user.tenant_id)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        # Get paginated results
        query = query.offset(skip).limit(limit).order_by(User.created_at.desc())
        result = await db.execute(query)
        users = result.scalars().all()

        logger.info(
            "users_listed",
            total=total,
            returned=len(users),
            tenant_id=str(current_user.tenant_id) if current_user and current_user.tenant_id else "all",
        )

        return list(users), total

    @staticmethod
    async def update_user(
        db: AsyncSession,
        user_id: UUID,
        user_data: UserUpdate,
        current_user: Optional[User] = None,
    ) -> User:
        """
        Update user

        Args:
            db: Database session
            user_id: User ID
            user_data: User update data
            current_user: Current user (for tenant filtering)

        Returns:
            Updated user

        Raises:
            NotFoundException: If user not found
            ConflictException: If email already exists
        """
        # Get existing user
        user = await UserService.get_user(db, user_id, current_user)

        # Check email uniqueness if updating email
        if user_data.email and user_data.email != user.email:
            result = await db.execute(
                select(User).where(User.email == user_data.email)
            )
            existing_user = result.scalar_one_or_none()
            if existing_user:
                raise ConflictException(
                    "Email already exists",
                    detail=f"Email {user_data.email} is already registered"
                )

        # Update fields
        update_data = user_data.model_dump(exclude_unset=True)

        # Handle password update separately
        if "password" in update_data and update_data["password"]:
            update_data["hashed_password"] = security.hash_password(update_data.pop("password"))

        for field, value in update_data.items():
            setattr(user, field, value)

        try:
            await db.commit()
            await db.refresh(user)

            logger.info(
                "user_updated",
                user_id=str(user.id),
                updated_fields=list(update_data.keys()),
            )

            return user

        except IntegrityError as e:
            await db.rollback()
            logger.error("user_update_failed", error=str(e))
            raise ConflictException(
                "User update failed",
                detail="Database constraint violation"
            )

    @staticmethod
    async def delete_user(
        db: AsyncSession,
        user_id: UUID,
        current_user: Optional[User] = None,
    ) -> None:
        """
        Delete user

        Args:
            db: Database session
            user_id: User ID
            current_user: Current user (for tenant filtering)

        Raises:
            NotFoundException: If user not found
        """
        user = await UserService.get_user(db, user_id, current_user)

        await db.delete(user)
        await db.commit()

        logger.info("user_deleted", user_id=str(user_id))


# Create singleton instance
user_service = UserService()
