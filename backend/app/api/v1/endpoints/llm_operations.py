from fastapi import APIRouter, Depends, HTTPException, status
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
    DocumentAskRequest,
    DocumentAskResponse,
    DocumentTransformRequest,
    DocumentTransformResponse,
    LLMOperationResponse
)
from app.models.llm_operation import LLMOperation
from sqlalchemy import select
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/llm", tags=["LLM Operations"])


@router.post("/documents/summarize", response_model=DocumentSummarizeResponse)
async def summarize_document(
    request: DocumentSummarizeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Summarize a document

    Generate a concise summary of the document using LLM
    """
    service = DocumentRAGService(db, current_user.tenant_id, current_user.id)

    try:
        result = await service.summarize_document(
            document_id=request.document_id,
            model=request.model,
            max_length=request.max_length
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("summarize_endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to summarize document")


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
        logger.error("ask_endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to answer question")


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
