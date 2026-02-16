# Development environment variables

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

# Azure authentication
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

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "fraud-detection"
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "eastus"
}

# Database configuration
variable "postgresql_sku_name" {
  description = "PostgreSQL SKU (B1ms = 1 vCore, 2GB RAM for dev)"
  type        = string
  default     = "B_Standard_B1ms"
}

variable "postgresql_storage_mb" {
  description = "PostgreSQL storage size in MB"
  type        = number
  default     = 32768 # 32 GB
}

variable "postgresql_backup_retention_days" {
  description = "Backup retention days"
  type        = number
  default     = 7
}

# Container Apps configuration
variable "backend_replicas_min" {
  description = "Minimum number of backend replicas"
  type        = number
  default     = 1
}

variable "backend_replicas_max" {
  description = "Maximum number of backend replicas"
  type        = number
  default     = 2
}

variable "backend_cpu" {
  description = "Backend CPU allocation"
  type        = string
  default     = "0.5"
}

variable "backend_memory" {
  description = "Backend memory allocation"
  type        = string
  default     = "1Gi"
}

variable "frontend_replicas_min" {
  description = "Minimum number of frontend replicas"
  type        = number
  default     = 1
}

variable "frontend_replicas_max" {
  description = "Maximum number of frontend replicas"
  type        = number
  default     = 2
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

# Azure OpenAI configuration
variable "azure_openai_gpt35_capacity" {
  description = "GPT-3.5 Turbo TPM capacity (thousands of tokens per minute)"
  type        = number
  default     = 30
}

variable "azure_openai_gpt4_capacity" {
  description = "GPT-4 TPM capacity (0 = disabled for cost savings in dev)"
  type        = number
  default     = 0 # Disabled in dev to save costs
}

# Storage configuration
variable "chromadb_storage_size_gb" {
  description = "ChromaDB Azure Files share size in GB"
  type        = number
  default     = 10
}

# Container Registry
variable "acr_sku" {
  description = "Azure Container Registry SKU"
  type        = string
  default     = "Basic"
}

# Monitoring
variable "log_analytics_retention_days" {
  description = "Log Analytics retention in days"
  type        = number
  default     = 30
}

variable "app_insights_sampling_percentage" {
  description = "Application Insights sampling percentage"
  type        = number
  default     = 100 # No sampling in dev
}

# Tags
variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default = {
    Project     = "Fraud Detection Multi-Agent System"
    ManagedBy   = "Terraform"
    Environment = "development"
    CostCenter  = "R&D"
  }
}
