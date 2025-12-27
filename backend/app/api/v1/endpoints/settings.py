"""
Settings API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.core.config import settings as app_settings
from app.core.vault import vault_client
from app.models.user import User
from app.models.tenant import Tenant
from app.schemas.settings import (
    EmbeddingProviderUpdate,
    EmbeddingProviderResponse,
    EmbeddingProviderTest,
    EmbeddingProviderTestResponse,
)
from app.services.embedding_providers import ProviderFactory, ProviderType

logger = structlog.get_logger()
router = APIRouter(tags=["Settings"])


@router.get("/embedding-provider", response_model=EmbeddingProviderResponse)
async def get_embedding_provider(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get current tenant's embedding provider settings

    Returns provider type, model, dimensions, and whether API key is configured.
    Does NOT return the actual API key for security.
    """
    try:
        # Get tenant
        tenant = await db.get(Tenant, current_user.tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )

        # Get provider settings
        provider_type = ProviderType(tenant.embedding_provider)
        config = tenant.embedding_config or ProviderFactory.get_default_config(provider_type)

        # Check if API key exists (without exposing it)
        has_api_key = False
        if provider_type == ProviderType.OPENAI:
            # Check Vault first
            try:
                vault_key = await vault_client.get_tenant_secret(
                    tenant_id=str(tenant.id),
                    secret_key="openai_api_key"
                )
                has_api_key = bool(vault_key)
            except Exception:
                pass

            # Check config or fallback
            if not has_api_key:
                has_api_key = bool(config.get("api_key") or app_settings.OPENAI_API_KEY)

        # Get dimensions
        dimensions = config.get("dimensions", 1536)

        logger.info(
            "embedding_provider_retrieved",
            tenant_id=str(tenant.id),
            provider=provider_type.value,
        )

        return EmbeddingProviderResponse(
            provider=provider_type,
            model=config.get("model", "text-embedding-3-small"),
            dimensions=dimensions,
            base_url=config.get("base_url") if provider_type == ProviderType.OLLAMA else None,
            has_api_key=has_api_key,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "get_embedding_provider_failed",
            tenant_id=str(current_user.tenant_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve embedding provider settings"
        )


@router.put("/embedding-provider", response_model=EmbeddingProviderResponse)
async def update_embedding_provider(
    request: EmbeddingProviderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update tenant's embedding provider settings

    This will:
    1. Validate the provider configuration
    2. Test the connection (optional but recommended)
    3. Store API key in Vault (for OpenAI, Claude, Gemini)
    4. Update tenant's embedding_config
    """
    try:
        # Get tenant
        tenant = await db.get(Tenant, current_user.tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )

        # Validate configuration
        config = {
            "provider": request.provider.value,
            "model": request.model,
        }

        # Add provider-specific config
        if request.provider == ProviderType.OPENAI:
            if request.api_key:
                # Store API key in Vault
                try:
                    await vault_client.set_tenant_secret(
                        tenant_id=str(tenant.id),
                        secret_key="openai_api_key",
                        secret_value=request.api_key,
                    )
                    logger.info(
                        "openai_api_key_stored_in_vault",
                        tenant_id=str(tenant.id),
                    )
                except Exception as vault_error:
                    logger.warning(
                        "vault_storage_failed_storing_in_config",
                        tenant_id=str(tenant.id),
                        error=str(vault_error),
                    )
                    # Fallback: store in config (less secure)
                    config["api_key"] = request.api_key

            # Get dimensions for the model
            from app.services.embedding_providers.openai_provider import OpenAIProvider
            config["dimensions"] = OpenAIProvider.MODEL_DIMENSIONS.get(request.model, 1536)

        elif request.provider == ProviderType.OLLAMA:
            config["base_url"] = request.base_url or "http://localhost:11434"
            # Get dimensions for the model
            from app.services.embedding_providers.ollama_provider import OllamaProvider
            config["dimensions"] = OllamaProvider.MODEL_DIMENSIONS.get(request.model, 768)

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Provider {request.provider.value} is not yet supported"
            )

        # Validate config
        is_valid, error_msg = ProviderFactory.validate_config(request.provider, config)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg or "Invalid provider configuration"
            )

        # Update tenant
        tenant.embedding_provider = request.provider.value
        tenant.embedding_config = config

        await db.commit()
        await db.refresh(tenant)

        logger.info(
            "embedding_provider_updated",
            tenant_id=str(tenant.id),
            provider=request.provider.value,
            model=request.model,
        )

        # Return response
        has_api_key = bool(request.api_key or config.get("api_key"))

        return EmbeddingProviderResponse(
            provider=request.provider,
            model=request.model,
            dimensions=config["dimensions"],
            base_url=config.get("base_url"),
            has_api_key=has_api_key,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "update_embedding_provider_failed",
            tenant_id=str(current_user.tenant_id),
            error=str(e),
        )
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update embedding provider: {str(e)}"
        )


@router.post("/embedding-provider/test", response_model=EmbeddingProviderTestResponse)
async def test_embedding_provider(
    request: EmbeddingProviderTest,
    current_user: User = Depends(get_current_user),
):
    """
    Test embedding provider connection

    This will:
    1. Create a provider instance with the given config
    2. Test connection by generating a sample embedding
    3. Return success/failure status

    Does NOT modify any tenant settings.
    """
    try:
        # Prepare config
        config = {
            "model": request.model,
        }

        if request.provider == ProviderType.OPENAI:
            if not request.api_key:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="API key is required for OpenAI"
                )
            config["api_key"] = request.api_key

        elif request.provider == ProviderType.OLLAMA:
            config["base_url"] = request.base_url or "http://localhost:11434"

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Provider {request.provider.value} is not yet supported"
            )

        # Create provider instance
        provider = ProviderFactory.create_provider(request.provider, config)

        # Test connection
        logger.info(
            "testing_embedding_provider_connection",
            tenant_id=str(current_user.tenant_id),
            provider=request.provider.value,
            model=request.model,
        )

        success = await provider.test_connection()

        if success:
            dimensions = provider.get_dimensions()
            logger.info(
                "embedding_provider_test_successful",
                tenant_id=str(current_user.tenant_id),
                provider=request.provider.value,
                dimensions=dimensions,
            )

            return EmbeddingProviderTestResponse(
                success=True,
                message=f"Successfully connected to {request.provider.value} and generated test embedding",
                dimensions=dimensions,
            )
        else:
            logger.warning(
                "embedding_provider_test_failed",
                tenant_id=str(current_user.tenant_id),
                provider=request.provider.value,
            )

            return EmbeddingProviderTestResponse(
                success=False,
                message=f"Failed to connect to {request.provider.value}. Please check your configuration.",
                dimensions=None,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "test_embedding_provider_failed",
            tenant_id=str(current_user.tenant_id),
            error=str(e),
        )
        return EmbeddingProviderTestResponse(
            success=False,
            message=f"Connection test failed: {str(e)}",
            dimensions=None,
        )
