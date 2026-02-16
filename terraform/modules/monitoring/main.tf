# Monitoring Module - Application Insights + Log Analytics

# Log Analytics Workspace
resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-${var.project_name}-${var.environment}"
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "PerGB2018"
  retention_in_days   = var.retention_days

  tags = var.tags
}

# Application Insights
resource "azurerm_application_insights" "main" {
  name                = "appi-${var.project_name}-${var.environment}"
  location            = var.location
  resource_group_name = var.resource_group_name
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"

  # Sampling to reduce costs
  sampling_percentage = var.sampling_percentage

  tags = var.tags
}

# Note: Smart Detection rules removed - azurerm v4.60.0 has breaking changes in rule names
# Configure these manually in Azure Portal after deployment if needed:
# - Slow page load time
# - Slow server response time
# - Abnormal rise in exception volume
