# Container Apps Module - Backend + Frontend applications

# Container Apps Environment
resource "azurerm_container_app_environment" "main" {
  name                       = "cae-${var.project_name}-${var.environment}"
  location                   = var.location
  resource_group_name        = var.resource_group_name
  log_analytics_workspace_id = var.log_analytics_workspace_id
  infrastructure_subnet_id   = var.subnet_infra_id

  tags = var.tags
}

# Storage for Container Apps Environment (Azure Files mount for ChromaDB)
resource "azurerm_container_app_environment_storage" "chromadb" {
  name                         = "chromadb-storage"
  container_app_environment_id = azurerm_container_app_environment.main.id
  account_name                 = var.storage_account_name
  share_name                   = var.storage_share_name
  access_key                   = var.storage_access_key
  access_mode                  = "ReadWrite"
}

# Managed Identity for Container Apps (to pull from ACR and access Key Vault)
resource "azurerm_user_assigned_identity" "container_apps" {
  name                = "id-container-apps-${var.environment}"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

# Role assignment: AcrPull for Container Registry
resource "azurerm_role_assignment" "acr_pull" {
  scope                = var.container_registry_server # Should be ACR resource ID
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.container_apps.principal_id
}

# Backend Container App (FastAPI + LangGraph)
resource "azurerm_container_app" "backend" {
  name                         = "ca-fraud-backend-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"

  # Managed identity
  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.container_apps.id]
  }

  # Registry configuration
  registry {
    server   = var.container_registry_server
    identity = azurerm_user_assigned_identity.container_apps.id
  }

  # Container template
  template {
    min_replicas = var.backend_replicas_min
    max_replicas = var.backend_replicas_max

    # Azure Files volume for ChromaDB
    volume {
      name         = "chromadb-volume"
      storage_type = "AzureFile"
      storage_name = azurerm_container_app_environment_storage.chromadb.name
    }

    container {
      name   = "backend"
      image  = "${var.container_registry_server}/fraud-backend:${var.backend_image_tag}"
      cpu    = var.backend_cpu
      memory = var.backend_memory

      # Volume mount for ChromaDB
      volume_mounts {
        name = "chromadb-volume"
        path = "/mnt/chromadb"
      }

      # Environment variables
      env {
        name  = "APP_ENV"
        value = var.environment
      }

      env {
        name  = "USE_AZURE_OPENAI"
        value = "true"
      }

      env {
        name  = "CHROMA_PERSIST_DIR"
        value = "/mnt/chromadb"
      }

      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }

      env {
        name        = "AZURE_OPENAI_ENDPOINT"
        secret_name = "azure-openai-endpoint"
      }

      env {
        name        = "AZURE_OPENAI_KEY"
        secret_name = "azure-openai-key"
      }

      env {
        name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
        value = var.app_insights_connection_string
      }

      # Health probes
      liveness_probe {
        transport = "HTTP"
        port      = 8000
        path      = "/api/v1/health"
      }

      readiness_probe {
        transport = "HTTP"
        port      = 8000
        path      = "/api/v1/health"
      }

      # Startup command (run migrations before starting server)
      # Note: Adjust if your Dockerfile uses different commands
      # command = ["/bin/sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
    }
  }

  # Secrets from Key Vault
  secret {
    name  = "database-url"
    value = var.key_vault_secrets["database-url"]
  }

  secret {
    name  = "azure-openai-endpoint"
    value = var.key_vault_secrets["azure-openai-endpoint"]
  }

  secret {
    name  = "azure-openai-key"
    value = var.key_vault_secrets["azure-openai-key"]
  }

  # Ingress configuration (HTTPS public)
  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "auto"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  tags = var.tags

  depends_on = [
    azurerm_container_app_environment_storage.chromadb,
    azurerm_role_assignment.acr_pull
  ]
}

# Frontend Container App (Next.js)
resource "azurerm_container_app" "frontend" {
  name                         = "ca-fraud-frontend-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"

  # Managed identity
  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.container_apps.id]
  }

  # Registry configuration
  registry {
    server   = var.container_registry_server
    identity = azurerm_user_assigned_identity.container_apps.id
  }

  # Container template
  template {
    min_replicas = var.frontend_replicas_min
    max_replicas = var.frontend_replicas_max

    container {
      name   = "frontend"
      image  = "${var.container_registry_server}/fraud-frontend:${var.frontend_image_tag}"
      cpu    = var.frontend_cpu
      memory = var.frontend_memory

      # Environment variables
      env {
        name  = "NODE_ENV"
        value = var.environment == "dev" ? "development" : "production"
      }

      env {
        name  = "NEXT_PUBLIC_API_URL"
        value = "https://${azurerm_container_app.backend.ingress[0].fqdn}"
      }

      env {
        name  = "NEXT_PUBLIC_WS_URL"
        value = "wss://${azurerm_container_app.backend.ingress[0].fqdn}"
      }

      # Health probes
      liveness_probe {
        transport = "HTTP"
        port      = 3000
        path      = "/"
      }

      readiness_probe {
        transport = "HTTP"
        port      = 3000
        path      = "/"
      }
    }
  }

  # Ingress configuration (HTTPS public)
  ingress {
    external_enabled = true
    target_port      = 3000
    transport        = "auto"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  tags = var.tags

  depends_on = [
    azurerm_container_app.backend,
    azurerm_role_assignment.acr_pull
  ]
}
