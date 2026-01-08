from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.models.user import User
from app.api.dependencies import get_current_active_user
from app.services.document_rag_service import DocumentRAGService
from app.schemas.llm import (
    DocumentSummarizeRequest,
    DocumentSummarizeResponse,
    DocumentOperationStartResponse,
    DocumentAskRequest,
    DocumentAskResponse,
    DocumentTransformRequest,
    DocumentTransformResponse,
    LLMOperationResponse
)
from app.models.llm_operation import LLMOperation
from sqlalchemy import select
import structlog
import asyncio

logger = structlog.get_logger()
router = APIRouter(prefix="/llm", tags=["LLM Operations"])


# Background task functions
async def _run_summarize_task(
    operation_id: UUID,
    document_id: UUID,
    tenant_id: UUID,
    user_id: UUID,
    model: str = None,
    max_length: int = 500,
    force: bool = False
):
    """
    Background task to run document summarization

    This runs independently of the HTTP request/response cycle,
    allowing long-running LLM operations without timeout.
    """
    from app.core.database import AsyncSessionLocal
    from datetime import datetime

    async with AsyncSessionLocal() as db:
        try:
            # Get the operation record
            operation = await db.get(LLMOperation, operation_id)
            if not operation:
                logger.error("operation_not_found", operation_id=str(operation_id))
                return

            # Check if there's already a completed summary (unless force=True)
            if not force:
                from sqlalchemy import select
                stmt = select(LLMOperation).where(
                    LLMOperation.document_id == document_id,
                    LLMOperation.tenant_id == tenant_id,
                    LLMOperation.operation_type == "summarize",
                    LLMOperation.status == "completed",
                    LLMOperation.id != operation_id  # Exclude current operation
                ).order_by(LLMOperation.completed_at.desc()).limit(1)

                result = await db.execute(stmt)
                existing_summary = result.scalar_one_or_none()

                if existing_summary:
                    # Use existing summary
                    operation.output_data = existing_summary.output_data
                    operation.model_used = existing_summary.model_used
                    operation.tokens_used = existing_summary.tokens_used
                    operation.cost_estimate = existing_summary.cost_estimate
                    operation.status = "completed"
                    operation.completed_at = datetime.utcnow()
                    await db.commit()

                    logger.info(
                        "background_summarize_cached",
                        operation_id=str(operation_id),
                        cached_from=str(existing_summary.id)
                    )
                    return

            service = DocumentRAGService(db, tenant_id, user_id)

            logger.info(
                "background_summarize_started",
                operation_id=str(operation_id),
                document_id=str(document_id)
            )

            # Get document and chunks
            from app.models.document import Document
            from app.models.document_chunk import DocumentChunk

            document = await db.get(Document, document_id)
            if not document:
                raise ValueError(f"Document {document_id} not found")

            stmt = select(DocumentChunk).where(
                DocumentChunk.document_id == document_id
            ).order_by(DocumentChunk.chunk_index)
            result = await db.execute(stmt)
            chunks = result.scalars().all()

            full_content = "\n\n".join([chunk.content for chunk in chunks])

            # Limit content length
            max_content_chars = 8000
            if len(full_content) > max_content_chars:
                full_content = full_content[:max_content_chars] + "\n\n[Content truncated for performance...]"

            # Initialize LLM service
            await service._initialize_llm_service()
            llm_config = await service._get_tenant_llm_config()

            if model is None:
                model = llm_config["model"]

            if llm_config["provider"] == "ollama" and not model.startswith("ollama/"):
                model = f"ollama/{model}"

            # Create prompt
            messages = [
                {
                    "role": "system",
                    "content": f"You are a document summarization expert. Summarize the following document concisely in MAXIMUM {max_length} words. The summary should be significantly shorter than the original text. Focus only on the main points and key information."
                },
                {
                    "role": "user",
                    "content": f"Document: {document.filename}\n\nContent:\n{full_content}"
                }
            ]

            # Generate summary
            max_tokens_limit = int(max_length * 1.5)
            llm_result = await service.llm_service.complete(
                messages=messages,
                model=model,
                temperature=0.3,
                max_tokens=max_tokens_limit
            )

            # Update operation
            operation.output_data = {"summary": llm_result["content"]}
            operation.model_used = llm_result["model"]
            operation.tokens_used = llm_result["tokens"]["total"]
            operation.cost_estimate = llm_result["cost"]
            operation.status = "completed"
            operation.completed_at = datetime.utcnow()
            await db.commit()

            logger.info(
                "background_summarize_completed",
                operation_id=str(operation_id),
                tokens=llm_result["tokens"]["total"]
            )

        except Exception as e:
            logger.error(
                "background_summarize_error",
                operation_id=str(operation_id),
                error=str(e),
                exc_info=True
            )

            # Update operation status to failed
            operation = await db.get(LLMOperation, operation_id)
            if operation:
                operation.status = "failed"
                operation.error_message = str(e)
                operation.completed_at = datetime.utcnow()
                await db.commit()


