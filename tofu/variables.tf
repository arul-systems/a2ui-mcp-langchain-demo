variable "location" {
  description = "Azure region to deploy into."
  type        = string
  default     = "eastus"
}

variable "resource_group_name" {
  description = "Name of the resource group to create."
  type        = string
  default     = "rg-a2uidemo-dev"
}

variable "openai_api_key" {
  description = "OpenAI API key the agent Function App uses to call the LLM. Supply via TF_VAR_openai_api_key or an untracked *.tfvars file -- never commit it."
  type        = string
  sensitive   = true
}

variable "tags" {
  description = "Common tags applied to all resources."
  type        = map(string)
  default = {
    project = "a2ui-mcp-langchain-demo"
  }
}
