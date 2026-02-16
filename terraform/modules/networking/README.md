# Networking Module

Creates Virtual Network with subnets for Container Apps, PostgreSQL, and supporting infrastructure.

## Architecture

### VNet
- Address space: `10.0.0.0/16`

### Subnets

1. **Container Apps Infrastructure** (`10.0.0.0/23`)
   - Delegated to `Microsoft.App/environments`
   - 512 IPs required for Container Apps Environment

2. **Workload** (`10.0.2.0/24`)
   - For Container Apps, Storage, Key Vault access
   - Service endpoints: Storage, Key Vault, Cognitive Services

3. **PostgreSQL** (`10.0.3.0/24`)
   - Delegated to `Microsoft.DBforPostgreSQL/flexibleServers`
   - Private only (no public access)

### Network Security Groups

- **Workload NSG**: Allows HTTPS (443), HTTP (80) for health checks
- **PostgreSQL NSG**: Denies all inbound (accessible only via VNet)

### Private DNS

- Private DNS Zone for PostgreSQL: `{project}-{env}.postgres.database.azure.com`
- Linked to VNet for private name resolution

## Inputs

| Name | Description | Type | Required |
|------|-------------|------|----------|
| resource_group_name | Resource group name | string | yes |
| location | Azure region | string | yes |
| environment | Environment (dev/staging/prod) | string | yes |
| project_name | Project name | string | yes |
| tags | Resource tags | map(string) | no |

## Outputs

| Name | Description |
|------|-------------|
| vnet_id | Virtual Network ID |
| subnet_container_apps_infra_id | Container Apps infra subnet ID |
| subnet_workload_id | Workload subnet ID |
| subnet_postgresql_id | PostgreSQL subnet ID |
| private_dns_zone_postgresql_id | PostgreSQL Private DNS Zone ID |

## Usage

```hcl
module "networking" {
  source = "../../modules/networking"

  resource_group_name = azurerm_resource_group.main.name
  location            = "eastus"
  environment         = "dev"
  project_name        = "fraud-detection"
  tags                = local.common_tags
}
```

## Security

- PostgreSQL subnet has no public access
- Network isolation via VNet
- Service endpoints for secure Azure service access
- NSGs enforce traffic rules
