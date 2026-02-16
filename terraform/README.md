# Terraform Infrastructure as Code

Infrastructure automation for deploying the Fraud Detection Multi-Agent System to Azure Cloud.

## Architecture Overview

- **Azure Container Apps** - Serverless containers for backend (FastAPI) and frontend (Next.js)
- **PostgreSQL Flexible Server** - Managed database (B1ms dev, GP tier production)
- **Azure OpenAI** - GPT-3.5 Turbo + GPT-4 for LLM agents
- **Azure Files** - SMB persistent storage for ChromaDB vector database
- **Key Vault** - Secure secrets management
- **Application Insights** - Monitoring and logging
- **Virtual Network** - Private networking with service endpoints

## Directory Structure

```
terraform/
├── environments/           # Environment-specific configurations
│   ├── dev/               # Development environment (~$25-30/month)
│   │   ├── main.tf        # Resource definitions
│   │   ├── variables.tf   # Input variables
│   │   ├── outputs.tf     # Output values
│   │   ├── backend.tf     # Remote state config
│   │   └── terraform.tfvars.example
│   ├── staging/           # Staging environment (future)
│   └── prod/              # Production environment (future)
├── modules/               # Reusable Terraform modules
│   ├── networking/        # VNet, subnets, NSGs, private DNS
│   ├── container-registry/# Azure Container Registry
│   ├── database/          # PostgreSQL Flexible Server
│   ├── storage/           # Storage Account + Files
│   ├── key-vault/         # Key Vault + secrets
│   ├── monitoring/        # App Insights + Log Analytics
│   ├── container-apps/    # Container Apps Environment + Apps
│   └── azure-openai/      # Azure OpenAI deployments
├── scripts/               # Automation scripts
│   ├── setup.sh           # Initialize Terraform backend
│   ├── deploy.sh          # Deploy infrastructure
│   ├── destroy.sh         # Destroy infrastructure
│   ├── migrate-chromadb.sh# Migrate ChromaDB to Azure Files
│   ├── secrets-sync.sh    # Sync secrets to Key Vault
│   └── health-check.sh    # Post-deploy validation
└── shared/                # Shared configuration
    ├── variables.tf       # Common variables
    └── locals.tf          # Common locals
```

## Prerequisites

### 1. Install Required Tools

```bash
# Terraform
brew install terraform  # macOS
choco install terraform # Windows

# Azure CLI
brew install azure-cli  # macOS
choco install azure-cli # Windows

# Login to Azure
az login
```

### 2. Create Azure Service Principal

```bash
# Create service principal for Terraform
az ad sp create-for-rbac \
  --name "sp-fraud-terraform" \
  --role Contributor \
  --scopes /subscriptions/YOUR_SUBSCRIPTION_ID

# Output (save these values):
# {
#   "appId": "...",        # AZURE_CLIENT_ID
#   "password": "...",     # AZURE_CLIENT_SECRET
#   "tenant": "..."        # AZURE_TENANT_ID
# }
```

### 3. Configure GitHub Secrets

Add these secrets to your GitHub repository (Settings > Secrets and variables > Actions):

- `AZURE_CLIENT_ID` - Service principal app ID
- `AZURE_CLIENT_SECRET` - Service principal password
- `AZURE_SUBSCRIPTION_ID` - Your Azure subscription ID
- `AZURE_TENANT_ID` - Your Azure tenant ID
- `OPENSANCTIONS_API_KEY` - OpenSanctions API key

## Deployment

### Phase 1: Dev Environment Only

**Estimated cost: ~$25-30/month**

#### Step 1: Initialize Terraform Backend

```bash
# Create storage account for Terraform state
cd terraform
bash scripts/setup.sh dev
```

#### Step 2: Configure Variables

```bash
cd environments/dev
cp terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars with your values
nano terraform.tfvars
```

#### Step 3: Deploy Infrastructure

```bash
# Initialize Terraform
terraform init

# Preview changes
terraform plan

# Deploy (requires approval)
terraform apply
```

#### Step 4: Migrate ChromaDB Data

```bash
# Upload local ChromaDB data to Azure Files
cd ../../
bash scripts/migrate-chromadb.sh dev
```

#### Step 5: Verify Deployment

```bash
# Run health checks
bash scripts/health-check.sh dev

# Get outputs
cd environments/dev
terraform output
```

## Cost Optimization

### Dev Environment (~$25-30/month)

| Resource | Spec | Monthly Cost |
|----------|------|--------------|
| Container Apps (Backend) | 1 replica, 0.5 vCPU, 1GB | $10 |
| Container Apps (Frontend) | 1 replica, 0.5 vCPU, 1GB | $5 |
| PostgreSQL B1ms | 1 vCore, 2GB RAM | $12 |
| Azure OpenAI | GPT-3.5 Turbo only | $3-5 |
| Storage + ACR + Monitoring | | $3 |
| **Total** | | **~$33/month** |

**Cost-saving tips for dev:**
- GPT-4 disabled (set `azure_openai_gpt4_capacity = 0`)
- Single replica for backend/frontend
- Basic ACR tier
- 30-day log retention
- No geo-replication

## Modules Documentation

Each module in `modules/` has its own README.md with:
- Input variables
- Output values
- Resource descriptions
- Usage examples

**Status: Modules to be implemented (Tasks #4-11)**

## CI/CD Pipeline

GitHub Actions workflows (`.github/workflows/`):
- `terraform-plan.yml` - Run on PRs (preview changes)
- `terraform-apply-dev.yml` - Auto-deploy to dev on merge to main
- `terraform-apply-prod.yml` - Manual deploy to prod (requires approval)

**Status: Workflows to be implemented (Task #14)**

## Security Considerations

- **Never commit `terraform.tfvars`** - Contains sensitive credentials
- **Never commit `.terraform/`** - Contains state and plugins
- **State stored remotely** - Azure Storage with encryption
- **Secrets in Key Vault** - Referenced by Container Apps via managed identity
- **Private networking** - PostgreSQL not publicly accessible
- **Network ACLs** - Restrictive firewall rules on all services

## Troubleshooting

### "Error: Backend not initialized"

```bash
cd environments/dev
terraform init -reconfigure
```

### "Error: Insufficient quota"

Check Azure quotas:
```bash
az vm list-usage --location eastus --output table
```

### Container App not pulling images

```bash
# Check ACR credentials
az acr credential show --name <acr-name>

# Verify managed identity has AcrPull role
az role assignment list --assignee <identity-principal-id>
```

## Next Steps

1. ✅ **Security fixes** (Task #1) - Completed
2. ✅ **LLM factory** (Task #2) - Completed
3. ✅ **Terraform structure** (Task #3) - Completed
4. 🔄 **Implement modules** (Tasks #4-11) - In Progress
5. ⏳ **Create scripts** (Task #12) - Pending
6. ⏳ **GitHub Actions** (Task #14) - Pending
7. ⏳ **Documentation** (Task #16) - Pending

## Support

For issues or questions:
- Check module READMEs for specific troubleshooting
- Review Azure OpenAI pricing at https://azure.microsoft.com/pricing/details/cognitive-services/openai-service/
- Review Container Apps pricing at https://azure.microsoft.com/pricing/details/container-apps/