@router.post("/documents/summarize", response_model=DocumentOperationStartResponse)
async def summarize_document(
    request: DocumentSummarizeRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Summarize a document (Async)

    Starts a background task to summarize the document.
    Returns immediately with operation_id.
    Use GET /operations/{operation_id} to check status and get results.

    TODO (V0.4): Add streaming support with SSE for real-time token delivery
    """
    service = DocumentRAGService(db, current_user.tenant_id, current_user.id)

    try:
        # Create operation record immediately
        from app.models.llm_operation import LLMOperation
        from app.models.tenant import Tenant

        # Get tenant config for model
        tenant = await db.get(Tenant, current_user.tenant_id)
        llm_config = tenant.llm_config if tenant else {}
        model = request.model or llm_config.get("model", "llama3.2")

        # Add provider prefix if needed
        if tenant and tenant.llm_provider == "ollama" and not model.startswith("ollama/"):
            model = f"ollama/{model}"

        operation = LLMOperation(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            document_id=request.document_id,
            operation_type="summarize",
            input_data={"model": model, "max_length": request.max_length},
            status="processing"
        )
        db.add(operation)
        await db.commit()
        await db.refresh(operation)

        # Start background task
        background_tasks.add_task(
            _run_summarize_task,
            operation_id=operation.id,
            document_id=request.document_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            model=request.model,
            max_length=request.max_length,
            force=request.force
        )

        logger.info(
            "summarize_operation_started",
            operation_id=str(operation.id),
            document_id=str(request.document_id),
            tenant_id=str(current_user.tenant_id)
        )

        return DocumentOperationStartResponse(
            operation_id=operation.id,
            status="processing",
            message="Summary generation started. Use GET /operations/{operation_id} to check status."
        )

    except Exception as e:
        logger.error("summarize_start_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start summarize operation: {str(e)}")


async def _run_ask_task(
    operation_id: UUID,
    document_id: UUID,
    tenant_id: UUID,
    user_id: UUID,
    question: str,
    model: str = None,
    max_chunks: int = 5
):
    """Background task to run document Q&A"""
    from app.core.database import AsyncSessionLocal
    from datetime import datetime

    async with AsyncSessionLocal() as db:
        try:
            operation = await db.get(LLMOperation, operation_id)
            if not operation:
                logger.error("operation_not_found", operation_id=str(operation_id))
                return

            service = DocumentRAGService(db, tenant_id, user_id)

            logger.info(
                "background_ask_started",
                operation_id=str(operation_id),
                document_id=str(document_id)
            )

            # Get document
            from app.models.document import Document
            from app.models.tenant import Tenant
            from app.services.embedding_providers import create_provider_from_tenant_config
            from app.core.config import settings

            document = await db.get(Document, document_id)
            if not document:
                raise ValueError(f"Document {document_id} not found")

            # Get tenant's embedding provider configuration
            tenant = await db.get(Tenant, tenant_id)
            if not tenant:
                raise ValueError(f"Tenant {tenant_id} not found")

            provider_config = tenant.embedding_config or {
                "provider": "openai",
                "model": "text-embedding-3-small",
            }

            # Get fallback API key from settings if using OpenAI
            fallback_api_key = None
            if tenant.embedding_provider == "openai":
                fallback_api_key = settings.OPENAI_API_KEY

            # Create provider instance from tenant configuration
            provider = await create_provider_from_tenant_config(
                tenant_config=provider_config,
                fallback_api_key=fallback_api_key,
            )

            # Generate embedding for question
            question_embeddings = await provider.generate_embeddings_batch(
                texts=[question],
            )

            if not question_embeddings or not question_embeddings[0]:
                raise ValueError("Failed to generate embedding for question")

            question_embedding = question_embeddings[0]

            # Vector search for relevant chunks using Qdrant
            from app.core.qdrant_client import qdrant_store

            search_results = await qdrant_store.search(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                query_vector=question_embedding,
                tenant_id=str(tenant_id),
                limit=max_chunks,
                filter_conditions={"document_id": str(document_id)}
            )

            # Prepare context
            context_chunks = []
            sources = []

            for i, result in enumerate(search_results):
                chunk_content = result["payload"]["content"]
                chunk_num = result["payload"].get("chunk_index", i)
                score = result.get("score", 0)

                context_chunks.append(f"[Chunk {chunk_num}]:\n{chunk_content}")
                sources.append({
                    "chunk_index": chunk_num,
                    "score": float(score),
                    "content_preview": chunk_content[:200] + "..."
                })

            context = "\n\n".join(context_chunks)

            # Initialize LLM service
            await service._initialize_llm_service()
            llm_config = await service._get_tenant_llm_config()

            if model is None:
                model = llm_config["model"]

            if llm_config["provider"] == "ollama" and not model.startswith("ollama/"):
                model = f"ollama/{model}"

            # Create prompt
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant. Answer the user's question based on the provided document context. If the answer is not in the context, say so."
                },
                {
                    "role": "user",
                    "content": f"Document: {document.filename}\n\nContext:\n{context}\n\nQuestion: {question}\n\nAnswer:"
                }
            ]

            # Generate answer
            llm_result = await service.llm_service.complete(
                messages=messages,
                model=model,
                temperature=0.7
            )

            # Update operation
            operation.output_data = {
                "answer": llm_result["content"],
                "sources": sources
            }
            operation.model_used = llm_result["model"]
            operation.tokens_used = llm_result["tokens"]["total"]
            operation.cost_estimate = llm_result["cost"]
            operation.status = "completed"
            operation.completed_at = datetime.utcnow()
            await db.commit()

            logger.info(
                "background_ask_completed",
                operation_id=str(operation_id),
                tokens=llm_result["tokens"]["total"]
            )

        except Exception as e:
            logger.error(
                "background_ask_error",
                operation_id=str(operation_id),
                error=str(e),
                exc_info=True
            )

            operation = await db.get(LLMOperation, operation_id)
            if operation:
                operation.status = "failed"
                operation.error_message = str(e)
                operation.completed_at = datetime.utcnow()
                await db.commit()


@router.post("/documents/ask", response_model=DocumentOperationStartResponse)
async def ask_document_question(
    request: DocumentAskRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Ask a question about a document (Async)

    Starts a background task to answer the question using RAG.
    Returns immediately with operation_id.
    Use GET /operations/{operation_id} to check status and get results.
    """
    try:
        # Get tenant config for model
        from app.models.tenant import Tenant

        tenant = await db.get(Tenant, current_user.tenant_id)
        llm_config = tenant.llm_config if tenant else {}
        model = request.model or llm_config.get("model", "llama3.2")

        # Add provider prefix if needed
        if tenant and tenant.llm_provider == "ollama" and not model.startswith("ollama/"):
            model = f"ollama/{model}"

        operation = LLMOperation(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            document_id=request.document_id,
            operation_type="ask",
            input_data={
                "question": request.question,
                "model": model,
                "max_chunks": request.max_chunks
            },
            status="processing"
        )
        db.add(operation)
        await db.commit()
        await db.refresh(operation)

        # Start background task
        background_tasks.add_task(
            _run_ask_task,
            operation_id=operation.id,
            document_id=request.document_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            question=request.question,
            model=request.model,
            max_chunks=request.max_chunks
        )

        logger.info(
            "ask_operation_started",
            operation_id=str(operation.id),
            document_id=str(request.document_id)
        )

        return DocumentOperationStartResponse(
            operation_id=operation.id,
            status="processing",
            message="Question answering started. Use GET /operations/{operation_id} to check status."
        )

    except Exception as e:
        logger.error("ask_start_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start ask operation: {str(e)}")


async def _run_transform_task(
    operation_id: UUID,
    document_id: UUID,
    tenant_id: UUID,
    user_id: UUID,
    instruction: str,
    model: str = None,
    output_format: str = "text"
):
    """Background task to run document transformation"""
    from app.core.database import AsyncSessionLocal
    from datetime import datetime

    async with AsyncSessionLocal() as db:
        try:
            operation = await db.get(LLMOperation, operation_id)
            if not operation:
                logger.error("operation_not_found", operation_id=str(operation_id))
                return

            service = DocumentRAGService(db, tenant_id, user_id)

            logger.info(
                "background_transform_started",
                operation_id=str(operation_id),
                document_id=str(document_id)
            )

            # Get document and chunks
            from app.models.document import Document
            from app.models.document_chunk import DocumentChunk

            document = await db.get(Document, document_id)
            if not document:
                raise ValueError(f"Document {document_id} not found")

            stmt = select(DocumentChunk).where(
                DocumentChunk.document_id == document_id
            ).order_by(DocumentChunk.chunk_index)
            result = await db.execute(stmt)
            chunks = result.scalars().all()

            full_content = "\n\n".join([chunk.content for chunk in chunks])

            # Initialize LLM service
            await service._initialize_llm_service()
            llm_config = await service._get_tenant_llm_config()

            if model is None:
                model = llm_config["model"]

            if llm_config["provider"] == "ollama" and not model.startswith("ollama/"):
                model = f"ollama/{model}"

            # Create prompt
            format_instruction = ""
            if output_format == "markdown":
                format_instruction = " Format the output as Markdown."
            elif output_format == "json":
                format_instruction = " Format the output as JSON."

            messages = [
                {
                    "role": "system",
                    "content": f"You are a document transformation assistant. Follow the user's instruction to transform the document.{format_instruction}"
                },
                {
                    "role": "user",
                    "content": f"Document: {document.filename}\n\nContent:\n{full_content}\n\nInstruction: {instruction}"
                }
            ]

            # Generate transformation
            llm_result = await service.llm_service.complete(
                messages=messages,
                model=model,
                temperature=0.5
            )

            # Update operation
            operation.output_data = {
                "transformed_content": llm_result["content"],
                "output_format": output_format
            }
            operation.model_used = llm_result["model"]
            operation.tokens_used = llm_result["tokens"]["total"]
            operation.cost_estimate = llm_result["cost"]
            operation.status = "completed"
            operation.completed_at = datetime.utcnow()
            await db.commit()

            logger.info(
                "background_transform_completed",
                operation_id=str(operation_id),
                tokens=llm_result["tokens"]["total"]
            )

        except Exception as e:
            logger.error(
                "background_transform_error",
                operation_id=str(operation_id),
                error=str(e),
                exc_info=True
            )

            operation = await db.get(LLMOperation, operation_id)
            if operation:
                operation.status = "failed"
                operation.error_message = str(e)
                operation.completed_at = datetime.utcnow()
                await db.commit()


@router.post("/documents/transform", response_model=DocumentOperationStartResponse)
async def transform_document(
    request: DocumentTransformRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Transform document content (Async)

    Starts a background task to transform the document.
    Returns immediately with operation_id.
    Use GET /operations/{operation_id} to check status and get results.
    """
    try:
        # Get tenant config for model
        from app.models.tenant import Tenant

        tenant = await db.get(Tenant, current_user.tenant_id)
        llm_config = tenant.llm_config if tenant else {}
        model = request.model or llm_config.get("model", "llama3.2")

        # Add provider prefix if needed
        if tenant and tenant.llm_provider == "ollama" and not model.startswith("ollama/"):
            model = f"ollama/{model}"

        operation = LLMOperation(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            document_id=request.document_id,
            operation_type="transform",
            input_data={
                "instruction": request.instruction,
                "model": model,
                "output_format": request.output_format
            },
            status="processing"
        )
        db.add(operation)
        await db.commit()
        await db.refresh(operation)

        # Start background task
        background_tasks.add_task(
            _run_transform_task,
            operation_id=operation.id,
            document_id=request.document_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            instruction=request.instruction,
            model=request.model,
            output_format=request.output_format
        )

        logger.info(
            "transform_operation_started",
            operation_id=str(operation.id),
            document_id=str(request.document_id)
        )

        return DocumentOperationStartResponse(
            operation_id=operation.id,
            status="processing",
            message="Transform operation started. Use GET /operations/{operation_id} to check status."
        )

    except Exception as e:
        logger.error("transform_start_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start transform operation: {str(e)}")


@router.get("/operations", response_model=List[LLMOperationResponse])
async def list_operations(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all LLM operations for current user

    Returns history of summarize, ask, transform operations
    """
    stmt = select(LLMOperation).where(
        LLMOperation.tenant_id == current_user.tenant_id
    ).order_by(
        LLMOperation.created_at.desc()
    ).offset(skip).limit(limit)

    result = await db.execute(stmt)
    operations = result.scalars().all()

    return operations


@router.get("/operations/{operation_id}", response_model=LLMOperationResponse)
async def get_operation(
    operation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific operation details"""
    stmt = select(LLMOperation).where(
        LLMOperation.id == operation_id,
        LLMOperation.tenant_id == current_user.tenant_id
    )

    result = await db.execute(stmt)
    operation = result.scalar_one_or_none()

    if not operation:
        raise HTTPException(status_code=404, detail="Operation not found")

    return operation


@router.get("/documents/{document_id}/summarize/latest", response_model=LLMOperationResponse)
async def get_latest_summary(
    document_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the latest completed summary for a document

    Returns 404 if no completed summary exists for this document
    """
    stmt = select(LLMOperation).where(
        LLMOperation.document_id == document_id,
        LLMOperation.tenant_id == current_user.tenant_id,
        LLMOperation.operation_type == "summarize",
        LLMOperation.status == "completed"
    ).order_by(LLMOperation.completed_at.desc()).limit(1)

    result = await db.execute(stmt)
    operation = result.scalar_one_or_none()

    if not operation:
        raise HTTPException(
            status_code=404,
            detail="No completed summary found for this document"
        )

    return operation
