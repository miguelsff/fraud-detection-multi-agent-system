# Container Apps Module - Input Variables

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

# Networking
variable "subnet_infra_id" {
  description = "Subnet ID for Container Apps infrastructure"
  type        = string
}

variable "subnet_workload_id" {
  description = "Subnet ID for workloads (not used directly but for reference)"
  type        = string
}

# Container Registry
variable "container_registry_id" {
  description = "ACR resource ID (for role assignment)"
  type        = string
}

variable "container_registry_server" {
  description = "ACR login server URL"
  type        = string
}

variable "container_registry_identity_id" {
  description = "ACR managed identity principal ID (for role assignment)"
  type        = string
}

# Storage (ChromaDB)
variable "storage_account_name" {
  description = "Storage account name for Azure Files"
  type        = string
}

variable "storage_share_name" {
  description = "Azure Files share name for ChromaDB"
  type        = string
}

variable "storage_access_key" {
  description = "Storage account access key"
  type        = string
  sensitive   = true
}

# Key Vault
variable "key_vault_id" {
  description = "Key Vault ID (for reference)"
  type        = string
}

variable "key_vault_secrets" {
  description = "Map of secrets from Key Vault"
  type        = map(string)
  sensitive   = true
  default     = {}
}

# Monitoring
variable "log_analytics_workspace_id" {
  description = "Log Analytics Workspace ID"
  type        = string
}

variable "app_insights_connection_string" {
  description = "Application Insights connection string"
  type        = string
  sensitive   = true
}

# Backend configuration
variable "backend_replicas_min" {
  description = "Minimum number of backend replicas"
  type        = number
  default     = 1
}

variable "backend_replicas_max" {
  description = "Maximum number of backend replicas"
  type        = number
  default     = 10
}

variable "backend_cpu" {
  description = "Backend CPU allocation (0.25, 0.5, 0.75, 1.0, etc.)"
  type        = string
  default     = "1.0"
}

variable "backend_memory" {
  description = "Backend memory allocation (0.5Gi, 1Gi, 2Gi, etc.)"
  type        = string
  default     = "2Gi"
}

variable "backend_image_tag" {
  description = "Backend image tag (git SHA or version)"
  type        = string
  default     = "latest"
}

# Frontend configuration
variable "frontend_replicas_min" {
  description = "Minimum number of frontend replicas"
  type        = number
  default     = 1
}

variable "frontend_replicas_max" {
  description = "Maximum number of frontend replicas"
  type        = number
  default     = 5
}

variable "frontend_cpu" {
  description = "Frontend CPU allocation"
  type        = string
  default     = "0.5"
}

variable "frontend_memory" {
  description = "Frontend memory allocation"
  type        = string
  default     = "1Gi"
}

variable "frontend_image_tag" {
  description = "Frontend image tag (git SHA or version)"
  type        = string
  default     = "latest"
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
