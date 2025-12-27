from typing import List, Dict, Any, Optional
from uuid import UUID
import structlog
from litellm import completion, cost_per_token

from app.core.vault_client import vault_client

logger = structlog.get_logger()


class LiteLLMService:
    """
    Simple LiteLLM service for Version 0.3

    No routing, no fallbacks - just basic completion
    (Advanced features moved to Version 0.4)
    """

    def __init__(self, tenant_id: UUID):
        self.tenant_id = tenant_id
        self.api_keys = self._load_api_keys()

    def _load_api_keys(self) -> Dict[str, str]:
        """Load API keys from Vault"""
        try:
            secrets = vault_client.get_tenant_secrets(str(self.tenant_id))
            return {
                "openai_api_key": secrets.get("openai_api_key"),
                "anthropic_api_key": secrets.get("anthropic_api_key"),
            }
        except Exception as e:
            logger.warning(
                "vault_load_failed",
                tenant_id=str(self.tenant_id),
                error=str(e)
            )
            return {}

    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate completion using LiteLLM

        Args:
            messages: Chat messages [{"role": "user", "content": "..."}]
            model: Model name (gpt-4, gpt-3.5-turbo, claude-3-sonnet, etc.)
            temperature: 0-1
            max_tokens: Max response tokens

        Returns:
            {
                "content": "...",
                "model": "gpt-4",
                "tokens": {"prompt": 100, "completion": 50, "total": 150},
                "cost": 0.015
            }
        """
        try:
            # Prepare API key based on model
            api_key = None
            if model.startswith("gpt"):
                api_key = self.api_keys.get("openai_api_key")
            elif model.startswith("claude"):
                api_key = self.api_keys.get("anthropic_api_key")

            # Call LiteLLM
            response = completion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=api_key,
                **kwargs
            )

            # Extract response
            content = response.choices[0].message.content
            usage = response.usage

            # Calculate cost using litellm's cost_per_token
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
            total_cost = prompt_cost + completion_cost

            logger.info(
                "llm_completion",
                tenant_id=str(self.tenant_id),
                model=model,
                tokens_total=usage.total_tokens,
                cost=total_cost
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
