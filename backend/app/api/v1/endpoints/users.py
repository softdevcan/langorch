"""
User management endpoints
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, status, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db
from app.core.exceptions import (
    NotFoundException,
    ConflictException,
    http_404_not_found,
    http_409_conflict,
)
from app.api.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
    UserPreferencesUpdate,
    PasswordChange,
)
from app.schemas import MessageResponse
from app.services.user_service import user_service
from app.core.security import verify_password, get_password_hash

logger = structlog.get_logger()

router = APIRouter(prefix="/users", tags=["Users"])


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
    description="Create a new user (requires admin role)",
)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.TENANT_ADMIN)),
):
    """
    Create a new user

    - **email**: User email (unique)
    - **password**: User password (min 8 chars, must have upper, lower, digit)
    - **full_name**: User full name
    - **role**: User role
    - **tenant_id**: Tenant ID (required for non-super_admin users)
    - **is_active**: User active status

    Requires: SUPER_ADMIN or TENANT_ADMIN role
    """
    try:
        # Tenant admins can only create users for their own tenant
        if current_user.role == UserRole.TENANT_ADMIN:
            if user_data.tenant_id != current_user.tenant_id:
                raise ConflictException(
                    "Unauthorized",
                    detail="Tenant admins can only create users for their own tenant"
                )
            # Tenant admins cannot create super_admins or other tenant_admins
            if user_data.role in [UserRole.SUPER_ADMIN, UserRole.TENANT_ADMIN]:
                raise ConflictException(
                    "Unauthorized",
                    detail="Tenant admins cannot create admin users"
                )

        user = await user_service.create_user(db, user_data)
        logger.info("user_created_via_api", user_id=str(user.id), created_by=str(current_user.id))
        return user
    except ConflictException as e:
        raise http_409_conflict(detail=e.detail or e.message)


@router.get(
    "/",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    summary="List users",
    description="List users with pagination and tenant filtering",
)
async def list_users(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List users with pagination

    - Automatically filters by tenant (except for super_admin)
    - **skip**: Pagination offset
    - **limit**: Maximum results per page
    """
    users, total = await user_service.list_users(db, current_user, skip, limit)

    return UserListResponse(
        items=users,
        total=total,
        page=skip // limit + 1,
        page_size=limit,
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user",
    description="Get user by ID",
)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get user by ID

    - Automatically applies tenant filtering
    """
    try:
        user = await user_service.get_user(db, user_id, current_user)
        return user
    except NotFoundException as e:
        raise http_404_not_found(detail=e.detail or e.message)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user",
    description="Update user by ID",
)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.TENANT_ADMIN)),
):
    """
    Update user

    - **email**: New email (optional)
    - **full_name**: New full name (optional)
    - **role**: New role (optional)
    - **password**: New password (optional)
    - **is_active**: New active status (optional)

    Requires: SUPER_ADMIN or TENANT_ADMIN role
    """
    try:
        user = await user_service.update_user(db, user_id, user_data, current_user)
        logger.info("user_updated_via_api", user_id=str(user_id), updated_by=str(current_user.id))
        return user
    except NotFoundException as e:
        raise http_404_not_found(detail=e.detail or e.message)
    except ConflictException as e:
        raise http_409_conflict(detail=e.detail or e.message)


@router.delete(
    "/{user_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete user",
    description="Delete user by ID",
)
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.TENANT_ADMIN)),
):
    """
    Delete user

    Requires: SUPER_ADMIN or TENANT_ADMIN role
    """
    try:
        await user_service.delete_user(db, user_id, current_user)
        logger.info("user_deleted_via_api", user_id=str(user_id), deleted_by=str(current_user.id))
        return MessageResponse(message="User deleted successfully")
    except NotFoundException as e:
        raise http_404_not_found(detail=e.detail or e.message)


@router.get(
    "/me/preferences",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get current user preferences",
    description="Get preferences for the current user",
)
async def get_my_preferences(
    current_user: User = Depends(get_current_user),
):
    """
    Get current user's preferences (theme, language, timezone)

    Returns preferences stored in user metadata
    """
    return {
        "preferences": current_user.metadata or {}
    }


@router.put(
    "/me/preferences",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Update current user preferences",
    description="Update preferences for the current user",
)
async def update_my_preferences(
    preferences: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update current user's preferences

    - **theme**: Theme preference ('light', 'dark', 'system')
    - **language**: Language preference ('en', 'tr')
    - **timezone**: Timezone preference
    """
    # Update user preferences (stored in metadata JSONB column)
    if not current_user.metadata:
        current_user.metadata = {}

    if preferences.theme:
        current_user.metadata["theme"] = preferences.theme
    if preferences.language:
        current_user.metadata["language"] = preferences.language
    if preferences.timezone:
        current_user.metadata["timezone"] = preferences.timezone

    await db.commit()
    await db.refresh(current_user)

    logger.info("user_preferences_updated", user_id=str(current_user.id))

    return {
        "message": "Preferences updated successfully",
        "preferences": current_user.metadata
    }


@router.put(
    "/me/password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Change current user password",
    description="Change password for the current user",
)
async def change_my_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Change current user's password

    - **current_password**: Current password (for verification)
    - **new_password**: New password (min 8 chars, must have upper, lower, digit)
    """
    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    # Hash and save new password
    current_user.hashed_password = get_password_hash(password_data.new_password)

    await db.commit()

    logger.info("user_password_changed", user_id=str(current_user.id))

    return MessageResponse(message="Password changed successfully")
