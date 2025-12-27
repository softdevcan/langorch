"""
Embedding providers package

Supports multiple embedding providers:
- OpenAI (text-embedding-3-small, text-embedding-3-large, text-embedding-ada-002)
- Ollama (local models: nomic-embed-text, mxbai-embed-large, all-minilm)
- Gemini (Google: text-embedding-004, embedding-001)
- Claude (Voyage AI: voyage-2, voyage-large-2, voyage-code-2, voyage-lite-02-instruct)
"""
from app.services.embedding_providers.base import BaseEmbeddingProvider, ProviderType
from app.services.embedding_providers.openai_provider import OpenAIProvider
from app.services.embedding_providers.ollama_provider import OllamaProvider
from app.services.embedding_providers.gemini_provider import GeminiProvider
from app.services.embedding_providers.claude_provider import ClaudeProvider
from app.services.embedding_providers.factory import ProviderFactory, create_provider_from_tenant_config

__all__ = [
    "BaseEmbeddingProvider",
    "ProviderType",
    "OpenAIProvider",
    "OllamaProvider",
    "GeminiProvider",
    "ClaudeProvider",
    "ProviderFactory",
    "create_provider_from_tenant_config",
]
