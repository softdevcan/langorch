"""
Pydantic schemas for request/response validation
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=False,
    )


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields"""
    id: UUID
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseSchema):
    """Generic message response"""
    message: str
    detail: Optional[str] = None


class ErrorResponse(BaseSchema):
    """Error response schema"""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


__all__ = [
    "BaseSchema",
    "TimestampSchema",
    "MessageResponse",
    "ErrorResponse",
]
