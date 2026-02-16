# Azure OpenAI Module - Input Variables

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region (must support Azure OpenAI + GPT-4)"
  type        = string

  validation {
    condition     = contains(["eastus", "westus", "swedencentral", "switzerlandnorth"], var.location)
    error_message = "Location must support Azure OpenAI GPT-4 (eastus, westus, swedencentral, switzerlandnorth)"
  }
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

# Deployment capacities (TPM = thousands of tokens per minute)
variable "gpt35_capacity" {
  description = "GPT-3.5 Turbo deployment capacity (0 = disabled)"
  type        = number
  default     = 30

  validation {
    condition     = var.gpt35_capacity >= 0 && var.gpt35_capacity <= 240
    error_message = "GPT-3.5 capacity must be between 0 and 240 TPM"
  }
}

variable "gpt4_capacity" {
  description = "GPT-4 deployment capacity (0 = disabled, expensive)"
  type        = number
  default     = 0

  validation {
    condition     = var.gpt4_capacity >= 0 && var.gpt4_capacity <= 80
    error_message = "GPT-4 capacity must be between 0 and 80 TPM"
  }
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
