"""
Unified workflow builder for v0.4.1

Creates a single workflow with intelligent routing that handles both
direct chat and RAG queries based on user intent and session context.
"""
from typing import Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
import structlog

from app.workflows.state import UnifiedWorkflowState
from app.workflows.nodes.router_node import create_router_node, route_condition
from app.workflows.nodes.llm_nodes import create_llm_node, create_rag_generator_node
from app.workflows.nodes.retriever_nodes import create_retriever_node

logger = structlog.get_logger()


def build_unified_workflow(
    checkpointer: Optional[AsyncPostgresSaver] = None,
    config: Optional[dict] = None
) -> StateGraph:
    """
    Build unified workflow with conditional routing

    This creates a single workflow that intelligently routes queries between
    direct chat and RAG paths based on user intent and session context.

    Workflow Structure:
        START → router → [conditional routing] → chat_generator OR retriever
                                                       ↓
                                                  rag_generator
                                                       ↓
                                                      END

    Nodes:
        - router: Analyzes query and decides routing path
        - chat_generator: Direct LLM for chat queries
        - retriever: Document search for RAG queries
        - rag_generator: LLM with document context

    Routing Logic (in router node):
        - Explicit mode override (session mode)
        - Greeting → direct chat
        - Document keywords + has docs → RAG
        - Has docs but unclear → hybrid (try RAG)
        - No docs → direct chat

    Args:
        checkpointer: PostgreSQL checkpointer for state persistence
        config: Optional workflow configuration overrides

    Returns:
        Compiled StateGraph ready for execution
    """
    config = config or {}

    # Create graph with UnifiedWorkflowState
    graph = StateGraph(UnifiedWorkflowState)

    # Node configurations
    router_config = config.get("router", {
        "strategy": "heuristic"
    })

    chat_config = config.get("chat_generator", {
        "model": "ollama/llama3.2",
        "system_prompt": "You are a helpful AI assistant. Provide clear, concise, and accurate responses.",
        "temperature": 0.7,
    })

    retriever_config = config.get("retriever", {
        "search_type": "similarity",
        "k": 5,
        "score_threshold": 0.7,
    })

    rag_config = config.get("rag_generator", {
        "model": "ollama/llama3.2",
        "system_prompt": (
            "You are a helpful AI assistant. Answer the user's question based on the provided context. "
            "If the context doesn't contain relevant information, say so and provide a general response."
        ),
        "temperature": 0.7,
        "include_sources": True,
    })

    # Create nodes
    router_node = create_router_node(router_config)
    chat_generator = create_llm_node(chat_config)
    retriever = create_retriever_node(retriever_config)
    rag_generator = create_rag_generator_node(rag_config)

    # Add nodes to graph
    graph.add_node("router", router_node)
    graph.add_node("chat_generator", chat_generator)
    graph.add_node("retriever", retriever)
    graph.add_node("rag_generator", rag_generator)

    # Add edges
    # START → router
    graph.add_edge(START, "router")

    # router → [conditional] → chat_generator OR retriever
    graph.add_conditional_edges(
        "router",
        route_condition,
        {
            "chat_generator": "chat_generator",
            "retriever": "retriever",
        }
    )

    # retriever → rag_generator
    graph.add_edge("retriever", "rag_generator")

    # chat_generator → END
    graph.add_edge("chat_generator", END)

    # rag_generator → END
    graph.add_edge("rag_generator", END)

    # Compile graph
    compiled_graph = graph.compile(checkpointer=checkpointer)

    logger.info(
        "unified_workflow_built",
        nodes=["router", "chat_generator", "retriever", "rag_generator"],
        router_strategy=router_config.get("strategy"),
    )

    return compiled_graph


def get_unified_workflow_config() -> dict:
    """
    Get default configuration for unified workflow

    This provides a sensible default configuration that can be
    overridden by passing custom config to build_unified_workflow().

    Returns:
        Default workflow configuration
    """
    return {
        "name": "unified_chat_workflow",
        "version": "1.0",
        "description": "Unified workflow with intelligent routing for chat and RAG",
        "router": {
            "strategy": "heuristic"
        },
        "chat_generator": {
            "model": "ollama/llama3.2",
            "system_prompt": "You are a helpful AI assistant. Provide clear, concise, and accurate responses.",
            "temperature": 0.7,
        },
        "retriever": {
            "search_type": "similarity",
            "k": 5,
            "score_threshold": 0.7,
        },
        "rag_generator": {
            "model": "ollama/llama3.2",
            "system_prompt": (
                "You are a helpful AI assistant. Answer the user's question based on the provided context. "
                "If the context doesn't contain relevant information, say so and provide a general response."
            ),
            "temperature": 0.7,
            "include_sources": True,
        }
    }
