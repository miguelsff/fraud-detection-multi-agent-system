---
name: azure-terraform
description: >
  Deploy infrastructure to Azure using Terraform following industry best practices.
  Use this skill whenever the user mentions Azure deployment, Terraform with Azure,
  Azure infrastructure as code, cloud provisioning on Azure, or wants to create/manage
  any Azure resources programmatically. Also trigger when the user mentions specific
  Azure services like App Service, AKS, Azure SQL, Storage Accounts, VNets, or
  Container Apps in the context of infrastructure setup. Even if the user just says
  "deploy to Azure" or "set up Azure infra", use this skill.
---

# Azure Terraform Deployment Skill

Deploy Azure infrastructure with Terraform using production-grade patterns without overengineering.

## Core Principles

1. **Start simple, scale when needed** — Don't add modules, workspaces, or remote state until the project demands it
2. **Security by default** — No secrets in code, least-privilege access, private endpoints where practical
3. **Repeatable environments** — Same code deploys to dev/staging/prod via variables
4. **Cost awareness** — Always pick the smallest viable SKU, tag everything for cost tracking

## Decision Flow

Before writing any Terraform, determine the deployment type:

```
What are you deploying?
├─ Static site / SPA → Read references/app-service.md (Static Web App section)
├─ Web API / Web App → Read references/app-service.md
├─ Containers (single service) → Read references/container-apps.md
├─ Containers (orchestration) → Read references/aks.md
├─ Database only → Read references/data.md
├─ Full-stack app → Combine relevant references
└─ Networking / VNet setup → Read references/networking.md
```

## Project Structure

Use this standard layout. Do NOT create nested module hierarchies for small/medium projects.

```
infra/
├── main.tf              # Provider config + resource group
├── variables.tf         # Input variables with descriptions and validation
├── outputs.tf           # Useful outputs (URLs, connection strings, IDs)
├── terraform.tfvars     # Default values (NOT secrets — gitignored if contains sensitive data)
├── <resource>.tf        # One file per logical resource group (e.g., app.tf, db.tf, network.tf)
└── environments/        # Only if 2+ environments
    ├── dev.tfvars
    ├── staging.tfvars
    └── prod.tfvars
```

For projects with 3+ environments or team collaboration, add:
```
├── backend.tf           # Remote state config (Azure Storage)
```

**When to use modules:** Only when you have genuinely reusable infrastructure patterns across 2+ projects. A single project does NOT need custom modules — use resource blocks directly.

## Provider Setup (Always Start Here)

```hcl
# main.tf
terraform {
  required_version = ">= 1.5"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

resource "azurerm_resource_group" "main" {
  name     = "rg-${var.project_name}-${var.environment}"
  location = var.location

  tags = local.common_tags
}

locals {
  common_tags = {
    project     = var.project_name
    environment = var.environment
    managed_by  = "terraform"
  }
}
```

```hcl
# variables.tf — Always include these base variables
variable "project_name" {
  description = "Short project identifier used in resource naming"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "Project name must be lowercase alphanumeric with hyphens only."
  }
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus2"
}

variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
  sensitive   = true
}
```

```hcl
# outputs.tf
output "resource_group_name" {
  value = azurerm_resource_group.main.name
}
```

## Naming Convention

Follow Microsoft's Cloud Adoption Framework abbreviations:

| Resource | Prefix | Example |
|----------|--------|---------|
| Resource Group | `rg-` | `rg-myapp-dev` |
| App Service | `app-` | `app-myapp-dev` |
| App Service Plan | `asp-` | `asp-myapp-dev` |
| Container App | `ca-` | `ca-myapp-api-dev` |
| Container App Env | `cae-` | `cae-myapp-dev` |
| SQL Server | `sql-` | `sql-myapp-dev` |
| SQL Database | `sqldb-` | `sqldb-myapp-dev` |
| Storage Account | `st` | `stmyappdev` (no hyphens, max 24 chars) |
| Key Vault | `kv-` | `kv-myapp-dev` |
| Virtual Network | `vnet-` | `vnet-myapp-dev` |
| AKS Cluster | `aks-` | `aks-myapp-dev` |

Pattern: `{prefix}{project}-{environment}`

## Security Checklist

Apply these to EVERY deployment:

1. **No hardcoded secrets** — Use `sensitive = true` on variables, reference Key Vault
2. **Managed Identity** — Prefer `SystemAssigned` identity over connection strings
3. **HTTPS only** — Set `https_only = true` on all web resources
4. **Minimum TLS 1.2** — Set `minimum_tls_version = "1.2"` everywhere available
5. **Tags on everything** — Use `local.common_tags` on all resources
6. **Diagnostics** — Enable diagnostic settings for production workloads

## Remote State (When Needed)

Add when: team > 1 person OR deploying to staging/prod.

```hcl
# backend.tf
terraform {
  backend "azurerm" {
    resource_group_name  = "rg-terraform-state"
    storage_account_name = "stterraformstate"
    container_name       = "tfstate"
    key                  = "myapp.terraform.tfstate"
  }
}
```

Bootstrap script for state storage — read `references/remote-state.md`.

## Common Workflows

### First-time setup
```bash
cd infra/
az login
terraform init
terraform plan -var-file="environments/dev.tfvars"
terraform apply -var-file="environments/dev.tfvars"
```

### Adding a new resource
1. Create or edit the appropriate `.tf` file
2. Run `terraform plan` to preview
3. Run `terraform apply` after review
4. Update `outputs.tf` if the user needs values

### Destroying
```bash
terraform destroy -var-file="environments/dev.tfvars"
```

## What NOT to Do

- Don't create custom modules for a single project
- Don't use `count` when `for_each` with a map is clearer
- Don't hardcode SKUs — use variables with sensible defaults
- Don't skip `terraform plan` before `apply`
- Don't store `.tfstate` in git
- Don't use `latest` tags for container images
- Don't create resources outside the resource group without good reason

## Reference Files

Read these based on what you're deploying:

| File | When to Read |
|------|-------------|
| `references/app-service.md` | Web apps, APIs, static sites on App Service |
| `references/container-apps.md` | Containerized workloads without Kubernetes |
| `references/aks.md` | Kubernetes clusters |
| `references/data.md` | SQL, PostgreSQL, Cosmos DB, Storage Accounts |
| `references/networking.md` | VNets, subnets, NSGs, private endpoints |
| `references/remote-state.md` | Setting up remote state backend |
| `references/cicd.md` | GitHub Actions / Azure DevOps pipelines for Terraform |
