"""
Router node for intelligent query routing

LangOrch v0.4.1 - Unified Workflow
Analyzes user queries and session context to determine optimal routing path.
"""
from typing import Dict, Any, Callable
from uuid import UUID
import structlog
from sqlalchemy import select, and_

from app.workflows.state import UnifiedWorkflowState
from app.workflows.nodes.router_strategies import get_routing_strategy
from app.core.database import AsyncSessionLocal
from app.core.enums import SessionMode
from app.models.conversation_session import ConversationSession
from app.models.session_document import SessionDocument
from app.models.document import Document

logger = structlog.get_logger()


def create_router_node(config: Dict[str, Any]) -> Callable:
    """
    Create intelligent routing node

    The router analyzes user input and session context to decide whether
    to use direct chat or RAG pipeline.

    Config:
        strategy: "heuristic" (rule-based, fast) or "llm" (model-based, accurate)
                 Default: "heuristic"

    Returns:
        Callable node function (state -> state)
    """
    strategy_name = config.get("strategy", "heuristic")
    routing_strategy = get_routing_strategy(strategy_name)

    async def router_node(state: UnifiedWorkflowState) -> UnifiedWorkflowState:
        """
        Router node execution

        Responsibilities:
        1. Load session context from DB
        2. Load active documents for session
        3. Apply routing strategy
        4. Update state with decision
        """
        # Get metadata
        metadata = state.get("metadata", {})
        tenant_id_str = metadata.get("tenant_id")
        session_id_str = metadata.get("session_id")

        if not tenant_id_str or not session_id_str:
            logger.error(
                "router_node_missing_ids",
                has_tenant=bool(tenant_id_str),
                has_session=bool(session_id_str)
            )
            return {
                **state,
                "route_decision": "direct_chat",
                "route_confidence": 0.5,
                "routing_metadata": {
                    "error": "Missing tenant_id or session_id",
                    "fallback": "direct_chat"
                }
            }

        tenant_id = UUID(tenant_id_str)
        session_id = UUID(session_id_str)

        # Load session context and documents
        async with AsyncSessionLocal() as db:
            try:
                # Get session
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
                    logger.warning(
                        "router_node_session_not_found",
                        session_id=str(session_id),
                        tenant_id=str(tenant_id)
                    )
                    return {
                        **state,
                        "route_decision": "direct_chat",
                        "route_confidence": 0.5,
                        "routing_metadata": {
                            "error": "Session not found",
                            "fallback": "direct_chat"
                        }
                    }

                # Extract session metadata
                session_metadata = session.session_metadata or {}
                mode = SessionMode(session_metadata.get("mode", "auto"))

                # Get active documents
                docs_result = await db.execute(
                    select(SessionDocument, Document).join(
                        Document,
                        SessionDocument.document_id == Document.id
                    ).where(
                        and_(
                            SessionDocument.session_id == session_id,
                            SessionDocument.is_active == True,
                        )
                    )
                )
                session_docs = docs_result.all()

                # Build active documents list
                active_documents = [
                    {
                        "id": str(doc.id),
                        "filename": doc.filename,
                        "chunk_count": doc.chunk_count,
                        "status": doc.status.value,
                    }
                    for _, doc in session_docs
                ]

                has_documents = len(active_documents) > 0

                # Get user input from messages
                messages = state.get("messages", [])
                if not messages:
                    logger.warning("router_node_no_messages")
                    return {
                        **state,
                        "route_decision": "direct_chat",
                        "route_confidence": 0.5,
                        "routing_metadata": {
                            "error": "No messages in state",
                            "fallback": "direct_chat"
                        }
                    }

                # Get last user message
                user_input = None
                for msg in reversed(messages):
                    if hasattr(msg, 'type') and msg.type == "human":
                        user_input = msg.content
                        break
                    elif not hasattr(msg, 'type'):
                        # Fallback for messages without type
                        user_input = str(msg)
                        break

                if not user_input:
                    logger.warning("router_node_no_user_input")
                    return {
                        **state,
                        "route_decision": "direct_chat",
                        "route_confidence": 0.5,
                        "routing_metadata": {
                            "error": "No user input found",
                            "fallback": "direct_chat"
                        }
                    }

                # Apply routing strategy
                if strategy_name == "llm":
                    # LLM routing needs service instance
                    # For now, fall back to heuristic
                    logger.warning(
                        "router_node_llm_fallback",
                        message="LLM routing not fully implemented, using heuristic"
                    )
                    from app.workflows.nodes.router_strategies import heuristic_route
                    routing_decision = heuristic_route(
                        user_input=user_input,
                        has_documents=has_documents,
                        session_mode=mode,
                        session_context=session_metadata
                    )
                else:
                    # Heuristic routing
                    routing_decision = routing_strategy(
                        user_input=user_input,
                        has_documents=has_documents,
                        session_mode=mode,
                        session_context=session_metadata
                    )

                logger.info(
                    "router_node_decision",
                    session_id=str(session_id),
                    route=routing_decision["route"],
                    confidence=routing_decision["confidence"],
                    has_documents=has_documents,
                    mode=mode.value
                )

                # Update state with routing decision
                return {
                    **state,
                    "route_decision": routing_decision["route"],
                    "route_confidence": routing_decision["confidence"],
                    "routing_metadata": routing_decision["reasoning"],
                    "session_context": session_metadata,
                    "active_documents": active_documents,
                }

            except Exception as e:
                logger.error(
                    "router_node_error",
                    session_id=str(session_id),
                    tenant_id=str(tenant_id),
                    error=str(e),
                    exc_info=True
                )
                return {
                    **state,
                    "route_decision": "direct_chat",
                    "route_confidence": 0.3,
                    "routing_metadata": {
                        "error": str(e),
                        "fallback": "direct_chat"
                    }
                }

    return router_node


def route_condition(state: UnifiedWorkflowState) -> str:
    """
    Conditional edge function for router

    Reads the route_decision from state and returns the target node name.

    Returns:
        Node name: "direct_chat" | "rag_pipeline" | "rag_pipeline" (hybrid uses RAG)
    """
    route = state.get("route_decision", "direct_chat")

    # Map routes to node names
    # "direct_chat" → "chat_generator"
    # "rag_needed" → "retriever"
    # "hybrid" → "retriever" (try RAG first)

    route_mapping = {
        "direct_chat": "chat_generator",
        "rag_needed": "retriever",
        "hybrid": "retriever",  # Hybrid uses RAG path with fallback in generator
    }

    target = route_mapping.get(route, "chat_generator")

    logger.debug(
        "route_condition",
        route_decision=route,
        target_node=target
    )

    return target
