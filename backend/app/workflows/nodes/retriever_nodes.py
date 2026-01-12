"""
Retriever nodes for LangGraph workflows

This module provides node creators for document retrieval and relevance grading operations.
"""
from typing import Dict, Any, Callable
from uuid import UUID
from langchain_core.messages import HumanMessage
import structlog
from sqlalchemy import select

from app.workflows.state import WorkflowState
from app.services.document_service import DocumentService
from app.schemas.document import DocumentSearchRequest
from app.services.litellm_service import LiteLLMService
from app.core.database import AsyncSessionLocal
from app.models.tenant import Tenant

logger = structlog.get_logger()


def create_retriever_node(config: Dict[str, Any]) -> Callable:
    """
    Create retriever node for document search

    Retrieves relevant documents from vector store based on user query.

    Config:
        top_k: Number of documents to retrieve (default: 5)
        score_threshold: Minimum similarity score 0-1 (default: 0.7)
        filter_metadata: Optional metadata filters (default: None)

    Returns:
        Callable node function (state -> state)
    """
    top_k = config.get("top_k", 5)
    score_threshold = config.get("score_threshold", 0.7)
    filter_metadata = config.get("filter_metadata")

    async def retriever_node(state: WorkflowState) -> WorkflowState:
        """
        Retrieve relevant documents from vector store

        Extracts query from last user message and performs semantic search.
        """
        tenant_id_str = state["metadata"].get("tenant_id")
        tenant_id = UUID(tenant_id_str) if tenant_id_str else None

        if not tenant_id:
            logger.error("retriever_node_missing_tenant_id")
            return {
                **state,
                "error": "Missing tenant_id in metadata"
            }

        # Extract query from last user message
        query = ""
        for msg in reversed(state.get("messages", [])):
            if isinstance(msg, HumanMessage):
                query = msg.content
                break

        if not query:
            logger.warning(
                "retriever_node_no_query",
                tenant_id=str(tenant_id)
            )
            return {
                **state,
                "error": "No user query found in messages"
            }

        try:
            # Create search request
            search_request = DocumentSearchRequest(
                query=query,
                limit=top_k,
                score_threshold=score_threshold,
                filter_metadata=filter_metadata
            )

            # Perform search
            async with AsyncSessionLocal() as db:
                search_results = await DocumentService.search_documents(
                    db=db,
                    search_request=search_request,
                    tenant_id=tenant_id
                )

            # Extract results
            results = search_results.get("results", [])

            # Convert to dict format for state
            documents = []
            for result in results:
                documents.append({
                    "id": str(result.chunk_id),
                    "document_id": str(result.document_id),
                    "score": result.score,
                    "payload": {
                        "content": result.content,
                        "filename": result.document_filename,
                        "chunk_index": result.chunk_index,
                        "metadata": result.doc_metadata or {}
                    }
                })

            # Filter by score threshold (double-check)
            filtered_documents = [
                doc for doc in documents
                if doc.get("score", 0) >= score_threshold
            ]

            logger.info(
                "retriever_node_completed",
                tenant_id=str(tenant_id),
                query_length=len(query),
                results_total=len(documents),
                results_filtered=len(filtered_documents),
                search_time_ms=search_results.get("search_time_ms", 0)
            )

            # Update state
            return {
                **state,
                "documents": filtered_documents,
                "context": "\n\n".join([
                    doc["payload"]["content"]
                    for doc in filtered_documents
                ]),
                "intermediate_results": {
                    **state.get("intermediate_results", {}),
                    "retrieval_count": len(filtered_documents),
                    "retrieval_time_ms": search_results.get("search_time_ms", 0)
                }
            }

        except Exception as e:
            logger.error(
                "retriever_node_error",
                tenant_id=str(tenant_id),
                query=query,
                error=str(e)
            )
            return {
                **state,
                "error": f"Document retrieval failed: {str(e)}"
            }

    return retriever_node


def create_relevance_grader_node(config: Dict[str, Any]) -> Callable:
    """
    Create relevance grading node

    Grades each retrieved document for relevance to the query using an LLM.
    Filters out non-relevant documents.

    Config:
        model: Model to use for grading (default: "ollama/llama3.2")
        provider: Provider hint (optional)

    Returns:
        Callable node function (state -> state)
    """
    model = config.get("model", "ollama/llama3.2")
    provider = config.get("provider")

    async def grader_node(state: WorkflowState) -> WorkflowState:
        """
        Grade retrieved documents for relevance

        Uses LLM to determine if each document is relevant to the query.
        """
        tenant_id_str = state["metadata"].get("tenant_id")
        tenant_id = UUID(tenant_id_str) if tenant_id_str else None

        if not tenant_id:
            logger.error("grader_node_missing_tenant_id")
            return {
                **state,
                "error": "Missing tenant_id in metadata"
            }

        # Get query and documents
        query = ""
        for msg in reversed(state.get("messages", [])):
            if isinstance(msg, HumanMessage):
                query = msg.content
                break

        documents = state.get("documents", [])

        if not documents:
            logger.warning(
                "grader_node_no_documents",
                tenant_id=str(tenant_id)
            )
            return state  # No documents to grade, pass through

        if not query:
            logger.warning(
                "grader_node_no_query",
                tenant_id=str(tenant_id)
            )
            return state  # No query, pass through

        try:
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

            graded_docs = []
            relevance_scores = []

            for doc in documents:
                content = doc["payload"]["content"]

                # Create grading prompt
                prompt = f"""Grade the relevance of this document to the query.

Query: {query}

Document: {content[:500]}...

Is this document relevant to answering the query? Answer with just 'yes' or 'no'."""

                messages = [{"role": "user", "content": prompt}]

                # Get LLM response
                response = await llm_service.complete(
                    messages=messages,
                    model=model,
                    temperature=0,  # Use deterministic grading
                    max_tokens=10
                )

                relevance = response["content"].strip().lower()

                # Keep document if relevant
                if "yes" in relevance:
                    graded_docs.append(doc)
                    relevance_scores.append(doc.get("score", 0))

            logger.info(
                "grader_node_completed",
                tenant_id=str(tenant_id),
                documents_total=len(documents),
                documents_relevant=len(graded_docs),
                model=model
            )

            return {
                **state,
                "documents": graded_docs,
                "relevance_scores": relevance_scores,
                "context": "\n\n".join([
                    doc["payload"]["content"]
                    for doc in graded_docs
                ]),
                "intermediate_results": {
                    **state.get("intermediate_results", {}),
                    "graded_documents": len(graded_docs),
                    "grading_model": model
                }
            }

        except Exception as e:
            logger.error(
                "grader_node_error",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            # On error, return original documents (fail gracefully)
            return state

    return grader_node
