# Azure OpenAI Module - Cognitive Services for LLM agents

resource "azurerm_cognitive_account" "openai" {
  name                = "oai-${var.project_name}-${var.environment}"
  location            = var.location
  resource_group_name = var.resource_group_name
  kind                = "OpenAI"
  sku_name            = "S0" # Standard tier (pay-as-you-go)

  # Managed identity for secure access
  identity {
    type = "SystemAssigned"
  }

  # Network ACLs - deny by default, allow from Container Apps subnet
  network_acls {
    default_action = "Deny"
    virtual_network_rules {
      subnet_id                            = var.subnet_id
      ignore_missing_vnet_service_endpoint = false
    }
  }

  tags = var.tags
}

# GPT-3.5 Turbo Deployment (for cost-optimized agents)
resource "azurerm_cognitive_deployment" "gpt35" {
  count                = var.gpt35_capacity > 0 ? 1 : 0
  name                 = "gpt-35-turbo-deployment"
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "gpt-35-turbo"
    version = "0125" # Latest stable version (Jan 2025)
  }

  scale {
    type     = "Standard"
    capacity = var.gpt35_capacity # TPM (thousands of tokens per minute)
  }
}

# GPT-4 Deployment (for critical agents - DecisionArbiter, Explainability)
resource "azurerm_cognitive_deployment" "gpt4" {
  count                = var.gpt4_capacity > 0 ? 1 : 0
  name                 = "gpt-4-deployment"
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "gpt-4"
    version = "turbo-2024-04-09" # Latest GPT-4 Turbo
  }

  scale {
    type     = "Standard"
    capacity = var.gpt4_capacity # TPM
  }
}
