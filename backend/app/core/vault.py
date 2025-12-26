"""
HashiCorp Vault client for secure secret management
"""
from typing import Optional, Dict, Any
import hvac
from hvac.exceptions import VaultError
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class VaultClient:
    """
    HashiCorp Vault client for managing tenant secrets

    Each tenant has their own secret space in Vault:
    - Path: secret/tenants/{tenant_id}/
    - Stores: OpenAI API keys, Anthropic API keys, etc.
    """

    def __init__(self):
        """Initialize Vault client"""
        self._client: Optional[hvac.Client] = None
        self._initialized = False

    def _ensure_client(self) -> hvac.Client:
        """
        Ensure Vault client is initialized and authenticated

        Returns:
            Authenticated Vault client

        Raises:
            VaultError: If Vault connection fails
        """
        if not self._client or not self._initialized:
            try:
                self._client = hvac.Client(
                    url=settings.VAULT_ADDR,
                    token=settings.VAULT_TOKEN,
                )

                # Verify authentication
                if not self._client.is_authenticated():
                    raise VaultError("Vault authentication failed")

                self._initialized = True
                logger.info(
                    "vault_client_initialized",
                    vault_addr=settings.VAULT_ADDR,
                    mount_point=settings.VAULT_MOUNT_POINT,
                )

            except Exception as e:
                logger.error(
                    "vault_client_initialization_failed",
                    error=str(e),
                    vault_addr=settings.VAULT_ADDR,
                )
                raise VaultError(f"Failed to initialize Vault client: {str(e)}")

        return self._client

    def _get_tenant_path(self, tenant_id: str) -> str:
        """
        Get Vault path for tenant secrets

        Args:
            tenant_id: Tenant UUID

        Returns:
            Vault path (e.g., 'tenants/abc123')
        """
        return f"{settings.VAULT_TENANT_PATH}/{tenant_id}"

    async def set_tenant_secret(
        self,
        tenant_id: str,
        secret_key: str,
        secret_value: str,
    ) -> bool:
        """
        Store a secret for a tenant in Vault

        Args:
            tenant_id: Tenant UUID
            secret_key: Secret key name (e.g., 'openai_api_key')
            secret_value: Secret value

        Returns:
            True if successful

        Raises:
            VaultError: If operation fails
        """
        try:
            client = self._ensure_client()
            path = self._get_tenant_path(tenant_id)

            # Read existing secrets first
            existing_secrets = await self.get_tenant_secrets(tenant_id) or {}

            # Update with new secret
            existing_secrets[secret_key] = secret_value

            # Write back to Vault
            client.secrets.kv.v2.create_or_update_secret(
                path=path,
                secret=existing_secrets,
                mount_point=settings.VAULT_MOUNT_POINT,
            )

            logger.info(
                "tenant_secret_stored",
                tenant_id=tenant_id,
                secret_key=secret_key,
                path=path,
            )

            return True

        except Exception as e:
            logger.error(
                "tenant_secret_store_failed",
                tenant_id=tenant_id,
                secret_key=secret_key,
                error=str(e),
            )
            raise VaultError(f"Failed to store secret: {str(e)}")

    async def get_tenant_secret(
        self,
        tenant_id: str,
        secret_key: str,
    ) -> Optional[str]:
        """
        Retrieve a specific secret for a tenant

        Args:
            tenant_id: Tenant UUID
            secret_key: Secret key name (e.g., 'openai_api_key')

        Returns:
            Secret value or None if not found
        """
        try:
            secrets = await self.get_tenant_secrets(tenant_id)
            return secrets.get(secret_key) if secrets else None

        except Exception as e:
            logger.error(
                "tenant_secret_retrieval_failed",
                tenant_id=tenant_id,
                secret_key=secret_key,
                error=str(e),
            )
            return None

    async def get_tenant_secrets(
        self,
        tenant_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve all secrets for a tenant

        Args:
            tenant_id: Tenant UUID

        Returns:
            Dictionary of secrets or None if not found
        """
        try:
            client = self._ensure_client()
            path = self._get_tenant_path(tenant_id)

            response = client.secrets.kv.v2.read_secret_version(
                path=path,
                mount_point=settings.VAULT_MOUNT_POINT,
            )

            secrets = response.get("data", {}).get("data", {})

            logger.debug(
                "tenant_secrets_retrieved",
                tenant_id=tenant_id,
                secret_count=len(secrets),
            )

            return secrets

        except hvac.exceptions.InvalidPath:
            logger.debug(
                "tenant_secrets_not_found",
                tenant_id=tenant_id,
            )
            return None

        except Exception as e:
            logger.error(
                "tenant_secrets_retrieval_failed",
                tenant_id=tenant_id,
                error=str(e),
            )
            return None

    async def delete_tenant_secret(
        self,
        tenant_id: str,
        secret_key: str,
    ) -> bool:
        """
        Delete a specific secret for a tenant

        Args:
            tenant_id: Tenant UUID
            secret_key: Secret key name

        Returns:
            True if successful
        """
        try:
            client = self._ensure_client()
            path = self._get_tenant_path(tenant_id)

            # Read existing secrets
            existing_secrets = await self.get_tenant_secrets(tenant_id) or {}

            # Remove the secret
            if secret_key in existing_secrets:
                del existing_secrets[secret_key]

                # Write back to Vault
                if existing_secrets:
                    client.secrets.kv.v2.create_or_update_secret(
                        path=path,
                        secret=existing_secrets,
                        mount_point=settings.VAULT_MOUNT_POINT,
                    )
                else:
                    # Delete entire secret if no keys left
                    client.secrets.kv.v2.delete_metadata_and_all_versions(
                        path=path,
                        mount_point=settings.VAULT_MOUNT_POINT,
                    )

                logger.info(
                    "tenant_secret_deleted",
                    tenant_id=tenant_id,
                    secret_key=secret_key,
                )

                return True

            return False

        except Exception as e:
            logger.error(
                "tenant_secret_deletion_failed",
                tenant_id=tenant_id,
                secret_key=secret_key,
                error=str(e),
            )
            return False

    async def delete_all_tenant_secrets(
        self,
        tenant_id: str,
    ) -> bool:
        """
        Delete all secrets for a tenant

        Args:
            tenant_id: Tenant UUID

        Returns:
            True if successful
        """
        try:
            client = self._ensure_client()
            path = self._get_tenant_path(tenant_id)

            client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=path,
                mount_point=settings.VAULT_MOUNT_POINT,
            )

            logger.info(
                "all_tenant_secrets_deleted",
                tenant_id=tenant_id,
            )

            return True

        except hvac.exceptions.InvalidPath:
            # Secret doesn't exist, that's fine
            return True

        except Exception as e:
            logger.error(
                "all_tenant_secrets_deletion_failed",
                tenant_id=tenant_id,
                error=str(e),
            )
            return False


# Global Vault client instance
vault_client = VaultClient()
