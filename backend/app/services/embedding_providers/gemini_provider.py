"""
Google Gemini embedding provider implementation
"""
from typing import List, Optional
import httpx
import structlog

from .base import BaseEmbeddingProvider, ProviderType

logger = structlog.get_logger()


class GeminiProvider(BaseEmbeddingProvider):
    """
    Google Gemini embedding provider using text-embedding-004

    Supports:
    - text-embedding-004 (768 dimensions, latest)
    - embedding-001 (768 dimensions, older)

    API Docs: https://ai.google.dev/api/embeddings
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    # Model dimensions mapping
    MODEL_DIMENSIONS = {
        "text-embedding-004": 768,
        "embedding-001": 768,
    }

    # Maximum batch size for Gemini API
    MAX_BATCH_SIZE = 100

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-004",
        **kwargs
    ):
        """
        Initialize Gemini provider

        Args:
            api_key: Google AI API key
            model: Model name (default: text-embedding-004)
            **kwargs: Additional parameters
        """
        super().__init__(
            provider_type=ProviderType.GEMINI,
            api_key=api_key,
            model=model,
            **kwargs
        )

        if not api_key:
            raise ValueError("Gemini API key is required")

        self.client = httpx.AsyncClient(timeout=30.0)

        # Validate model
        if model not in self.MODEL_DIMENSIONS:
            logger.warning(
                "unknown_gemini_model_using_default_dimensions",
                model=model,
                default_dimensions=768,
            )

    async def generate_embedding(
        self,
        text: str,
        **kwargs
    ) -> Optional[List[float]]:
        """
        Generate embedding for a single text using Gemini API

        Args:
            text: Input text
            **kwargs: Additional Gemini parameters

        Returns:
            Embedding vector or None if failed
        """
        try:
            if not text or not text.strip():
                logger.warning("empty_text_provided_for_gemini_embedding")
                return None

            url = f"{self.BASE_URL}/models/{self.model}:embedContent"
            params = {"key": self.api_key}

            payload = {
                "model": f"models/{self.model}",
                "content": {
                    "parts": [{"text": text}]
                }
            }

            response = await self.client.post(url, json=payload, params=params)

            if response.status_code != 200:
                error_text = response.text
                logger.error(
                    "gemini_api_error",
                    status=response.status_code,
                    error=error_text[:500],
                )
                return None

            data = response.json()
            embedding = data.get("embedding", {}).get("values")

            if not embedding:
                logger.error("gemini_empty_embedding_response")
                return None

            logger.info(
                "gemini_embedding_generated",
                model=self.model,
                text_length=len(text),
                embedding_dim=len(embedding),
            )

            return embedding

        except httpx.HTTPStatusError as e:
            logger.error(
                "gemini_http_error",
                status=e.response.status_code,
                error=str(e),
            )
            return None
        except Exception as e:
            logger.error(
                "gemini_embedding_generation_failed",
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

        Gemini supports up to 100 texts per batch request.

        Args:
            texts: List of input texts
            **kwargs: Additional Gemini parameters

        Returns:
            List of embedding vectors (same order as input)
        """
        try:
            if not texts:
                logger.warning("empty_texts_list_provided_gemini")
                return []

            # Filter out empty texts but keep track of indices
            valid_texts = []
            valid_indices = []

            for i, text in enumerate(texts):
                if text and text.strip():
                    valid_texts.append(text)
                    valid_indices.append(i)

            if not valid_texts:
                logger.warning("no_valid_texts_in_gemini_batch")
                return [None] * len(texts)

            # Process in chunks if needed (max 100 per batch)
            if len(valid_texts) > self.MAX_BATCH_SIZE:
                logger.warning(
                    "batch_size_exceeds_gemini_limit",
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
                "gemini_batch_embeddings_generated",
                model=self.model,
                batch_size=len(texts),
                valid_count=len(valid_texts),
            )

            return final_results

        except Exception as e:
            logger.error(
                "gemini_batch_embedding_generation_failed",
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
            texts: List of texts (max 100)
            **kwargs: Additional Gemini parameters

        Returns:
            List of embeddings
        """
        url = f"{self.BASE_URL}/models/{self.model}:batchEmbedContents"
        params = {"key": self.api_key}

        # Build batch request payload
        requests = [
            {
                "model": f"models/{self.model}",
                "content": {
                    "parts": [{"text": text}]
                }
            }
            for text in texts
        ]

        payload = {"requests": requests}

        response = await self.client.post(url, json=payload, params=params)

        if response.status_code != 200:
            error_text = response.text
            logger.error(
                "gemini_batch_api_error",
                status=response.status_code,
                error=error_text[:500],
            )
            # Fall back to individual processing
            logger.info("falling_back_to_individual_gemini_processing")
            import asyncio
            tasks = [self.generate_embedding(text, **kwargs) for text in texts]
            return await asyncio.gather(*tasks, return_exceptions=False)

        data = response.json()
        embeddings_data = data.get("embeddings", [])

        # Extract embeddings in order
        embeddings = [item.get("values") for item in embeddings_data]

        return embeddings

    def get_dimensions(self) -> int:
        """
        Get embedding vector dimensions for this model

        Returns:
            Dimension count
        """
        return self.MODEL_DIMENSIONS.get(self.model, 768)

    async def test_connection(self) -> bool:
        """
        Test if Gemini API is accessible

        Returns:
            True if connection successful
        """
        try:
            # Generate a simple test embedding
            test_text = "test connection"
            embedding = await self.generate_embedding(test_text)

            if embedding and len(embedding) > 0:
                logger.info(
                    "gemini_connection_test_successful",
                    model=self.model,
                    dimensions=len(embedding),
                )
                return True
            else:
                logger.error("gemini_connection_test_failed_empty_response")
                return False

        except Exception as e:
            logger.error(
                "gemini_connection_test_failed",
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
