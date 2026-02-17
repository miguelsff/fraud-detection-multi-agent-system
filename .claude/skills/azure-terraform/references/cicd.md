# CI/CD for Terraform

## Decision: GitHub Actions vs Azure DevOps

| Aspect | GitHub Actions | Azure DevOps |
|--------|---------------|--------------|
| Best for | Open source, GitHub repos | Enterprise, Azure-heavy orgs |
| Terraform support | Excellent (many actions) | Good (tasks available) |
| Cost | Free for public repos | Free tier for 5 users |
| Recommendation | Default choice | Only if org already uses it |

## GitHub Actions (Recommended)

### Workflow: Plan on PR, Apply on Merge

```yaml
# .github/workflows/terraform.yml

name: Terraform

on:
  push:
    branches: [main]
    paths: ['infra/**']
  pull_request:
    branches: [main]
    paths: ['infra/**']

permissions:
  id-token: write   # For OIDC auth with Azure
  contents: read
  pull-requests: write  # For plan comments

env:
  TF_WORKING_DIR: infra
  ARM_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}
  ARM_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
  ARM_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}

jobs:
  plan:
    name: Terraform Plan
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'

    steps:
      - uses: actions/checkout@v4

      - name: Azure Login (OIDC)
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "1.9"

      - name: Terraform Init
        working-directory: ${{ env.TF_WORKING_DIR }}
        run: terraform init

      - name: Terraform Plan
        working-directory: ${{ env.TF_WORKING_DIR }}
        run: terraform plan -var-file="environments/dev.tfvars" -no-color -out=tfplan
        continue-on-error: true

      - name: Post Plan to PR
        uses: actions/github-script@v7
        if: github.event_name == 'pull_request'
        with:
          script: |
            const { execSync } = require('child_process');
            const output = execSync('cd ${{ env.TF_WORKING_DIR }} && terraform show -no-color tfplan').toString();
            const truncated = output.length > 60000 ? output.substring(0, 60000) + '\n... (truncated)' : output;
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## Terraform Plan\n\`\`\`\n${truncated}\n\`\`\``
            });

  apply:
    name: Terraform Apply
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    environment: production  # Requires manual approval in GitHub settings

    steps:
      - uses: actions/checkout@v4

      - name: Azure Login (OIDC)
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "1.9"

      - name: Terraform Init
        working-directory: ${{ env.TF_WORKING_DIR }}
        run: terraform init

      - name: Terraform Apply
        working-directory: ${{ env.TF_WORKING_DIR }}
        run: terraform apply -var-file="environments/dev.tfvars" -auto-approve
```

### Setup OIDC Authentication (No Secrets Needed)

Federated credentials are more secure than storing client secrets:

```bash
# 1. Create service principal
az ad sp create-for-rbac --name "sp-terraform-github" --role Contributor \
  --scopes /subscriptions/<SUBSCRIPTION_ID>

# 2. Create federated credential for GitHub
az ad app federated-credential create \
  --id <APP_ID> \
  --parameters '{
    "name": "github-main",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:<OWNER>/<REPO>:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# 3. Also for pull requests
az ad app federated-credential create \
  --id <APP_ID> \
  --parameters '{
    "name": "github-pr",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:<OWNER>/<REPO>:pull_request",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

Then add these GitHub Secrets:
- `AZURE_CLIENT_ID` — App registration client ID
- `AZURE_TENANT_ID` — Azure AD tenant ID
- `AZURE_SUBSCRIPTION_ID` — Target subscription

## Azure DevOps Pipeline

```yaml
# azure-pipelines.yml

trigger:
  branches:
    include: [main]
  paths:
    include: ['infra/*']

pool:
  vmImage: 'ubuntu-latest'

variables:
  - group: terraform-vars  # Variable group with Azure creds

stages:
  - stage: Plan
    jobs:
      - job: TerraformPlan
        steps:
          - task: TerraformInstaller@1
            inputs:
              terraformVersion: '1.9'

          - task: TerraformTaskV4@4
            displayName: 'Init'
            inputs:
              provider: 'azurerm'
              command: 'init'
              workingDirectory: 'infra'
              backendServiceArm: 'azure-service-connection'
              backendAzureRmResourceGroupName: 'rg-terraform-state'
              backendAzureRmStorageAccountName: 'stterraformstate'
              backendAzureRmContainerName: 'tfstate'
              backendAzureRmKey: 'myapp.tfstate'

          - task: TerraformTaskV4@4
            displayName: 'Plan'
            inputs:
              provider: 'azurerm'
              command: 'plan'
              workingDirectory: 'infra'
              commandOptions: '-var-file="environments/dev.tfvars"'
              environmentServiceNameAzureRM: 'azure-service-connection'

  - stage: Apply
    dependsOn: Plan
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    jobs:
      - deployment: TerraformApply
        environment: 'production'  # Requires approval gate
        strategy:
          runOnce:
            deploy:
              steps:
                - checkout: self
                - task: TerraformInstaller@1
                  inputs:
                    terraformVersion: '1.9'
                - task: TerraformTaskV4@4
                  displayName: 'Init'
                  inputs:
                    provider: 'azurerm'
                    command: 'init'
                    workingDirectory: 'infra'
                    backendServiceArm: 'azure-service-connection'
                    backendAzureRmResourceGroupName: 'rg-terraform-state'
                    backendAzureRmStorageAccountName: 'stterraformstate'
                    backendAzureRmContainerName: 'tfstate'
                    backendAzureRmKey: 'myapp.tfstate'
                - task: TerraformTaskV4@4
                  displayName: 'Apply'
                  inputs:
                    provider: 'azurerm'
                    command: 'apply'
                    workingDirectory: 'infra'
                    commandOptions: '-var-file="environments/dev.tfvars"'
                    environmentServiceNameAzureRM: 'azure-service-connection'
```

## Best Practices

1. **Always plan on PR** — Review infra changes before applying
2. **Apply only on main** — Never auto-apply from feature branches
3. **Use environments with approval gates** — Require manual approval for prod
4. **OIDC over secrets** — Federated credentials don't expire and can't leak
5. **Pin Terraform version** — Same version in CI as locally
6. **Lock provider versions** — Prevent unexpected updates via `required_providers`
