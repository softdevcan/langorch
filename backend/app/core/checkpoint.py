"""
LangGraph checkpoint manager for state persistence

This module provides PostgreSQL-based checkpoint management for LangGraph workflows.
Checkpoints allow workflows to be paused, resumed, and maintain conversation history.
"""
from typing import Optional
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class CheckpointManager:
    """
    Manage LangGraph checkpoints in PostgreSQL

    Provides checkpoint-based state persistence for workflows, enabling:
    - Workflow pause/resume (for HITL)
    - Conversation history
    - Error recovery
    - Multi-turn interactions
    """

    def __init__(self):
        """Initialize checkpoint manager"""
        self._pool: Optional[AsyncConnectionPool] = None
        self._checkpointer: Optional[AsyncPostgresSaver] = None
        self._initialized = False

    async def initialize(self):
        """
        Initialize checkpointer with connection pool

        Creates PostgreSQL connection pool and initializes AsyncPostgresSaver.
        Must be called before using the checkpointer.
        """
        if self._initialized:
            logger.debug("checkpoint_manager_already_initialized")
            return

        try:
            # Create connection string for psycopg (not asyncpg)
            # AsyncPostgresSaver requires psycopg, not asyncpg
            conninfo = (
                f"host={settings.POSTGRES_HOST} "
                f"port={settings.POSTGRES_PORT} "
                f"dbname={settings.POSTGRES_DB} "
                f"user={settings.POSTGRES_USER} "
                f"password={settings.POSTGRES_PASSWORD}"
            )

            # Create connection pool
            self._pool = AsyncConnectionPool(
                conninfo=conninfo,
                min_size=2,
                max_size=10,
                timeout=30
            )

            # Initialize checkpointer
            async with self._pool.connection() as conn:
                self._checkpointer = AsyncPostgresSaver(conn)
                # Setup checkpoint tables (creates tables if they don't exist)
                await self._checkpointer.setup()

            self._initialized = True

            logger.info(
                "checkpoint_manager_initialized",
                pool_min_size=2,
                pool_max_size=10
            )

        except Exception as e:
            logger.error(
                "checkpoint_manager_initialization_failed",
                error=str(e)
            )
            raise

    async def close(self):
        """Close connection pool"""
        if self._pool:
            await self._pool.close()
            logger.info("checkpoint_manager_closed")

    async def get_checkpointer(self) -> AsyncPostgresSaver:
        """
        Get checkpointer instance

        Returns:
            AsyncPostgresSaver: Initialized checkpointer

        Raises:
            RuntimeError: If checkpointer not initialized
        """
        if not self._initialized:
            await self.initialize()

        if not self._checkpointer:
            raise RuntimeError("Checkpointer not initialized")

        return self._checkpointer

    @staticmethod
    def create_thread_id(tenant_id: str, session_id: str) -> str:
        """
        Create thread ID for tenant isolation

        Thread IDs are used by LangGraph to identify conversation threads.
        We namespace them by tenant for multi-tenancy.

        Format: tenant_{tenant_id}_session_{session_id}

        Args:
            tenant_id: Tenant UUID string
            session_id: Session UUID string

        Returns:
            Thread ID string
        """
        return f"tenant_{tenant_id}_session_{session_id}"

    async def get_checkpoint(self, thread_id: str):
        """
        Get checkpoint for a thread

        Args:
            thread_id: Thread identifier

        Returns:
            Checkpoint data or None if not found
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Note: This is a simplified version
            # Full implementation would query checkpoint tables directly
            logger.debug("get_checkpoint", thread_id=thread_id)
            return None

        except Exception as e:
            logger.error(
                "get_checkpoint_error",
                thread_id=thread_id,
                error=str(e)
            )
            return None

    async def list_checkpoints(self, tenant_id: str) -> list:
        """
        List all checkpoints for a tenant

        Args:
            tenant_id: Tenant UUID string

        Returns:
            List of checkpoint metadata
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Filter checkpoints by tenant prefix
            prefix = f"tenant_{tenant_id}_"

            # Note: This would require querying checkpoint tables
            # For now, return empty list
            logger.debug("list_checkpoints", tenant_id=tenant_id)
            return []

        except Exception as e:
            logger.error(
                "list_checkpoints_error",
                tenant_id=tenant_id,
                error=str(e)
            )
            return []


# Global checkpoint manager instance
checkpoint_manager = CheckpointManager()
