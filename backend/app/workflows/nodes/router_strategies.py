"""
Router strategies for intelligent query routing

LangOrch v0.4.1 - Unified Workflow
Provides heuristic and LLM-based routing strategies for determining
whether to use direct chat or RAG pipeline.
"""
from typing import Dict, Any
import re
import structlog

from app.core.enums import SessionMode

logger = structlog.get_logger()


# Document-related keywords that suggest RAG is needed
DOCUMENT_KEYWORDS = [
    # English
    "document", "documents", "file", "files", "pdf", "paper", "papers",
    "content", "text", "page", "pages", "section", "chapter",
    "what does", "according to", "based on", "in the", "from the",
    "find", "search", "look for", "show me", "tell me about",
    "summarize", "summary", "explain",

    # Turkish
    "doküman", "döküman", "dosya", "sayfa", "bölüm", "içerik",
    "nedir", "nelerdir", "göre", "göster", "bul", "ara",
    "özetle", "özet", "açıkla",
]

# Greeting patterns that suggest direct chat
GREETING_PATTERNS = [
    # English
    r"^(hi|hello|hey|greetings|good morning|good afternoon|good evening)",
    r"^(how are you|how do you do|what's up|whats up)",

    # Turkish
    r"^(merhaba|selam|günaydın|iyi günler|iyi akşamlar)",
    r"^(nasılsın|nasılsınız|naber)",
]

# Small talk patterns that suggest direct chat
SMALL_TALK_PATTERNS = [
    r"(who are you|what are you|what can you do)",
    r"(your name|you called|introduce yourself)",
    r"(help me|assist me|can you help)",
    r"(thank you|thanks|appreciate)",

    # Turkish
    r"(kimsin|nedir|ne yapabilir)",
    r"(adın ne|seni kim|tanıt)",
    r"(yardım|yardımcı)",
    r"(teşekkür|sağol|mersi)",
]


