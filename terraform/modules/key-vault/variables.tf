# Key Vault Module - Input Variables

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "tenant_id" {
  description = "Azure tenant ID"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID for network rules (Container Apps workload subnet)"
  type        = string
}

variable "enable_purge_protection" {
  description = "Enable purge protection (recommended for production)"
  type        = bool
  default     = false
}

variable "secrets" {
  description = "Map of secrets to store (key = secret name, value = secret value)"
  type        = map(string)
  default     = {}
  sensitive   = true
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
