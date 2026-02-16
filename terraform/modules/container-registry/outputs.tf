# Container Registry Module - Outputs

output "id" {
  description = "ACR resource ID"
  value       = azurerm_container_registry.main.id
}

output "name" {
  description = "ACR name"
  value       = azurerm_container_registry.main.name
}

output "login_server" {
  description = "ACR login server URL"
  value       = azurerm_container_registry.main.login_server
}

output "identity_principal_id" {
  description = "ACR managed identity principal ID"
  value       = azurerm_container_registry.main.identity[0].principal_id
}

output "admin_username" {
  description = "ACR admin username (empty if admin disabled)"
  value       = azurerm_container_registry.main.admin_enabled ? azurerm_container_registry.main.admin_username : ""
  sensitive   = true
}
