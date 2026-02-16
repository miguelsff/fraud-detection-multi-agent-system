# Monitoring Module - Outputs

output "workspace_id" {
  description = "Log Analytics Workspace ID"
  value       = azurerm_log_analytics_workspace.main.id
}

output "workspace_name" {
  description = "Log Analytics Workspace name"
  value       = azurerm_log_analytics_workspace.main.name
}

output "app_insights_id" {
  description = "Application Insights ID"
  value       = azurerm_application_insights.main.id
}

output "app_insights_name" {
  description = "Application Insights name"
  value       = azurerm_application_insights.main.name
}

output "instrumentation_key" {
  description = "Application Insights instrumentation key"
  value       = azurerm_application_insights.main.instrumentation_key
  sensitive   = true
}

output "connection_string" {
  description = "Application Insights connection string"
  value       = azurerm_application_insights.main.connection_string
  sensitive   = true
}

output "app_id" {
  description = "Application Insights application ID"
  value       = azurerm_application_insights.main.app_id
}
