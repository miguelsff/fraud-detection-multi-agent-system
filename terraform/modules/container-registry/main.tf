# Container Registry Module - Azure Container Registry (ACR)

resource "azurerm_container_registry" "main" {
  name                = "acr${replace(var.project_name, "-", "")}${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = var.sku
  admin_enabled       = false # Use managed identity instead

  # Enable managed identity for Container Apps to pull images
  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# Note: Geo-replication removed - azurerm_container_registry_replication not supported in azurerm v4.60.0
# For production, consider using Premium tier with manual replication setup via Azure Portal
