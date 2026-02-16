#!/bin/bash
# Migrate ChromaDB data from local to Azure Files

set -e

ENVIRONMENT=${1:-dev}

echo "📦 Migrating ChromaDB data to Azure Files for environment: $ENVIRONMENT"

# Configuration
LOCAL_CHROMA_DIR="backend/data/chroma"
TERRAFORM_DIR="terraform/environments/${ENVIRONMENT}"

if [ ! -d "$LOCAL_CHROMA_DIR" ]; then
    echo "❌ Local ChromaDB directory not found: $LOCAL_CHROMA_DIR"
    echo "   Run 'python backend/seed_test.py' to generate test data first."
    exit 1
fi

if [ ! -d "$TERRAFORM_DIR" ]; then
    echo "❌ Environment directory not found: $TERRAFORM_DIR"
    exit 1
fi

cd "$TERRAFORM_DIR"

# Get storage account info from Terraform outputs
echo "🔍 Getting storage account info from Terraform..."
STORAGE_ACCOUNT=$(terraform output -raw storage_account_name 2>/dev/null) || {
    echo "❌ Failed to get storage account name. Has infrastructure been deployed?"
    exit 1
}

SHARE_NAME=$(terraform output -raw chromadb_share_name 2>/dev/null) || {
    echo "❌ Failed to get share name from Terraform outputs"
    exit 1
}

echo "✅ Storage Account: $STORAGE_ACCOUNT"
echo "✅ Share Name: $SHARE_NAME"

# Go back to repo root
cd ../../..

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI not found. Please install: https://docs.microsoft.com/cli/azure/install-azure-cli"
    exit 1
fi

# Get storage account key
echo "🔑 Getting storage account key..."
STORAGE_KEY=$(az storage account keys list \
    --account-name "$STORAGE_ACCOUNT" \
    --query '[0].value' \
    --output tsv)

# Upload files to Azure Files
echo "⬆️  Uploading ChromaDB data to Azure Files..."
az storage file upload-batch \
    --destination "$SHARE_NAME" \
    --source "$LOCAL_CHROMA_DIR" \
    --account-name "$STORAGE_ACCOUNT" \
    --account-key "$STORAGE_KEY" \
    --no-progress

echo ""
echo "✅ ChromaDB migration complete!"
echo ""
echo "📊 Verification:"
az storage file list \
    --share-name "$SHARE_NAME" \
    --account-name "$STORAGE_ACCOUNT" \
    --account-key "$STORAGE_KEY" \
    --output table

echo ""
echo "🔗 Azure Files URL:"
echo "https://${STORAGE_ACCOUNT}.file.core.windows.net/${SHARE_NAME}/"
