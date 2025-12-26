"""
Document management endpoints
"""
from typing import Optional
from uuid import UUID
from fastapi import (
    APIRouter,
    Depends,
    status,
    Query,
    UploadFile,
    File,
    BackgroundTasks,
    HTTPException,
)
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import os
import aiofiles
from datetime import datetime

from app.core.database import get_db
from app.core.config import settings
from app.core.exceptions import (
    NotFoundException,
    ValidationException,
    http_404_not_found,
    http_400_bad_request,
)
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.document import DocumentStatus
from app.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
    DocumentSearchRequest,
    DocumentSearchResponse,
    DocumentUploadResponse,
    DocumentChunkResponse,
    DocumentChunkListResponse,
)
from app.schemas import MessageResponse
from app.services.document_service import DocumentService

logger = structlog.get_logger()

router = APIRouter(prefix="/documents", tags=["Documents"])


# File upload directory
UPLOAD_DIR = "uploads/documents"
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def save_upload_file(upload_file: UploadFile, tenant_id: UUID) -> tuple[str, int]:
    """
    Save uploaded file to disk

    Args:
        upload_file: Uploaded file
        tenant_id: Tenant UUID

    Returns:
        Tuple of (file_path, file_size)
    """
    # Create tenant-specific directory
    tenant_dir = os.path.join(UPLOAD_DIR, str(tenant_id))
    os.makedirs(tenant_dir, exist_ok=True)

    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{upload_file.filename}"
    file_path = os.path.join(tenant_dir, filename)

    # Save file
    file_size = 0
    async with aiofiles.open(file_path, "wb") as f:
        while chunk := await upload_file.read(1024 * 1024):  # 1MB chunks
            await f.write(chunk)
            file_size += len(chunk)

    return file_path, file_size


