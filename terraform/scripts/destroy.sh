#!/bin/bash
# Destroy script - Tear down infrastructure

set -e

ENVIRONMENT=${1:-dev}

echo "⚠️  WARNING: This will destroy ALL infrastructure for environment: $ENVIRONMENT"
echo "⚠️  This action is IRREVERSIBLE!"
echo ""

# Configuration
TERRAFORM_DIR="terraform/environments/${ENVIRONMENT}"

if [ ! -d "$TERRAFORM_DIR" ]; then
    echo "❌ Environment directory not found: $TERRAFORM_DIR"
    exit 1
fi

cd "$TERRAFORM_DIR"

# Confirm
read -p "🤔 Type the environment name to confirm destruction: " CONFIRM
if [ "$CONFIRM" != "$ENVIRONMENT" ]; then
    echo "❌ Confirmation failed. Aborting."
    exit 0
fi

read -p "🔴 Are you ABSOLUTELY SURE? (yes/no): " FINAL_CONFIRM
if [ "$FINAL_CONFIRM" != "yes" ]; then
    echo "❌ Destruction cancelled"
    exit 0
fi

# Initialize (in case not initialized)
echo "🔧 Initializing Terraform..."
terraform init

# Destroy
echo "💥 Destroying infrastructure..."
terraform destroy

echo ""
echo "✅ Infrastructure destroyed for environment: $ENVIRONMENT"
echo ""
echo "⚠️  Note: Terraform state backend (storage account) was NOT destroyed."
echo "   To remove it manually:"
echo "   az group delete --name rg-fraud-terraform-state --yes"
