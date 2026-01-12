"""
Workflow state definitions for LangGraph

This module defines TypedDict state classes used by LangGraph workflows.
"""
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class WorkflowState(TypedDict):
    """
    Base workflow state for LangGraph workflows

    Uses add_messages reducer for automatic message history management.
    This allows appending messages without losing previous conversation history.
    """
    # Messages with automatic history management (uses add_messages reducer)
    messages: Annotated[List[BaseMessage], add_messages]

    # Retrieved documents from vector search
    documents: List[Dict[str, Any]]

    # Formatted context string for LLM prompts
    context: str

    # Metadata (tenant_id, session_id, etc.)
    metadata: Dict[str, Any]

    # HITL approval status (None=not requested, True=approved, False=rejected)
    approved: Optional[bool]

    # Intermediate results from nodes
    intermediate_results: Dict[str, Any]

    # Error message if workflow fails
    error: Optional[str]


class RAGState(WorkflowState):
    """
    Extended state for RAG (Retrieval-Augmented Generation) workflows

    Includes additional fields specific to RAG operations like query processing,
    document retrieval, relevance grading, and hallucination detection.
    """
    # Query processing
    query: str
    reformulated_query: Optional[str]

    # Retrieval results
    retrieved_docs: List[Dict[str, Any]]
    relevance_scores: List[float]

    # Generation
    generation: str
    hallucination_score: Optional[float]

    # User feedback from HITL
    user_feedback: Optional[str]
