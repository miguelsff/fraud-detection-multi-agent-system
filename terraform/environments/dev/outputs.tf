# Development environment outputs

output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.main.name
}

output "backend_url" {
  description = "Backend Container App FQDN"
  value       = module.container_apps.backend_fqdn
}

output "frontend_url" {
  description = "Frontend Container App FQDN"
  value       = module.container_apps.frontend_fqdn
}

output "container_registry_login_server" {
  description = "ACR login server"
  value       = module.container_registry.login_server
}

output "database_fqdn" {
  description = "PostgreSQL server FQDN"
  value       = module.database.server_fqdn
}

output "key_vault_name" {
  description = "Key Vault name"
  value       = module.key_vault.name
}

output "app_insights_instrumentation_key" {
  description = "Application Insights instrumentation key"
  value       = module.monitoring.instrumentation_key
  sensitive   = true
}

output "azure_openai_endpoint" {
  description = "Azure OpenAI endpoint"
  value       = module.azure_openai.endpoint
}
