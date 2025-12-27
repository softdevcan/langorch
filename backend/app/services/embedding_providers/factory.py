"""
Provider factory for creating embedding provider instances
"""
from typing import Dict, Any, Optional
import structlog

from .base import BaseEmbeddingProvider, ProviderType
from .openai_provider import OpenAIProvider
from .ollama_provider import OllamaProvider

logger = structlog.get_logger()


class ProviderFactory:
    """
    Factory for creating embedding provider instances

    Handles:
    - Provider instantiation based on type
    - Configuration validation
    - Error handling
    """

    @staticmethod
    def create_provider(
        provider_type: ProviderType,
        config: Dict[str, Any],
    ) -> BaseEmbeddingProvider:
        """
        Create an embedding provider instance

        Args:
            provider_type: Type of provider to create
            config: Provider configuration
                For OpenAI:
                {
                    "api_key": "sk-...",
                    "model": "text-embedding-3-small"  # optional
                }
                For Ollama:
                {
                    "base_url": "http://localhost:11434",  # optional
                    "model": "nomic-embed-text"
                }

        Returns:
            Provider instance

        Raises:
            ValueError: If provider type is unsupported or config is invalid
        """
        try:
            if provider_type == ProviderType.OPENAI:
                return ProviderFactory._create_openai_provider(config)

            elif provider_type == ProviderType.OLLAMA:
                return ProviderFactory._create_ollama_provider(config)

            elif provider_type == ProviderType.CLAUDE:
                # TODO: Implement Claude provider
                raise NotImplementedError(
                    "Claude provider not yet implemented. "
                    "Please use OpenAI or Ollama for now."
                )

            elif provider_type == ProviderType.GEMINI:
                # TODO: Implement Gemini provider
                raise NotImplementedError(
                    "Gemini provider not yet implemented. "
                    "Please use OpenAI or Ollama for now."
                )

            else:
                raise ValueError(f"Unsupported provider type: {provider_type}")

        except Exception as e:
            logger.error(
                "provider_creation_failed",
                provider_type=provider_type,
                error=str(e),
            )
            raise

    @staticmethod
    def _create_openai_provider(config: Dict[str, Any]) -> OpenAIProvider:
        """
        Create OpenAI provider instance

        Args:
            config: OpenAI configuration

        Returns:
            OpenAI provider instance

        Raises:
            ValueError: If API key is missing
        """
        api_key = config.get("api_key")
        if not api_key:
            raise ValueError("OpenAI API key is required")

        model = config.get("model", "text-embedding-3-small")

        logger.info(
            "creating_openai_provider",
            model=model,
        )

        return OpenAIProvider(
            api_key=api_key,
            model=model,
        )

    @staticmethod
    def _create_ollama_provider(config: Dict[str, Any]) -> OllamaProvider:
        """
        Create Ollama provider instance

        Args:
            config: Ollama configuration

        Returns:
            Ollama provider instance

        Raises:
            ValueError: If model is missing
        """
        base_url = config.get("base_url", "http://localhost:11434")
        model = config.get("model")

        if not model:
            raise ValueError("Ollama model name is required")

        timeout = config.get("timeout", 30)

        logger.info(
            "creating_ollama_provider",
            base_url=base_url,
            model=model,
            timeout=timeout,
        )

        return OllamaProvider(
            base_url=base_url,
            model=model,
            timeout=timeout,
        )

    @staticmethod
    def get_default_config(provider_type: ProviderType) -> Dict[str, Any]:
        """
        Get default configuration for a provider type

        Args:
            provider_type: Type of provider

        Returns:
            Default configuration dict
        """
        if provider_type == ProviderType.OPENAI:
            return {
                "model": "text-embedding-3-small",
                "dimensions": 1536,
            }

        elif provider_type == ProviderType.OLLAMA:
            return {
                "base_url": "http://localhost:11434",
                "model": "nomic-embed-text",
                "dimensions": 768,
            }

        elif provider_type == ProviderType.CLAUDE:
            return {
                "model": "claude-3-haiku-20240307",  # Placeholder
                "dimensions": 1024,  # Placeholder
            }

        elif provider_type == ProviderType.GEMINI:
            return {
                "model": "embedding-001",  # Placeholder
                "dimensions": 768,  # Placeholder
            }

        else:
            return {}

    @staticmethod
    def validate_config(
        provider_type: ProviderType,
        config: Dict[str, Any],
    ) -> tuple[bool, Optional[str]]:
        """
        Validate provider configuration

        Args:
            provider_type: Type of provider
            config: Configuration to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if provider_type == ProviderType.OPENAI:
                if not config.get("api_key"):
                    return False, "OpenAI API key is required"

                model = config.get("model", "text-embedding-3-small")
                valid_models = [
                    "text-embedding-3-small",
                    "text-embedding-3-large",
                    "text-embedding-ada-002",
                ]
                if model not in valid_models:
                    return False, f"Invalid OpenAI model. Valid models: {', '.join(valid_models)}"

            elif provider_type == ProviderType.OLLAMA:
                if not config.get("model"):
                    return False, "Ollama model name is required"

                base_url = config.get("base_url", "http://localhost:11434")
                if not base_url.startswith("http"):
                    return False, "Ollama base URL must start with http:// or https://"

            elif provider_type == ProviderType.CLAUDE:
                return False, "Claude provider not yet implemented"

            elif provider_type == ProviderType.GEMINI:
                return False, "Gemini provider not yet implemented"

            else:
                return False, f"Unsupported provider type: {provider_type}"

            return True, None

        except Exception as e:
            logger.error(
                "config_validation_failed",
                provider_type=provider_type,
                error=str(e),
            )
            return False, str(e)


# Convenience function for creating providers
async def create_provider_from_tenant_config(
    tenant_config: Dict[str, Any],
    fallback_api_key: Optional[str] = None,
) -> BaseEmbeddingProvider:
    """
    Create provider from tenant configuration

    Args:
        tenant_config: Tenant's embedding_config from database
        fallback_api_key: Fallback API key for OpenAI if not in config

    Returns:
        Provider instance

    Example tenant_config:
    {
        "provider": "openai",
        "model": "text-embedding-3-small",
        "api_key": "sk-...",  # or None if using Vault
        "dimensions": 1536
    }
    """
    provider_type_str = tenant_config.get("provider", "openai")
    provider_type = ProviderType(provider_type_str)

    config = dict(tenant_config)

    # Handle fallback API key for OpenAI
    if provider_type == ProviderType.OPENAI:
        if not config.get("api_key") and fallback_api_key:
            config["api_key"] = fallback_api_key
            logger.info("using_fallback_api_key_for_openai")

    return ProviderFactory.create_provider(provider_type, config)
