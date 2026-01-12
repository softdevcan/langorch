"""
Session service - Manage chat sessions with document context

LangOrch v0.4.1 - Session Enhancement
SOLID Principles:
- Single Responsibility: Only manages session-document associations and context
- Open/Closed: Extensible for new context types
- Liskov Substitution: Follows standard service patterns
- Interface Segregation: Minimal, focused interface
- Dependency Inversion: Depends on database abstraction
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
import structlog

from app.core.exceptions import (
    NotFoundException,
    ValidationException,
)
from app.core.enums import SessionMode
from app.models.conversation_session import ConversationSession
from app.models.session_document import SessionDocument
from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.schemas.session import (
    SessionDocumentWithDetails,
    SessionContextResponse,
)

logger = structlog.get_logger()


class SessionService:
    """
    Session service for managing conversation sessions with document context

    Features:
    - Session-document association management
    - Session mode management (auto/chat_only/rag_only)
    - Document context tracking
    - Tenant isolation enforced
    - RLS policy compliant
    """

    @staticmethod
    async def add_document_to_session(
        db: AsyncSession,
        session_id: UUID,
        document_id: UUID,
        tenant_id: UUID,
    ) -> SessionDocument:
        """
        Add a document to a conversation session

        Args:
            db: Database session
            session_id: Session UUID
            document_id: Document UUID
            tenant_id: Tenant UUID for isolation

        Returns:
            Created SessionDocument

        Raises:
            NotFoundException: If session or document not found
            ValidationException: If document already in session or validation fails
        """
        try:
            # Verify session exists and belongs to tenant
            session_result = await db.execute(
                select(ConversationSession).where(
                    and_(
                        ConversationSession.id == session_id,
                        ConversationSession.tenant_id == tenant_id,
                    )
                )
            )
            session = session_result.scalar_one_or_none()
            if not session:
                raise NotFoundException(
                    "Session not found",
                    detail=f"Session {session_id} not found for tenant {tenant_id}"
                )

            # Verify document exists and belongs to tenant
            doc_result = await db.execute(
                select(Document).where(
                    and_(
                        Document.id == document_id,
                        Document.tenant_id == tenant_id,
                        Document.status == DocumentStatus.COMPLETED,
                    )
                )
            )
            document = doc_result.scalar_one_or_none()
            if not document:
                raise NotFoundException(
                    "Document not found or not ready",
                    detail=f"Document {document_id} not found or not completed for tenant {tenant_id}"
                )

            # Check if already associated
            existing_result = await db.execute(
                select(SessionDocument).where(
                    and_(
                        SessionDocument.session_id == session_id,
                        SessionDocument.document_id == document_id,
                    )
                )
            )
            existing = existing_result.scalar_one_or_none()
            if existing:
                # If exists but inactive, reactivate it
                if not existing.is_active:
                    existing.is_active = True
                    existing.added_at = datetime.utcnow()
                    await db.commit()
                    await db.refresh(existing)

                    logger.info(
                        "session_document_reactivated",
                        session_id=str(session_id),
                        document_id=str(document_id),
                        tenant_id=str(tenant_id),
                    )

                    # Update session metadata
                    await SessionService._update_session_document_context(
                        db, session_id, tenant_id
                    )

                    return existing
                else:
                    raise ValidationException(
                        "Document already in session",
                        detail=f"Document {document_id} is already active in session {session_id}"
                    )

            # Create association
            session_document = SessionDocument(
                session_id=session_id,
                document_id=document_id,
                is_active=True,
            )

            db.add(session_document)
            await db.commit()
            await db.refresh(session_document)

            logger.info(
                "session_document_added",
                session_id=str(session_id),
                document_id=str(document_id),
                tenant_id=str(tenant_id),
            )

            # Update session metadata
            await SessionService._update_session_document_context(
                db, session_id, tenant_id
            )

            return session_document

        except IntegrityError as e:
            await db.rollback()
            logger.error("session_document_add_failed", error=str(e))
            raise ValidationException(
                "Failed to add document to session",
                detail="Database constraint violation"
            )

    @staticmethod
    async def remove_document_from_session(
        db: AsyncSession,
        session_id: UUID,
        document_id: UUID,
        tenant_id: UUID,
    ) -> None:
        """
        Remove a document from a conversation session

        Args:
            db: Database session
            session_id: Session UUID
            document_id: Document UUID
            tenant_id: Tenant UUID for isolation

        Raises:
            NotFoundException: If association not found
        """
        # Verify session belongs to tenant
        session_result = await db.execute(
            select(ConversationSession).where(
                and_(
                    ConversationSession.id == session_id,
                    ConversationSession.tenant_id == tenant_id,
                )
            )
        )
        session = session_result.scalar_one_or_none()
        if not session:
            raise NotFoundException(
                "Session not found",
                detail=f"Session {session_id} not found for tenant {tenant_id}"
            )

        # Find and deactivate association
        result = await db.execute(
            select(SessionDocument).where(
                and_(
                    SessionDocument.session_id == session_id,
                    SessionDocument.document_id == document_id,
                )
            )
        )
        session_document = result.scalar_one_or_none()

        if not session_document:
            raise NotFoundException(
                "Document not in session",
                detail=f"Document {document_id} not found in session {session_id}"
            )

        # Soft delete by setting is_active to False
        session_document.is_active = False
        await db.commit()

        logger.info(
            "session_document_removed",
            session_id=str(session_id),
            document_id=str(document_id),
            tenant_id=str(tenant_id),
        )

        # Update session metadata
        await SessionService._update_session_document_context(
            db, session_id, tenant_id
        )

    @staticmethod
    async def get_active_documents(
        db: AsyncSession,
        session_id: UUID,
        tenant_id: UUID,
    ) -> List[SessionDocumentWithDetails]:
        """
        Get all active documents for a session

        Args:
            db: Database session
            session_id: Session UUID
            tenant_id: Tenant UUID for isolation

        Returns:
            List of session documents with details

        Raises:
            NotFoundException: If session not found
        """
        # Verify session belongs to tenant
        session_result = await db.execute(
            select(ConversationSession).where(
                and_(
                    ConversationSession.id == session_id,
                    ConversationSession.tenant_id == tenant_id,
                )
            )
        )
        session = session_result.scalar_one_or_none()
        if not session:
            raise NotFoundException(
                "Session not found",
                detail=f"Session {session_id} not found for tenant {tenant_id}"
            )

        # Get active session documents with document details
        result = await db.execute(
            select(SessionDocument)
            .options(selectinload(SessionDocument.document))
            .where(
                and_(
                    SessionDocument.session_id == session_id,
                    SessionDocument.is_active == True,
                )
            )
            .order_by(SessionDocument.added_at.desc())
        )
        session_documents = result.scalars().all()

        # Map to response schema
        return [
            SessionDocumentWithDetails(
                id=sd.id,
                session_id=sd.session_id,
                document_id=sd.document_id,
                added_at=sd.added_at,
                is_active=sd.is_active,
                document_filename=sd.document.filename,
                document_status=sd.document.status.value,
                document_chunk_count=sd.document.chunk_count,
            )
            for sd in session_documents
        ]

    @staticmethod
    async def update_session_mode(
        db: AsyncSession,
        session_id: UUID,
        mode: SessionMode,
        tenant_id: UUID,
    ) -> ConversationSession:
        """
        Update session mode (auto/chat_only/rag_only)

        Args:
            db: Database session
            session_id: Session UUID
            mode: New session mode
            tenant_id: Tenant UUID for isolation

        Returns:
            Updated session

        Raises:
            NotFoundException: If session not found
            ValidationException: If mode is RAG_ONLY but no documents available
        """
        # Get session
        result = await db.execute(
            select(ConversationSession).where(
                and_(
                    ConversationSession.id == session_id,
                    ConversationSession.tenant_id == tenant_id,
                )
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            raise NotFoundException(
                "Session not found",
                detail=f"Session {session_id} not found for tenant {tenant_id}"
            )

        # Validate RAG_ONLY mode requires documents
        if mode == SessionMode.RAG_ONLY:
            active_docs_result = await db.execute(
                select(func.count(SessionDocument.id)).where(
                    and_(
                        SessionDocument.session_id == session_id,
                        SessionDocument.is_active == True,
                    )
                )
            )
            active_doc_count = active_docs_result.scalar()
            if active_doc_count == 0:
                raise ValidationException(
                    "RAG_ONLY mode requires documents",
                    detail="Cannot set RAG_ONLY mode when no documents are active in session"
                )

        # Update mode in metadata
        metadata = session.session_metadata or {}
        metadata["mode"] = mode.value
        session.session_metadata = metadata
        session.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(session)

        logger.info(
            "session_mode_updated",
            session_id=str(session_id),
            new_mode=mode.value,
            tenant_id=str(tenant_id),
        )

        return session

    @staticmethod
    async def get_session_context(
        db: AsyncSession,
        session_id: UUID,
        tenant_id: UUID,
    ) -> SessionContextResponse:
        """
        Get full session context including documents and preferences

        Args:
            db: Database session
            session_id: Session UUID
            tenant_id: Tenant UUID for isolation

        Returns:
            Session context response

        Raises:
            NotFoundException: If session not found
        """
        # Get session
        result = await db.execute(
            select(ConversationSession).where(
                and_(
                    ConversationSession.id == session_id,
                    ConversationSession.tenant_id == tenant_id,
                )
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            raise NotFoundException(
                "Session not found",
                detail=f"Session {session_id} not found for tenant {tenant_id}"
            )

        # Get active documents
        active_docs_result = await db.execute(
            select(SessionDocument.document_id).where(
                and_(
                    SessionDocument.session_id == session_id,
                    SessionDocument.is_active == True,
                )
            )
        )
        active_document_ids = [row[0] for row in active_docs_result.all()]

        # Get total chunk count
        chunk_count_result = await db.execute(
            select(func.sum(Document.chunk_count)).where(
                and_(
                    Document.id.in_(active_document_ids) if active_document_ids else False,
                )
            )
        )
        total_chunks = chunk_count_result.scalar() or 0

        # Extract metadata
        metadata = session.session_metadata or {}
        mode = SessionMode(metadata.get("mode", "auto"))
        routing_prefs = metadata.get("routing_preferences", {
            "auto_route": True,
            "prefer_rag_when_available": True
        })

        return SessionContextResponse(
            mode=mode,
            active_documents=active_document_ids,
            total_documents=len(active_document_ids),
            total_chunks=int(total_chunks),
            routing_preferences=routing_prefs,
        )

    @staticmethod
    async def _update_session_document_context(
        db: AsyncSession,
        session_id: UUID,
        tenant_id: UUID,
    ) -> None:
        """
        Internal method to update session metadata with current document context

        Args:
            db: Database session
            session_id: Session UUID
            tenant_id: Tenant UUID for isolation
        """
        # Get session
        result = await db.execute(
            select(ConversationSession).where(
                and_(
                    ConversationSession.id == session_id,
                    ConversationSession.tenant_id == tenant_id,
                )
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            return

        # Get active documents
        active_docs_result = await db.execute(
            select(SessionDocument.document_id).where(
                and_(
                    SessionDocument.session_id == session_id,
                    SessionDocument.is_active == True,
                )
            )
        )
        active_document_ids = [str(row[0]) for row in active_docs_result.all()]

        # Get total chunk count
        chunk_count_result = await db.execute(
            select(func.sum(Document.chunk_count)).where(
                and_(
                    Document.id.in_([UUID(did) for did in active_document_ids]) if active_document_ids else False,
                )
            )
        )
        total_chunks = chunk_count_result.scalar() or 0

        # Update metadata
        metadata = session.session_metadata or {}
        doc_context = metadata.get("document_context", {})
        doc_context.update({
            "active_document_ids": active_document_ids,
            "last_upload_at": datetime.utcnow().isoformat(),
            "total_documents": len(active_document_ids),
            "total_chunks": int(total_chunks),
        })
        metadata["document_context"] = doc_context
        session.session_metadata = metadata
        session.updated_at = datetime.utcnow()

        await db.commit()


# Export service instance
session_service = SessionService()
