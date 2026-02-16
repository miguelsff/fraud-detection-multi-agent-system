#!/bin/bash
# Sync secrets to Key Vault from environment variables or .env file

set -e

ENVIRONMENT=${1:-dev}

echo "🔐 Syncing secrets to Key Vault for environment: $ENVIRONMENT"

# Configuration
TERRAFORM_DIR="terraform/environments/${ENVIRONMENT}"

if [ ! -d "$TERRAFORM_DIR" ]; then
    echo "❌ Environment directory not found: $TERRAFORM_DIR"
    exit 1
fi

cd "$TERRAFORM_DIR"

# Get Key Vault name from Terraform outputs
echo "🔍 Getting Key Vault info from Terraform..."
KEY_VAULT_NAME=$(terraform output -raw key_vault_name 2>/dev/null) || {
    echo "❌ Failed to get Key Vault name. Has infrastructure been deployed?"
    exit 1
}

echo "✅ Key Vault: $KEY_VAULT_NAME"

# Go back to repo root
cd ../../..

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI not found. Please install: https://docs.microsoft.com/cli/azure/install-azure-cli"
    exit 1
fi

# Prompt for secrets if not in environment
if [ -z "$OPENSANCTIONS_API_KEY" ]; then
    read -sp "🔑 Enter OpenSanctions API Key: " OPENSANCTIONS_API_KEY
    echo ""
fi

# Set secrets in Key Vault
echo "📝 Setting secrets in Key Vault..."

# OpenSanctions API Key
if [ -n "$OPENSANCTIONS_API_KEY" ]; then
    echo "  - opensanctions-api-key"
    az keyvault secret set \
        --vault-name "$KEY_VAULT_NAME" \
        --name "opensanctions-api-key" \
        --value "$OPENSANCTIONS_API_KEY" \
        --output none
fi

# Database URL (already set by Terraform, but can update if needed)
# Azure OpenAI credentials (already set by Terraform)

echo ""
echo "✅ Secrets synced to Key Vault!"
echo ""
echo "📋 Current secrets:"
az keyvault secret list \
    --vault-name "$KEY_VAULT_NAME" \
    --query '[].name' \
    --output table

echo ""
echo "⚠️  Note: Container Apps need to be restarted to pick up new secrets."
echo "   Run: az containerapp revision restart --name <app-name> --resource-group <rg>"
