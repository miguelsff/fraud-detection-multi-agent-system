#!/bin/bash
# Setup script - Initialize Terraform backend (Azure Storage for state)

set -e

ENVIRONMENT=${1:-dev}

echo "🚀 Setting up Terraform backend for environment: $ENVIRONMENT"

# Configuration
RESOURCE_GROUP="rg-fraud-terraform-state"
LOCATION="eastus"
STORAGE_ACCOUNT="stfraudtfstate${ENVIRONMENT}"
CONTAINER_NAME="tfstate"

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI not found. Please install: https://docs.microsoft.com/cli/azure/install-azure-cli"
    exit 1
fi

# Check if logged in
if ! az account show &> /dev/null; then
    echo "❌ Not logged in to Azure. Run: az login"
    exit 1
fi

echo "✅ Azure CLI authenticated"

# Get subscription info
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
SUBSCRIPTION_NAME=$(az account show --query name -o tsv)
echo "📋 Using subscription: $SUBSCRIPTION_NAME ($SUBSCRIPTION_ID)"

# Create resource group
echo "📦 Creating resource group: $RESOURCE_GROUP"
az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --tags Environment=shared ManagedBy=Terraform Purpose=TerraformState \
  --output none

# Create storage account
echo "💾 Creating storage account: $STORAGE_ACCOUNT"
az storage account create \
  --name "$STORAGE_ACCOUNT" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --encryption-services blob \
  --https-only true \
  --min-tls-version TLS1_2 \
  --allow-blob-public-access false \
  --output none

# Create blob container
echo "📂 Creating blob container: $CONTAINER_NAME"
az storage container create \
  --name "$CONTAINER_NAME" \
  --account-name "$STORAGE_ACCOUNT" \
  --auth-mode login \
  --output none

# Enable versioning (for state recovery)
echo "🔄 Enabling blob versioning"
az storage account blob-service-properties update \
  --resource-group "$RESOURCE_GROUP" \
  --account-name "$STORAGE_ACCOUNT" \
  --enable-versioning true \
  --output none

echo ""
echo "✅ Terraform backend setup complete!"
echo ""
echo "📝 Backend configuration:"
echo "  Resource Group:    $RESOURCE_GROUP"
echo "  Storage Account:   $STORAGE_ACCOUNT"
echo "  Container:         $CONTAINER_NAME"
echo "  State File:        ${ENVIRONMENT}.terraform.tfstate"
echo ""
echo "🔧 Add this to your backend.tf:"
echo ""
echo "terraform {"
echo "  backend \"azurerm\" {"
echo "    resource_group_name  = \"$RESOURCE_GROUP\""
echo "    storage_account_name = \"$STORAGE_ACCOUNT\""
echo "    container_name       = \"$CONTAINER_NAME\""
echo "    key                  = \"${ENVIRONMENT}.terraform.tfstate\""
echo "  }"
echo "}"
echo ""
echo "Next steps:"
echo "  1. cd terraform/environments/${ENVIRONMENT}"
echo "  2. terraform init"
echo "  3. terraform plan"
