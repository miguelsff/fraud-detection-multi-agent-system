# ============================================================================
# FRAUD DETECTION MULTI-AGENT SYSTEM - Azure Infrastructure (KISS)
# ============================================================================
# Single-file configuration for all resources
# Resource Group: rg-fraudguard

terraform {
  required_version = ">= 1.9"

  backend "azurerm" {
    resource_group_name  = "rg-fraudguard"
    storage_account_name = "stfraudguardtfstate"
    container_name       = "tfstate"
    key                  = "fraudguard.tfstate"
  }

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.21"
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

# ============================================================================
# LOCALS
# ============================================================================

locals {
  # Fixed suffix matching existing resources (was random_string, now hardcoded to prevent drift)
  name_suffix = "ytxme4"
  common_tags = {
    Project   = "FraudGuard Multi-Agent System"
    ManagedBy = "Terraform"
  }
  # Derive URLs from environment domain (no circular dependency)
  backend_fqdn  = "ca-fraudguard-backend.${azurerm_container_app_environment.main.default_domain}"
  frontend_fqdn = "ca-fraudguard-frontend.${azurerm_container_app_environment.main.default_domain}"
}

# ============================================================================
# RESOURCE GROUP
# ============================================================================

resource "azurerm_resource_group" "main" {
  name     = "rg-fraudguard"
  location = var.location
  tags     = local.common_tags
}

# ============================================================================
# NETWORKING
# ============================================================================

resource "azurerm_virtual_network" "main" {
  name                = "vnet-fraudguard"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  address_space       = ["10.0.0.0/16"]
  tags                = local.common_tags
}

# Subnet para Container Apps Infrastructure (requiere /23 mínimo)
resource "azurerm_subnet" "container_apps_infra" {
  name                 = "snet-container-apps-infra"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.0.0/23"]

  delegation {
    name = "delegation"
    service_delegation {
      name = "Microsoft.App/environments"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action"
      ]
    }
  }
}

# Subnet para workloads
resource "azurerm_subnet" "workload" {
  name                 = "snet-workload"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.2.0/24"]
  service_endpoints    = ["Microsoft.Storage", "Microsoft.KeyVault", "Microsoft.CognitiveServices"]
}

# Subnet para PostgreSQL (delegada)
resource "azurerm_subnet" "postgresql" {
  name                 = "snet-postgresql"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.3.0/24"]
  service_endpoints    = ["Microsoft.Storage"]

  delegation {
    name = "delegation"
    service_delegation {
      name = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action"
      ]
    }
  }
}

# NAT Gateway — required for Container Apps in VNet to reach external services
resource "azurerm_public_ip" "nat" {
  name                = "pip-nat-fraudguard"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = local.common_tags
}

resource "azurerm_nat_gateway" "main" {
  name                    = "natgw-fraudguard"
  resource_group_name     = azurerm_resource_group.main.name
  location                = azurerm_resource_group.main.location
  sku_name                = "Standard"
  idle_timeout_in_minutes = 10
  tags                    = local.common_tags
}

resource "azurerm_nat_gateway_public_ip_association" "main" {
  nat_gateway_id       = azurerm_nat_gateway.main.id
  public_ip_address_id = azurerm_public_ip.nat.id
}

resource "azurerm_subnet_nat_gateway_association" "container_apps" {
  subnet_id      = azurerm_subnet.container_apps_infra.id
  nat_gateway_id = azurerm_nat_gateway.main.id
}

