"""
Embedding providers package

Supports multiple embedding providers:
- OpenAI (text-embedding-3-small, text-embedding-3-large)
- Ollama (local models)
- Claude (via Anthropic - text only)
- Gemini (via Google)
"""
from app.services.embedding_providers.base import BaseEmbeddingProvider, ProviderType
from app.services.embedding_providers.openai_provider import OpenAIProvider
from app.services.embedding_providers.ollama_provider import OllamaProvider
from app.services.embedding_providers.factory import ProviderFactory, create_provider_from_tenant_config

__all__ = [
    "BaseEmbeddingProvider",
    "ProviderType",
    "OpenAIProvider",
    "OllamaProvider",
    "ProviderFactory",
    "create_provider_from_tenant_config",
]
