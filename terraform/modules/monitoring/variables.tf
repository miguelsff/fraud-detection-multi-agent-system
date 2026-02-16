# Monitoring Module - Input Variables

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

variable "retention_days" {
  description = "Log Analytics retention in days (30-730)"
  type        = number
  default     = 30

  validation {
    condition     = var.retention_days >= 30 && var.retention_days <= 730
    error_message = "Retention must be between 30 and 730 days"
  }
}

variable "sampling_percentage" {
  description = "Application Insights sampling percentage (1-100)"
  type        = number
  default     = 100

  validation {
    condition     = var.sampling_percentage >= 1 && var.sampling_percentage <= 100
    error_message = "Sampling percentage must be between 1 and 100"
  }
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
