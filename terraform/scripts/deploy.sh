#!/bin/bash
# Deploy script - Full deployment of infrastructure

set -e

ENVIRONMENT=${1:-dev}

echo "🚀 Deploying infrastructure for environment: $ENVIRONMENT"

# Configuration
TERRAFORM_DIR="terraform/environments/${ENVIRONMENT}"

if [ ! -d "$TERRAFORM_DIR" ]; then
    echo "❌ Environment directory not found: $TERRAFORM_DIR"
    exit 1
fi

cd "$TERRAFORM_DIR"

# Check if terraform.tfvars exists
if [ ! -f "terraform.tfvars" ]; then
    echo "❌ terraform.tfvars not found. Copy from terraform.tfvars.example and fill in values."
    exit 1
fi

# Initialize Terraform
echo "🔧 Initializing Terraform..."
terraform init -upgrade

# Validate configuration
echo "🔍 Validating configuration..."
terraform validate

# Format check
echo "📝 Checking formatting..."
terraform fmt -check -recursive || {
    echo "⚠️  Formatting issues found. Run 'terraform fmt -recursive' to fix."
}

# Plan
echo "📋 Planning deployment..."
terraform plan -out=tfplan

# Confirm
read -p "🤔 Do you want to apply this plan? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "❌ Deployment cancelled"
    rm -f tfplan
    exit 0
fi

# Apply
echo "🚀 Applying deployment..."
terraform apply tfplan

# Cleanup
rm -f tfplan

# Get outputs
echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Outputs:"
terraform output

# Health check
echo ""
read -p "🏥 Run health check? (yes/no): " RUN_HEALTH
if [ "$RUN_HEALTH" = "yes" ]; then
    cd ../../..
    bash terraform/scripts/health-check.sh "$ENVIRONMENT"
fi
