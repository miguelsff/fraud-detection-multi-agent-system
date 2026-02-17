# Data Services

## Decision Guide

```
What kind of data?
├─ Relational (SQL) → Azure SQL or PostgreSQL Flexible Server
│   ├─ .NET / SQL Server background → Azure SQL
│   └─ Open source preference → PostgreSQL Flexible Server
├─ Document / NoSQL → Cosmos DB
├─ Files / Blobs → Storage Account
└─ Cache → Redis Cache
```

## PostgreSQL Flexible Server (Recommended for Most Apps)

```hcl
# db.tf

resource "azurerm_postgresql_flexible_server" "main" {
  name                          = "psql-${var.project_name}-${var.environment}"
  resource_group_name           = azurerm_resource_group.main.name
  location                      = azurerm_resource_group.main.location
  version                       = "16"
  administrator_login           = var.db_admin_username
  administrator_password        = var.db_admin_password
  sku_name                      = var.db_sku
  storage_mb                    = var.db_storage_mb
  backup_retention_days         = var.environment == "prod" ? 35 : 7
  geo_redundant_backup_enabled  = var.environment == "prod"
  zone                          = "1"

  tags = local.common_tags
}

resource "azurerm_postgresql_flexible_server_database" "main" {
  name      = var.project_name
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# Allow Azure services to access (for App Service / Container Apps)
resource "azurerm_postgresql_flexible_server_firewall_rule" "azure_services" {
  name             = "AllowAzureServices"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}
```

```hcl
# In variables.tf add:

variable "db_admin_username" {
  description = "Database administrator username"
  type        = string
  default     = "pgadmin"
}

variable "db_admin_password" {
  description = "Database administrator password"
  type        = string
  sensitive   = true
}

variable "db_sku" {
  description = "PostgreSQL SKU name"
  type        = string
  default     = "B_Standard_B1ms"  # Burstable, cheapest
}

variable "db_storage_mb" {
  description = "Database storage in MB"
  type        = number
  default     = 32768  # 32 GB
}
```

```hcl
# In outputs.tf add:

output "postgresql_fqdn" {
  value = azurerm_postgresql_flexible_server.main.fqdn
}

output "postgresql_connection_string" {
  value     = "postgresql://${var.db_admin_username}:${var.db_admin_password}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/${var.project_name}?sslmode=require"
  sensitive = true
}
```

### PostgreSQL SKU Guide

| Environment | SKU | vCores | RAM | Monthly |
|-------------|-----|--------|-----|---------|
| Dev/Test | `B_Standard_B1ms` | 1 | 2GB | ~$13 |
| Small prod | `GP_Standard_D2ds_v4` | 2 | 8GB | ~$125 |
| Medium prod | `GP_Standard_D4ds_v4` | 4 | 16GB | ~$250 |

## Azure SQL Database

```hcl
# db.tf

resource "azurerm_mssql_server" "main" {
  name                         = "sql-${var.project_name}-${var.environment}"
  resource_group_name          = azurerm_resource_group.main.name
  location                     = azurerm_resource_group.main.location
  version                      = "12.0"
  administrator_login          = var.db_admin_username
  administrator_login_password = var.db_admin_password
  minimum_tls_version          = "1.2"

  tags = local.common_tags
}

resource "azurerm_mssql_database" "main" {
  name      = "sqldb-${var.project_name}-${var.environment}"
  server_id = azurerm_mssql_server.main.id
  sku_name  = var.environment == "prod" ? "S1" : "Basic"

  tags = local.common_tags
}

resource "azurerm_mssql_firewall_rule" "azure_services" {
  name             = "AllowAzureServices"
  server_id        = azurerm_mssql_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}
```

## Storage Account

```hcl
# storage.tf

resource "azurerm_storage_account" "main" {
  name                     = "st${replace(var.project_name, "-", "")}${var.environment}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = var.environment == "prod" ? "GRS" : "LRS"
  min_tls_version          = "TLS1_2"

  blob_properties {
    versioning_enabled = var.environment == "prod"
  }

  tags = local.common_tags
}

# Blob container for uploads/media
resource "azurerm_storage_container" "uploads" {
  name                  = "uploads"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}
```

```hcl
# In outputs.tf:

output "storage_account_name" {
  value = azurerm_storage_account.main.name
}

output "storage_primary_connection_string" {
  value     = azurerm_storage_account.main.primary_connection_string
  sensitive = true
}
```

## Redis Cache

```hcl
# cache.tf

resource "azurerm_redis_cache" "main" {
  name                = "redis-${var.project_name}-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  capacity            = 0
  family              = "C"
  sku_name            = var.environment == "prod" ? "Standard" : "Basic"
  minimum_tls_version = "1.2"
  redis_version       = "6"

  redis_configuration {}

  tags = local.common_tags
}
```

## Key Vault (For Secrets Management)

Always use Key Vault for sensitive data in production:

```hcl
# keyvault.tf

data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "main" {
  name                     = "kv-${var.project_name}-${var.environment}"
  location                 = azurerm_resource_group.main.location
  resource_group_name      = azurerm_resource_group.main.name
  tenant_id                = data.azurerm_client_config.current.tenant_id
  sku_name                 = "standard"
  purge_protection_enabled = var.environment == "prod"

  # Grant access to the current user/service principal deploying
  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    secret_permissions = ["Get", "List", "Set", "Delete", "Purge"]
  }

  tags = local.common_tags
}

# Store database password in Key Vault
resource "azurerm_key_vault_secret" "db_password" {
  name         = "database-password"
  value        = var.db_admin_password
  key_vault_id = azurerm_key_vault.main.id
}
```
