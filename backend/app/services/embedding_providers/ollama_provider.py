"""
Ollama embedding provider implementation for local embeddings
"""
from typing import List, Optional
import aiohttp
import structlog

from .base import BaseEmbeddingProvider, ProviderType

logger = structlog.get_logger()


class OllamaProvider(BaseEmbeddingProvider):
    """
    Ollama embedding provider for local models

    Supports models like:
    - nomic-embed-text (768 dimensions)
    - mxbai-embed-large (1024 dimensions)
    - all-minilm (384 dimensions)
    - And any other embedding model available in Ollama
    """

    # Common model dimensions (can be overridden)
    MODEL_DIMENSIONS = {
        "nomic-embed-text": 768,
        "mxbai-embed-large": 1024,
        "all-minilm": 384,
        "llama2": 4096,  # If using llama2 for embeddings
    }

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
        **kwargs
    ):
        """
        Initialize Ollama provider

        Args:
            base_url: Ollama API base URL (default: http://localhost:11434)
            model: Model name (default: nomic-embed-text)
            **kwargs: Additional parameters
        """
        super().__init__(
            provider_type=ProviderType.OLLAMA,
            base_url=base_url,
            model=model,
            **kwargs
        )

        if not base_url:
            raise ValueError("Ollama base URL is required")

        if not model:
            raise ValueError("Ollama model name is required")

        # Store timeout settings
        self.timeout = kwargs.get("timeout", 30)  # 30 seconds default

    async def generate_embedding(
        self,
        text: str,
        **kwargs
    ) -> Optional[List[float]]:
        """
        Generate embedding for a single text using Ollama

        Args:
            text: Input text
            **kwargs: Additional Ollama parameters

        Returns:
            Embedding vector or None if failed
        """
        try:
            if not text or not text.strip():
                logger.warning("empty_text_provided_for_ollama_embedding")
                return None

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/embeddings",
                    json={
                        "model": self.model,
                        "prompt": text,
                        **kwargs
                    },
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(
                            "ollama_api_error",
                            status=response.status,
                            error=error_text,
                        )
                        return None

                    data = await response.json()
                    embedding = data.get("embedding")

                    if not embedding:
                        logger.error("ollama_empty_embedding_response")
                        return None

                    # logger.info(
                    #     "ollama_embedding_generated",
                    #     model=self.model,
                    #     text_length=len(text),
                    #     embedding_dim=len(embedding),
                    # )

                    return embedding

        except aiohttp.ClientError as e:
            logger.error(
                "ollama_connection_error",
                base_url=self.base_url,
                model=self.model,
                error=str(e),
            )
            return None
        except Exception as e:
            logger.error(
                "ollama_embedding_generation_failed",
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
        Generate embeddings for multiple texts

        Note: Ollama doesn't have native batch support, so we process sequentially.
        For better performance, consider using asyncio.gather for parallel requests.

        Args:
            texts: List of input texts
            **kwargs: Additional Ollama parameters

        Returns:
            List of embedding vectors (same order as input)
        """
        try:
            if not texts:
                logger.warning("empty_texts_list_provided_ollama")
                return []

            # Process all texts in parallel using asyncio
            import asyncio

            tasks = [
                self.generate_embedding(text, **kwargs)
                for text in texts
            ]

            embeddings = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle exceptions in results
            results = []
            for i, embedding in enumerate(embeddings):
                if isinstance(embedding, Exception):
                    logger.error(
                        "ollama_batch_item_failed",
                        index=i,
                        error=str(embedding),
                    )
                    results.append(None)
                else:
                    results.append(embedding)

            logger.info(
                "ollama_batch_embeddings_generated",
                model=self.model,
                batch_size=len(texts),
                successful=sum(1 for r in results if r is not None),
            )

            return results

        except Exception as e:
            logger.error(
                "ollama_batch_embedding_generation_failed",
                model=self.model,
                error=str(e),
            )
            return [None] * len(texts)

    def get_dimensions(self) -> int:
        """
        Get embedding vector dimensions for this model

        Returns:
            Dimension count (default 768 if model unknown)
        """
        return self.MODEL_DIMENSIONS.get(self.model, 768)

    async def test_connection(self) -> bool:
        """
        Test if Ollama is accessible and model is available

        Returns:
            True if connection successful
        """
        try:
            # First, check if Ollama is running
            async with aiohttp.ClientSession() as session:
                # Try to get version info
                async with session.get(
                    f"{self.base_url}/api/version",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status != 200:
                        logger.error(
                            "ollama_not_running",
                            base_url=self.base_url,
                            status=response.status,
                        )
                        return False

                # Try to generate a test embedding
                test_text = "test connection"
                embedding = await self.generate_embedding(test_text)

                if embedding and len(embedding) > 0:
                    logger.info(
                        "ollama_connection_test_successful",
                        base_url=self.base_url,
                        model=self.model,
                        dimensions=len(embedding),
                    )
                    return True
                else:
                    logger.error(
                        "ollama_connection_test_failed_empty_response",
                        model=self.model,
                    )
                    return False

        except aiohttp.ClientError as e:
            logger.error(
                "ollama_connection_test_failed",
                base_url=self.base_url,
                model=self.model,
                error=str(e),
            )
            return False
        except Exception as e:
            logger.error(
                "ollama_unexpected_error_during_test",
                base_url=self.base_url,
                model=self.model,
                error=str(e),
            )
            return False

    async def list_available_models(self) -> List[str]:
        """
        Get list of available models in Ollama

        Returns:
            List of model names
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status != 200:
                        logger.error("ollama_models_list_failed", status=response.status)
                        return []

                    data = await response.json()
                    models = [model["name"] for model in data.get("models", [])]

                    logger.info(
                        "ollama_models_listed",
                        count=len(models),
                    )

                    return models

        except Exception as e:
            logger.error(
                "ollama_models_list_error",
                error=str(e),
            )
            return []
