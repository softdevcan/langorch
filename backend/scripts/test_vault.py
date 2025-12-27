"""Test Vault connectivity and secret retrieval"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.core.vault_client import get_vault_client

def test_vault():
    print("Testing Vault connectivity...\n")

    vault = get_vault_client()

    if not vault.enabled:
        print("❌ Vault is not enabled or not connected")
        return

    print("✅ Vault connected successfully!\n")

    # Test retrieving the secret we just created
    tenant_id = "4b5b546f-d9ac-4958-8d1f-5405f0d2b311"

    print(f"Retrieving secret for tenant: {tenant_id}")
    api_key = vault.get_secret(
        tenant_id=tenant_id,
        secret_path="embedding-providers/openai",
        key="api_key"
    )

    if api_key:
        print(f"✅ Secret retrieved: {api_key[:10]}...{api_key[-10:]}")
    else:
        print("❌ Failed to retrieve secret")

    # Test storing a new secret
    print("\nStoring a new secret...")
    success = vault.set_secret(
        tenant_id=tenant_id,
        secret_path="embedding-providers/ollama",
        secrets={"base_url": "http://ollama:11434", "model": "nomic-embed-text"}
    )

    if success:
        print("✅ Secret stored successfully")
    else:
        print("❌ Failed to store secret")

    # Test listing secrets
    print("\nListing tenant secrets...")
    secrets = vault.list_secrets(
        tenant_id=tenant_id,
        secret_path="embedding-providers"
    )

    print(f"Found {len(secrets)} secret(s):")
    for secret in secrets:
        print(f"  - {secret}")

if __name__ == "__main__":
    test_vault()
