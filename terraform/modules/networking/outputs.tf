# Networking Module - Outputs

output "vnet_id" {
  description = "Virtual Network ID"
  value       = azurerm_virtual_network.main.id
}

output "vnet_name" {
  description = "Virtual Network name"
  value       = azurerm_virtual_network.main.name
}

output "subnet_container_apps_infra_id" {
  description = "Container Apps Infrastructure subnet ID"
  value       = azurerm_subnet.container_apps_infra.id
}

output "subnet_workload_id" {
  description = "Workload subnet ID (for Container Apps, Storage, Key Vault)"
  value       = azurerm_subnet.workload.id
}

output "subnet_postgresql_id" {
  description = "PostgreSQL subnet ID"
  value       = azurerm_subnet.postgresql.id
}

output "private_dns_zone_postgresql_id" {
  description = "PostgreSQL Private DNS Zone ID"
  value       = azurerm_private_dns_zone.postgresql.id
}

output "nsg_workload_id" {
  description = "Workload NSG ID"
  value       = azurerm_network_security_group.workload.id
}

output "nsg_postgresql_id" {
  description = "PostgreSQL NSG ID"
  value       = azurerm_network_security_group.postgresql.id
}
