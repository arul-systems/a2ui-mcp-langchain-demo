data "azurerm_client_config" "current" {}

resource "azurerm_role_assignment" "func_identity_storage_blob_contributor" {
  scope                = azurerm_storage_account.func.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_function_app_flex_consumption.agent.identity[0].principal_id
}