# Private DNS Zone para PostgreSQL
resource "azurerm_private_dns_zone" "postgresql" {
  name                = "privatelink.postgres.database.azure.com"
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.common_tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "postgresql" {
  name                  = "pdnsl-postgresql"
  resource_group_name   = azurerm_resource_group.main.name
  private_dns_zone_name = azurerm_private_dns_zone.postgresql.name
  virtual_network_id    = azurerm_virtual_network.main.id
  tags                  = local.common_tags
}

# ============================================================================
# CONTAINER REGISTRY
# ============================================================================

resource "azurerm_container_registry" "main" {
  name                = "acrfraudguard"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic"
  admin_enabled       = true
  tags                = local.common_tags
}

# ============================================================================
# STORAGE (ChromaDB Azure Files)
# ============================================================================

resource "azurerm_storage_account" "main" {
  name                       = "stfraudguard${local.name_suffix}"
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  account_tier               = "Standard"
  account_replication_type   = "LRS"
  min_tls_version            = "TLS1_2"
  https_traffic_only_enabled = true

  # Network rules disabled during initial deployment to allow Terraform access
  # Enable after deployment for production security
  # network_rules {
  #   default_action             = "Deny"
  #   bypass                     = ["AzureServices"]
  #   virtual_network_subnet_ids = [azurerm_subnet.workload.id]
  # }

  tags = local.common_tags
}

resource "azurerm_storage_share" "chromadb" {
  name                 = "chromadb"
  storage_account_name = azurerm_storage_account.main.name
  quota                = 10
}

# ============================================================================
# POSTGRESQL - DISABLED (Using Supabase instead)
# ============================================================================
# PostgreSQL is hosted on Supabase - no Azure deployment needed

# resource "azurerm_postgresql_flexible_server" "main" {
#   name                = "psql-fraudguard-eus2"
#   resource_group_name = azurerm_resource_group.main.name
#   location            = "eastus2"
#
#   sku_name   = "B_Standard_B1ms"
#   storage_mb = 32768
#   version    = "16"
#
#   administrator_login    = "fraudguardadmin"
#   administrator_password = random_password.postgresql_admin.result
#
#   delegated_subnet_id           = azurerm_subnet.postgresql.id
#   private_dns_zone_id           = azurerm_private_dns_zone.postgresql.id
#   public_network_access_enabled = false
#
#   backup_retention_days = 7
#   zone                  = "1"
#
#   tags = local.common_tags
#
#   depends_on = [azurerm_private_dns_zone_virtual_network_link.postgresql]
# }
#
# resource "azurerm_postgresql_flexible_server_database" "main" {
#   name      = "fraudguard"
#   server_id = azurerm_postgresql_flexible_server.main.id
#   charset   = "UTF8"
#   collation = "en_US.utf8"
# }
#
# resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_azure" {
#   name             = "AllowAzureServices"
#   server_id        = azurerm_postgresql_flexible_server.main.id
#   start_ip_address = "0.0.0.0"
#   end_ip_address   = "0.0.0.0"
# }

# ============================================================================
# AZURE OPENAI - DISABLED (Subscription does not have access)
# ============================================================================
# Azure OpenAI requires special access approval from Microsoft
# Apply for access: https://aka.ms/oai/access
# Backend will use Ollama locally instead

# resource "azurerm_cognitive_account" "openai" {
#   name                  = "aoai-fraudguard"
#   resource_group_name   = azurerm_resource_group.main.name
#   location              = var.location
#   kind                  = "OpenAI"
#   sku_name              = "S0"
#   custom_subdomain_name = "aoai-fraudguard"
#
#   tags = local.common_tags
# }
#
# resource "azurerm_cognitive_deployment" "gpt4o_mini" {
#   name                 = "gpt-4o-mini"
#   cognitive_account_id = azurerm_cognitive_account.openai.id
#
#   model {
#     format  = "OpenAI"
#     name    = "gpt-4o-mini"
#     version = "2024-07-18"
#   }
#
#   sku {
#     name     = "GlobalStandard"
#     capacity = 30
#   }
# }
#
# resource "azurerm_cognitive_deployment" "embeddings" {
#   name                 = "text-embedding-ada-002"
#   cognitive_account_id = azurerm_cognitive_account.openai.id
#
#   model {
#     format  = "OpenAI"
#     name    = "text-embedding-ada-002"
#     version = "2"
#   }
#
#   sku {
#     name     = "Standard"
#     capacity = 30
#   }
# }

# ============================================================================
# MONITORING
# ============================================================================

resource "azurerm_log_analytics_workspace" "main" {
  name                = "law-fraudguard"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.common_tags
}

resource "azurerm_application_insights" "main" {
  name                = "appi-fraudguard"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"
  sampling_percentage = 100
  tags                = local.common_tags
}

# ============================================================================
# KEY VAULT
# ============================================================================

data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "main" {
  name                       = "kv-fraudguard-${local.name_suffix}"
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  tenant_id                  = var.azure_tenant_id
  sku_name                   = "standard"
  soft_delete_retention_days = 7
  purge_protection_enabled   = false

  # Network ACLs disabled during initial deployment to allow Terraform access
  # Enable after deployment for production security
  # network_acls {
  #   default_action             = "Deny"
  #   bypass                     = "AzureServices"
  #   virtual_network_subnet_ids = [azurerm_subnet.workload.id]
  # }

  tags = local.common_tags
}

# Access policy para el usuario actual (para poder gestionar secretos)
resource "azurerm_key_vault_access_policy" "current_user" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = var.azure_tenant_id
  object_id    = data.azurerm_client_config.current.object_id

  secret_permissions = [
    "Get", "List", "Set", "Delete", "Purge", "Recover"
  ]
}

