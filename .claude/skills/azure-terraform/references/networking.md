# Networking

## When to Set Up Networking

**Skip networking if:**
- Dev/test environment
- Public-facing app with managed database (firewall rules are enough)
- Using App Service with Azure SQL firewall

**Set up VNet if:**
- Production environment with compliance requirements
- Need private connectivity between services
- Using AKS (requires VNet)
- Need private endpoints for databases/storage

## Basic VNet Setup

```hcl
# network.tf

resource "azurerm_virtual_network" "main" {
  name                = "vnet-${var.project_name}-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  address_space       = [var.vnet_address_space]

  tags = local.common_tags
}

# Subnet for App Service / Container Apps
resource "azurerm_subnet" "app" {
  name                 = "snet-app"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [cidrsubnet(var.vnet_address_space, 8, 1)]  # /24

  delegation {
    name = "app-delegation"
    service_delegation {
      name = "Microsoft.Web/serverFarms"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }
}

# Subnet for databases / private endpoints
resource "azurerm_subnet" "data" {
  name                 = "snet-data"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [cidrsubnet(var.vnet_address_space, 8, 2)]  # /24

  private_endpoint_network_policies = "Enabled"
}

# Subnet for AKS (if using)
resource "azurerm_subnet" "aks" {
  name                 = "snet-aks"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [cidrsubnet(var.vnet_address_space, 4, 1)]  # /20 — AKS needs large subnet
}
```

```hcl
# In variables.tf add:

variable "vnet_address_space" {
  description = "VNet address space"
  type        = string
  default     = "10.0.0.0/16"
}
```

## Network Security Group (NSG)

```hcl
resource "azurerm_network_security_group" "app" {
  name                = "nsg-app-${var.project_name}-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  security_rule {
    name                       = "AllowHTTPS"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "DenyAll"
    priority                   = 4096
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  tags = local.common_tags
}

resource "azurerm_subnet_network_security_group_association" "app" {
  subnet_id                 = azurerm_subnet.app.id
  network_security_group_id = azurerm_network_security_group.app.id
}
```

## Private Endpoint (Database)

Keeps database traffic on Azure's private network:

```hcl
# private-endpoints.tf

resource "azurerm_private_endpoint" "postgresql" {
  name                = "pe-psql-${var.project_name}-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  subnet_id           = azurerm_subnet.data.id

  private_service_connection {
    name                           = "psc-psql"
    private_connection_resource_id = azurerm_postgresql_flexible_server.main.id
    subresource_names              = ["postgresqlServer"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "default"
    private_dns_zone_ids = [azurerm_private_dns_zone.postgresql.id]
  }

  tags = local.common_tags
}

resource "azurerm_private_dns_zone" "postgresql" {
  name                = "privatelink.postgres.database.azure.com"
  resource_group_name = azurerm_resource_group.main.name

  tags = local.common_tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "postgresql" {
  name                  = "vnet-link-psql"
  resource_group_name   = azurerm_resource_group.main.name
  private_dns_zone_name = azurerm_private_dns_zone.postgresql.name
  virtual_network_id    = azurerm_virtual_network.main.id
}
```

## VNet Integration for App Service

Connect App Service to VNet so it can reach private endpoints:

```hcl
resource "azurerm_app_service_virtual_network_swift_connection" "main" {
  app_service_id = azurerm_linux_web_app.main.id
  subnet_id      = azurerm_subnet.app.id
}
```

## Subnet Sizing Guide

| Subnet | CIDR | IPs | Use |
|--------|------|-----|-----|
| App | /24 | 251 | App Service VNet integration |
| Data | /24 | 251 | Private endpoints |
| AKS | /20 | 4091 | AKS nodes + pods (needs large range) |

Rule of thumb: AKS needs ~30 IPs per node. A /20 supports ~130 nodes.

## When to Skip All This

For dev environments, just use:
- Database firewall rules (allow Azure services + your IP)
- App Service without VNet integration
- Storage Account with public access + SAS tokens

Add VNet + private endpoints when moving to staging/production.
