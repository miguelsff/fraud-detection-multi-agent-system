# Container Apps Module - Outputs

output "environment_id" {
  description = "Container Apps Environment ID"
  value       = azurerm_container_app_environment.main.id
}

output "environment_name" {
  description = "Container Apps Environment name"
  value       = azurerm_container_app_environment.main.name
}

output "backend_id" {
  description = "Backend Container App ID"
  value       = azurerm_container_app.backend.id
}

output "backend_name" {
  description = "Backend Container App name"
  value       = azurerm_container_app.backend.name
}

output "backend_fqdn" {
  description = "Backend Container App FQDN (public URL)"
  value       = "https://${azurerm_container_app.backend.ingress[0].fqdn}"
}

output "frontend_id" {
  description = "Frontend Container App ID"
  value       = azurerm_container_app.frontend.id
}

output "frontend_name" {
  description = "Frontend Container App name"
  value       = azurerm_container_app.frontend.name
}

output "frontend_fqdn" {
  description = "Frontend Container App FQDN (public URL)"
  value       = "https://${azurerm_container_app.frontend.ingress[0].fqdn}"
}

output "managed_identity_id" {
  description = "Managed identity ID for Container Apps"
  value       = azurerm_user_assigned_identity.container_apps.id
}

output "managed_identity_principal_id" {
  description = "Managed identity principal ID"
  value       = azurerm_user_assigned_identity.container_apps.principal_id
}
