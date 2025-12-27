#!/bin/bash
# Vault Initialization Script for LangOrch
# This script configures Vault for multi-tenant secret management

set -e

echo "🔐 Initializing Vault for LangOrch..."

# Wait for Vault to be ready
echo "⏳ Waiting for Vault to start..."
until vault status >/dev/null 2>&1; do
    echo "   Vault not ready yet, waiting 2 seconds..."
    sleep 2
done

echo "✅ Vault is ready!"

# Set Vault address and token
export VAULT_ADDR='http://127.0.0.1:8200'
export VAULT_TOKEN="${VAULT_DEV_ROOT_TOKEN_ID:-dev-root-token}"

# Enable KV v2 secrets engine for tenants
echo "📝 Enabling KV v2 secrets engine..."
vault secrets enable -version=2 -path=tenants kv || echo "   Secrets engine already enabled"

# Create a policy for tenant secret management
echo "📋 Creating tenant secrets policy..."
vault policy write tenant-secrets - <<EOF
# Allow full access to tenant-specific secrets
path "tenants/data/{{identity.entity.metadata.tenant_id}}/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "tenants/metadata/{{identity.entity.metadata.tenant_id}}/*" {
  capabilities = ["read", "list"]
}

# Allow listing tenant secrets
path "tenants/metadata/{{identity.entity.metadata.tenant_id}}" {
  capabilities = ["list"]
}
EOF

# Create example secrets for default tenant (for testing)
TENANT_ID="4b5b546f-d9ac-4958-8d1f-5405f0d2b311"  # Default admin tenant from seed

echo "🔑 Creating example secrets for default tenant..."
vault kv put tenants/${TENANT_ID}/embedding-providers/openai \
  api_key="sk-example-openai-key-replace-with-real" \
  || echo "   Example secret already exists"

vault kv put tenants/${TENANT_ID}/embedding-providers/claude \
  api_key="sk-ant-example-claude-key-replace-with-real" \
  || echo "   Example secret already exists"

echo ""
echo "🎉 Vault initialization complete!"
echo ""
echo "📝 Vault Configuration:"
echo "   URL: http://localhost:8200"
echo "   Token: ${VAULT_TOKEN}"
echo "   Secrets Engine: tenants/ (KV v2)"
echo ""
echo "📚 Usage Examples:"
echo ""
echo "# Store a secret for a tenant:"
echo "vault kv put tenants/<tenant-id>/embedding-providers/openai api_key=sk-..."
echo ""
echo "# Read a secret:"
echo "vault kv get tenants/<tenant-id>/embedding-providers/openai"
echo ""
echo "# List tenant secrets:"
echo "vault kv list tenants/<tenant-id>/embedding-providers"
echo ""
