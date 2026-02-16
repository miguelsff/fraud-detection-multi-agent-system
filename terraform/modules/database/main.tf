# Database Module - PostgreSQL Flexible Server

# Random password for PostgreSQL admin
resource "random_password" "postgresql_admin" {
  length  = 32
  special = true
}

# PostgreSQL Flexible Server
resource "azurerm_postgresql_flexible_server" "main" {
  name                = "psql-${var.project_name}-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location

  # Database configuration
  sku_name   = var.sku_name
  version    = "16"
  storage_mb = var.storage_mb

  # Admin credentials
  administrator_login    = var.admin_username
  administrator_password = random_password.postgresql_admin.result

  # Networking (private, VNet-integrated)
  delegated_subnet_id         = var.subnet_id
  private_dns_zone_id         = var.private_dns_zone_id
  public_network_access_enabled = false # Required when using VNet integration

  # High availability (only for production)
  zone = var.zone

  dynamic "high_availability" {
    for_each = var.enable_high_availability ? [1] : []
    content {
      mode                      = "ZoneRedundant"
      standby_availability_zone = var.standby_zone
    }
  }

  # Backup configuration
  backup_retention_days        = var.backup_retention_days
  geo_redundant_backup_enabled = var.enable_geo_redundant_backup

  # Maintenance window (Sunday 2-3 AM UTC)
  maintenance_window {
    day_of_week  = 0
    start_hour   = 2
    start_minute = 0
  }

  tags = var.tags

  # Lifecycle: prevent accidental deletion in production
  lifecycle {
    prevent_destroy = false # Set to true in production
    ignore_changes = [
      zone, # Immutable after creation
    ]
  }
}

# Database for the application
resource "azurerm_postgresql_flexible_server_database" "main" {
  name      = var.database_name
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# PostgreSQL configurations (performance tuning)
resource "azurerm_postgresql_flexible_server_configuration" "max_connections" {
  name      = "max_connections"
  server_id = azurerm_postgresql_flexible_server.main.id
  value     = var.max_connections
}

resource "azurerm_postgresql_flexible_server_configuration" "shared_buffers" {
  name      = "shared_buffers"
  server_id = azurerm_postgresql_flexible_server.main.id
  value     = var.shared_buffers_mb
}
