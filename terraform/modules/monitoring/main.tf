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

# Smart Detection - Anomaly detection rules
resource "azurerm_application_insights_smart_detection_rule" "failure_anomalies" {
  name                    = "Failure Anomalies"
  application_insights_id = azurerm_application_insights.main.id
  enabled                 = true
}

resource "azurerm_application_insights_smart_detection_rule" "slow_page_load" {
  name                    = "Slow page load time"
  application_insights_id = azurerm_application_insights.main.id
  enabled                 = true
}

resource "azurerm_application_insights_smart_detection_rule" "slow_server_response" {
  name                    = "Slow server response time"
  application_insights_id = azurerm_application_insights.main.id
  enabled                 = true
}
