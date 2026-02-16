# Terraform backend configuration for dev environment
# Remote state stored in Azure Storage

terraform {
  backend "azurerm" {
    resource_group_name  = "rg-fraud-terraform-state"
    storage_account_name = "stfraudtfstatedev"
    container_name       = "tfstate"
    key                  = "dev.terraform.tfstate"
  }
}
