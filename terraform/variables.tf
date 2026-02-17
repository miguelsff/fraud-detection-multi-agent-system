# ============================================================================
# VARIABLES - Fraud Detection Multi-Agent System
# ============================================================================

variable "azure_subscription_id" {
  description = "Azure subscription ID"
  type        = string
  sensitive   = true
}

variable "azure_tenant_id" {
  description = "Azure tenant ID"
  type        = string
  sensitive   = true
}

variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "westus2"

  validation {
    condition     = can(regex("^(eastus|eastus2|westus|westus2|centralus)$", var.location))
    error_message = "Location must be a valid US Azure region."
  }
}

variable "azure_openai_api_key" {
  description = "API key for Azure OpenAI (stored in Key Vault)"
  type        = string
  sensitive   = true
}

variable "azure_ai_services_resource_id" {
  description = "Resource ID of the Azure AI Services account (created via AI Foundry)"
  type        = string
  default     = "/subscriptions/053c0308-de35-4b7e-b556-063e93e25407/resourceGroups/rg-fraudguard/providers/Microsoft.CognitiveServices/accounts/migue-mlq261f9-eastus2"
}

