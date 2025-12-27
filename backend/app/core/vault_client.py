"""
HashiCorp Vault Client for Secure Secret Management
"""
from typing import Optional, Dict, Any
import hvac
import structlog
from app.core.config import settings

logger = structlog.get_logger()


class VaultClient:
    """
    Vault client for managing tenant secrets

    Supports graceful degradation - if Vault is not available,
    falls back to environment variables without breaking the application.
    """

    def __init__(self):
        self.client: Optional[hvac.Client] = None
        self.enabled = False

        if settings.VAULT_ENABLED:
            try:
                self.client = hvac.Client(
                    url=settings.VAULT_URL,
                    token=settings.VAULT_TOKEN
                )

                # Test connection
                if self.client.is_authenticated():
                    self.enabled = True
                    logger.info(
                        "vault_connected",
                        url=settings.VAULT_URL,
                        status="authenticated"
                    )
                else:
                    logger.warning(
                        "vault_authentication_failed",
                        url=settings.VAULT_URL
                    )
            except Exception as e:
                logger.warning(
                    "vault_connection_failed",
                    error=str(e),
                    fallback="environment_variables"
                )
        else:
            logger.info("vault_disabled", fallback="environment_variables")

    def get_secret(
        self,
        tenant_id: str,
        secret_path: str,
        key: str
    ) -> Optional[str]:
        """
        Get a secret from Vault for a specific tenant

        Args:
            tenant_id: Tenant UUID
            secret_path: Path under tenant (e.g., 'embedding-providers/openai')
            key: Secret key (e.g., 'api_key')

        Returns:
            Secret value or None if not found

        Example:
            api_key = vault.get_secret(
                tenant_id="uuid-here",
                secret_path="embedding-providers/openai",
                key="api_key"
            )
        """
        if not self.enabled or not self.client:
            return None

        try:
            full_path = f"tenants/{tenant_id}/{secret_path}"
            response = self.client.secrets.kv.v2.read_secret_version(
                path=full_path,
                mount_point="tenants"
            )

            secret_data = response.get("data", {}).get("data", {})
            value = secret_data.get(key)

            if value:
                logger.info(
                    "vault_secret_retrieved",
                    tenant_id=tenant_id,
                    path=secret_path,
                    key=key
                )

            return value

        except hvac.exceptions.InvalidPath:
            logger.debug(
                "vault_secret_not_found",
                tenant_id=tenant_id,
                path=secret_path,
                key=key
            )
            return None
        except Exception as e:
            logger.error(
                "vault_get_secret_error",
                tenant_id=tenant_id,
                path=secret_path,
                error=str(e)
            )
            return None

    def set_secret(
        self,
        tenant_id: str,
        secret_path: str,
        secrets: Dict[str, str]
    ) -> bool:
        """
        Store secrets in Vault for a specific tenant

        Args:
            tenant_id: Tenant UUID
            secret_path: Path under tenant
            secrets: Dictionary of key-value pairs to store

        Returns:
            True if successful, False otherwise

        Example:
            success = vault.set_secret(
                tenant_id="uuid-here",
                secret_path="embedding-providers/openai",
                secrets={"api_key": "sk-..."}
            )
        """
        if not self.enabled or not self.client:
            logger.warning("vault_disabled_cannot_store_secret")
            return False

        try:
            full_path = f"tenants/{tenant_id}/{secret_path}"
            self.client.secrets.kv.v2.create_or_update_secret(
                path=full_path,
                secret=secrets,
                mount_point="tenants"
            )

            logger.info(
                "vault_secret_stored",
                tenant_id=tenant_id,
                path=secret_path,
                keys=list(secrets.keys())
            )
            return True

        except Exception as e:
            logger.error(
                "vault_set_secret_error",
                tenant_id=tenant_id,
                path=secret_path,
                error=str(e)
            )
            return False

    def delete_secret(
        self,
        tenant_id: str,
        secret_path: str
    ) -> bool:
        """
        Delete a secret from Vault

        Args:
            tenant_id: Tenant UUID
            secret_path: Path under tenant

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.client:
            return False

        try:
            full_path = f"tenants/{tenant_id}/{secret_path}"
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=full_path,
                mount_point="tenants"
            )

            logger.info(
                "vault_secret_deleted",
                tenant_id=tenant_id,
                path=secret_path
            )
            return True

        except Exception as e:
            logger.error(
                "vault_delete_secret_error",
                tenant_id=tenant_id,
                path=secret_path,
                error=str(e)
            )
            return False

    def list_secrets(
        self,
        tenant_id: str,
        secret_path: str = ""
    ) -> list[str]:
        """
        List all secrets under a path for a tenant

        Args:
            tenant_id: Tenant UUID
            secret_path: Path under tenant (optional)

        Returns:
            List of secret names
        """
        if not self.enabled or not self.client:
            return []

        try:
            full_path = f"tenants/{tenant_id}"
            if secret_path:
                full_path = f"{full_path}/{secret_path}"

            response = self.client.secrets.kv.v2.list_secrets(
                path=full_path,
                mount_point="tenants"
            )

            keys = response.get("data", {}).get("keys", [])
            return keys

        except hvac.exceptions.InvalidPath:
            return []
        except Exception as e:
            logger.error(
                "vault_list_secrets_error",
                tenant_id=tenant_id,
                path=secret_path,
                error=str(e)
            )
            return []


# Singleton instance
_vault_client: Optional[VaultClient] = None


def get_vault_client() -> VaultClient:
    """Get or create Vault client singleton"""
    global _vault_client
    if _vault_client is None:
        _vault_client = VaultClient()
    return _vault_client
