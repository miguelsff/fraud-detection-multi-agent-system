# ============================================================================
# OUTPUTS - Fraud Detection Multi-Agent System
# ============================================================================

output "resource_group_name" {
  description = "Resource group name"
  value       = azurerm_resource_group.main.name
}

output "container_registry_login_server" {
  description = "Container Registry login server"
  value       = azurerm_container_registry.main.login_server
}

output "backend_url" {
  description = "Backend API URL"
  value       = "https://${azurerm_container_app.backend.ingress[0].fqdn}"
}

output "frontend_url" {
  description = "Frontend application URL"
  value       = "https://${azurerm_container_app.frontend.ingress[0].fqdn}"
}

# PostgreSQL outputs disabled - using Supabase
# output "postgresql_fqdn" {
#   description = "PostgreSQL server FQDN"
#   value       = azurerm_postgresql_flexible_server.main.fqdn
#   sensitive   = true
# }
#
# output "postgresql_database_name" {
#   description = "PostgreSQL database name"
#   value       = azurerm_postgresql_flexible_server_database.main.name
# }

output "key_vault_name" {
  description = "Key Vault name"
  value       = azurerm_key_vault.main.name
}

# Azure OpenAI disabled (no subscription access)
# output "azure_openai_endpoint" {
#   description = "Azure OpenAI endpoint"
#   value       = azurerm_cognitive_account.openai.endpoint
# }

output "storage_account_name" {
  description = "Storage account name (ChromaDB)"
  value       = azurerm_storage_account.main.name
}

output "application_insights_connection_string" {
  description = "Application Insights connection string"
  value       = azurerm_application_insights.main.connection_string
  sensitive   = true
}
