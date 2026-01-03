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
    max_length: int = 500
):
    """
    Background task to run document summarization

    This runs independently of the HTTP request/response cycle,
    allowing long-running LLM operations without timeout.
    """
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            service = DocumentRAGService(db, tenant_id, user_id)

            logger.info(
                "background_summarize_started",
                operation_id=str(operation_id),
                document_id=str(document_id)
            )

            # Run the actual summarization
            result = await service.summarize_document(
                document_id=document_id,
                model=model,
                max_length=max_length
            )

            logger.info(
                "background_summarize_completed",
                operation_id=str(operation_id),
                tokens=result.get("tokens_used", 0)
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
                from datetime import datetime
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
            max_length=request.max_length
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


@router.post("/documents/ask", response_model=DocumentAskResponse)
async def ask_document_question(
    request: DocumentAskRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Ask a question about a document

    Uses RAG to answer questions based on document content
    """
    service = DocumentRAGService(db, current_user.tenant_id, current_user.id)

    try:
        result = await service.ask_question(
            document_id=request.document_id,
            question=request.question,
            model=request.model,
            max_chunks=request.max_chunks
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("ask_endpoint_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to answer question: {str(e)}")


@router.post("/documents/transform", response_model=DocumentTransformResponse)
async def transform_document(
    request: DocumentTransformRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Transform document content

    Apply transformations like translation, formatting, etc.
    """
    service = DocumentRAGService(db, current_user.tenant_id, current_user.id)

    try:
        result = await service.transform_document(
            document_id=request.document_id,
            instruction=request.instruction,
            model=request.model,
            output_format=request.output_format
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("transform_endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to transform document")


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
