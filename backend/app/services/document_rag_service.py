from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.llm_operation import LLMOperation
from app.models.tenant import Tenant
from app.services.litellm_service import LiteLLMService
from app.services.embedding_service import EmbeddingService
from app.core.qdrant_client import qdrant_store
from app.core.config import settings

logger = structlog.get_logger()


class DocumentRAGService:
    """
    Simple RAG operations for documents (Version 0.3)

    Provides: Summarize, Ask, Transform
    """

    def __init__(self, db: AsyncSession, tenant_id: UUID, user_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.llm_service = None  # Will be initialized with provider info
        self.embedding_service = EmbeddingService()

    async def _get_tenant_llm_config(self) -> Dict[str, Any]:
        """Get tenant's LLM provider configuration"""
        tenant = await self.db.get(Tenant, self.tenant_id)
        if not tenant:
            # Default to ollama if tenant not found
            return {
                "provider": "ollama",
                "model": "llama3.2",
                "base_url": "http://localhost:11434"
            }

        provider = tenant.llm_provider or "ollama"
        config = tenant.llm_config or {
            "model": "llama3.2",
            "base_url": "http://localhost:11434"
        }

        return {
            "provider": provider,
            "model": config.get("model", "llama3.2"),
            "base_url": config.get("base_url"),
        }

    async def _initialize_llm_service(self):
        """Initialize LLM service with tenant's provider settings"""
        if self.llm_service is None:
            llm_config = await self._get_tenant_llm_config()
            self.llm_service = LiteLLMService(
                tenant_id=self.tenant_id,
                provider=llm_config["provider"]
            )

    async def summarize_document(
        self,
        document_id: UUID,
        model: Optional[str] = None,
        max_length: int = 500
    ) -> Dict[str, Any]:
        """
        Summarize document content

        Args:
            document_id: Document to summarize
            model: LLM model to use (if None, uses tenant's default)
            max_length: Max summary length in words

        Returns:
            {
                "operation_id": UUID,
                "summary": "...",
                "model_used": "gpt-4",
                "tokens_used": 150,
                "cost_estimate": 0.015
            }
        """
        # Initialize LLM service with tenant config
        await self._initialize_llm_service()
        llm_config = await self._get_tenant_llm_config()

        # Use tenant's model if not specified
        if model is None:
            model = llm_config["model"]

        # Add provider prefix if needed (e.g., ollama/llama3.2)
        if llm_config["provider"] == "ollama" and not model.startswith("ollama/"):
            model = f"ollama/{model}"

        # Create operation record
        operation = LLMOperation(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            document_id=document_id,
            operation_type="summarize",
            input_data={"model": model, "max_length": max_length},
            status="processing"
        )
        self.db.add(operation)
        await self.db.commit()
        await self.db.refresh(operation)

        try:
            # Get document content
            document = await self._get_document(document_id)

            # Get chunks
            chunks = await self._get_document_chunks(document_id)
            full_content = "\n\n".join([chunk.content for chunk in chunks])

            # Limit content length for faster processing (max ~2000 tokens ≈ 8000 chars)
            # This is especially important for Ollama which can be slow with long contexts
            max_content_chars = 8000
            if len(full_content) > max_content_chars:
                full_content = full_content[:max_content_chars] + "\n\n[Content truncated for performance...]"
                logger.info(
                    "document_content_truncated",
                    tenant_id=str(self.tenant_id),
                    document_id=str(document_id),
                    original_length=len(full_content),
                    truncated_to=max_content_chars
                )

            # Create prompt
            messages = [
                {
                    "role": "system",
                    "content": f"You are a document summarization expert. Summarize the following document in approximately {max_length} words. Be concise and focus on the main points."
                },
                {
                    "role": "user",
                    "content": f"Document: {document.filename}\n\nContent:\n{full_content}"
                }
            ]

            # Generate summary
            # Limit max_tokens for faster response (especially with Ollama)
            # For 500 words, use ~400 tokens (conservative estimate)
            max_tokens_limit = min(max_length, 400)

            result = await self.llm_service.complete(
                messages=messages,
                model=model,
                temperature=0.3,
                max_tokens=max_tokens_limit
            )

            # Update operation
            operation.output_data = {"summary": result["content"]}
            operation.model_used = result["model"]
            operation.tokens_used = result["tokens"]["total"]
            operation.cost_estimate = result["cost"]
            operation.status = "completed"
            operation.completed_at = datetime.utcnow()
            await self.db.commit()

            logger.info(
                "document_summarized",
                tenant_id=str(self.tenant_id),
                document_id=str(document_id),
                operation_id=str(operation.id),
                tokens=result["tokens"]["total"]
            )

            return {
                "operation_id": operation.id,
                "summary": result["content"],
                "model_used": result["model"],
                "tokens_used": result["tokens"]["total"],
                "cost_estimate": result["cost"]
            }

        except Exception as e:
            # Mark operation as failed
            operation.status = "failed"
            operation.error_message = str(e)
            operation.completed_at = datetime.utcnow()
            await self.db.commit()

            logger.error(
                "document_summarize_error",
                tenant_id=str(self.tenant_id),
                document_id=str(document_id),
                error=str(e)
            )
            raise

    async def ask_question(
        self,
        document_id: UUID,
        question: str,
        model: Optional[str] = None,
        max_chunks: int = 5
    ) -> Dict[str, Any]:
        """
        Ask question about document using RAG

        Args:
            document_id: Document to query
            question: User question
            model: LLM model (if None, uses tenant's default)
            max_chunks: Max relevant chunks to retrieve

        Returns:
            {
                "operation_id": UUID,
                "answer": "...",
                "sources": [...],
                "model_used": "gpt-4",
                "tokens_used": 200,
                "cost_estimate": 0.02
            }
        """
        # Initialize LLM service with tenant config
        await self._initialize_llm_service()
        llm_config = await self._get_tenant_llm_config()

        # Use tenant's model if not specified
        if model is None:
            model = llm_config["model"]

        # Add provider prefix if needed (e.g., ollama/llama3.2)
        if llm_config["provider"] == "ollama" and not model.startswith("ollama/"):
            model = f"ollama/{model}"

        # Create operation
        operation = LLMOperation(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            document_id=document_id,
            operation_type="ask",
            input_data={"question": question, "model": model, "max_chunks": max_chunks},
            status="processing"
        )
        self.db.add(operation)
        await self.db.commit()
        await self.db.refresh(operation)

        try:
            # Get document
            document = await self._get_document(document_id)

            # Generate embedding for question
            question_embedding = await self.embedding_service.generate_embedding(
                text=question,
                tenant_id=str(self.tenant_id)
            )

            if not question_embedding:
                raise ValueError("Failed to generate embedding for question")

            # Vector search for relevant chunks using Qdrant
            search_results = await qdrant_store.search(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                query_vector=question_embedding,
                limit=max_chunks,
                filter_metadata={"document_id": str(document_id), "tenant_id": str(self.tenant_id)}
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
            result = await self.llm_service.complete(
                messages=messages,
                model=model,
                temperature=0.7
            )

            # Update operation
            operation.output_data = {
                "answer": result["content"],
                "sources": sources
            }
            operation.model_used = result["model"]
            operation.tokens_used = result["tokens"]["total"]
            operation.cost_estimate = result["cost"]
            operation.status = "completed"
            operation.completed_at = datetime.utcnow()
            await self.db.commit()

            logger.info(
                "document_question_answered",
                tenant_id=str(self.tenant_id),
                document_id=str(document_id),
                operation_id=str(operation.id)
            )

            return {
                "operation_id": operation.id,
                "answer": result["content"],
                "sources": sources,
                "model_used": result["model"],
                "tokens_used": result["tokens"]["total"],
                "cost_estimate": result["cost"]
            }

        except Exception as e:
            operation.status = "failed"
            operation.error_message = str(e)
            operation.completed_at = datetime.utcnow()
            await self.db.commit()

            logger.error(
                "document_ask_error",
                tenant_id=str(self.tenant_id),
                document_id=str(document_id),
                error=str(e)
            )
            raise

    async def transform_document(
        self,
        document_id: UUID,
        instruction: str,
        model: Optional[str] = None,
        output_format: str = "text"
    ) -> Dict[str, Any]:
        """
        Transform/edit document content based on instruction

        Args:
            document_id: Document to transform
            instruction: Transformation instruction (e.g., "Translate to Turkish", "Make it formal")
            model: LLM model (if None, uses tenant's default)
            output_format: 'text', 'markdown', 'json'

        Returns:
            {
                "operation_id": UUID,
                "transformed_content": "...",
                "model_used": "gpt-4",
                "tokens_used": 300,
                "cost_estimate": 0.03
            }
        """
        # Initialize LLM service with tenant config
        await self._initialize_llm_service()
        llm_config = await self._get_tenant_llm_config()

        # Use tenant's model if not specified
        if model is None:
            model = llm_config["model"]

        # Add provider prefix if needed (e.g., ollama/llama3.2)
        if llm_config["provider"] == "ollama" and not model.startswith("ollama/"):
            model = f"ollama/{model}"

        # Create operation
        operation = LLMOperation(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            document_id=document_id,
            operation_type="transform",
            input_data={
                "instruction": instruction,
                "model": model,
                "output_format": output_format
            },
            status="processing"
        )
        self.db.add(operation)
        await self.db.commit()
        await self.db.refresh(operation)

        try:
            # Get document and chunks
            document = await self._get_document(document_id)
            chunks = await self._get_document_chunks(document_id)
            full_content = "\n\n".join([chunk.content for chunk in chunks])

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
            result = await self.llm_service.complete(
                messages=messages,
                model=model,
                temperature=0.5
            )

            # Update operation
            operation.output_data = {
                "transformed_content": result["content"],
                "output_format": output_format
            }
            operation.model_used = result["model"]
            operation.tokens_used = result["tokens"]["total"]
            operation.cost_estimate = result["cost"]
            operation.status = "completed"
            operation.completed_at = datetime.utcnow()
            await self.db.commit()

            logger.info(
                "document_transformed",
                tenant_id=str(self.tenant_id),
                document_id=str(document_id),
                operation_id=str(operation.id)
            )

            return {
                "operation_id": operation.id,
                "transformed_content": result["content"],
                "model_used": result["model"],
                "tokens_used": result["tokens"]["total"],
                "cost_estimate": result["cost"]
            }

        except Exception as e:
            operation.status = "failed"
            operation.error_message = str(e)
            operation.completed_at = datetime.utcnow()
            await self.db.commit()

            logger.error(
                "document_transform_error",
                tenant_id=str(self.tenant_id),
                document_id=str(document_id),
                error=str(e)
            )
            raise

    # Helper methods

    async def _get_document(self, document_id: UUID) -> Document:
        """Get document by ID with tenant filtering"""
        stmt = select(Document).where(
            Document.id == document_id,
            Document.tenant_id == self.tenant_id
        )
        result = await self.db.execute(stmt)
        document = result.scalar_one_or_none()

        if not document:
            raise ValueError(f"Document {document_id} not found")

        return document

    async def _get_document_chunks(self, document_id: UUID) -> List[DocumentChunk]:
        """Get all chunks for a document"""
        stmt = select(DocumentChunk).where(
            DocumentChunk.document_id == document_id
        ).order_by(DocumentChunk.chunk_index)

        result = await self.db.execute(stmt)
        return result.scalars().all()
