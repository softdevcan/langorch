"""
Secret management endpoints (API keys, tokens, etc.)
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
import structlog

from app.core.vault import vault_client
from app.core.exceptions import http_400_bad_request
from app.api.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.schemas import MessageResponse

logger = structlog.get_logger()

router = APIRouter(prefix="/secrets", tags=["Secrets"])


class ApiKeyRequest(BaseModel):
    """Request schema for setting API keys"""
    provider: str = Field(..., description="Provider name (openai, anthropic, etc.)")
    api_key: str = Field(..., min_length=1, description="API key value")


class ApiKeyResponse(BaseModel):
    """Response schema for API key status"""
    provider: str
    key_set: bool
    key_preview: str = Field(..., description="First 8 chars of key (masked)")


@router.post(
    "/api-keys",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Set API key",
    description="Set API key for a provider (requires tenant admin)",
)
async def set_api_key(
    request: ApiKeyRequest,
    current_user: User = Depends(require_role(UserRole.TENANT_ADMIN, UserRole.SUPER_ADMIN)),
):
    """
    Set API key for a provider

    - **provider**: Provider name (e.g., 'openai', 'anthropic')
    - **api_key**: API key value

    Stores the key securely in HashiCorp Vault under tenant namespace.

    Supported providers:
    - openai: OpenAI API key (for embeddings and chat)
    - anthropic: Anthropic API key (for Claude models)

    Requires: TENANT_ADMIN or SUPER_ADMIN role
    """
    if not current_user.tenant_id:
        raise http_400_bad_request(
            detail="Super admins must specify a tenant_id"
        )

    # Normalize provider name
    provider = request.provider.lower()
    secret_key = f"{provider}_api_key"

    try:
        # Store in Vault
        success = await vault_client.set_tenant_secret(
            tenant_id=str(current_user.tenant_id),
            secret_key=secret_key,
            secret_value=request.api_key,
        )

        if not success:
            raise http_400_bad_request(detail="Failed to store API key")

        logger.info(
            "api_key_set",
            tenant_id=str(current_user.tenant_id),
            provider=provider,
            set_by=str(current_user.id),
        )

        return MessageResponse(
            message="API key stored successfully",
            detail=f"{provider.capitalize()} API key has been securely stored in Vault"
        )

    except Exception as e:
        logger.error(
            "api_key_storage_failed",
            tenant_id=str(current_user.tenant_id),
            provider=provider,
            error=str(e),
        )
        raise http_400_bad_request(detail=f"Failed to store API key: {str(e)}")


@router.get(
    "/api-keys/{provider}",
    response_model=ApiKeyResponse,
    status_code=status.HTTP_200_OK,
    summary="Check API key status",
    description="Check if API key is set for a provider",
)
async def get_api_key_status(
    provider: str,
    current_user: User = Depends(require_role(UserRole.TENANT_ADMIN, UserRole.SUPER_ADMIN)),
):
    """
    Check if API key is set for a provider

    - **provider**: Provider name (e.g., 'openai', 'anthropic')

    Returns:
    - key_set: Whether key is configured
    - key_preview: First 8 characters (masked)

    Does NOT return the actual key for security reasons.

    Requires: TENANT_ADMIN or SUPER_ADMIN role
    """
    if not current_user.tenant_id:
        raise http_400_bad_request(
            detail="Super admins must specify a tenant_id"
        )

    # Normalize provider name
    provider = provider.lower()
    secret_key = f"{provider}_api_key"

    try:
        # Get from Vault
        api_key = await vault_client.get_tenant_secret(
            tenant_id=str(current_user.tenant_id),
            secret_key=secret_key,
        )

        if api_key:
            # Mask key (show first 8 chars + asterisks)
            preview = api_key[:8] + "*" * (len(api_key) - 8)

            return ApiKeyResponse(
                provider=provider,
                key_set=True,
                key_preview=preview,
            )
        else:
            return ApiKeyResponse(
                provider=provider,
                key_set=False,
                key_preview="Not set",
            )

    except Exception as e:
        logger.error(
            "api_key_retrieval_failed",
            tenant_id=str(current_user.tenant_id),
            provider=provider,
            error=str(e),
        )
        raise http_400_bad_request(detail=f"Failed to retrieve API key status: {str(e)}")


@router.delete(
    "/api-keys/{provider}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete API key",
    description="Delete API key for a provider",
)
async def delete_api_key(
    provider: str,
    current_user: User = Depends(require_role(UserRole.TENANT_ADMIN, UserRole.SUPER_ADMIN)),
):
    """
    Delete API key for a provider

    - **provider**: Provider name (e.g., 'openai', 'anthropic')

    Removes the key from HashiCorp Vault.

    Requires: TENANT_ADMIN or SUPER_ADMIN role
    """
    if not current_user.tenant_id:
        raise http_400_bad_request(
            detail="Super admins must specify a tenant_id"
        )

    # Normalize provider name
    provider = provider.lower()
    secret_key = f"{provider}_api_key"

    try:
        # Delete from Vault
        success = await vault_client.delete_tenant_secret(
            tenant_id=str(current_user.tenant_id),
            secret_key=secret_key,
        )

        if not success:
            raise http_400_bad_request(detail="API key not found or already deleted")

        logger.info(
            "api_key_deleted",
            tenant_id=str(current_user.tenant_id),
            provider=provider,
            deleted_by=str(current_user.id),
        )

        return MessageResponse(
            message="API key deleted successfully",
            detail=f"{provider.capitalize()} API key has been removed from Vault"
        )

    except Exception as e:
        logger.error(
            "api_key_deletion_failed",
            tenant_id=str(current_user.tenant_id),
            provider=provider,
            error=str(e),
        )
        raise http_400_bad_request(detail=f"Failed to delete API key: {str(e)}")


@router.get(
    "/api-keys",
    response_model=Dict[str, ApiKeyResponse],
    status_code=status.HTTP_200_OK,
    summary="List all API keys",
    description="List status of all configured API keys",
)
async def list_api_keys(
    current_user: User = Depends(require_role(UserRole.TENANT_ADMIN, UserRole.SUPER_ADMIN)),
):
    """
    List all configured API keys for the tenant

    Returns status for all supported providers:
    - openai
    - anthropic

    Shows which keys are set and their previews.

    Requires: TENANT_ADMIN or SUPER_ADMIN role
    """
    if not current_user.tenant_id:
        raise http_400_bad_request(
            detail="Super admins must specify a tenant_id"
        )

    providers = ["openai", "anthropic"]
    results = {}

    try:
        # Get all secrets for tenant
        all_secrets = await vault_client.get_tenant_secrets(
            tenant_id=str(current_user.tenant_id),
        )

        for provider in providers:
            secret_key = f"{provider}_api_key"
            api_key = all_secrets.get(secret_key) if all_secrets else None

            if api_key:
                preview = api_key[:8] + "*" * (len(api_key) - 8)
                results[provider] = ApiKeyResponse(
                    provider=provider,
                    key_set=True,
                    key_preview=preview,
                )
            else:
                results[provider] = ApiKeyResponse(
                    provider=provider,
                    key_set=False,
                    key_preview="Not set",
                )

        return results

    except Exception as e:
        logger.error(
            "api_keys_list_failed",
            tenant_id=str(current_user.tenant_id),
            error=str(e),
        )
        raise http_400_bad_request(detail=f"Failed to list API keys: {str(e)}")
