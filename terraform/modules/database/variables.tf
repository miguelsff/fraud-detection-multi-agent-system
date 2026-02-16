# Database Module - Input Variables

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

variable "subnet_id" {
  description = "Subnet ID for PostgreSQL (delegated subnet)"
  type        = string
}

variable "private_dns_zone_id" {
  description = "Private DNS Zone ID for PostgreSQL"
  type        = string
}

# Database sizing
variable "sku_name" {
  description = "PostgreSQL SKU (e.g., B_Standard_B1ms, GP_Standard_D2ds_v4)"
  type        = string
}

variable "storage_mb" {
  description = "Storage size in MB"
  type        = number
  default     = 32768 # 32 GB
}

# Admin credentials
variable "admin_username" {
  description = "PostgreSQL admin username"
  type        = string
  default     = "fraud_admin"
}

variable "database_name" {
  description = "Name of the application database"
  type        = string
  default     = "fraud_detection"
}

# High availability (production only)
variable "enable_high_availability" {
  description = "Enable zone-redundant high availability"
  type        = bool
  default     = false
}

variable "zone" {
  description = "Availability zone for primary"
  type        = string
  default     = "1"
}

variable "standby_zone" {
  description = "Availability zone for standby (if HA enabled)"
  type        = string
  default     = "2"
}

# Backup
variable "backup_retention_days" {
  description = "Backup retention in days (7-35)"
  type        = number
  default     = 7

  validation {
    condition     = var.backup_retention_days >= 7 && var.backup_retention_days <= 35
    error_message = "Backup retention must be between 7 and 35 days"
  }
}

variable "enable_geo_redundant_backup" {
  description = "Enable geo-redundant backup (production only)"
  type        = bool
  default     = false
}

# Performance tuning
variable "max_connections" {
  description = "Maximum number of connections"
  type        = string
  default     = "100"
}

variable "shared_buffers_mb" {
  description = "Shared buffers in MB (percentage of RAM)"
  type        = string
  default     = "512" # Will be auto-adjusted by Azure
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
