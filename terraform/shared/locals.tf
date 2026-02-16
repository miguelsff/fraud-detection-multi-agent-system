# Shared local values

locals {
  # Naming conventions
  resource_group_name = "rg-${var.project_name}-${var.environment}"

  # Common prefixes
  prefix = "${var.project_name}-${var.environment}"

  # Network CIDR blocks
  vnet_cidr = "10.0.0.0/16"
  subnet_container_apps_infra_cidr = "10.0.0.0/23"  # /23 = 512 IPs (required for Container Apps)
  subnet_container_apps_workload_cidr = "10.0.2.0/24"
  subnet_postgresql_cidr = "10.0.3.0/24"

  # Common tags merged with environment-specific tags
  common_tags = merge(
    var.tags,
    {
      Environment = var.environment
    }
  )
}