# Secrets managed manually in Key Vault (not in Terraform)
# - your-prod-password (Supabase DB password)
# - your-opensanctions-key

resource "azurerm_key_vault_secret" "azure_openai_api_key" {
  name         = "azure-openai-api-key"
  value        = var.azure_openai_api_key
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_key_vault_access_policy.current_user]
}

# ============================================================================
# CONTAINER APPS
# ============================================================================

resource "azurerm_container_app_environment" "main" {
  name                               = "cae-fraudguard"
  resource_group_name                = azurerm_resource_group.main.name
  location                           = azurerm_resource_group.main.location
  log_analytics_workspace_id         = azurerm_log_analytics_workspace.main.id
  infrastructure_subnet_id           = azurerm_subnet.container_apps_infra.id
  infrastructure_resource_group_name = "ME_cae-fraudguard_rg-fraudguard_westus2"
  tags                               = local.common_tags

  workload_profile {
    name                  = "Consumption"
    workload_profile_type = "Consumption"
  }
}

# Storage mount para ChromaDB
resource "azurerm_container_app_environment_storage" "chromadb" {
  name                         = "chromadb-storage"
  container_app_environment_id = azurerm_container_app_environment.main.id
  account_name                 = azurerm_storage_account.main.name
  share_name                   = azurerm_storage_share.chromadb.name
  access_key                   = azurerm_storage_account.main.primary_access_key
  access_mode                  = "ReadWrite"
}

# Managed Identity para Container Apps
resource "azurerm_user_assigned_identity" "container_apps" {
  name                = "id-container-apps"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tags                = local.common_tags
}

# Permisos para acceder a Azure AI Services (Managed Identity auth)
resource "azurerm_role_assignment" "cognitive_services_user" {
  scope                = var.azure_ai_services_resource_id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_user_assigned_identity.container_apps.principal_id
}

# Permisos para acceder al Container Registry
# COMMENTED OUT: Role assignment already exists from previous deployment
# resource "azurerm_role_assignment" "acr_pull" {
#   scope                = azurerm_container_registry.main.id
#   role_definition_name = "AcrPull"
#   principal_id         = azurerm_user_assigned_identity.container_apps.principal_id
# }

# Permisos para acceder al Key Vault
resource "azurerm_key_vault_access_policy" "container_apps" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = var.azure_tenant_id
  object_id    = azurerm_user_assigned_identity.container_apps.principal_id

  secret_permissions = ["Get", "List"]
}

