"""
LLM nodes for LangGraph workflows

This module provides node creators for LLM-based operations including
general chat completions and RAG-aware generation.
"""
from typing import Dict, Any, Callable
from uuid import UUID
from langchain_core.messages import HumanMessage, AIMessage
import structlog
from sqlalchemy import select

from app.workflows.state import WorkflowState
from app.services.litellm_service import LiteLLMService
from app.core.database import AsyncSessionLocal
from app.models.tenant import Tenant

logger = structlog.get_logger()


def create_llm_node(config: Dict[str, Any]) -> Callable:
    """
    Create general LLM completion node

    Config:
        model: Model name (gpt-4, ollama/llama3.2, claude-3-sonnet, etc.)
        system_prompt: System prompt (default: "You are a helpful assistant.")
        temperature: Temperature 0-1 (default: 0.7)
        max_tokens: Max response tokens (optional)
        provider: Provider hint (openai, anthropic, ollama) (optional)

    Returns:
        Callable node function (state -> state)
    """
    model = config.get("model", "ollama/llama3.2")
    system_prompt = config.get("system_prompt", "You are a helpful assistant.")
    temperature = config.get("temperature", 0.7)
    max_tokens = config.get("max_tokens")
    provider = config.get("provider")

    async def llm_node(state: WorkflowState) -> WorkflowState:
        """
        LLM node execution

        Processes conversation history and generates AI response.
        """
        # Get tenant ID from state metadata
        tenant_id_str = state["metadata"].get("tenant_id")
        tenant_id = UUID(tenant_id_str) if tenant_id_str else None

        if not tenant_id:
            logger.error("llm_node_missing_tenant_id")
            return {
                **state,
                "error": "Missing tenant_id in metadata"
            }

        # Load tenant LLM config from database
        tenant_llm_config = None
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Tenant).where(Tenant.id == tenant_id)
            )
            tenant = result.scalar_one_or_none()
            if tenant:
                tenant_llm_config = tenant.llm_config or {}

        # Initialize LiteLLM service with tenant config
        llm_service = LiteLLMService(
            tenant_id=tenant_id,
            provider=provider,
            tenant_config=tenant_llm_config
        )

        # Prepare messages
        messages = [
            {"role": "system", "content": system_prompt}
        ]

        # Add conversation history
        for msg in state.get("messages", []):
            if isinstance(msg, HumanMessage):
                messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                messages.append({"role": "assistant", "content": msg.content})

        try:
            # Get completion
            response = await llm_service.complete(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )

            # Add to state
            ai_message = AIMessage(content=response["content"])

            logger.info(
                "llm_node_completed",
                tenant_id=str(tenant_id),
                model=response["model"],
                tokens=response["tokens"]["total"],
                cost=float(response["cost"])
            )

            return {
                **state,
                "messages": state["messages"] + [ai_message],
                "intermediate_results": {
                    **state.get("intermediate_results", {}),
                    "llm_tokens": response["tokens"],
                    "llm_cost": float(response["cost"])
                }
            }

        except Exception as e:
            logger.error(
                "llm_node_error",
                tenant_id=str(tenant_id),
                model=model,
                error=str(e)
            )
            return {
                **state,
                "error": f"LLM completion failed: {str(e)}"
            }

    return llm_node


def create_rag_generator_node(config: Dict[str, Any]) -> Callable:
    """
    Create RAG generation node

    This node generates answers based on retrieved documents.
    It formats the documents as context and includes them in the prompt.

    Config:
        model: Model name (default: "ollama/llama3.2")
        temperature: Temperature 0-1 (default: 0.7)
        max_tokens: Max response tokens (optional)
        provider: Provider hint (optional)
        include_sources: Whether to cite sources (default: True)

    Returns:
        Callable node function (state -> state)
    """
    model = config.get("model", "ollama/llama3.2")
    temperature = config.get("temperature", 0.7)
    max_tokens = config.get("max_tokens")
    provider = config.get("provider")
    include_sources = config.get("include_sources", True)

    async def rag_generator(state: WorkflowState) -> WorkflowState:
        """
        Generate answer from retrieved documents

        Uses documents from state to create context-aware response.
        """
        tenant_id_str = state["metadata"].get("tenant_id")
        tenant_id = UUID(tenant_id_str) if tenant_id_str else None

        if not tenant_id:
            logger.error("rag_generator_missing_tenant_id")
            return {
                **state,
                "error": "Missing tenant_id in metadata"
            }

        # Load tenant LLM config from database
        tenant_llm_config = None
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Tenant).where(Tenant.id == tenant_id)
            )
            tenant = result.scalar_one_or_none()
            if tenant:
                tenant_llm_config = tenant.llm_config or {}

        # Initialize LLM service with tenant config
        llm_service = LiteLLMService(
            tenant_id=tenant_id,
            provider=provider,
            tenant_config=tenant_llm_config
        )

        # Prepare context from retrieved documents
        docs = state.get("documents", [])

        if not docs:
            logger.warning(
                "rag_generator_no_documents",
                tenant_id=str(tenant_id)
            )
            # Fallback to general chat without documents
            # Don't return error, continue with no context

        # Format documents as context
        context_parts = []
        for i, doc in enumerate(docs):
            # Extract content from different possible document structures
            if "payload" in doc:
                content = doc["payload"].get("content", "")
                metadata = doc["payload"].get("metadata", {})
            else:
                content = doc.get("content", "")
                metadata = doc.get("metadata", {})

            source_info = ""
            if include_sources and metadata:
                filename = metadata.get("filename", f"Document {i+1}")
                page = metadata.get("page_number", "")
                if page:
                    source_info = f" (Source: {filename}, Page {page})"
                else:
                    source_info = f" (Source: {filename})"

            context_parts.append(f"Document {i+1}{source_info}:\n{content}")

        context = "\n\n".join(context_parts)

        # Get user query from last message
        query = ""
        for msg in reversed(state.get("messages", [])):
            if isinstance(msg, HumanMessage):
                query = msg.content
                break

        if not query:
            logger.error("rag_generator_no_query", tenant_id=str(tenant_id))
            return {
                **state,
                "error": "No user query found in messages"
            }

        # Create prompt based on whether documents are available
        if docs:
            # RAG prompt with documents
            prompt = f"""Based on the following documents, answer the user's question.
Use only information from the provided documents. If the answer cannot be found in the documents, say so.

Documents:
{context}

Question: {query}

Answer:"""
        else:
            # Fallback to general chat without documents
            prompt = query

        messages = [
            {"role": "user", "content": prompt}
        ]

        try:
            # Generate answer
            response = await llm_service.complete(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )

            answer = response["content"]

            # Add AI message to conversation
            ai_message = AIMessage(content=answer)

            logger.info(
                "rag_generator_completed",
                tenant_id=str(tenant_id),
                model=response["model"],
                documents_count=len(docs),
                tokens=response["tokens"]["total"],
                cost=float(response["cost"])
            )

            return {
                **state,
                "generation": answer,
                "messages": state["messages"] + [ai_message],
                "intermediate_results": {
                    **state.get("intermediate_results", {}),
                    "rag_tokens": response["tokens"],
                    "rag_cost": float(response["cost"]),
                    "documents_used": len(docs)
                }
            }

        except Exception as e:
            logger.error(
                "rag_generator_error",
                tenant_id=str(tenant_id),
                model=model,
                error=str(e)
            )
            return {
                **state,
                "error": f"RAG generation failed: {str(e)}"
            }

    return rag_generator
