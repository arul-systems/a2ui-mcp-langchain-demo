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
  name     = "${local.name_prefix}rg${random_string.suffix.result}"
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

resource "azurerm_storage_container" "func_deployments" {
  name                  = "function-deployments"
  storage_account_id    = azurerm_storage_account.func.id
  container_access_type = "private"
}

resource "azurerm_service_plan" "func" {
  name                = "${local.name_prefix}-plan"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  os_type             = "Linux"
  sku_name            = "FC1"

  tags = var.tags
}

resource "azurerm_application_insights" "func" {
  name                = "${local.name_prefix}-ai"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  application_type    = "web"

  tags = var.tags
}

resource "azurerm_function_app_flex_consumption" "agent" {
  name                = "${local.name_prefix}-agent"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  service_plan_id     = azurerm_service_plan.func.id

  storage_container_type      = "blobContainer"
  storage_container_endpoint  = "${azurerm_storage_account.func.primary_blob_endpoint}${azurerm_storage_container.func_deployments.name}"
  storage_authentication_type = "StorageAccountConnectionString"
  storage_access_key          = azurerm_storage_account.func.primary_access_key

  runtime_name           = "python"
  runtime_version        = "3.12"
  maximum_instance_count = 100
  instance_memory_in_mb  = 2048

  identity {
    type = "SystemAssigned"
  }

  site_config {
    cors {
      allowed_origins = [
        trimsuffix(azurerm_storage_account.ui.primary_web_endpoint, "/"),
        "https://portal.azure.com",
      ]
    }
  }

  app_settings = {
    OPENAI_API_KEY                        = var.openai_api_key
    APPLICATIONINSIGHTS_CONNECTION_STRING = azurerm_application_insights.func.connection_string
  }

  tags = var.tags
}

resource "azurerm_storage_account" "item_mcp_func" {
  name                     = "${local.name_prefix}imfn${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  tags = var.tags
}

resource "azurerm_storage_container" "item_mcp_deployments" {
  name                  = "function-deployments"
  storage_account_id    = azurerm_storage_account.item_mcp_func.id
  container_access_type = "private"
}

resource "azurerm_service_plan" "item_mcp" {
  # Flex Consumption allows exactly one Function App per service plan --
  # confirmed by Azure rejecting a second site on azurerm_service_plan.func
  # with "There can only be one site per Flex Consumption serverfarm" --
  # so item-mcp needs its own plan, not azurerm_service_plan.func.
  name                = "${local.name_prefix}-item-mcp-plan"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  os_type             = "Linux"
  sku_name            = "FC1"

  tags = var.tags
}

resource "azurerm_function_app_flex_consumption" "item_mcp" {
  name                = "${local.name_prefix}-item-mcp"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  service_plan_id     = azurerm_service_plan.item_mcp.id

  storage_container_type      = "blobContainer"
  storage_container_endpoint  = "${azurerm_storage_account.item_mcp_func.primary_blob_endpoint}${azurerm_storage_container.item_mcp_deployments.name}"
  storage_authentication_type = "StorageAccountConnectionString"
  storage_access_key          = azurerm_storage_account.item_mcp_func.primary_access_key

  runtime_name           = "python"
  runtime_version        = "3.12"
  maximum_instance_count = 100
  instance_memory_in_mb  = 2048

  identity {
    type = "SystemAssigned"
  }

  site_config {
    application_insights_connection_string = azurerm_application_insights.func.connection_string
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
  value       = "https://${azurerm_function_app_flex_consumption.agent.default_hostname}"
}

output "function_app_name" {
  description = "Function App name, for `func azure functionapp publish <name>` or az cli deploys."
  value       = azurerm_function_app_flex_consumption.agent.name
}

output "item_mcp_function_app_url" {
  description = "Public HTTPS URL of the item-mcp Function App."
  value       = "https://${azurerm_function_app_flex_consumption.item_mcp.default_hostname}"
}

output "item_mcp_function_app_name" {
  description = "item-mcp Function App name, for `func azure functionapp publish <name>` or az cli deploys."
  value       = azurerm_function_app_flex_consumption.item_mcp.name
}
