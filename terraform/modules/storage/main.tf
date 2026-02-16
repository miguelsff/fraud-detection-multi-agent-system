# Storage Module - Azure Storage Account + Files Share for ChromaDB

resource "azurerm_storage_account" "main" {
  name                     = "st${replace(var.project_name, "-", "")}${var.environment}"
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = var.replication_type
  account_kind             = "StorageV2"

  # Enable secure transfer (HTTPS only) - renamed in azurerm v4+
  https_traffic_only_enabled = true
  min_tls_version            = "TLS1_2"

  # Network rules - allow from Container Apps subnet
  # Note: Using "Allow" for dev to simplify deployment. Change to "Deny" in production.
  network_rules {
    default_action             = "Allow"
    bypass                     = ["AzureServices"]
    virtual_network_subnet_ids = [var.subnet_id]
  }

  tags = var.tags
}

# Azure Files Share for ChromaDB persistence
resource "azurerm_storage_share" "chromadb" {
  name                 = var.chromadb_share_name
  storage_account_id   = azurerm_storage_account.main.id # Updated for azurerm v4+
  quota                = var.chromadb_share_size_gb

  # Enable SMB protocol (required for ChromaDB SQLite)
  enabled_protocol = "SMB"

  metadata = {
    purpose     = "ChromaDB vector database persistence"
    environment = var.environment
  }
}
