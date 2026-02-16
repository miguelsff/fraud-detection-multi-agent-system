# Shared variables used across all environments

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "fraud-detection"
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "eastus" # GPT-4 available in East US
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project     = "Fraud Detection Multi-Agent System"
    ManagedBy   = "Terraform"
    Repository  = "fraud-detection-multi-agent-system"
  }
}