async def extract_text_from_file(file_path: str, file_type: str) -> str:
    """
    Extract text content from uploaded file

    Args:
        file_path: Path to file
        file_type: MIME type

    Returns:
        Extracted text content

    TODO: Implement proper text extraction for different file types
    - PDF: PyPDF2 or pdfplumber
    - DOCX: python-docx
    - TXT: direct read
    - etc.
    """
    # For now, just handle text files
    if file_type.startswith("text/"):
        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            content = await f.read()
            return content

    # Placeholder for other file types
    return f"[Content extraction not implemented for {file_type}]"


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload document",
    description="Upload a document for processing and semantic search",
)
async def upload_document(
    file: UploadFile = File(..., description="Document file to upload"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a document for processing

    - **file**: Document file (PDF, TXT, DOCX, etc.)

    Flow:
    1. Validate file size and type
    2. Save file to disk
    3. Create document record (status: UPLOADING)
    4. Queue background task for processing
    5. Return document ID immediately

    Background processing:
    - Extract text content
    - Chunk text
    - Generate embeddings
    - Store in vector database
    - Update status to COMPLETED
    """
    try:
        # Validate file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset

        max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        if file_size > max_size:
            raise ValidationException(
                "File too large",
                detail=f"File size exceeds {settings.MAX_FILE_SIZE_MB}MB limit"
            )

        if file_size == 0:
            raise ValidationException(
                "Empty file",
                detail="File is empty"
            )

        # Get MIME type
        file_type = file.content_type or "application/octet-stream"

        # Save file to disk
        file_path, actual_size = await save_upload_file(file, current_user.tenant_id)

        # Extract text content (for now, only text files)
        content = await extract_text_from_file(file_path, file_type)

        # Create document record
        from app.schemas.document import DocumentCreate

        document_data = DocumentCreate(
            filename=file.filename,
            file_path=file_path,
            file_size=actual_size,
            file_type=file_type,
            content=content,
        )

        document = await DocumentService.create_document(
            db=db,
            document_data=document_data,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
        )

        # Queue background task for processing
        background_tasks.add_task(
            process_document_background,
            document_id=document.id,
            tenant_id=current_user.tenant_id,
        )

        logger.info(
            "document_uploaded",
            document_id=str(document.id),
            filename=file.filename,
            tenant_id=str(current_user.tenant_id),
            user_id=str(current_user.id),
        )

        return DocumentUploadResponse(
            document_id=document.id,
            filename=document.filename,
            file_size=document.file_size,
            status=document.status,
        )

    except ValidationException as e:
        raise http_400_bad_request(detail=e.detail or e.message)
    except Exception as e:
        logger.error("document_upload_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document upload failed"
        )


async def process_document_background(document_id: UUID, tenant_id: UUID):
    """
    Background task to process document

    Args:
        document_id: Document UUID
        tenant_id: Tenant UUID
    """
    from app.core.database import async_session_maker

    async with async_session_maker() as db:
        try:
            success = await DocumentService.process_document(
                db=db,
                document_id=document_id,
                tenant_id=tenant_id,
            )

            if success:
                logger.info(
                    "document_processed_background",
                    document_id=str(document_id),
                )
            else:
                logger.error(
                    "document_processing_failed_background",
                    document_id=str(document_id),
                )

        except Exception as e:
            logger.error(
                "document_background_task_error",
                document_id=str(document_id),
                error=str(e),
            )


@router.get(
    "/",
    response_model=DocumentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List documents",
    description="List documents with pagination and filtering",
)
async def list_documents(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum records to return"),
    status_filter: Optional[DocumentStatus] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List documents for current user's tenant

    - **skip**: Pagination offset
    - **limit**: Maximum results per page
    - **status_filter**: Optional status filter

    Returns paginated list with tenant isolation
    """
    result = await DocumentService.list_documents(
        db=db,
        tenant_id=current_user.tenant_id,
        skip=skip,
        limit=limit,
        status=status_filter,
    )

    return DocumentListResponse(**result)


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get document",
    description="Get document by ID with tenant isolation",
)
async def get_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get document by ID

    - **document_id**: Document UUID

    Returns document details with tenant isolation
    """
    document = await DocumentService.get_document(
        db=db,
        document_id=document_id,
        tenant_id=current_user.tenant_id,
    )

    if not document:
        raise http_404_not_found(detail=f"Document {document_id} not found")

    return document


@router.post(
    "/search",
    response_model=DocumentSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search documents",
    description="Semantic search across documents using vector similarity",
)
async def search_documents(
    search_request: DocumentSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Semantic search across documents

    - **query**: Search query text
    - **limit**: Maximum results (1-100)
    - **score_threshold**: Minimum similarity score (0.0-1.0)
    - **filter_metadata**: Optional metadata filters

    Returns ranked results with similarity scores
    """
    try:
        result = await DocumentService.search_documents(
            db=db,
            search_request=search_request,
            tenant_id=current_user.tenant_id,
        )

        return DocumentSearchResponse(**result)

    except ValidationException as e:
        raise http_400_bad_request(detail=e.detail or e.message)


@router.delete(
    "/{document_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete document",
    description="Delete document and all its chunks (DB + vector store)",
)
async def delete_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete document by ID

    - **document_id**: Document UUID

    Deletes:
    - Document record from database
    - All chunk records (cascade)
    - All vectors from Qdrant
    - File from disk (TODO)
    """
    try:
        success = await DocumentService.delete_document(
            db=db,
            document_id=document_id,
            tenant_id=current_user.tenant_id,
        )

        if not success:
            raise http_404_not_found(detail=f"Document {document_id} not found")

        return MessageResponse(
            message="Document deleted successfully",
            detail=f"Document {document_id} and all its chunks have been deleted"
        )

    except NotFoundException as e:
        raise http_404_not_found(detail=e.detail or e.message)


@router.get(
    "/{document_id}/chunks",
    response_model=DocumentChunkListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get document chunks",
    description="Get all chunks for a document",
)
async def get_document_chunks(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all chunks for a document

    - **document_id**: Document UUID

    Returns all chunks with content and metadata
    """
    from sqlalchemy import select, and_
    from app.models.document_chunk import DocumentChunk

    # Verify document exists and belongs to tenant
    document = await DocumentService.get_document(
        db=db,
        document_id=document_id,
        tenant_id=current_user.tenant_id,
    )

    if not document:
        raise http_404_not_found(detail=f"Document {document_id} not found")

    # Get chunks
    result = await db.execute(
        select(DocumentChunk)
        .where(
            and_(
                DocumentChunk.document_id == document_id,
                DocumentChunk.tenant_id == current_user.tenant_id,
            )
        )
        .order_by(DocumentChunk.chunk_index)
    )
    chunks = result.scalars().all()

    return DocumentChunkListResponse(
        items=chunks,
        total=len(chunks),
        document_id=document_id,
    )
