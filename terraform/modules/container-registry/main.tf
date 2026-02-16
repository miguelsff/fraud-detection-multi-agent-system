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

# Enable geo-replication for production (Standard+ tier only)
resource "azurerm_container_registry_replication" "geo" {
  count                     = var.sku == "Standard" || var.sku == "Premium" ? 1 : 0
  name                      = "westus"
  container_registry_name   = azurerm_container_registry.main.name
  resource_group_name       = var.resource_group_name
  location                  = "westus"
  zone_redundancy_enabled   = var.sku == "Premium" ? true : false
  tags                      = var.tags
}
