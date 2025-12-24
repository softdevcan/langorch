"""
Authentication schemas for request/response validation
"""
from typing import Optional
from uuid import UUID
from pydantic import Field, EmailStr

from app.models.user import UserRole
from app.schemas import BaseSchema


class LoginRequest(BaseSchema):
    """Schema for login request"""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=1, description="User password")


class TokenPayload(BaseSchema):
    """Schema for JWT token payload"""
    sub: UUID = Field(..., description="User ID (subject)")
    email: str = Field(..., description="User email")
    role: UserRole = Field(..., description="User role")
    tenant_id: Optional[UUID] = Field(None, description="Tenant ID")
    exp: int = Field(..., description="Token expiration timestamp")
    iat: int = Field(..., description="Token issued at timestamp")


class TokenResponse(BaseSchema):
    """Schema for token response"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")


class LoginResponse(TokenResponse):
    """Schema for login response"""
    user: dict = Field(..., description="User information")


class LogoutResponse(BaseSchema):
    """Schema for logout response"""
    message: str = Field("Successfully logged out", description="Logout message")
