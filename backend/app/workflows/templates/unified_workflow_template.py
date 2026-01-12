"""
Unified workflow template for v0.4.1

Provides JSON template for the unified workflow that can be used
with WorkflowBuilder for dynamic workflow construction.
"""

# Unified Chat Workflow Template
# Single workflow with intelligent routing for both chat and RAG
UNIFIED_CHAT_WORKFLOW = {
    "name": "unified_chat_workflow",
    "version": "1.0",
    "description": "Unified workflow with intelligent routing for chat and RAG capabilities",
    "state_schema": "UnifiedWorkflowState",
    "nodes": [
        {
            "id": "router",
            "type": "router",
            "config": {
                "strategy": "heuristic"  # "heuristic" or "llm"
            }
        },
        {
            "id": "chat_generator",
            "type": "llm",
            "config": {
                "model": "ollama/llama3.2",
                "system_prompt": "You are a helpful AI assistant. Provide clear, concise, and accurate responses.",
                "temperature": 0.7,
            }
        },
        {
            "id": "retriever",
            "type": "retriever",
            "config": {
                "search_type": "similarity",
                "k": 5,
                "score_threshold": 0.7,
            }
        },
        {
            "id": "rag_generator",
            "type": "rag_generator",
            "config": {
                "model": "ollama/llama3.2",
                "system_prompt": (
                    "You are a helpful AI assistant. Answer the user's question based on the provided context. "
                    "If the context doesn't contain relevant information, say so and provide a general response."
                ),
                "temperature": 0.7,
                "include_sources": True,
            }
        }
    ],
    "edges": [
        {
            "source": "__start__",
            "target": "router",
        },
        {
            "source": "router",
            "condition": "route_decision",
            "mapping": {
                "chat_generator": "chat_generator",
                "retriever": "retriever",
            }
        },
        {
            "source": "retriever",
            "target": "rag_generator",
        },
        {
            "source": "chat_generator",
            "target": "__end__",
        },
        {
            "source": "rag_generator",
            "target": "__end__",
        }
    ]
}


# Template with HITL (Human-in-the-Loop) approval
# Extended unified workflow with approval step for RAG responses
UNIFIED_CHAT_WITH_HITL = {
    "name": "unified_chat_with_hitl",
    "version": "1.0",
    "description": "Unified workflow with routing and HITL approval for RAG responses",
    "state_schema": "UnifiedWorkflowState",
    "nodes": [
        {
            "id": "router",
            "type": "router",
            "config": {
                "strategy": "heuristic"
            }
        },
        {
            "id": "chat_generator",
            "type": "llm",
            "config": {
                "model": "ollama/llama3.2",
                "system_prompt": "You are a helpful AI assistant.",
                "temperature": 0.7,
            }
        },
        {
            "id": "retriever",
            "type": "retriever",
            "config": {
                "search_type": "similarity",
                "k": 5,
                "score_threshold": 0.7,
            }
        },
        {
            "id": "rag_generator",
            "type": "rag_generator",
            "config": {
                "model": "ollama/llama3.2",
                "system_prompt": "Answer based on context. If unsure, say so.",
                "temperature": 0.7,
                "include_sources": True,
            }
        },
        {
            "id": "hitl_approval",
            "type": "human_in_loop",
            "config": {
                "prompt": "Please review the RAG response before sending to user.",
                "approval_required": True,
            }
        }
    ],
    "edges": [
        {
            "source": "__start__",
            "target": "router",
        },
        {
            "source": "router",
            "condition": "route_decision",
            "mapping": {
                "chat_generator": "chat_generator",
                "retriever": "retriever",
            }
        },
        {
            "source": "retriever",
            "target": "rag_generator",
        },
        {
            "source": "rag_generator",
            "target": "hitl_approval",
        },
        {
            "source": "hitl_approval",
            "target": "__end__",
        },
        {
            "source": "chat_generator",
            "target": "__end__",
        }
    ]
}


# Minimal template for testing
# Simplified version with just routing and direct paths
UNIFIED_CHAT_MINIMAL = {
    "name": "unified_chat_minimal",
    "version": "1.0",
    "description": "Minimal unified workflow for testing",
    "state_schema": "UnifiedWorkflowState",
    "nodes": [
        {
            "id": "router",
            "type": "router",
            "config": {
                "strategy": "heuristic"
            }
        },
        {
            "id": "chat_generator",
            "type": "llm",
            "config": {
                "model": "ollama/llama3.2",
                "temperature": 0.7,
            }
        },
        {
            "id": "retriever",
            "type": "retriever",
            "config": {
                "k": 3,
            }
        },
        {
            "id": "rag_generator",
            "type": "rag_generator",
            "config": {
                "model": "ollama/llama3.2",
                "temperature": 0.7,
            }
        }
    ],
    "edges": [
        {
            "source": "__start__",
            "target": "router",
        },
        {
            "source": "router",
            "condition": "route_decision",
            "mapping": {
                "chat_generator": "chat_generator",
                "retriever": "retriever",
            }
        },
        {
            "source": "retriever",
            "target": "rag_generator",
        },
        {
            "source": "chat_generator",
            "target": "__end__",
        },
        {
            "source": "rag_generator",
            "target": "__end__",
        }
    ]
}


def get_template(name: str = "unified_chat_workflow") -> dict:
    """
    Get workflow template by name

    Args:
        name: Template name (unified_chat_workflow, unified_chat_with_hitl, unified_chat_minimal)

    Returns:
        Workflow configuration dict

    Raises:
        ValueError: If template name not found
    """
    templates = {
        "unified_chat_workflow": UNIFIED_CHAT_WORKFLOW,
        "unified_chat_with_hitl": UNIFIED_CHAT_WITH_HITL,
        "unified_chat_minimal": UNIFIED_CHAT_MINIMAL,
    }

    if name not in templates:
        raise ValueError(
            f"Unknown template: {name}. "
            f"Available: {list(templates.keys())}"
        )

    return templates[name]
