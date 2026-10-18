variable "location" {
  description = "Azure region to deploy into. Must be one that supports the Flex Consumption plan -- verify with `az functionapp list-flexconsumption-locations -o table`, since the supported-region list is subscription/time dependent."
  type        = string
  default     = "eastus2"
}

variable "openai_api_key" {
  description = "OpenAI API key the agent Function App uses to call the LLM."
  type        = string
  sensitive   = true
}

variable "tags" {
  description = "Common tags applied to all resources."
  type        = map(string)
}
