"""
Unit tests for SessionService

LangOrch v0.4.1 - Session Enhancement
Tests session-document management, mode updates, and context retrieval.
"""
import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.session_service import SessionService
from app.models.conversation_session import ConversationSession
from app.models.document import Document, DocumentStatus
from app.models.session_document import SessionDocument
from app.models.tenant import Tenant
from app.models.user import User
from app.core.enums import SessionMode
from app.core.exceptions import NotFoundException, ValidationException


@pytest.fixture
async def test_session(db_session: AsyncSession, test_tenant: Tenant, test_user: User) -> ConversationSession:
    """Create test conversation session"""
    session = ConversationSession(
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        thread_id=f"test_thread_{uuid4()}",
        title="Test Session",
        session_metadata={"mode": "auto"}
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


@pytest.fixture
async def test_document(db_session: AsyncSession, test_tenant: Tenant, test_user: User) -> Document:
    """Create test document"""
    document = Document(
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        filename="test_document.pdf",
        file_path="/test/path/test_document.pdf",
        file_size=1024,
        file_type="application/pdf",
        status=DocumentStatus.COMPLETED,
        content="Test document content",
        chunk_count=5,
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)
    return document


@pytest.fixture
async def test_document_2(db_session: AsyncSession, test_tenant: Tenant, test_user: User) -> Document:
    """Create second test document"""
    document = Document(
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        filename="test_document_2.pdf",
        file_path="/test/path/test_document_2.pdf",
        file_size=2048,
        file_type="application/pdf",
        status=DocumentStatus.COMPLETED,
        content="Second test document content",
        chunk_count=3,
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)
    return document


@pytest.mark.asyncio
class TestSessionServiceAddDocument:
    """Tests for add_document_to_session method"""

    async def test_add_document_success(
        self,
        db_session: AsyncSession,
        test_session: ConversationSession,
        test_document: Document,
        test_tenant: Tenant,
    ):
        """Test successfully adding a document to a session"""
        service = SessionService()

        session_document = await service.add_document_to_session(
            db=db_session,
            session_id=test_session.id,
            document_id=test_document.id,
            tenant_id=test_tenant.id,
        )

        assert session_document is not None
        assert session_document.session_id == test_session.id
        assert session_document.document_id == test_document.id
        assert session_document.is_active is True

    async def test_add_document_session_not_found(
        self,
        db_session: AsyncSession,
        test_document: Document,
        test_tenant: Tenant,
    ):
        """Test adding document to non-existent session"""
        service = SessionService()
        fake_session_id = uuid4()

        with pytest.raises(NotFoundException) as exc_info:
            await service.add_document_to_session(
                db=db_session,
                session_id=fake_session_id,
                document_id=test_document.id,
                tenant_id=test_tenant.id,
            )

        assert "Session not found" in str(exc_info.value)

    async def test_add_document_document_not_found(
        self,
        db_session: AsyncSession,
        test_session: ConversationSession,
        test_tenant: Tenant,
    ):
        """Test adding non-existent document to session"""
        service = SessionService()
        fake_document_id = uuid4()

        with pytest.raises(NotFoundException) as exc_info:
            await service.add_document_to_session(
                db=db_session,
                session_id=test_session.id,
                document_id=fake_document_id,
                tenant_id=test_tenant.id,
            )

        assert "Document not found" in str(exc_info.value)

    async def test_add_document_already_active(
        self,
        db_session: AsyncSession,
        test_session: ConversationSession,
        test_document: Document,
        test_tenant: Tenant,
    ):
        """Test adding document that's already active in session"""
        service = SessionService()

        # Add document first time
        await service.add_document_to_session(
            db=db_session,
            session_id=test_session.id,
            document_id=test_document.id,
            tenant_id=test_tenant.id,
        )

        # Try adding again
        with pytest.raises(ValidationException) as exc_info:
            await service.add_document_to_session(
                db=db_session,
                session_id=test_session.id,
                document_id=test_document.id,
                tenant_id=test_tenant.id,
            )

        assert "already in session" in str(exc_info.value)

    async def test_add_document_reactivate_inactive(
        self,
        db_session: AsyncSession,
        test_session: ConversationSession,
        test_document: Document,
        test_tenant: Tenant,
    ):
        """Test reactivating an inactive document"""
        service = SessionService()

        # Add document
        session_doc = await service.add_document_to_session(
            db=db_session,
            session_id=test_session.id,
            document_id=test_document.id,
            tenant_id=test_tenant.id,
        )

        # Remove document (soft delete)
        await service.remove_document_from_session(
            db=db_session,
            session_id=test_session.id,
            document_id=test_document.id,
            tenant_id=test_tenant.id,
        )

        # Re-add document (should reactivate)
        reactivated = await service.add_document_to_session(
            db=db_session,
            session_id=test_session.id,
            document_id=test_document.id,
            tenant_id=test_tenant.id,
        )

        assert reactivated.id == session_doc.id
        assert reactivated.is_active is True


@pytest.mark.asyncio
class TestSessionServiceRemoveDocument:
    """Tests for remove_document_from_session method"""

    async def test_remove_document_success(
        self,
        db_session: AsyncSession,
        test_session: ConversationSession,
        test_document: Document,
        test_tenant: Tenant,
    ):
        """Test successfully removing a document from session"""
        service = SessionService()

        # Add document first
        await service.add_document_to_session(
            db=db_session,
            session_id=test_session.id,
            document_id=test_document.id,
            tenant_id=test_tenant.id,
        )

        # Remove document
        await service.remove_document_from_session(
            db=db_session,
            session_id=test_session.id,
            document_id=test_document.id,
            tenant_id=test_tenant.id,
        )

        # Verify it's inactive
        from sqlalchemy import select
        result = await db_session.execute(
            select(SessionDocument).where(
                SessionDocument.session_id == test_session.id,
                SessionDocument.document_id == test_document.id,
            )
        )
        session_doc = result.scalar_one_or_none()
        assert session_doc is not None
        assert session_doc.is_active is False

    async def test_remove_document_not_in_session(
        self,
        db_session: AsyncSession,
        test_session: ConversationSession,
        test_document: Document,
        test_tenant: Tenant,
    ):
        """Test removing document that's not in session"""
        service = SessionService()

        with pytest.raises(NotFoundException) as exc_info:
            await service.remove_document_from_session(
                db=db_session,
                session_id=test_session.id,
                document_id=test_document.id,
                tenant_id=test_tenant.id,
            )

        assert "not found in session" in str(exc_info.value)


@pytest.mark.asyncio
class TestSessionServiceGetActiveDocuments:
    """Tests for get_active_documents method"""

    async def test_get_active_documents_empty(
        self,
        db_session: AsyncSession,
        test_session: ConversationSession,
        test_tenant: Tenant,
    ):
        """Test getting active documents when none exist"""
        service = SessionService()

        documents = await service.get_active_documents(
            db=db_session,
            session_id=test_session.id,
            tenant_id=test_tenant.id,
        )

        assert documents == []

    async def test_get_active_documents_with_documents(
        self,
        db_session: AsyncSession,
        test_session: ConversationSession,
        test_document: Document,
        test_document_2: Document,
        test_tenant: Tenant,
    ):
        """Test getting active documents"""
        service = SessionService()

        # Add two documents
        await service.add_document_to_session(
            db=db_session,
            session_id=test_session.id,
            document_id=test_document.id,
            tenant_id=test_tenant.id,
        )
        await service.add_document_to_session(
            db=db_session,
            session_id=test_session.id,
            document_id=test_document_2.id,
            tenant_id=test_tenant.id,
        )

        documents = await service.get_active_documents(
            db=db_session,
            session_id=test_session.id,
            tenant_id=test_tenant.id,
        )

        assert len(documents) == 2
        assert documents[0].document_filename == test_document_2.filename  # Most recent first
        assert documents[1].document_filename == test_document.filename

    async def test_get_active_documents_excludes_inactive(
        self,
        db_session: AsyncSession,
        test_session: ConversationSession,
        test_document: Document,
        test_document_2: Document,
        test_tenant: Tenant,
    ):
        """Test that inactive documents are excluded"""
        service = SessionService()

        # Add two documents
        await service.add_document_to_session(
            db=db_session,
            session_id=test_session.id,
            document_id=test_document.id,
            tenant_id=test_tenant.id,
        )
        await service.add_document_to_session(
            db=db_session,
            session_id=test_session.id,
            document_id=test_document_2.id,
            tenant_id=test_tenant.id,
        )

        # Remove one document
        await service.remove_document_from_session(
            db=db_session,
            session_id=test_session.id,
            document_id=test_document.id,
            tenant_id=test_tenant.id,
        )

        documents = await service.get_active_documents(
            db=db_session,
            session_id=test_session.id,
            tenant_id=test_tenant.id,
        )

        assert len(documents) == 1
        assert documents[0].document_filename == test_document_2.filename


@pytest.mark.asyncio
class TestSessionServiceUpdateMode:
    """Tests for update_session_mode method"""

    async def test_update_mode_to_chat_only(
        self,
        db_session: AsyncSession,
        test_session: ConversationSession,
        test_tenant: Tenant,
    ):
        """Test updating mode to CHAT_ONLY"""
        service = SessionService()

        updated_session = await service.update_session_mode(
            db=db_session,
            session_id=test_session.id,
            mode=SessionMode.CHAT_ONLY,
            tenant_id=test_tenant.id,
        )

        assert updated_session.session_metadata["mode"] == "chat_only"

    async def test_update_mode_to_rag_only_with_documents(
        self,
        db_session: AsyncSession,
        test_session: ConversationSession,
        test_document: Document,
        test_tenant: Tenant,
    ):
        """Test updating mode to RAG_ONLY with documents"""
        service = SessionService()

        # Add document first
        await service.add_document_to_session(
            db=db_session,
            session_id=test_session.id,
            document_id=test_document.id,
            tenant_id=test_tenant.id,
        )

        updated_session = await service.update_session_mode(
            db=db_session,
            session_id=test_session.id,
            mode=SessionMode.RAG_ONLY,
            tenant_id=test_tenant.id,
        )

        assert updated_session.session_metadata["mode"] == "rag_only"

    async def test_update_mode_to_rag_only_without_documents(
        self,
        db_session: AsyncSession,
        test_session: ConversationSession,
        test_tenant: Tenant,
    ):
        """Test updating mode to RAG_ONLY without documents (should fail)"""
        service = SessionService()

        with pytest.raises(ValidationException) as exc_info:
            await service.update_session_mode(
                db=db_session,
                session_id=test_session.id,
                mode=SessionMode.RAG_ONLY,
                tenant_id=test_tenant.id,
            )

        assert "requires documents" in str(exc_info.value)


@pytest.mark.asyncio
class TestSessionServiceGetContext:
    """Tests for get_session_context method"""

    async def test_get_context_empty_session(
        self,
        db_session: AsyncSession,
        test_session: ConversationSession,
        test_tenant: Tenant,
    ):
        """Test getting context for session with no documents"""
        service = SessionService()

        context = await service.get_session_context(
            db=db_session,
            session_id=test_session.id,
            tenant_id=test_tenant.id,
        )

        assert context.mode == SessionMode.AUTO
        assert context.active_documents == []
        assert context.total_documents == 0
        assert context.total_chunks == 0

    async def test_get_context_with_documents(
        self,
        db_session: AsyncSession,
        test_session: ConversationSession,
        test_document: Document,
        test_document_2: Document,
        test_tenant: Tenant,
    ):
        """Test getting context with documents"""
        service = SessionService()

        # Add documents
        await service.add_document_to_session(
            db=db_session,
            session_id=test_session.id,
            document_id=test_document.id,
            tenant_id=test_tenant.id,
        )
        await service.add_document_to_session(
            db=db_session,
            session_id=test_session.id,
            document_id=test_document_2.id,
            tenant_id=test_tenant.id,
        )

        context = await service.get_session_context(
            db=db_session,
            session_id=test_session.id,
            tenant_id=test_tenant.id,
        )

        assert context.mode == SessionMode.AUTO
        assert len(context.active_documents) == 2
        assert test_document.id in context.active_documents
        assert test_document_2.id in context.active_documents
        assert context.total_documents == 2
        assert context.total_chunks == 8  # 5 + 3

    async def test_get_context_session_not_found(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
    ):
        """Test getting context for non-existent session"""
        service = SessionService()
        fake_session_id = uuid4()

        with pytest.raises(NotFoundException) as exc_info:
            await service.get_session_context(
                db=db_session,
                session_id=fake_session_id,
                tenant_id=test_tenant.id,
            )

        assert "Session not found" in str(exc_info.value)
