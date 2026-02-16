# Development environment - Main Terraform configuration

terraform {
  required_version = ">= 1.9"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.21"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy    = true
      recover_soft_deleted_key_vaults = true
    }
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
  subscription_id = var.azure_subscription_id
}

# Local values
locals {
  resource_group_name = "rg-${var.project_name}-${var.environment}"
  location            = var.location

  common_tags = merge(
    var.tags,
    {
      Environment = var.environment
      DeployedAt  = timestamp()
    }
  )
}

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = local.resource_group_name
  location = local.location
  tags     = local.common_tags
}

# Networking Module
module "networking" {
  source = "../../modules/networking"

  resource_group_name = azurerm_resource_group.main.name
  location            = local.location
  environment         = var.environment
  project_name        = var.project_name
  tags                = local.common_tags
}

# Container Registry Module
module "container_registry" {
  source = "../../modules/container-registry"

  resource_group_name = azurerm_resource_group.main.name
  location            = local.location
  environment         = var.environment
  project_name        = var.project_name
  sku                 = var.acr_sku
  tags                = local.common_tags
}

# Storage Module (for ChromaDB)
module "storage" {
  source = "../../modules/storage"

  resource_group_name       = azurerm_resource_group.main.name
  location                  = local.location
  environment               = var.environment
  project_name              = var.project_name
  chromadb_share_size_gb    = var.chromadb_storage_size_gb
  subnet_id                 = module.networking.subnet_workload_id
  tags                      = local.common_tags
}

# Database Module
module "database" {
  source = "../../modules/database"

  resource_group_name         = azurerm_resource_group.main.name
  location                    = local.location
  environment                 = var.environment
  project_name                = var.project_name
  sku_name                    = var.postgresql_sku_name
  storage_mb                  = var.postgresql_storage_mb
  backup_retention_days       = var.postgresql_backup_retention_days
  subnet_id                   = module.networking.subnet_postgresql_id
  private_dns_zone_id         = module.networking.private_dns_zone_postgresql_id
  tags                        = local.common_tags

  depends_on = [module.networking]
}

# Azure OpenAI Module
module "azure_openai" {
  source = "../../modules/azure-openai"

  resource_group_name     = azurerm_resource_group.main.name
  location                = local.location
  environment             = var.environment
  project_name            = var.project_name
  gpt35_capacity          = var.azure_openai_gpt35_capacity
  gpt4_capacity           = var.azure_openai_gpt4_capacity
  subnet_id               = module.networking.subnet_workload_id
  tags                    = local.common_tags
}

# Monitoring Module
module "monitoring" {
  source = "../../modules/monitoring"

  resource_group_name    = azurerm_resource_group.main.name
  location               = local.location
  environment            = var.environment
  project_name           = var.project_name
  retention_days         = var.log_analytics_retention_days
  sampling_percentage    = var.app_insights_sampling_percentage
  tags                   = local.common_tags
}

# Key Vault Module
module "key_vault" {
  source = "../../modules/key-vault"

  resource_group_name = azurerm_resource_group.main.name
  location            = local.location
  environment         = var.environment
  project_name        = var.project_name
  subnet_id           = module.networking.subnet_workload_id
  tenant_id           = var.azure_tenant_id

  # Secrets (will be synced from GitHub Secrets via script)
  secrets = {
    database-url          = module.database.connection_string
    azure-openai-endpoint = module.azure_openai.endpoint
    azure-openai-key      = module.azure_openai.primary_key
  }

  tags = local.common_tags

  depends_on = [
    module.database,
    module.azure_openai
  ]
}

# Container Apps Module
module "container_apps" {
  source = "../../modules/container-apps"

  resource_group_name           = azurerm_resource_group.main.name
  location                      = local.location
  environment                   = var.environment
  project_name                  = var.project_name

  # Networking
  subnet_infra_id               = module.networking.subnet_container_apps_infra_id
  subnet_workload_id            = module.networking.subnet_workload_id

  # Container Registry
  container_registry_id          = module.container_registry.id
  container_registry_server      = module.container_registry.login_server
  container_registry_identity_id = module.container_registry.identity_principal_id

  # Storage (ChromaDB)
  storage_account_name          = module.storage.account_name
  storage_share_name            = module.storage.chromadb_share_name
  storage_access_key            = module.storage.access_key

  # Key Vault
  key_vault_id                  = module.key_vault.id
  key_vault_secrets = {
    "database-url"          = module.database.connection_string
    "azure-openai-endpoint" = module.azure_openai.endpoint
    "azure-openai-key"      = module.azure_openai.primary_key
  }

  # Monitoring
  app_insights_connection_string = module.monitoring.connection_string
  log_analytics_workspace_id     = module.monitoring.workspace_id

  # Backend configuration
  backend_replicas_min          = var.backend_replicas_min
  backend_replicas_max          = var.backend_replicas_max
  backend_cpu                   = var.backend_cpu
  backend_memory                = var.backend_memory

  # Frontend configuration
  frontend_replicas_min         = var.frontend_replicas_min
  frontend_replicas_max         = var.frontend_replicas_max
  frontend_cpu                  = var.frontend_cpu
  frontend_memory               = var.frontend_memory

  tags = local.common_tags

  depends_on = [
    module.networking,
    module.container_registry,
    module.storage,
    module.key_vault,
    module.monitoring
  ]
}
