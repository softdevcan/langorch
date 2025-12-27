"""
User schemas for request/response validation
"""
from typing import Optional
from uuid import UUID
from pydantic import Field, EmailStr, field_validator

from app.models.user import UserRole
from app.schemas import BaseSchema, TimestampSchema


class UserBase(BaseSchema):
    """Base user schema with common fields"""
    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., min_length=1, max_length=255, description="User full name")
    role: UserRole = Field(UserRole.USER, description="User role")
    is_active: bool = Field(True, description="User account status")


class UserCreate(UserBase):
    """Schema for creating a user"""
    password: str = Field(..., min_length=8, max_length=100, description="User password")
    tenant_id: Optional[UUID] = Field(None, description="Tenant ID (required for non-super_admin)")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserUpdate(BaseSchema):
    """Schema for updating a user"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: Optional[str]) -> Optional[str]:
        """Validate password strength if provided"""
        if v is None:
            return v
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserResponse(UserBase, TimestampSchema):
    """Schema for user response"""
    tenant_id: Optional[UUID] = None

    # Don't expose hashed_password in response
    model_config = BaseSchema.model_config.copy()


class UserListResponse(BaseSchema):
    """Schema for paginated user list"""
    items: list[UserResponse]
    total: int
    page: int
    page_size: int


class UserPreferencesUpdate(BaseSchema):
    """Schema for updating user preferences"""
    theme: Optional[str] = Field(None, description="Theme preference: 'light', 'dark', 'system'")
    language: Optional[str] = Field(None, description="Language preference: 'en', 'tr'")
    timezone: Optional[str] = Field(None, description="Timezone preference")


class PasswordChange(BaseSchema):
    """Schema for changing user password"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=100, description="New password")

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate new password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v
