# Azure Container Apps

## When to Use Container Apps

- Microservices that need to scale independently
- Event-driven processing (queue consumers, scheduled jobs)
- APIs that need auto-scaling to zero (save costs)
- When you want containers but NOT Kubernetes complexity

If you have a single web app → App Service is simpler.
If you need full Kubernetes control → use AKS instead.

## Minimal Container App Setup

```hcl
# container-app.tf

resource "azurerm_container_app_environment" "main" {
  name                = "cae-${var.project_name}-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  tags = local.common_tags
}

resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-${var.project_name}-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = var.environment == "prod" ? 90 : 30

  tags = local.common_tags
}

resource "azurerm_container_app" "api" {
  name                         = "ca-${var.project_name}-api-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  identity {
    type = "SystemAssigned"
  }

  template {
    min_replicas = var.environment == "prod" ? 1 : 0
    max_replicas = var.max_replicas

    container {
      name   = "api"
      image  = "${azurerm_container_registry.main.login_server}/${var.project_name}:${var.image_tag}"
      cpu    = var.container_cpu
      memory = var.container_memory

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }

      # For secrets, use secret_name reference
      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }
    }
  }

  secret {
    name  = "database-url"
    value = var.database_url
  }

  ingress {
    external_enabled = true
    target_port      = var.app_port
    transport        = "auto"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  registry {
    server   = azurerm_container_registry.main.login_server
    identity = azurerm_container_app.api.identity[0].principal_id
  }

  tags = local.common_tags
}
```

```hcl
# In variables.tf add:

variable "max_replicas" {
  description = "Maximum container replicas for auto-scaling"
  type        = number
  default     = 5
}

variable "container_cpu" {
  description = "CPU cores for container (0.25, 0.5, 1, 2, 4)"
  type        = number
  default     = 0.25
}

variable "container_memory" {
  description = "Memory for container (0.5Gi, 1Gi, 2Gi, etc.)"
  type        = string
  default     = "0.5Gi"
}

variable "app_port" {
  description = "Container port to expose"
  type        = number
  default     = 8080
}

variable "image_tag" {
  description = "Container image tag"
  type        = string
  default     = "latest"
}

variable "database_url" {
  description = "Database connection string"
  type        = string
  sensitive   = true
  default     = ""
}
```

```hcl
# In outputs.tf add:

output "container_app_url" {
  value = "https://${azurerm_container_app.api.ingress[0].fqdn}"
}
```

## Container Registry (ACR)

Almost always needed with Container Apps:

```hcl
# acr.tf

resource "azurerm_container_registry" "main" {
  name                = "cr${replace(var.project_name, "-", "")}${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = var.environment == "prod" ? "Standard" : "Basic"
  admin_enabled       = false  # Use managed identity instead

  tags = local.common_tags
}

# Grant Container App pull access to ACR
resource "azurerm_role_assignment" "app_acr_pull" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_container_app.api.identity[0].principal_id
}

output "acr_login_server" {
  value = azurerm_container_registry.main.login_server
}
```

## Scaling Rules

```hcl
# Add inside the template block of container_app:

    http_scale_rule {
      name                = "http-scaling"
      concurrent_requests = 50  # Scale up when >50 concurrent requests per replica
    }

    # Or for queue-based scaling:
    azure_queue_scale_rule {
      name         = "queue-scaling"
      queue_name   = "my-queue"
      queue_length = 10
      authentication {
        secret_name       = "storage-connection"
        trigger_parameter = "connection"
      }
    }
```

## Multiple Services (Microservices)

For multi-service apps, create one `azurerm_container_app` per service sharing the same environment:

```hcl
# Each service gets its own container app
resource "azurerm_container_app" "worker" {
  name                         = "ca-${var.project_name}-worker-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  template {
    min_replicas = 1
    max_replicas = 10

    container {
      name   = "worker"
      image  = "${azurerm_container_registry.main.login_server}/${var.project_name}-worker:${var.image_tag}"
      cpu    = 0.5
      memory = "1Gi"
    }
  }

  # No ingress block = internal only (not exposed to internet)

  tags = local.common_tags
}
```

Services in the same environment can communicate via internal DNS: `http://ca-myapp-worker-dev`

## Cost Tips

- Set `min_replicas = 0` for dev/staging (scales to zero = no cost when idle)
- Use `Basic` ACR for non-prod
- Start with 0.25 CPU / 0.5Gi memory and scale up based on metrics
- Container Apps charge per vCPU-second and GiB-second of active usage
