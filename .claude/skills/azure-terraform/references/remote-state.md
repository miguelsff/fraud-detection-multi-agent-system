# Remote State Setup

## When to Use Remote State

- Team > 1 person working on same infrastructure
- Deploying to staging or production
- CI/CD pipeline runs Terraform
- Need state locking to prevent conflicts

For solo dev work on a personal project, local state is fine to start.

## Bootstrap Script

Run this ONCE to create the storage account for Terraform state. This is a chicken-and-egg problem — you need to create the state storage before Terraform can use it.

```bash
#!/bin/bash
# bootstrap-state.sh — Run once, manually

RESOURCE_GROUP="rg-terraform-state"
LOCATION="eastus2"
STORAGE_ACCOUNT="stterraformstate${RANDOM}"  # Must be globally unique
CONTAINER="tfstate"

# Create resource group
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION

# Create storage account
az storage account create \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS \
  --encryption-services blob \
  --min-tls-version TLS1_2

# Create blob container
az storage container create \
  --name $CONTAINER \
  --account-name $STORAGE_ACCOUNT

# Enable versioning for state recovery
az storage account blob-service-properties update \
  --account-name $STORAGE_ACCOUNT \
  --enable-versioning true

echo ""
echo "=== Add this to your backend.tf ==="
echo ""
echo 'terraform {'
echo '  backend "azurerm" {'
echo "    resource_group_name  = \"$RESOURCE_GROUP\""
echo "    storage_account_name = \"$STORAGE_ACCOUNT\""
echo "    container_name       = \"$CONTAINER\""
echo '    key                  = "myapp.terraform.tfstate"'
echo '  }'
echo '}'
```

## Backend Configuration

```hcl
# backend.tf

terraform {
  backend "azurerm" {
    resource_group_name  = "rg-terraform-state"
    storage_account_name = "stterraformstateXXXXX"  # From bootstrap output
    container_name       = "tfstate"
    key                  = "myapp.terraform.tfstate"  # Unique per project
  }
}
```

## Multiple Environments, One State Backend

Use different state file keys per environment:

```bash
# Dev
terraform init -backend-config="key=myapp-dev.tfstate"

# Staging
terraform init -backend-config="key=myapp-staging.tfstate"

# Prod
terraform init -backend-config="key=myapp-prod.tfstate"
```

Or use separate storage containers per environment for stronger isolation.

## Migrating from Local to Remote State

```bash
# 1. Add backend.tf with the azurerm backend config
# 2. Run:
terraform init -migrate-state

# Terraform will ask to copy local state to remote — say yes
```

## State Locking

Azure Storage backend automatically uses blob leasing for state locking. No extra configuration needed. If a lock gets stuck:

```bash
terraform force-unlock <LOCK_ID>
```

## Recovering State

If something goes wrong, blob versioning lets you recover previous state:

```bash
az storage blob list \
  --account-name stterraformstateXXXXX \
  --container-name tfstate \
  --include v \
  --query "[?name=='myapp.terraform.tfstate']"
```
