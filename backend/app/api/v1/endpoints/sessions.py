"""
Session API endpoints for LangOrch v0.4.1

Provides REST API for session-document management and session context.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID
import structlog

from app.models.user import User
from app.api.dependencies import get_current_active_user, get_db
from app.services.session_service import SessionService
from app.schemas.session import (
    SessionDocumentCreate,
    SessionDocumentResponse,
    SessionDocumentWithDetails,
    SessionDocumentListResponse,
    SessionDocumentAddResponse,
    SessionDocumentRemoveResponse,
    SessionModeUpdate,
    SessionContextResponse,
)
from app.schemas import MessageResponse
from app.core.exceptions import NotFoundException, ValidationException
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()
router = APIRouter(tags=["Sessions"])


@router.post(
    "/{session_id}/documents",
    response_model=SessionDocumentAddResponse,
    status_code=status.HTTP_201_CREATED
)
async def add_document_to_session(
    session_id: UUID,
    request: SessionDocumentCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a document to a conversation session

    This associates a document with a session, making it available for RAG queries.
    The document must be fully processed (status: completed) before it can be added.

    Args:
        session_id: Session UUID
        request: Document creation request with document_id
        current_user: Authenticated user
        db: Database session

    Returns:
        Created session document association

    Raises:
        404: Session or document not found
        400: Document already in session or validation failed
    """
    service = SessionService()

    try:
        session_document = await service.add_document_to_session(
            db=db,
            session_id=session_id,
            document_id=request.document_id,
            tenant_id=current_user.tenant_id,
        )

        return SessionDocumentAddResponse(
            session_document=SessionDocumentResponse(
                id=session_document.id,
                session_id=session_document.session_id,
                document_id=session_document.document_id,
                added_at=session_document.added_at,
                is_active=session_document.is_active,
            )
        )

    except NotFoundException as e:
        logger.warning(
            "session_document_add_not_found",
            session_id=str(session_id),
            document_id=str(request.document_id),
            tenant_id=str(current_user.tenant_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationException as e:
        logger.warning(
            "session_document_add_validation_failed",
            session_id=str(session_id),
            document_id=str(request.document_id),
            tenant_id=str(current_user.tenant_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "session_document_add_error",
            session_id=str(session_id),
            tenant_id=str(current_user.tenant_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add document to session: {str(e)}"
        )


@router.delete(
    "/{session_id}/documents/{document_id}",
    response_model=SessionDocumentRemoveResponse
)
async def remove_document_from_session(
    session_id: UUID,
    document_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a document from a conversation session

    This deactivates the document association (soft delete).
    The document will no longer be used for RAG queries in this session.

    Args:
        session_id: Session UUID
        document_id: Document UUID to remove
        current_user: Authenticated user
        db: Database session

    Returns:
        Success message

    Raises:
        404: Session or document association not found
    """
    service = SessionService()

    try:
        await service.remove_document_from_session(
            db=db,
            session_id=session_id,
            document_id=document_id,
            tenant_id=current_user.tenant_id,
        )

        return SessionDocumentRemoveResponse(
            removed_document_id=document_id
        )

    except NotFoundException as e:
        logger.warning(
            "session_document_remove_not_found",
            session_id=str(session_id),
            document_id=str(document_id),
            tenant_id=str(current_user.tenant_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "session_document_remove_error",
            session_id=str(session_id),
            document_id=str(document_id),
            tenant_id=str(current_user.tenant_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove document from session: {str(e)}"
        )


@router.get(
    "/{session_id}/documents",
    response_model=SessionDocumentListResponse
)
async def get_session_documents(
    session_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all active documents for a session

    Returns the list of documents currently associated with the session,
    including document details like filename, status, and chunk count.

    Args:
        session_id: Session UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        List of session documents with details

    Raises:
        404: Session not found
    """
    service = SessionService()

    try:
        documents = await service.get_active_documents(
            db=db,
            session_id=session_id,
            tenant_id=current_user.tenant_id,
        )

        return SessionDocumentListResponse(
            items=documents,
            total=len(documents),
            session_id=session_id,
        )

    except NotFoundException as e:
        logger.warning(
            "session_documents_get_not_found",
            session_id=str(session_id),
            tenant_id=str(current_user.tenant_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "session_documents_get_error",
            session_id=str(session_id),
            tenant_id=str(current_user.tenant_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session documents: {str(e)}"
        )


@router.put(
    "/{session_id}/mode",
    response_model=MessageResponse
)
async def update_session_mode(
    session_id: UUID,
    request: SessionModeUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update session routing mode

    Changes how the unified workflow routes queries for this session:
    - AUTO: Intelligent routing based on query analysis (recommended)
    - CHAT_ONLY: Force direct chat without RAG pipeline
    - RAG_ONLY: Force RAG pipeline (requires active documents)

    Args:
        session_id: Session UUID
        request: Mode update request
        current_user: Authenticated user
        db: Database session

    Returns:
        Success message

    Raises:
        404: Session not found
        400: Invalid mode (e.g., RAG_ONLY without documents)
    """
    service = SessionService()

    try:
        await service.update_session_mode(
            db=db,
            session_id=session_id,
            mode=request.mode,
            tenant_id=current_user.tenant_id,
        )

        return MessageResponse(
            message=f"Session mode updated to {request.mode.value}",
            detail=f"Session {session_id} routing mode updated successfully"
        )

    except NotFoundException as e:
        logger.warning(
            "session_mode_update_not_found",
            session_id=str(session_id),
            tenant_id=str(current_user.tenant_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationException as e:
        logger.warning(
            "session_mode_update_validation_failed",
            session_id=str(session_id),
            mode=request.mode.value,
            tenant_id=str(current_user.tenant_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "session_mode_update_error",
            session_id=str(session_id),
            tenant_id=str(current_user.tenant_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update session mode: {str(e)}"
        )


@router.get(
    "/{session_id}/context",
    response_model=SessionContextResponse
)
async def get_session_context(
    session_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get full session context

    Returns comprehensive context about the session including:
    - Current routing mode
    - Active document IDs
    - Total documents and chunks
    - Routing preferences

    This is used by the frontend to display session state and by the
    unified workflow for routing decisions.

    Args:
        session_id: Session UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        Complete session context

    Raises:
        404: Session not found
    """
    service = SessionService()

    try:
        context = await service.get_session_context(
            db=db,
            session_id=session_id,
            tenant_id=current_user.tenant_id,
        )

        return context

    except NotFoundException as e:
        logger.warning(
            "session_context_get_not_found",
            session_id=str(session_id),
            tenant_id=str(current_user.tenant_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "session_context_get_error",
            session_id=str(session_id),
            tenant_id=str(current_user.tenant_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session context: {str(e)}"
        )
