"""
HITL (Human-in-the-Loop) schemas for LangGraph v0.4
"""
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


# ============ HITL Approval Schemas ============

class HITLApprovalBase(BaseModel):
    """Base HITL approval schema"""
    prompt: str = Field(..., description="Approval prompt for the user")
    context_data: Optional[Dict[str, Any]] = Field(None, description="Context data for decision")


class HITLApprovalCreate(HITLApprovalBase):
    """Schema for creating HITL approval"""
    execution_id: UUID


class HITLApprovalResponse(HITLApprovalBase):
    """Schema for HITL approval response"""
    id: UUID
    execution_id: UUID
    tenant_id: UUID
    user_id: UUID
    status: str  # pending, approved, rejected
    user_response: Optional[Dict[str, Any]]
    created_at: datetime
    responded_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class HITLRespondRequest(BaseModel):
    """Request to respond to HITL approval"""
    approved: bool = Field(..., description="Whether to approve or reject")
    feedback: Optional[str] = Field(None, description="Optional user feedback")
