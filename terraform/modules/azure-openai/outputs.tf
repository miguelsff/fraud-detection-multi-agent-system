# Azure OpenAI Module - Outputs

output "id" {
  description = "Azure OpenAI resource ID"
  value       = azurerm_cognitive_account.openai.id
}

output "name" {
  description = "Azure OpenAI resource name"
  value       = azurerm_cognitive_account.openai.name
}

output "endpoint" {
  description = "Azure OpenAI endpoint URL"
  value       = azurerm_cognitive_account.openai.endpoint
}

output "primary_key" {
  description = "Azure OpenAI primary access key"
  value       = azurerm_cognitive_account.openai.primary_access_key
  sensitive   = true
}

output "secondary_key" {
  description = "Azure OpenAI secondary access key"
  value       = azurerm_cognitive_account.openai.secondary_access_key
  sensitive   = true
}

output "identity_principal_id" {
  description = "Managed identity principal ID"
  value       = azurerm_cognitive_account.openai.identity[0].principal_id
}

output "gpt35_deployment_name" {
  description = "GPT-3.5 Turbo deployment name (empty if disabled)"
  value       = var.gpt35_capacity > 0 ? azurerm_cognitive_deployment.gpt35[0].name : ""
}

output "gpt4_deployment_name" {
  description = "GPT-4 deployment name (empty if disabled)"
  value       = var.gpt4_capacity > 0 ? azurerm_cognitive_deployment.gpt4[0].name : ""
}
