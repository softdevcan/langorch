"""
Claude (Anthropic) embedding provider implementation using Voyage AI

Note: Anthropic doesn't have native embeddings API yet.
This implementation uses Voyage AI (Anthropic's recommended embeddings partner).
"""
from typing import List, Optional
import httpx
import structlog

from .base import BaseEmbeddingProvider, ProviderType

logger = structlog.get_logger()


class ClaudeProvider(BaseEmbeddingProvider):
    """
    Claude embedding provider using Voyage AI

    Anthropic recommends Voyage AI for embeddings as they don't have
    a native embeddings API yet.

    Supports:
    - voyage-2 (1024 dimensions)
    - voyage-large-2 (1536 dimensions)
    - voyage-code-2 (1536 dimensions)

    API Docs: https://docs.voyageai.com/
    """

    BASE_URL = "https://api.voyageai.com/v1"

    # Model dimensions mapping
    MODEL_DIMENSIONS = {
        "voyage-2": 1024,
        "voyage-large-2": 1536,
        "voyage-code-2": 1536,
        "voyage-lite-02-instruct": 1024,
    }

    # Maximum batch size for Voyage API
    MAX_BATCH_SIZE = 128

    def __init__(
        self,
        api_key: str,
        model: str = "voyage-2",
        **kwargs
    ):
        """
        Initialize Claude (Voyage AI) provider

        Args:
            api_key: Voyage AI API key
            model: Model name (default: voyage-2)
            **kwargs: Additional parameters
        """
        super().__init__(
            provider_type=ProviderType.CLAUDE,
            api_key=api_key,
            model=model,
            **kwargs
        )

        if not api_key:
            raise ValueError("Voyage AI API key is required for Claude embeddings")

        self.client = httpx.AsyncClient(timeout=30.0)

        # Validate model
        if model not in self.MODEL_DIMENSIONS:
            logger.warning(
                "unknown_voyage_model_using_default_dimensions",
                model=model,
                default_dimensions=1024,
            )

    async def generate_embedding(
        self,
        text: str,
        **kwargs
    ) -> Optional[List[float]]:
        """
        Generate embedding for a single text using Voyage AI

        Args:
            text: Input text
            **kwargs: Additional Voyage AI parameters

        Returns:
            Embedding vector or None if failed
        """
        try:
            if not text or not text.strip():
                logger.warning("empty_text_provided_for_voyage_embedding")
                return None

            url = f"{self.BASE_URL}/embeddings"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "input": text,
                "model": self.model,
            }

            # Add optional parameters if provided
            if "input_type" in kwargs:
                payload["input_type"] = kwargs["input_type"]

            response = await self.client.post(url, json=payload, headers=headers)

            if response.status_code != 200:
                error_text = response.text
                logger.error(
                    "voyage_api_error",
                    status=response.status_code,
                    error=error_text[:500],
                )
                return None

            data = response.json()
            # Voyage AI returns embeddings in data array
            embeddings_data = data.get("data", [])

            if not embeddings_data or len(embeddings_data) == 0:
                logger.error("voyage_empty_embedding_response")
                return None

            embedding = embeddings_data[0].get("embedding")

            if not embedding:
                logger.error("voyage_missing_embedding_in_response")
                return None

            logger.info(
                "voyage_embedding_generated",
                model=self.model,
                text_length=len(text),
                embedding_dim=len(embedding),
            )

            return embedding

        except httpx.HTTPStatusError as e:
            logger.error(
                "voyage_http_error",
                status=e.response.status_code,
                error=str(e),
            )
            return None
        except Exception as e:
            logger.error(
                "voyage_embedding_generation_failed",
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

        Voyage AI supports up to 128 texts per batch request.

        Args:
            texts: List of input texts
            **kwargs: Additional Voyage AI parameters

        Returns:
            List of embedding vectors (same order as input)
        """
        try:
            if not texts:
                logger.warning("empty_texts_list_provided_voyage")
                return []

            # Filter out empty texts but keep track of indices
            valid_texts = []
            valid_indices = []

            for i, text in enumerate(texts):
                if text and text.strip():
                    valid_texts.append(text)
                    valid_indices.append(i)

            if not valid_texts:
                logger.warning("no_valid_texts_in_voyage_batch")
                return [None] * len(texts)

            # Process in chunks if needed (max 128 per batch)
            if len(valid_texts) > self.MAX_BATCH_SIZE:
                logger.warning(
                    "batch_size_exceeds_voyage_limit",
                    batch_size=len(valid_texts),
                    limit=self.MAX_BATCH_SIZE,
                )
                # Process in chunks
                results = []
                for i in range(0, len(valid_texts), self.MAX_BATCH_SIZE):
                    chunk = valid_texts[i:i + self.MAX_BATCH_SIZE]
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
                "voyage_batch_embeddings_generated",
                model=self.model,
                batch_size=len(texts),
                valid_count=len(valid_texts),
            )

            return final_results

        except Exception as e:
            logger.error(
                "voyage_batch_embedding_generation_failed",
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
            texts: List of texts (max 128)
            **kwargs: Additional Voyage AI parameters

        Returns:
            List of embeddings
        """
        url = f"{self.BASE_URL}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "input": texts,
            "model": self.model,
        }

        # Add optional parameters if provided
        if "input_type" in kwargs:
            payload["input_type"] = kwargs["input_type"]

        response = await self.client.post(url, json=payload, headers=headers)

        if response.status_code != 200:
            error_text = response.text
            logger.error(
                "voyage_batch_api_error",
                status=response.status_code,
                error=error_text[:500],
            )
            # Fall back to individual processing
            logger.info("falling_back_to_individual_voyage_processing")
            import asyncio
            tasks = [self.generate_embedding(text, **kwargs) for text in texts]
            embeddings = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle exceptions in results
            results = []
            for embedding in embeddings:
                if isinstance(embedding, Exception):
                    results.append(None)
                else:
                    results.append(embedding)

            return results

        data = response.json()
        embeddings_data = data.get("data", [])

        # Extract embeddings in order
        embeddings = [item.get("embedding") for item in embeddings_data]

        return embeddings

    def get_dimensions(self) -> int:
        """
        Get embedding vector dimensions for this model

        Returns:
            Dimension count
        """
        return self.MODEL_DIMENSIONS.get(self.model, 1024)

    async def test_connection(self) -> bool:
        """
        Test if Voyage AI API is accessible

        Returns:
            True if connection successful
        """
        try:
            # Generate a simple test embedding
            test_text = "test connection"
            embedding = await self.generate_embedding(test_text)

            if embedding and len(embedding) > 0:
                logger.info(
                    "voyage_connection_test_successful",
                    model=self.model,
                    dimensions=len(embedding),
                )
                return True
            else:
                logger.error("voyage_connection_test_failed_empty_response")
                return False

        except Exception as e:
            logger.error(
                "voyage_connection_test_failed",
                model=self.model,
                error=str(e),
            )
            return False

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup resources"""
        await self.client.aclose()