# Backend Container App
resource "azurerm_container_app" "backend" {
  name                         = "ca-fraudguard-backend"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"
  tags                         = local.common_tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.container_apps.id]
  }

  registry {
    server   = azurerm_container_registry.main.login_server
    identity = azurerm_user_assigned_identity.container_apps.id
  }

  template {
    min_replicas = 1
    max_replicas = 3

    container {
      name   = "backend"
      image  = "${azurerm_container_registry.main.login_server}/fraudguard-backend:latest"
      cpu    = 0.5
      memory = "1Gi"

      # --- Secrets from Key Vault ---
      env {
        name        = "DATABASE_PASSWORD"
        secret_name = "your-prod-password"
      }

      env {
        name        = "OPENSANCTIONS_API_KEY"
        secret_name = "your-opensanctions-key"
      }

      # --- Azure OpenAI configuration ---
      env {
        name  = "USE_AZURE_OPENAI"
        value = "true"
      }

      env {
        name  = "AZURE_OPENAI_BASE_URL"
        value = "https://migue-mlq261f9-eastus2.openai.azure.com/openai/v1/"
      }

      env {
        name  = "AZURE_OPENAI_DEPLOYMENT"
        value = "gpt-5.2-chat"
      }

      env {
        name        = "AZURE_OPENAI_API_KEY"
        secret_name = "azure-openai-api-key"
      }

      # --- Database connection parts (non-secret) ---
      env {
        name  = "DATABASE_HOST"
        value = "aws-1-us-east-1.pooler.supabase.com"
      }

      env {
        name  = "DATABASE_PORT"
        value = "5432"
      }

      env {
        name  = "DATABASE_USER"
        value = "postgres.hlvydcvhekukmjvvmfnr"
      }

      env {
        name  = "DATABASE_NAME"
        value = "postgres"
      }

      # --- App config ---
      env {
        name  = "APP_ENV"
        value = "production"
      }

      env {
        name  = "LOG_LEVEL"
        value = "DEBUG"
      }

      env {
        name  = "CHROMA_PERSIST_DIR"
        value = "/app/data/chroma"
      }

      env {
        name  = "CHROMA_API_IMPL"
        value = "chromadb.api.segment.SegmentAPI"
      }

      env {
        name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
        value = azurerm_application_insights.main.connection_string
      }

      env {
        name  = "CORS_FRONTEND_PROD_URL"
        value = "https://${local.frontend_fqdn}"
      }

      volume_mounts {
        name = "chromadb-data"
        path = "/app/data/chroma"
      }

    }

    volume {
      name         = "chromadb-data"
      storage_type = "AzureFile"
      storage_name = azurerm_container_app_environment_storage.chromadb.name
    }
  }

  # Secrets from Key Vault (referenced by URI)
  secret {
    name                = "your-prod-password"
    key_vault_secret_id = "${azurerm_key_vault.main.vault_uri}secrets/your-prod-password"
    identity            = azurerm_user_assigned_identity.container_apps.id
  }

  secret {
    name                = "your-opensanctions-key"
    key_vault_secret_id = "${azurerm_key_vault.main.vault_uri}secrets/your-opensanctions-key"
    identity            = azurerm_user_assigned_identity.container_apps.id
  }

  secret {
    name                = "azure-openai-api-key"
    key_vault_secret_id = "${azurerm_key_vault.main.vault_uri}secrets/azure-openai-api-key"
    identity            = azurerm_user_assigned_identity.container_apps.id
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  depends_on = [
    # azurerm_role_assignment.acr_pull,  # Commented out - already exists
    azurerm_key_vault_access_policy.container_apps
  ]
}

# Frontend Container App
resource "azurerm_container_app" "frontend" {
  name                         = "ca-fraudguard-frontend"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"
  tags                         = local.common_tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.container_apps.id]
  }

  registry {
    server   = azurerm_container_registry.main.login_server
    identity = azurerm_user_assigned_identity.container_apps.id
  }

  template {
    min_replicas = 1
    max_replicas = 3

    container {
      name   = "frontend"
      image  = "${azurerm_container_registry.main.login_server}/fraudguard-frontend:latest"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "NEXT_PUBLIC_API_URL"
        value = "https://${local.backend_fqdn}"
      }

      env {
        name  = "NEXT_PUBLIC_WS_URL"
        value = "wss://${local.backend_fqdn}"
      }

      env {
        name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
        value = azurerm_application_insights.main.connection_string
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 3000
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }
}
