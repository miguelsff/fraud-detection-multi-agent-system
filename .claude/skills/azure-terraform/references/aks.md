# Azure Kubernetes Service (AKS)

## When to Use AKS

- Complex microservice architectures (10+ services)
- Need Kubernetes-native features (Helm, service mesh, custom operators)
- Team already knows Kubernetes
- Workloads that require fine-grained pod scheduling

If you have < 5 services and don't need K8s features → Container Apps is simpler and cheaper.

## Minimal AKS Cluster

```hcl
# aks.tf

resource "azurerm_kubernetes_cluster" "main" {
  name                = "aks-${var.project_name}-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  dns_prefix          = "${var.project_name}-${var.environment}"
  kubernetes_version  = var.kubernetes_version

  default_node_pool {
    name                = "default"
    vm_size             = var.aks_node_size
    min_count           = var.aks_min_nodes
    max_count           = var.aks_max_nodes
    auto_scaling_enabled = true
    os_disk_size_gb     = 30

    tags = local.common_tags
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin = "azure"
    service_cidr   = "10.0.16.0/20"
    dns_service_ip = "10.0.16.10"
  }

  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  }

  tags = local.common_tags
}
```

```hcl
# In variables.tf add:

variable "kubernetes_version" {
  description = "AKS Kubernetes version"
  type        = string
  default     = "1.29"
}

variable "aks_node_size" {
  description = "VM size for AKS nodes"
  type        = string
  default     = "Standard_B2s"  # 2 vCPU, 4GB — cheapest viable option
}

variable "aks_min_nodes" {
  description = "Minimum nodes in default pool"
  type        = number
  default     = 1
}

variable "aks_max_nodes" {
  description = "Maximum nodes in default pool"
  type        = number
  default     = 3
}
```

```hcl
# In outputs.tf add:

output "aks_cluster_name" {
  value = azurerm_kubernetes_cluster.main.name
}

output "kube_config" {
  value     = azurerm_kubernetes_cluster.main.kube_config_raw
  sensitive = true
}
```

## Connect ACR to AKS

```hcl
resource "azurerm_role_assignment" "aks_acr_pull" {
  scope                            = azurerm_container_registry.main.id
  role_definition_name             = "AcrPull"
  principal_id                     = azurerm_kubernetes_cluster.main.kubelet_identity[0].object_id
  skip_service_principal_aad_check = true
}
```

## Post-Deploy: Get Credentials

```bash
az aks get-credentials --resource-group rg-myapp-dev --name aks-myapp-dev
kubectl get nodes
```

## Node Size Guide

| Use Case | VM Size | vCPU | RAM | Monthly/node |
|----------|---------|------|-----|-------------|
| Dev/Test | `Standard_B2s` | 2 | 4GB | ~$30 |
| Small prod | `Standard_D2s_v5` | 2 | 8GB | ~$70 |
| Medium prod | `Standard_D4s_v5` | 4 | 16GB | ~$140 |
| Memory intensive | `Standard_E4s_v5` | 4 | 32GB | ~$200 |

Start small. AKS autoscaler adds nodes when needed.

## Add-ons Worth Enabling

Only enable what you actually need:

```hcl
# Inside azurerm_kubernetes_cluster:

  # Ingress controller (avoid deploying your own nginx)
  web_app_routing {
    dns_zone_ids = []  # Add DNS zone ID for custom domain
  }

  # Key Vault secrets provider
  key_vault_secrets_provider {
    secret_rotation_enabled = true
  }
```

## What NOT to Do with AKS

- Don't use AKS for < 3 services (use Container Apps)
- Don't skip autoscaler — manual node management is painful
- Don't use `Standard_B` series in production (burstable = inconsistent)
- Don't forget to set resource requests/limits in K8s manifests
- Don't manage certificates manually — use cert-manager or Web App Routing
