"""
Document service - CRUD and processing operations for documents
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.exc import IntegrityError
import structlog
import time

from app.core.exceptions import (
    NotFoundException,
    ValidationException,
)
from app.core.config import settings
from app.core.qdrant_client import qdrant_store
from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.schemas.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentSearchRequest,
    SearchResult,
)
from app.services.embedding_service import embedding_service
from app.services.embedding_providers import create_provider_from_tenant_config, ProviderType
from app.models.tenant import Tenant

logger = structlog.get_logger()


class DocumentService:
    """
    Document service for CRUD and processing operations

    Features:
    - Multi-layer tenant isolation (RLS + App layer)
    - Document chunking and embedding
    - Vector store integration (Qdrant)
    - Semantic search
    """

    @staticmethod
    async def create_document(
        db: AsyncSession,
        document_data: DocumentCreate,
        tenant_id: UUID,
        user_id: UUID,
    ) -> Document:
        """
        Create a new document

        Args:
            db: Database session
            document_data: Document creation data
            tenant_id: Tenant UUID
            user_id: User UUID (uploader)

        Returns:
            Created document

        Raises:
            ValidationException: If validation fails
        """
        try:
            # Create document
            document = Document(
                tenant_id=tenant_id,
                user_id=user_id,
                filename=document_data.filename,
                file_path=document_data.file_path,
                file_size=document_data.file_size,
                file_type=document_data.file_type,
                status=DocumentStatus.UPLOADING,
                content=document_data.content,
                doc_metadata=document_data.doc_metadata,
            )

            db.add(document)
            await db.commit()
            await db.refresh(document)

            logger.info(
                "document_created",
                document_id=str(document.id),
                filename=document.filename,
                tenant_id=str(tenant_id),
                user_id=str(user_id),
            )

            return document

        except IntegrityError as e:
            await db.rollback()
            logger.error("document_creation_failed", error=str(e))
            raise ValidationException(
                "Document creation failed",
                detail="Database constraint violation"
            )

    @staticmethod
    async def process_document(
        db: AsyncSession,
        document_id: UUID,
        tenant_id: UUID,
    ) -> bool:
        """
        Process document: chunk text, generate embeddings, store in vector DB

        Args:
            db: Database session
            document_id: Document UUID
            tenant_id: Tenant UUID

        Returns:
            True if successful

        Raises:
            NotFoundException: If document not found
        """
        try:
            # Get document with tenant isolation
            result = await db.execute(
                select(Document).where(
                    and_(
                        Document.id == document_id,
                        Document.tenant_id == tenant_id,
                    )
                )
            )
            document = result.scalar_one_or_none()

            if not document:
                raise NotFoundException(
                    "Document not found",
                    detail=f"Document {document_id} not found for tenant {tenant_id}"
                )

            # Update status to processing
            document.status = DocumentStatus.PROCESSING
            await db.commit()

            # Extract text content (should be populated during upload)
            if not document.content:
                raise ValidationException(
                    "No content to process",
                    detail="Document content is empty"
                )

            # Chunk the text
            chunks = embedding_service.chunk_text(document.content)

            if not chunks:
                raise ValidationException(
                    "Chunking failed",
                    detail="No chunks generated from document content"
                )

            # Get tenant's embedding provider configuration
            tenant = await db.get(Tenant, tenant_id)
            if not tenant:
                raise NotFoundException(
                    "Tenant not found",
                    detail=f"Tenant {tenant_id} not found"
                )

            # Try to generate embeddings for all chunks (batch)
            # NOTE: Embeddings are optional - documents can be uploaded without them
            chunk_texts = [chunk["content"] for chunk in chunks]
            embeddings = []
            try:
                # Create provider instance from tenant configuration
                provider_config = tenant.embedding_config or {
                    "provider": "openai",
                    "model": "text-embedding-3-small",
                }

                # Get fallback API key from settings if using OpenAI
                fallback_api_key = None
                if tenant.embedding_provider == "openai":
                    fallback_api_key = settings.OPENAI_API_KEY

                provider = await create_provider_from_tenant_config(
                    tenant_config=provider_config,
                    fallback_api_key=fallback_api_key,
                )

                # Generate embeddings using the configured provider
                embeddings = await provider.generate_embeddings_batch(
                    texts=chunk_texts,
                )

                logger.info(
                    "embeddings_generated_with_provider",
                    document_id=str(document_id),
                    provider=tenant.embedding_provider,
                    model=provider_config.get("model"),
                    chunk_count=len(chunk_texts),
                    embedding_dim=len(embeddings[0]) if embeddings and embeddings[0] else 0,
                )

            except Exception as emb_error:
                logger.warning(
                    "embedding_generation_skipped",
                    document_id=str(document_id),
                    provider=tenant.embedding_provider,
                    error=str(emb_error),
                    message="Document will be saved without embeddings (search will be disabled)",
                )

            # Create DocumentChunk records and prepare for Qdrant
            qdrant_points = []
            db_chunks = []

            for i, chunk in enumerate(chunks):
                # Get embedding if available
                embedding = embeddings[i] if i < len(embeddings) and embeddings[i] is not None else None

                if embedding is None:
                    logger.info(
                        "chunk_saved_without_embedding",
                        document_id=str(document_id),
                        chunk_index=chunk["chunk_index"],
                    )

                # Create database record (embedding can be None)
                db_chunk = DocumentChunk(
                    document_id=document.id,
                    tenant_id=tenant_id,
                    chunk_index=chunk["chunk_index"],
                    content=chunk["content"],
                    token_count=chunk["token_count"],
                    embedding=embedding,  # Can be None
                    start_char=chunk["start_char"],
                    end_char=chunk["end_char"],
                    chunk_metadata={"source": "document_processing", "has_embedding": embedding is not None},
                )
                db_chunks.append(db_chunk)

                # Only add to Qdrant if embedding exists
                if embedding is not None:
                    qdrant_points.append({
                        "id": str(db_chunk.id),  # Will be set after DB insert
                        "vector": embedding,
                        "payload": {
                            "document_id": str(document.id),
                            "chunk_index": chunk["chunk_index"],
                            "content": chunk["content"],
                            "filename": document.filename,
                            "doc_metadata": document.doc_metadata,
                        }
                    })

            # Save chunks to database
            db.add_all(db_chunks)
            await db.commit()

            # Refresh to get IDs
            for db_chunk in db_chunks:
                await db.refresh(db_chunk)

            # Update Qdrant point IDs and upsert if we have any embeddings
            if qdrant_points:
                for i, db_chunk in enumerate([c for c in db_chunks if c.embedding is not None]):
                    qdrant_points[i]["id"] = str(db_chunk.id)

                # Upsert to Qdrant
                success = await qdrant_store.upsert_points(
                    collection_name=settings.QDRANT_COLLECTION_NAME,
                    points=qdrant_points,
                    tenant_id=str(tenant_id),
                )

                if not success:
                    logger.warning(
                        "qdrant_upsert_failed_document_saved_anyway",
                        document_id=str(document_id),
                    )
            else:
                logger.info(
                    "document_saved_without_vector_search",
                    document_id=str(document_id),
                    message="No embeddings generated - vector search will not work for this document",
                )

            # Generate document-level embedding if available
            if embeddings and len(embeddings) > 0 and embeddings[0]:
                document.embedding = embeddings[0]

            # Update document status
            document.status = DocumentStatus.COMPLETED
            document.chunk_count = len(db_chunks)
            await db.commit()

            logger.info(
                "document_processed_successfully",
                document_id=str(document_id),
                chunk_count=len(db_chunks),
                tenant_id=str(tenant_id),
            )

            return True

        except Exception as e:
            # Mark document as failed
            try:
                await db.rollback()  # Rollback any pending transaction
                result = await db.execute(
                    select(Document).where(
                        and_(
                            Document.id == document_id,
                            Document.tenant_id == tenant_id,
                        )
                    )
                )
                doc = result.scalar_one_or_none()

                if doc:
                    doc.status = DocumentStatus.FAILED
                    doc.error_message = str(e)
                    await db.commit()
            except Exception as update_error:
                logger.error(
                    "failed_to_update_document_status",
                    document_id=str(document_id),
                    error=str(update_error),
                )

            logger.error(
                "document_processing_failed",
                document_id=str(document_id),
                error=str(e),
            )

            return False

    @staticmethod
    async def search_documents(
        db: AsyncSession,
        search_request: DocumentSearchRequest,
        tenant_id: UUID,
    ) -> Dict[str, Any]:
        """
        Semantic search across documents

        Args:
            db: Database session
            search_request: Search parameters
            tenant_id: Tenant UUID

        Returns:
            Search results with metadata
        """
        start_time = time.time()

        try:
            # Generate embedding for query
            query_embedding = await embedding_service.generate_embedding(
                text=search_request.query,
                tenant_id=str(tenant_id),
            )

            if not query_embedding:
                raise ValidationException(
                    "Query embedding generation failed",
                    detail="Failed to generate embedding for search query"
                )

            # Search in Qdrant
            qdrant_results = await qdrant_store.search(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                query_vector=query_embedding,
                tenant_id=str(tenant_id),
                limit=search_request.limit,
                score_threshold=search_request.score_threshold,
                filter_conditions=search_request.filter_metadata,
            )

            # Format results
            search_results = []
            for hit in qdrant_results:
                payload = hit["payload"]
                search_results.append(
                    SearchResult(
                        chunk_id=UUID(hit["id"]),
                        document_id=UUID(payload["document_id"]),
                        document_filename=payload["filename"],
                        content=payload["content"],
                        score=hit["score"],
                        chunk_index=payload["chunk_index"],
                        chunk_metadata=None,
                        doc_metadata=payload.get("doc_metadata"),
                    )
                )

            elapsed_time = (time.time() - start_time) * 1000  # milliseconds

            logger.info(
                "document_search_completed",
                query=search_request.query,
                tenant_id=str(tenant_id),
                result_count=len(search_results),
                search_time_ms=elapsed_time,
            )

            return {
                "query": search_request.query,
                "results": search_results,
                "total_results": len(search_results),
                "search_time_ms": elapsed_time,
            }

        except Exception as e:
            logger.error(
                "document_search_failed",
                query=search_request.query,
                tenant_id=str(tenant_id),
                error=str(e),
            )
            raise ValidationException(
                "Search failed",
                detail=str(e)
            )

    @staticmethod
    async def get_document(
        db: AsyncSession,
        document_id: UUID,
        tenant_id: UUID,
    ) -> Optional[Document]:
        """
        Get document by ID with tenant isolation

        Args:
            db: Database session
            document_id: Document UUID
            tenant_id: Tenant UUID

        Returns:
            Document or None
        """
        result = await db.execute(
            select(Document).where(
                and_(
                    Document.id == document_id,
                    Document.tenant_id == tenant_id,
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_documents(
        db: AsyncSession,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 20,
        status: Optional[DocumentStatus] = None,
    ) -> Dict[str, Any]:
        """
        List documents for tenant with pagination

        Args:
            db: Database session
            tenant_id: Tenant UUID
            skip: Number of records to skip
            limit: Maximum records to return
            status: Optional status filter

        Returns:
            Paginated document list
        """
        # Build query
        query = select(Document).where(Document.tenant_id == tenant_id)

        if status:
            query = query.where(Document.status == status)

        # Get total count
        count_query = select(func.count()).select_from(Document).where(
            Document.tenant_id == tenant_id
        )
        if status:
            count_query = count_query.where(Document.status == status)

        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # Get paginated results
        query = query.order_by(Document.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        documents = result.scalars().all()

        return {
            "items": documents,
            "total": total,
            "page": (skip // limit) + 1,
            "page_size": limit,
        }

    @staticmethod
    async def delete_document(
        db: AsyncSession,
        document_id: UUID,
        tenant_id: UUID,
    ) -> bool:
        """
        Delete document and its chunks (both DB and vector store)

        Args:
            db: Database session
            document_id: Document UUID
            tenant_id: Tenant UUID

        Returns:
            True if successful

        Raises:
            NotFoundException: If document not found
        """
        # Get document
        document = await DocumentService.get_document(db, document_id, tenant_id)

        if not document:
            raise NotFoundException(
                "Document not found",
                detail=f"Document {document_id} not found"
            )

        try:
            # Delete from Qdrant (all chunks of this document)
            await qdrant_store.delete_by_filter(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                tenant_id=str(tenant_id),
                document_id=str(document_id),
            )

            # Delete from database (cascades to chunks)
            await db.delete(document)
            await db.commit()

            logger.info(
                "document_deleted",
                document_id=str(document_id),
                tenant_id=str(tenant_id),
            )

            return True

        except Exception as e:
            await db.rollback()
            logger.error(
                "document_deletion_failed",
                document_id=str(document_id),
                error=str(e),
            )
            return False
