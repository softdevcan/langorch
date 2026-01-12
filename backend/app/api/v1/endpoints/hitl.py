"""
HITL (Human-in-the-Loop) API endpoints for LangOrch v0.4

Provides endpoints for managing workflow approvals and interruptions.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import structlog

from app.models.user import User
from app.api.dependencies import get_current_active_user
from app.core.database import get_db
from app.models.hitl_approval import HITLApproval, ApprovalStatus
from app.schemas.hitl import (
    HITLApprovalResponse,
    HITLApprovalRespondRequest
)

logger = structlog.get_logger()
router = APIRouter(prefix="/hitl", tags=["Human-in-the-Loop"])


@router.get("/approvals/pending", response_model=List[HITLApprovalResponse])
async def list_pending_approvals(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List pending approval requests for current user

    Returns all approval requests that are waiting for user response.
    Frontend should poll this endpoint or use websockets for real-time updates.

    Args:
        current_user: Authenticated user
        db: Database session

    Returns:
        List of pending approval requests
    """
    try:
        result = await db.execute(
            select(HITLApproval).where(
                and_(
                    HITLApproval.tenant_id == current_user.tenant_id,
                    HITLApproval.user_id == current_user.id,
                    HITLApproval.status == ApprovalStatus.PENDING
                )
            ).order_by(HITLApproval.created_at.desc())
        )

        approvals = list(result.scalars().all())

        logger.debug(
            "pending_approvals_listed",
            tenant_id=str(current_user.tenant_id),
            user_id=str(current_user.id),
            count=len(approvals)
        )

        return approvals

    except Exception as e:
        logger.error(
            "list_pending_approvals_error",
            tenant_id=str(current_user.tenant_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list approvals: {str(e)}"
        )


@router.get("/approvals/{approval_id}", response_model=HITLApprovalResponse)
async def get_approval(
    approval_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get approval request by ID

    Args:
        approval_id: Approval UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        Approval request details
    """
    try:
        result = await db.execute(
            select(HITLApproval).where(
                and_(
                    HITLApproval.id == UUID(approval_id),
                    HITLApproval.tenant_id == current_user.tenant_id
                )
            )
        )

        approval = result.scalar_one_or_none()

        if not approval:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Approval {approval_id} not found"
            )

        return approval

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "get_approval_error",
            approval_id=approval_id,
            tenant_id=str(current_user.tenant_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get approval: {str(e)}"
        )


@router.post("/approvals/{approval_id}/respond", response_model=HITLApprovalResponse)
async def respond_to_approval(
    approval_id: str,
    request: HITLApprovalRespondRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Respond to approval request (approve/reject)

    This endpoint updates the approval status and triggers workflow resumption.
    The workflow will continue execution based on the user's response.

    Args:
        approval_id: Approval UUID
        request: Approval response (approved + optional feedback)
        current_user: Authenticated user
        db: Database session

    Returns:
        Updated approval record
    """
    try:
        # Get approval
        result = await db.execute(
            select(HITLApproval).where(
                and_(
                    HITLApproval.id == UUID(approval_id),
                    HITLApproval.tenant_id == current_user.tenant_id,
                    HITLApproval.user_id == current_user.id
                )
            )
        )

        approval = result.scalar_one_or_none()

        if not approval:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Approval {approval_id} not found"
            )

        if approval.status != ApprovalStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Approval already {approval.status}"
            )

        # Update approval
        approval.status = ApprovalStatus.APPROVED if request.approved else ApprovalStatus.REJECTED
        approval.user_response = {
            "approved": request.approved,
            "feedback": request.feedback
        }

        await db.commit()
        await db.refresh(approval)

        logger.info(
            "approval_responded",
            approval_id=approval_id,
            tenant_id=str(current_user.tenant_id),
            user_id=str(current_user.id),
            approved=request.approved
        )

        # TODO: Trigger workflow resumption
        # This would require integration with WorkflowExecutionService
        # to resume the paused workflow with the user's response

        return approval

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "respond_to_approval_error",
            approval_id=approval_id,
            tenant_id=str(current_user.tenant_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to respond to approval: {str(e)}"
        )


@router.get("/approvals", response_model=List[HITLApprovalResponse])
async def list_all_approvals(
    status_filter: ApprovalStatus = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all approval requests with optional status filter

    Args:
        status_filter: Optional status filter (pending, approved, rejected)
        limit: Max results to return
        offset: Pagination offset
        current_user: Authenticated user
        db: Database session

    Returns:
        List of approval requests
    """
    try:
        query = select(HITLApproval).where(
            and_(
                HITLApproval.tenant_id == current_user.tenant_id,
                HITLApproval.user_id == current_user.id
            )
        )

        if status_filter:
            query = query.where(HITLApproval.status == status_filter)

        query = query.order_by(HITLApproval.created_at.desc()).limit(limit).offset(offset)

        result = await db.execute(query)
        approvals = list(result.scalars().all())

        logger.debug(
            "approvals_listed",
            tenant_id=str(current_user.tenant_id),
            status_filter=status_filter,
            count=len(approvals)
        )

        return approvals

    except Exception as e:
        logger.error(
            "list_approvals_error",
            tenant_id=str(current_user.tenant_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list approvals: {str(e)}"
        )
