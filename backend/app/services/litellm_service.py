from typing import List, Dict, Any, Optional
from uuid import UUID
from decimal import Decimal
import structlog
from litellm import acompletion, cost_per_token

from app.core.vault_client import vault_client

logger = structlog.get_logger()


class LiteLLMService:
    """
    Simple LiteLLM service for Version 0.3

    No routing, no fallbacks - just basic completion
    (Advanced features moved to Version 0.4)
    """

    def __init__(self, tenant_id: UUID, provider: Optional[str] = None):
        self.tenant_id = tenant_id
        self.provider = provider
        self.api_keys = self._load_api_keys()

    def _load_api_keys(self) -> Dict[str, str]:
        """Load API keys from Vault based on provider"""
        keys = {}

        # Only load API keys if provider requires them
        if self.provider == "openai":
            try:
                key = vault_client.get_tenant_secret(
                    tenant_id=str(self.tenant_id),
                    secret_key="openai_api_key"
                )
                if key:
                    keys["openai_api_key"] = key
            except Exception as e:
                logger.debug(
                    "vault_secret_not_found",
                    tenant_id=str(self.tenant_id),
                    provider="openai",
                    error=str(e)
                )
        elif self.provider == "anthropic":
            try:
                key = vault_client.get_tenant_secret(
                    tenant_id=str(self.tenant_id),
                    secret_key="anthropic_api_key"
                )
                if key:
                    keys["anthropic_api_key"] = key
            except Exception as e:
                logger.debug(
                    "vault_secret_not_found",
                    tenant_id=str(self.tenant_id),
                    provider="anthropic",
                    error=str(e)
                )

        return keys

    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate completion using LiteLLM

        Args:
            messages: Chat messages [{"role": "user", "content": "..."}]
            model: Model name (required: gpt-4, ollama/llama3.2, claude-3-sonnet, etc.)
            temperature: 0-1
            max_tokens: Max response tokens

        Returns:
            {
                "content": "...",
                "model": "ollama/llama3.2",
                "tokens": {"prompt": 100, "completion": 50, "total": 150},
                "cost": 0.015
            }
        """
        try:
            # Prepare API key and base URL based on model
            api_key = None
            api_base = None

            if model.startswith("gpt"):
                api_key = self.api_keys.get("openai_api_key")
            elif model.startswith("claude"):
                api_key = self.api_keys.get("anthropic_api_key")
            elif model.startswith("ollama/") or model.startswith("llama") or model.startswith("mistral"):
                # Ollama models - use local Ollama server
                api_base = "http://localhost:11434"
                # Ensure model has ollama/ prefix for LiteLLM
                if not model.startswith("ollama/"):
                    model = f"ollama/{model}"

            logger.info(
                "llm_completion_request",
                tenant_id=str(self.tenant_id),
                model=model,
                api_base=api_base,
                has_api_key=bool(api_key),
                message_count=len(messages)
            )

            # Call LiteLLM async
            response = await acompletion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=api_key,
                api_base=api_base,
                **kwargs
            )

            # Extract response
            content = response.choices[0].message.content
            usage = response.usage

            # Calculate cost using litellm's cost_per_token
            # For local/free models (like Ollama), cost will be 0
            try:
                prompt_cost = cost_per_token(
                    model=model,
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=0
                )
                completion_cost = cost_per_token(
                    model=model,
                    prompt_tokens=0,
                    completion_tokens=usage.completion_tokens
                )

                # Convert to Decimal, handle tuple/None responses
                if isinstance(prompt_cost, (tuple, list)):
                    prompt_cost = 0.0
                if isinstance(completion_cost, (tuple, list)):
                    completion_cost = 0.0

                total_cost = Decimal(str(prompt_cost + completion_cost))
            except Exception as e:
                logger.debug(
                    "cost_calculation_failed",
                    tenant_id=str(self.tenant_id),
                    model=model,
                    error=str(e)
                )
                total_cost = Decimal("0.0")

            logger.info(
                "llm_completion",
                tenant_id=str(self.tenant_id),
                model=model,
                tokens_total=usage.total_tokens,
                cost=float(total_cost)
            )

            return {
                "content": content,
                "model": model,
                "tokens": {
                    "prompt": usage.prompt_tokens,
                    "completion": usage.completion_tokens,
                    "total": usage.total_tokens
                },
                "cost": total_cost
            }

        except Exception as e:
            logger.error(
                "llm_completion_error",
                tenant_id=str(self.tenant_id),
                model=model,
                error=str(e)
            )
            raise