def heuristic_route(
    user_input: str,
    has_documents: bool,
    session_mode: SessionMode,
    session_context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Rule-based routing strategy (fast, deterministic)

    Analyzes user input and session context to determine routing decision.

    Routing Logic:
    1. Explicit mode override (chat_only/rag_only)
    2. Greeting detection → direct_chat
    3. Small talk detection → direct_chat
    4. Document keywords + has documents → rag_needed
    5. Has documents but unclear → hybrid (try RAG with fallback)
    6. No documents → direct_chat

    Args:
        user_input: User's query text
        has_documents: Whether session has active documents
        session_mode: Session routing mode
        session_context: Full session context metadata

    Returns:
        Dict with:
            - route: str - "direct_chat" | "rag_needed" | "hybrid"
            - confidence: float - 0.0-1.0
            - reasoning: dict - Why this decision
    """
    user_input_lower = user_input.lower().strip()

    # Rule 1: Explicit mode override
    if session_mode == SessionMode.CHAT_ONLY:
        return {
            "route": "direct_chat",
            "confidence": 1.0,
            "reasoning": {
                "rule": "explicit_mode_override",
                "mode": "chat_only",
                "description": "Session mode explicitly set to CHAT_ONLY"
            }
        }

    if session_mode == SessionMode.RAG_ONLY:
        if not has_documents:
            # RAG_ONLY mode but no documents - this shouldn't happen
            # (should be caught at mode update), but handle gracefully
            return {
                "route": "direct_chat",
                "confidence": 0.8,
                "reasoning": {
                    "rule": "rag_only_fallback",
                    "mode": "rag_only",
                    "description": "RAG_ONLY mode but no documents available, falling back to chat"
                }
            }
        return {
            "route": "rag_needed",
            "confidence": 1.0,
            "reasoning": {
                "rule": "explicit_mode_override",
                "mode": "rag_only",
                "description": "Session mode explicitly set to RAG_ONLY"
            }
        }

    # Rule 2: Greeting detection
    for pattern in GREETING_PATTERNS:
        if re.search(pattern, user_input_lower, re.IGNORECASE):
            return {
                "route": "direct_chat",
                "confidence": 0.95,
                "reasoning": {
                    "rule": "greeting_detection",
                    "matched_pattern": pattern,
                    "description": "User greeting detected, direct chat appropriate"
                }
            }

    # Rule 3: Small talk detection
    for pattern in SMALL_TALK_PATTERNS:
        if re.search(pattern, user_input_lower, re.IGNORECASE):
            return {
                "route": "direct_chat",
                "confidence": 0.9,
                "reasoning": {
                    "rule": "small_talk_detection",
                    "matched_pattern": pattern,
                    "description": "Small talk detected, direct chat appropriate"
                }
            }

    # Rule 4: Document keywords + has documents
    if has_documents:
        # Check for document-related keywords
        matched_keywords = [
            kw for kw in DOCUMENT_KEYWORDS
            if kw in user_input_lower
        ]

        if matched_keywords:
            return {
                "route": "rag_needed",
                "confidence": 0.85,
                "reasoning": {
                    "rule": "document_keywords_with_docs",
                    "matched_keywords": matched_keywords[:5],  # Top 5
                    "total_documents": session_context.get("document_context", {}).get("total_documents", 0),
                    "description": "Document-related query with available documents"
                }
            }

        # Rule 5: Has documents but unclear intent
        # Use hybrid mode - try RAG, fallback to chat if poor results
        if len(user_input_lower.split()) >= 5:  # Substantial query
            return {
                "route": "hybrid",
                "confidence": 0.6,
                "reasoning": {
                    "rule": "ambiguous_with_docs",
                    "query_length": len(user_input_lower.split()),
                    "total_documents": session_context.get("document_context", {}).get("total_documents", 0),
                    "description": "Unclear intent but documents available, try RAG with fallback"
                }
            }

    # Rule 6: No documents or very short query
    return {
        "route": "direct_chat",
        "confidence": 0.8 if not has_documents else 0.7,
        "reasoning": {
            "rule": "default_chat",
            "has_documents": has_documents,
            "query_length": len(user_input_lower.split()),
            "description": "No clear RAG indicators" + (" and no documents available" if not has_documents else "")
        }
    }


async def llm_route(
    user_input: str,
    has_documents: bool,
    session_mode: SessionMode,
    session_context: Dict[str, Any],
    llm_service: Any
) -> Dict[str, Any]:
    """
    LLM-powered routing strategy (slower, more accurate)

    Uses an LLM to analyze the user's intent and determine the best routing path.
    This provides more nuanced understanding but is slower than heuristic routing.

    NOTE: This is Phase 2B (optional) - Not implemented in Phase 2 initial release.

    Args:
        user_input: User's query text
        has_documents: Whether session has active documents
        session_mode: Session routing mode
        session_context: Full session context metadata
        llm_service: LiteLLM service instance

    Returns:
        Dict with:
            - route: str - "direct_chat" | "rag_needed" | "hybrid"
            - confidence: float - 0.0-1.0
            - reasoning: dict - LLM's reasoning
    """
    # Placeholder for Phase 2B
    # For now, fall back to heuristic routing
    logger.warning(
        "llm_route_not_implemented",
        message="LLM routing not yet implemented, falling back to heuristic"
    )
    return heuristic_route(user_input, has_documents, session_mode, session_context)


def get_routing_strategy(strategy_name: str = "heuristic"):
    """
    Get routing strategy function by name

    Args:
        strategy_name: "heuristic" or "llm"

    Returns:
        Routing strategy function
    """
    strategies = {
        "heuristic": heuristic_route,
        "llm": llm_route,
    }

    strategy = strategies.get(strategy_name)
    if not strategy:
        logger.warning(
            "unknown_routing_strategy",
            strategy_name=strategy_name,
            available=list(strategies.keys()),
            message="Unknown strategy, defaulting to heuristic"
        )
        return strategies["heuristic"]

    return strategy
