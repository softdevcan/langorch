"""
OpenAI embedding provider implementation
"""
from typing import List, Optional
from openai import AsyncOpenAI
import structlog

from .base import BaseEmbeddingProvider, ProviderType

logger = structlog.get_logger()


class OpenAIProvider(BaseEmbeddingProvider):
    """
    OpenAI embedding provider

    Supports:
    - text-embedding-3-small (1536 dimensions)
    - text-embedding-3-large (3072 dimensions)
    - text-embedding-ada-002 (1536 dimensions, legacy)
    """

    # Model dimensions mapping
    MODEL_DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        **kwargs
    ):
        """
        Initialize OpenAI provider

        Args:
            api_key: OpenAI API key
            model: Model name (default: text-embedding-3-small)
            **kwargs: Additional parameters
        """
        super().__init__(
            provider_type=ProviderType.OPENAI,
            api_key=api_key,
            model=model,
            **kwargs
        )

        if not api_key:
            raise ValueError("OpenAI API key is required")

        self.client = AsyncOpenAI(api_key=api_key)

        # Validate model
        if model not in self.MODEL_DIMENSIONS:
            logger.warning(
                "unknown_openai_model_using_default_dimensions",
                model=model,
                default_dimensions=1536,
            )

    async def generate_embedding(
        self,
        text: str,
        **kwargs
    ) -> Optional[List[float]]:
        """
        Generate embedding for a single text

        Args:
            text: Input text
            **kwargs: Additional OpenAI parameters

        Returns:
            Embedding vector or None if failed
        """
        try:
            if not text or not text.strip():
                logger.warning("empty_text_provided_for_embedding")
                return None

            response = await self.client.embeddings.create(
                input=text,
                model=self.model,
                **kwargs
            )

            embedding = response.data[0].embedding

            logger.info(
                "openai_embedding_generated",
                model=self.model,
                text_length=len(text),
                embedding_dim=len(embedding),
            )

            return embedding

        except Exception as e:
            logger.error(
                "openai_embedding_generation_failed",
                model=self.model,
                error=str(e),
            )
            return None

    async def generate_embeddings_batch(
        self,
        texts: List[str],
        **kwargs
    ) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts (batch processing)

        OpenAI supports up to 2048 texts in a single batch.

        Args:
            texts: List of input texts
            **kwargs: Additional OpenAI parameters

        Returns:
            List of embedding vectors (same order as input)
        """
        try:
            if not texts:
                logger.warning("empty_texts_list_provided")
                return []

            # Filter out empty texts but keep track of indices
            valid_texts = []
            valid_indices = []

            for i, text in enumerate(texts):
                if text and text.strip():
                    valid_texts.append(text)
                    valid_indices.append(i)

            if not valid_texts:
                logger.warning("no_valid_texts_in_batch")
                return [None] * len(texts)

            # OpenAI batch limit is 2048
            if len(valid_texts) > 2048:
                logger.warning(
                    "batch_size_exceeds_openai_limit",
                    batch_size=len(valid_texts),
                    limit=2048,
                )
                # Process in chunks
                results = []
                for i in range(0, len(valid_texts), 2048):
                    chunk = valid_texts[i:i + 2048]
                    chunk_results = await self._generate_batch_chunk(chunk, **kwargs)
                    results.extend(chunk_results)
            else:
                results = await self._generate_batch_chunk(valid_texts, **kwargs)

            # Map results back to original indices
            final_results = [None] * len(texts)
            for i, idx in enumerate(valid_indices):
                if i < len(results):
                    final_results[idx] = results[i]

            logger.info(
                "openai_batch_embeddings_generated",
                model=self.model,
                batch_size=len(texts),
                valid_count=len(valid_texts),
            )

            return final_results

        except Exception as e:
            logger.error(
                "openai_batch_embedding_generation_failed",
                model=self.model,
                error=str(e),
            )
            return [None] * len(texts)

    async def _generate_batch_chunk(
        self,
        texts: List[str],
        **kwargs
    ) -> List[Optional[List[float]]]:
        """
        Helper method to generate embeddings for a batch chunk

        Args:
            texts: List of texts (max 2048)
            **kwargs: Additional OpenAI parameters

        Returns:
            List of embeddings
        """
        response = await self.client.embeddings.create(
            input=texts,
            model=self.model,
            **kwargs
        )

        # Extract embeddings in order
        embeddings = [item.embedding for item in response.data]
        return embeddings

    def get_dimensions(self) -> int:
        """
        Get embedding vector dimensions for this model

        Returns:
            Dimension count
        """
        return self.MODEL_DIMENSIONS.get(self.model, 1536)

    async def test_connection(self) -> bool:
        """
        Test if OpenAI API is accessible

        Returns:
            True if connection successful
        """
        try:
            # Generate a simple test embedding
            test_text = "test connection"
            embedding = await self.generate_embedding(test_text)

            if embedding and len(embedding) > 0:
                logger.info(
                    "openai_connection_test_successful",
                    model=self.model,
                )
                return True
            else:
                logger.error("openai_connection_test_failed_empty_response")
                return False

        except Exception as e:
            logger.error(
                "openai_connection_test_failed",
                model=self.model,
                error=str(e),
            )
            return False
