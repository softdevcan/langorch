"""
Tenant schemas for request/response validation
"""
from typing import Optional
from pydantic import Field, field_validator
import re

from app.schemas import BaseSchema, TimestampSchema


class TenantBase(BaseSchema):
    """Base tenant schema with common fields"""
    name: str = Field(..., min_length=1, max_length=255, description="Organization name")
    slug: str = Field(..., min_length=1, max_length=100, description="URL-friendly identifier")
    domain: Optional[str] = Field(None, max_length=255, description="Custom domain")
    is_active: bool = Field(True, description="Tenant status")
    settings: Optional[str] = Field(None, description="Tenant-specific settings (JSON)")

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Validate slug is URL-friendly"""
        if not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError("Slug must contain only lowercase letters, numbers, and hyphens")
        return v


class TenantCreate(TenantBase):
    """Schema for creating a tenant"""
    pass


class TenantUpdate(BaseSchema):
    """Schema for updating a tenant"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    domain: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    settings: Optional[str] = None


class TenantResponse(TenantBase, TimestampSchema):
    """Schema for tenant response"""
    pass


class TenantListResponse(BaseSchema):
    """Schema for paginated tenant list"""
    items: list[TenantResponse]
    total: int
    page: int
    page_size: int
