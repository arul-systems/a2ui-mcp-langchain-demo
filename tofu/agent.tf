locals {
  name_prefix = "a2uidemo"
}

resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
  numeric = true
}

resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

resource "azurerm_storage_account" "ui" {
  name                     = "${local.name_prefix}ui${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  tags = var.tags
}

resource "azurerm_storage_account_static_website" "ui" {
  storage_account_id = azurerm_storage_account.ui.id
  index_document     = "index.html"
  error_404_document = "index.html"
}

resource "azurerm_storage_account" "func" {
  name                     = "${local.name_prefix}fn${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  tags = var.tags
}

resource "azurerm_service_plan" "func" {
  name                = "${local.name_prefix}-plan"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  os_type             = "Linux"
  sku_name            = "Y1"

  tags = var.tags
}

resource "azurerm_application_insights" "func" {
  name                = "${local.name_prefix}-ai"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  application_type    = "web"

  tags = var.tags
}

resource "azurerm_linux_function_app" "agent" {
  name                = "${local.name_prefix}-agent"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  service_plan_id            = azurerm_service_plan.func.id
  storage_account_name       = azurerm_storage_account.func.name
  storage_account_access_key = azurerm_storage_account.func.primary_access_key

  identity {
    type = "SystemAssigned"
  }

  site_config {
    application_insights_connection_string = azurerm_application_insights.func.connection_string

    application_stack {
      python_version = "3.12"
    }

    cors {
      allowed_origins = [trimsuffix(azurerm_storage_account.ui.primary_web_endpoint, "/")]
    }
  }

  app_settings = {
    FUNCTIONS_WORKER_RUNTIME = "python"
    OPENAI_API_KEY           = var.openai_api_key
  }

  tags = var.tags
}

output "static_website_url" {
  description = "Public URL of the agent-ui static website."
  value       = azurerm_storage_account.ui.primary_web_endpoint
}

output "ui_storage_account_name" {
  description = "Storage account to upload the agent-ui build into (the $web container)."
  value       = azurerm_storage_account.ui.name
}

output "function_app_url" {
  description = "Public HTTPS URL of the agent Function App."
  value       = "https://${azurerm_linux_function_app.agent.default_hostname}"
}

output "function_app_name" {
  description = "Function App name, for `func azure functionapp publish <name>` or az cli deploys."
  value       = azurerm_linux_function_app.agent.name
}
