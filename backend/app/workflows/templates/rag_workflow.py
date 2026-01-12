"""
Pre-built workflow templates for LangOrch v0.4

This module contains workflow configuration templates that can be used
directly or customized for specific use cases.
"""

# RAG Workflow Template with HITL
RAG_WORKFLOW_TEMPLATE = {
    "name": "rag_workflow",
    "version": "1.0",
    "description": "Retrieval-Augmented Generation workflow with document grading and hallucination checking",
    "state_schema": {
        "messages": {"type": "array"},
        "documents": {"type": "array"},
        "context": {"type": "string"},
        "generation": {"type": "string"},
        "approved": {"type": "boolean"},
        "hallucination_score": {"type": "number"}
    },
    "nodes": [
        {
            "id": "retriever",
            "type": "retriever",
            "config": {
                "top_k": 5,
                "score_threshold": 0.7
            }
        },
        {
            "id": "grader",
            "type": "relevance_grader",
            "config": {
                "model": "ollama/llama3.2",
                "provider": "ollama"
            }
        },
        {
            "id": "generator",
            "type": "rag_generator",
            "config": {
                "model": "ollama/llama3.2",
                "temperature": 0.7,
                "provider": "ollama",
                "include_sources": True
            }
        },
        {
            "id": "hallucination_check",
            "type": "hallucination_checker",
            "config": {
                "threshold": 0.7,
                "model": "ollama/llama3.2",
                "provider": "ollama"
            }
        }
    ],
    "edges": [
        {"source": "__start__", "target": "retriever"},
        {"source": "retriever", "target": "grader"},
        {"source": "grader", "target": "generator"},
        {"source": "generator", "target": "hallucination_check"},
        {"source": "hallucination_check", "target": "__end__"}
    ]
}


# Simple Chat Workflow Template
SIMPLE_CHAT_WORKFLOW = {
    "name": "simple_chat",
    "version": "1.0",
    "description": "Simple conversational chat workflow",
    "state_schema": {
        "messages": {"type": "array"},
        "metadata": {"type": "object"}
    },
    "nodes": [
        {
            "id": "chat",
            "type": "llm",
            "config": {
                "model": "ollama/llama3.2",
                "system_prompt": "You are a helpful AI assistant. Provide clear, accurate, and friendly responses.",
                "temperature": 0.7,
                "provider": "ollama"
            }
        }
    ],
    "edges": [
        {"source": "__start__", "target": "chat"},
        {"source": "chat", "target": "__end__"}
    ]
}


# RAG Workflow with HITL Approval
RAG_WITH_HITL_WORKFLOW = {
    "name": "rag_with_hitl",
    "version": "1.0",
    "description": "RAG workflow with explicit human approval step",
    "nodes": [
        {
            "id": "retriever",
            "type": "retriever",
            "config": {
                "top_k": 5,
                "score_threshold": 0.7
            }
        },
        {
            "id": "generator",
            "type": "rag_generator",
            "config": {
                "model": "ollama/llama3.2",
                "temperature": 0.7,
                "provider": "ollama"
            }
        },
        {
            "id": "approval",
            "type": "human_in_loop",
            "config": {
                "prompt": "Please review and approve this generated response",
                "approval_required": True
            }
        }
    ],
    "edges": [
        {"source": "__start__", "target": "retriever"},
        {"source": "retriever", "target": "generator"},
        {"source": "generator", "target": "approval"},
        {"source": "approval", "target": "__end__"}
    ]
}


# Advanced RAG Workflow with All Features
ADVANCED_RAG_WORKFLOW = {
    "name": "advanced_rag",
    "version": "1.0",
    "description": "Advanced RAG with retrieval, grading, generation, hallucination check, and HITL",
    "nodes": [
        {
            "id": "retriever",
            "type": "retriever",
            "config": {
                "top_k": 10,
                "score_threshold": 0.6
            }
        },
        {
            "id": "grader",
            "type": "relevance_grader",
            "config": {
                "model": "ollama/llama3.2",
                "provider": "ollama"
            }
        },
        {
            "id": "generator",
            "type": "rag_generator",
            "config": {
                "model": "ollama/llama3.2",
                "temperature": 0.7,
                "provider": "ollama",
                "include_sources": True
            }
        },
        {
            "id": "hallucination_check",
            "type": "hallucination_checker",
            "config": {
                "threshold": 0.8,
                "model": "ollama/llama3.2",
                "provider": "ollama"
            }
        },
        {
            "id": "final_approval",
            "type": "human_in_loop",
            "config": {
                "prompt": "Please review the final answer before sending to user",
                "approval_required": False
            }
        }
    ],
    "edges": [
        {"source": "__start__", "target": "retriever"},
        {"source": "retriever", "target": "grader"},
        {"source": "grader", "target": "generator"},
        {"source": "generator", "target": "hallucination_check"},
        {"source": "hallucination_check", "target": "final_approval"},
        {"source": "final_approval", "target": "__end__"}
    ]
}


# Helper function to get template by name
def get_template(name: str) -> dict:
    """
    Get workflow template by name

    Args:
        name: Template name (rag_workflow, simple_chat, rag_with_hitl, advanced_rag)

    Returns:
        Workflow configuration dictionary

    Raises:
        ValueError: If template name not found
    """
    templates = {
        "rag_workflow": RAG_WORKFLOW_TEMPLATE,
        "simple_chat": SIMPLE_CHAT_WORKFLOW,
        "rag_with_hitl": RAG_WITH_HITL_WORKFLOW,
        "advanced_rag": ADVANCED_RAG_WORKFLOW
    }

    if name not in templates:
        raise ValueError(f"Template '{name}' not found. Available: {list(templates.keys())}")

    return templates[name]


# List all available templates
def list_templates() -> list:
    """
    List all available workflow templates

    Returns:
        List of template names
    """
    return [
        "rag_workflow",
        "simple_chat",
        "rag_with_hitl",
        "advanced_rag"
    ]
