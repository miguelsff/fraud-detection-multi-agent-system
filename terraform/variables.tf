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

variable "supabase_database_url" {
  description = "Supabase PostgreSQL connection string (use asyncpg driver for async support)"
  type        = string
  sensitive   = true
  default     = ""  # Optional - can be set manually in Azure Portal after deployment
}

variable "azure_openai_key" {
  description = "Azure OpenAI API key (sensitive - do not commit)"
  type        = string
  sensitive   = true
  # No default - must be provided via terraform.tfvars or environment variable
}
