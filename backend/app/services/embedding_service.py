"""
Embedding service - Text chunking and embedding generation
"""
from typing import List, Dict, Any, Optional
import tiktoken
from openai import AsyncOpenAI
import structlog

from app.core.config import settings
from app.core.vault import vault_client

logger = structlog.get_logger()


class EmbeddingService:
    """
    Embedding service for text chunking and vector generation

    Features:
    - Text chunking with RecursiveCharacterTextSplitter logic
    - Token counting
    - OpenAI embedding generation
    - Tenant API key management via Vault
    """

    def __init__(self):
        """Initialize embedding service"""
        self._encoding = tiktoken.get_encoding("cl100k_base")  # OpenAI tokenizer

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken

        Args:
            text: Input text

        Returns:
            Token count
        """
        try:
            tokens = self._encoding.encode(text)
            return len(tokens)
        except Exception as e:
            logger.error("token_counting_failed", error=str(e))
            # Fallback to rough estimation
            return len(text) // 4

    def chunk_text(
        self,
        text: str,
        chunk_size: int = None,
        chunk_overlap: int = None,
    ) -> List[Dict[str, Any]]:
        """
        Split text into chunks with overlap

        Args:
            text: Input text to chunk
            chunk_size: Maximum characters per chunk (default from settings)
            chunk_overlap: Overlap between chunks (default from settings)

        Returns:
            List of chunks with metadata:
            [
                {
                    "content": "chunk text",
                    "start_char": 0,
                    "end_char": 1000,
                    "chunk_index": 0,
                    "token_count": 250
                },
                ...
            ]
        """
        chunk_size = chunk_size or settings.CHUNK_SIZE
        chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

        if not text or not text.strip():
            return []

        chunks = []
        start_idx = 0
        chunk_index = 0
        text_length = len(text)

        # Separators for smart splitting (prioritized)
        separators = ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " "]

        while start_idx < text_length:
            # Calculate end index
            end_idx = min(start_idx + chunk_size, text_length)

            # If not at the end, try to split at a natural boundary
            if end_idx < text_length:
                # Try to find a separator near the end
                best_split = end_idx
                for separator in separators:
                    # Look for separator in the last 20% of chunk
                    search_start = int(end_idx - chunk_size * 0.2)
                    split_pos = text.rfind(separator, search_start, end_idx)

                    if split_pos != -1:
                        best_split = split_pos + len(separator)
                        break

                end_idx = best_split

            # Extract chunk
            chunk_text = text[start_idx:end_idx].strip()

            if chunk_text:
                chunks.append({
                    "content": chunk_text,
                    "start_char": start_idx,
                    "end_char": end_idx,
                    "chunk_index": chunk_index,
                    "token_count": self.count_tokens(chunk_text),
                })
                chunk_index += 1

            # Move to next chunk with overlap
            start_idx = max(start_idx + 1, end_idx - chunk_overlap)

            # Prevent infinite loop
            if start_idx <= end_idx - chunk_size and end_idx < text_length:
                start_idx = end_idx - chunk_overlap

        logger.info(
            "text_chunked",
            total_chunks=len(chunks),
            total_chars=text_length,
            chunk_size=chunk_size,
            overlap=chunk_overlap,
        )

        return chunks

    async def generate_embedding(
        self,
        text: str,
        tenant_id: str,
        model: Optional[str] = None,
    ) -> Optional[List[float]]:
        """
        Generate embedding vector for text using OpenAI

        Args:
            text: Input text
            tenant_id: Tenant UUID (to fetch API key from Vault)
            model: OpenAI model name (default from settings)

        Returns:
            Embedding vector (list of floats) or None if failed
        """
        try:
            # Get tenant's OpenAI API key from Vault
            api_key = await vault_client.get_tenant_secret(
                tenant_id=tenant_id,
                secret_key="openai_api_key",
            )

            if not api_key:
                logger.error(
                    "tenant_openai_api_key_not_found",
                    tenant_id=tenant_id,
                )
                raise ValueError(f"OpenAI API key not found for tenant {tenant_id}")

            # Initialize OpenAI client
            client = AsyncOpenAI(api_key=api_key)

            # Generate embedding
            model = model or settings.EMBEDDING_MODEL
            response = await client.embeddings.create(
                input=text,
                model=model,
            )

            embedding = response.data[0].embedding

            logger.info(
                "embedding_generated",
                tenant_id=tenant_id,
                model=model,
                text_length=len(text),
                embedding_dim=len(embedding),
            )

            return embedding

        except Exception as e:
            logger.error(
                "embedding_generation_failed",
                tenant_id=tenant_id,
                error=str(e),
            )
            return None

    async def generate_embeddings_batch(
        self,
        texts: List[str],
        tenant_id: str,
        model: Optional[str] = None,
    ) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts (batch processing)

        Args:
            texts: List of input texts
            tenant_id: Tenant UUID
            model: OpenAI model name

        Returns:
            List of embedding vectors (same order as input)
        """
        try:
            # Get tenant's OpenAI API key from Vault
            api_key = await vault_client.get_tenant_secret(
                tenant_id=tenant_id,
                secret_key="openai_api_key",
            )

            if not api_key:
                logger.error(
                    "tenant_openai_api_key_not_found",
                    tenant_id=tenant_id,
                )
                return [None] * len(texts)

            # Initialize OpenAI client
            client = AsyncOpenAI(api_key=api_key)

            # Generate embeddings (OpenAI supports batch up to 2048 inputs)
            model = model or settings.EMBEDDING_MODEL
            response = await client.embeddings.create(
                input=texts,
                model=model,
            )

            # Extract embeddings in order
            embeddings = [item.embedding for item in response.data]

            logger.info(
                "batch_embeddings_generated",
                tenant_id=tenant_id,
                model=model,
                batch_size=len(texts),
            )

            return embeddings

        except Exception as e:
            logger.error(
                "batch_embedding_generation_failed",
                tenant_id=tenant_id,
                error=str(e),
            )
            return [None] * len(texts)


# Global embedding service instance
embedding_service = EmbeddingService()
