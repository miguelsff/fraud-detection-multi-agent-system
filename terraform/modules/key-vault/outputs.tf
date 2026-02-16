# Key Vault Module - Outputs

output "id" {
  description = "Key Vault ID"
  value       = azurerm_key_vault.main.id
}

output "name" {
  description = "Key Vault name"
  value       = azurerm_key_vault.main.name
}

output "uri" {
  description = "Key Vault URI"
  value       = azurerm_key_vault.main.vault_uri
}

output "secret_ids" {
  description = "Map of secret names to their IDs"
  value       = { for k, v in azurerm_key_vault_secret.secrets : k => v.id }
}
