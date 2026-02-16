# Storage Module - Input Variables

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
  description = "Subnet ID for network rules (Container Apps workload subnet)"
  type        = string
}

variable "replication_type" {
  description = "Storage replication type (LRS, GRS, RAGRS, ZRS)"
  type        = string
  default     = "LRS"
}

variable "chromadb_share_name" {
  description = "Name of the Azure Files share for ChromaDB"
  type        = string
  default     = "chromadb-share"
}

variable "chromadb_share_size_gb" {
  description = "Size of the ChromaDB share in GB"
  type        = number
  default     = 10

  validation {
    condition     = var.chromadb_share_size_gb >= 1 && var.chromadb_share_size_gb <= 102400
    error_message = "Share size must be between 1 GB and 100 TB"
  }
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
