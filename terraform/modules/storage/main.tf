# Storage Module - Azure Storage Account + Files Share for ChromaDB

resource "azurerm_storage_account" "main" {
  name                     = "st${replace(var.project_name, "-", "")}${var.environment}"
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = var.replication_type
  account_kind             = "StorageV2"

  # Enable secure transfer (HTTPS only)
  enable_https_traffic_only = true
  min_tls_version           = "TLS1_2"

  # Network rules - allow only from Container Apps subnet
  network_rules {
    default_action             = "Deny"
    bypass                     = ["AzureServices"]
    virtual_network_subnet_ids = [var.subnet_id]
  }

  tags = var.tags
}

# Azure Files Share for ChromaDB persistence
resource "azurerm_storage_share" "chromadb" {
  name                 = var.chromadb_share_name
  storage_account_name = azurerm_storage_account.main.name
  quota                = var.chromadb_share_size_gb

  # Enable SMB protocol (required for ChromaDB SQLite)
  enabled_protocol = "SMB"

  metadata = {
    purpose     = "ChromaDB vector database persistence"
    environment = var.environment
  }
}
