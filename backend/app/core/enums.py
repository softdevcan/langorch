"""
Enumerations for the application

This module contains all enum types used throughout the application.
"""
from enum import Enum


class SessionMode(str, Enum):
    """
    Session mode enumeration for conversation routing

    Defines how the unified workflow should route user queries:
    - AUTO: Intelligent routing based on query analysis (recommended)
    - CHAT_ONLY: Force direct chat without RAG pipeline
    - RAG_ONLY: Force RAG pipeline (requires documents)
    """
    AUTO = "auto"
    CHAT_ONLY = "chat_only"
    RAG_ONLY = "rag_only"


class MessageStatus(str, Enum):
    """
    Message status enumeration for LangGraph v0.4

    Used in workflow execution and HITL approval flows.
    """
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalStatus(str, Enum):
    """
    HITL approval status enumeration

    Tracks the state of human-in-the-loop approval requests.
    """
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
