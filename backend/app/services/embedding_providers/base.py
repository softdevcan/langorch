"""
Base embedding provider abstract class
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from enum import Enum
import structlog

logger = structlog.get_logger()


class ProviderType(str, Enum):
    """Supported embedding providers"""
    OPENAI = "openai"
    OLLAMA = "ollama"
    CLAUDE = "claude"
    GEMINI = "gemini"


class BaseEmbeddingProvider(ABC):
    """
    Abstract base class for embedding providers

    All embedding providers must implement:
    - generate_embedding: Single text embedding
    - generate_embeddings_batch: Batch text embeddings
    - get_dimensions: Return embedding vector dimensions
    - test_connection: Test provider availability
    """

    def __init__(
        self,
        provider_type: ProviderType,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize provider

        Args:
            provider_type: Type of provider
            api_key: API key for the provider (if required)
            base_url: Base URL for the provider (for Ollama, custom endpoints)
            model: Model name to use
            **kwargs: Additional provider-specific parameters
        """
        self.provider_type = provider_type
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.extra_params = kwargs

    @abstractmethod
    async def generate_embedding(
        self,
        text: str,
        **kwargs
    ) -> Optional[List[float]]:
        """
        Generate embedding for a single text

        Args:
            text: Input text
            **kwargs: Provider-specific parameters

        Returns:
            Embedding vector or None if failed
        """
        pass

    @abstractmethod
    async def generate_embeddings_batch(
        self,
        texts: List[str],
        **kwargs
    ) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts

        Args:
            texts: List of input texts
            **kwargs: Provider-specific parameters

        Returns:
            List of embedding vectors (same order as input)
        """
        pass

    @abstractmethod
    def get_dimensions(self) -> int:
        """
        Get embedding vector dimensions for this provider/model

        Returns:
            Dimension count
        """
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Test if provider is accessible and configured correctly

        Returns:
            True if connection successful
        """
        pass

    def get_info(self) -> Dict[str, Any]:
        """
        Get provider information

        Returns:
            Provider metadata
        """
        return {
            "provider": self.provider_type.value,
            "model": self.model,
            "dimensions": self.get_dimensions(),
            "base_url": self.base_url,
        }
