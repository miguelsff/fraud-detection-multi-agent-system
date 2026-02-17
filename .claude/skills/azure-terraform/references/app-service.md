# App Service Deployment

## When to Use App Service

- Web APIs (Node.js, Python, .NET, Java)
- Server-rendered web apps (Next.js, Django, ASP.NET)
- Static Web Apps (SPAs, Jamstack)
- Budget-friendly containerized apps (via App Service + container)

If you need auto-scaling containers with microservices → use Container Apps instead.
If you need full Kubernetes → use AKS instead.

## Minimal App Service Setup

```hcl
# app.tf

resource "azurerm_service_plan" "main" {
  name                = "asp-${var.project_name}-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  os_type             = "Linux"
  sku_name            = var.app_service_sku

  tags = local.common_tags
}

resource "azurerm_linux_web_app" "main" {
  name                = "app-${var.project_name}-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  service_plan_id     = azurerm_service_plan.main.id

  https_only = true

  identity {
    type = "SystemAssigned"
  }

  site_config {
    minimum_tls_version = "1.2"
    always_on           = var.environment == "prod" ? true : false

    application_stack {
      node_version = var.node_version  # Or python_version, dotnet_version, etc.
    }
  }

  app_settings = {
    "WEBSITE_RUN_FROM_PACKAGE" = "1"
    "NODE_ENV"                 = var.environment == "prod" ? "production" : "development"
  }

  tags = local.common_tags
}
```

```hcl
# In variables.tf add:

variable "app_service_sku" {
  description = "App Service Plan SKU"
  type        = string
  default     = "B1"  # Basic tier — cheapest with always-on

  validation {
    condition     = contains(["F1", "B1", "B2", "S1", "S2", "P1v3", "P2v3"], var.app_service_sku)
    error_message = "Invalid App Service SKU."
  }
}

variable "node_version" {
  description = "Node.js version for App Service"
  type        = string
  default     = "20-lts"
}
```

```hcl
# In outputs.tf add:

output "app_service_url" {
  value = "https://${azurerm_linux_web_app.main.default_hostname}"
}

output "app_service_principal_id" {
  value       = azurerm_linux_web_app.main.identity[0].principal_id
  description = "Managed Identity principal ID for RBAC assignments"
}
```

## SKU Selection Guide

| Environment | SKU | Monthly Cost (approx) | Notes |
|-------------|-----|----------------------|-------|
| Dev/Test | `F1` | Free | No always-on, no custom domain SSL |
| Dev with always-on | `B1` | ~$13 | Cheapest with always-on |
| Staging | `B1`-`S1` | $13-$70 | S1 adds auto-scale |
| Production | `S1`-`P1v3` | $70-$150 | P-tier for high traffic |

Always start with the smallest SKU and scale up based on actual metrics.

## App Service with Container

For deploying a Docker image instead of code:

```hcl
resource "azurerm_linux_web_app" "containerized" {
  name                = "app-${var.project_name}-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  service_plan_id     = azurerm_service_plan.main.id

  https_only = true

  identity {
    type = "SystemAssigned"
  }

  site_config {
    minimum_tls_version = "1.2"
    always_on           = var.environment == "prod"

    application_stack {
      docker_registry_url = "https://${azurerm_container_registry.main.login_server}"
      docker_image_name   = "${var.project_name}:${var.image_tag}"
    }
  }

  app_settings = {
    "DOCKER_ENABLE_CI"                    = "true"
    "WEBSITES_ENABLE_APP_SERVICE_STORAGE" = "false"
  }

  tags = local.common_tags
}
```

## Static Web App (SPAs, Jamstack)

For React, Vue, Angular, Next.js static export:

```hcl
resource "azurerm_static_web_app" "main" {
  name                = "stapp-${var.project_name}-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku_tier            = var.environment == "prod" ? "Standard" : "Free"
  sku_size            = var.environment == "prod" ? "Standard" : "Free"

  tags = local.common_tags
}

output "static_web_app_url" {
  value = "https://${azurerm_static_web_app.main.default_host_name}"
}
```

Static Web Apps are deployed via GitHub Actions or Azure DevOps — Terraform creates the resource, CI/CD pushes the code.

## Custom Domain + SSL

```hcl
# Only for paid tiers (B1+)
resource "azurerm_app_service_custom_hostname_binding" "main" {
  hostname            = var.custom_domain
  app_service_name    = azurerm_linux_web_app.main.name
  resource_group_name = azurerm_resource_group.main.name
}

resource "azurerm_app_service_managed_certificate" "main" {
  custom_hostname_binding_id = azurerm_app_service_custom_hostname_binding.main.id

  tags = local.common_tags
}

resource "azurerm_app_service_certificate_binding" "main" {
  hostname_binding_id = azurerm_app_service_custom_hostname_binding.main.id
  certificate_id      = azurerm_app_service_managed_certificate.main.id
  ssl_state           = "SniEnabled"
}
```

## Deployment Slots (Staging → Prod)

Only for Standard tier and above:

```hcl
resource "azurerm_linux_web_app_slot" "staging" {
  name           = "staging"
  app_service_id = azurerm_linux_web_app.main.id

  site_config {
    minimum_tls_version = "1.2"
    application_stack {
      node_version = var.node_version
    }
  }

  app_settings = azurerm_linux_web_app.main.app_settings

  tags = local.common_tags
}
```

Swap slots via CLI: `az webapp deployment slot swap -g <rg> -n <app> -s staging`

## Connecting to Database

Prefer Managed Identity over connection strings:

```hcl
# Grant App Service access to Azure SQL
resource "azurerm_role_assignment" "app_to_sql" {
  scope                = azurerm_mssql_server.main.id
  role_definition_name = "SQL DB Contributor"
  principal_id         = azurerm_linux_web_app.main.identity[0].principal_id
}
```

If you must use connection strings, store them in Key Vault and reference via app settings:

```hcl
app_settings = {
  "DATABASE_URL" = "@Microsoft.KeyVault(VaultName=${azurerm_key_vault.main.name};SecretName=database-url)"
}
```
