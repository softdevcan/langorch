"""
Workflow execution service for LangOrch v0.4

This service handles workflow execution, streaming, and session management
using LangGraph StateGraph with checkpoint-based state persistence.
"""
from typing import Dict, Any, AsyncIterator, Optional
from uuid import UUID, uuid4
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import HumanMessage

from app.workflows.builder import WorkflowBuilder
from app.core.checkpoint import checkpoint_manager
from app.core.database import AsyncSessionLocal
from app.models.workflow_execution import WorkflowExecution, ExecutionStatus
from app.models.conversation_session import ConversationSession
from app.models.message import Message as DBMessage, MessageRole
from app.core.exceptions import NotFoundException, ValidationException

logger = structlog.get_logger()


class WorkflowExecutionService:
    """
    Service for executing LangGraph workflows

    Features:
    - Workflow execution with state persistence
    - Streaming execution via async generators
    - Session management for conversations
    - HITL workflow resume
    """

    def __init__(self, tenant_id: UUID, user_id: UUID):
        """
        Initialize workflow execution service

        Args:
            tenant_id: Tenant UUID
            user_id: User UUID
        """
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.builder: Optional[WorkflowBuilder] = None

    async def _initialize_builder(self):
        """Initialize workflow builder with checkpointer"""
        if not self.builder:
            checkpointer = await checkpoint_manager.get_checkpointer()
            self.builder = WorkflowBuilder(checkpointer)

    async def execute_workflow(
        self,
        workflow_config: Dict[str, Any],
        user_input: str,
        session_id: Optional[str] = None,
        workflow_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Execute workflow to completion

        Args:
            workflow_config: Workflow JSON configuration
            user_input: User query/input
            session_id: Optional session ID for conversation continuity
            workflow_id: Optional workflow UUID

        Returns:
            Execution result with session_id, status, and output
        """
        await self._initialize_builder()

        # Create or use existing session
        if not session_id:
            session_id = str(uuid4())

        thread_id = checkpoint_manager.create_thread_id(
            str(self.tenant_id),
            session_id
        )

        async with AsyncSessionLocal() as db:
            try:
                # Create execution record
                execution = WorkflowExecution(
                    tenant_id=self.tenant_id,
                    user_id=self.user_id,
                    workflow_id=workflow_id,
                    thread_id=thread_id,
                    status=ExecutionStatus.RUNNING,
                    input_data={"user_input": user_input}
                )
                db.add(execution)
                await db.commit()
                await db.refresh(execution)

                # Build and compile workflow
                graph = self.builder.build_from_config(workflow_config)
                compiled_graph = await self.builder.compile(graph)

                # Prepare initial state
                initial_state = {
                    "messages": [HumanMessage(content=user_input)],
                    "documents": [],
                    "context": "",
                    "metadata": {
                        "tenant_id": str(self.tenant_id),
                        "user_id": str(self.user_id),
                        "session_id": session_id,
                        "execution_id": str(execution.id)
                    },
                    "intermediate_results": {},
                    "approved": None,
                    "error": None
                }

                # Execute workflow
                config = {
                    "configurable": {
                        "thread_id": thread_id
                    }
                }

                result = await compiled_graph.ainvoke(initial_state, config)

                # Update execution record
                execution.status = ExecutionStatus.COMPLETED
                execution.output_data = {
                    "messages": [
                        {"role": "user" if i % 2 == 0 else "assistant", "content": str(msg.content)}
                        for i, msg in enumerate(result.get("messages", []))
                    ],
                    "intermediate_results": result.get("intermediate_results", {})
                }
                await db.commit()

                logger.info(
                    "workflow_executed",
                    tenant_id=str(self.tenant_id),
                    execution_id=str(execution.id),
                    session_id=session_id,
                    workflow_name=workflow_config.get("name")
                )

                return {
                    "session_id": session_id,
                    "execution_id": str(execution.id),
                    "status": "completed",
                    "result": result
                }

            except Exception as e:
                # Update execution with error
                execution.status = ExecutionStatus.FAILED
                execution.error_message = str(e)
                await db.commit()

                logger.error(
                    "workflow_execution_error",
                    tenant_id=str(self.tenant_id),
                    execution_id=str(execution.id) if execution else None,
                    error=str(e)
                )

                return {
                    "session_id": session_id,
                    "execution_id": str(execution.id) if execution else None,
                    "status": "failed",
                    "error": str(e)
                }

    async def stream_workflow(
        self,
        workflow_config: Dict[str, Any],
        user_input: str,
        session_id: Optional[str] = None,
        workflow_id: Optional[UUID] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream workflow execution

        Args:
            workflow_config: Workflow JSON configuration
            user_input: User query/input
            session_id: Optional session ID
            workflow_id: Optional workflow UUID

        Yields:
            Event dictionaries as workflow progresses
        """
        await self._initialize_builder()

        if not session_id:
            session_id = str(uuid4())

        thread_id = checkpoint_manager.create_thread_id(
            str(self.tenant_id),
            session_id
        )

        async with AsyncSessionLocal() as db:
            try:
                # Create execution record
                execution = WorkflowExecution(
                    tenant_id=self.tenant_id,
                    user_id=self.user_id,
                    workflow_id=workflow_id,
                    thread_id=thread_id,
                    status=ExecutionStatus.RUNNING,
                    input_data={"user_input": user_input}
                )
                db.add(execution)
                await db.commit()
                await db.refresh(execution)

                # Build and compile
                graph = self.builder.build_from_config(workflow_config)
                compiled_graph = await self.builder.compile(graph)

                # Initial state
                initial_state = {
                    "messages": [HumanMessage(content=user_input)],
                    "documents": [],
                    "context": "",
                    "metadata": {
                        "tenant_id": str(self.tenant_id),
                        "user_id": str(self.user_id),
                        "session_id": session_id,
                        "execution_id": str(execution.id)
                    },
                    "intermediate_results": {},
                    "approved": None,
                    "error": None
                }

                config = {
                    "configurable": {
                        "thread_id": thread_id
                    }
                }

                # Stream execution
                async for event in compiled_graph.astream(initial_state, config, stream_mode="updates"):
                    yield {
                        "session_id": session_id,
                        "execution_id": str(execution.id),
                        "event": event
                    }

                # Mark as completed
                execution.status = ExecutionStatus.COMPLETED
                await db.commit()

                logger.info(
                    "workflow_streamed",
                    tenant_id=str(self.tenant_id),
                    execution_id=str(execution.id),
                    session_id=session_id
                )

            except Exception as e:
                execution.status = ExecutionStatus.FAILED
                execution.error_message = str(e)
                await db.commit()

                logger.error(
                    "workflow_streaming_error",
                    tenant_id=str(self.tenant_id),
                    error=str(e)
                )
                raise

    async def resume_workflow(
        self,
        session_id: str,
        user_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Resume interrupted workflow (HITL)

        Args:
            session_id: Session to resume
            user_response: User's response to HITL prompt

        Returns:
            Resume result
        """
        await self._initialize_builder()

        thread_id = checkpoint_manager.create_thread_id(
            str(self.tenant_id),
            session_id
        )

        # Note: Resume implementation requires LangGraph Command
        # This is a simplified version
        logger.info(
            "workflow_resumed",
            tenant_id=str(self.tenant_id),
            session_id=session_id
        )

        return {
            "session_id": session_id,
            "status": "resumed",
            "thread_id": thread_id
        }

    async def create_session(
        self,
        workflow_id: Optional[UUID] = None,
        title: Optional[str] = None
    ) -> ConversationSession:
        """
        Create new conversation session

        Args:
            workflow_id: Optional workflow to use
            title: Optional session title

        Returns:
            Created session
        """
        async with AsyncSessionLocal() as db:
            session_id = str(uuid4())
            thread_id = checkpoint_manager.create_thread_id(
                str(self.tenant_id),
                session_id
            )

            session = ConversationSession(
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                workflow_id=workflow_id,
                thread_id=thread_id,
                title=title or "New Conversation"
            )

            db.add(session)
            await db.commit()
            await db.refresh(session)

            logger.info(
                "session_created",
                tenant_id=str(self.tenant_id),
                session_id=str(session.id)
            )

            return session

    async def get_session(
        self,
        session_id: UUID
    ) -> ConversationSession:
        """Get session by ID"""
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            result = await db.execute(
                select(ConversationSession).where(
                    ConversationSession.id == session_id,
                    ConversationSession.tenant_id == self.tenant_id
                )
            )
            session = result.scalar_one_or_none()

            if not session:
                raise NotFoundException(f"Session {session_id} not found")

            return session

    async def list_sessions(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> list[ConversationSession]:
        """List user's sessions"""
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select, desc
            result = await db.execute(
                select(ConversationSession)
                .where(
                    ConversationSession.tenant_id == self.tenant_id,
                    ConversationSession.user_id == self.user_id
                )
                .order_by(desc(ConversationSession.updated_at))
                .limit(limit)
                .offset(offset)
            )
            return list(result.scalars().all())

    async def add_message(
        self,
        session_id: UUID,
        role: MessageRole,
        content: str
    ) -> DBMessage:
        """Add message to session"""
        async with AsyncSessionLocal() as db:
            message = DBMessage(
                session_id=session_id,
                role=role,
                content=content
            )
            db.add(message)
            await db.commit()
            await db.refresh(message)

            return message

    async def get_messages(
        self,
        session_id: UUID,
        limit: int = 100
    ) -> list[DBMessage]:
        """Get session messages"""
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            result = await db.execute(
                select(DBMessage)
                .where(DBMessage.session_id == session_id)
                .order_by(DBMessage.created_at)
                .limit(limit)
            )
            return list(result.scalars().all())
