# Storage Module - Outputs

output "account_id" {
  description = "Storage account ID"
  value       = azurerm_storage_account.main.id
}

output "account_name" {
  description = "Storage account name"
  value       = azurerm_storage_account.main.name
}

output "chromadb_share_name" {
  description = "ChromaDB share name"
  value       = azurerm_storage_share.chromadb.name
}

output "chromadb_share_url" {
  description = "ChromaDB share URL"
  value       = azurerm_storage_share.chromadb.url
}

output "primary_connection_string" {
  description = "Storage account primary connection string"
  value       = azurerm_storage_account.main.primary_connection_string
  sensitive   = true
}

output "access_key" {
  description = "Storage account primary access key"
  value       = azurerm_storage_account.main.primary_access_key
  sensitive   = true
}
