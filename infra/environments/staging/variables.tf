variable "region" {
  description = "AWS region to deploy resources"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
}

variable "aws_account_id" {
  description = "Target AWS Account ID for deployment"
  type        = string
}

variable "aws_profile" {
  description = "AWS CLI profile to use for deployment"
  type        = string
}

variable "terraform_state_bucket" {
  description = "S3 bucket for Terraform state (account-specific)"
  type        = string
}

variable "terraform_locks_table" {
  description = "DynamoDB table for Terraform locks (account-specific)"
  type        = string
}

variable "cognito_callback_urls" {
  description = "List of callback URLs for Cognito client"
  type        = list(string)
}

variable "cognito_logout_urls" {
  description = "List of logout URLs for Cognito client"
  type        = list(string)
}

# NEW: Enhanced discovery variables
variable "knowledge_base_id" {
  description = "Bedrock Knowledge Base ID for RAG queries"
  type        = string
  default     = "V7XKVYPJFR"
}

variable "rag_model_id" {
  description = "Model ID for RAG queries"
  type        = string
  default     = "us.anthropic.claude-sonnet-4-6"
}

variable "bedrock_role_arn" {
  description = "Cross-account Bedrock role ARN to assume"
  type        = string
  default     = ""
}

variable "bedrock_account_id" {
  description = "AWS account ID for external Bedrock access"
  type        = string
  default     = null
}

variable "bedrock_model_id" {
  description = "Bedrock model ID to use for agents"
  type        = string
  default     = "us.anthropic.claude-sonnet-4-6"
}



variable "bedrock_parsing_model_id" {
  description = "Bedrock model ID to use for knowledge base parsing (must support on-demand)"
  type        = string
  default     = "us.anthropic.claude-sonnet-4-6"
}

variable "bedrock_role_name" {
  description = "Bedrock role name to assume"
  type        = string
  default     = null
}

variable "bedrock_max_tokens" {
  description = "Maximum tokens for Bedrock model responses"
  type        = number
  default     = 40000
}

variable "bedrock_temperature" {
  description = "Temperature for Bedrock model responses"
  type        = number
  default     = 0.0
}

variable "bedrock_top_p" {
  description = "Top P for Bedrock model responses"
  type        = number
  default     = 0.1
}

variable "bedrock_top_k" {
  description = "Top K for Bedrock model responses"
  type        = number
  default     = 1
}

variable "bedrock_timeout" {
  description = "Timeout for Bedrock model responses"
  type        = number
  default     = 120
}

# RAG-specific configuration for discover_framework_controls
variable "rag_bedrock_model_id" {
  description = "Bedrock model ID specifically for RAG operations in discover_framework_controls"
  type        = string
  default     = "us.anthropic.claude-sonnet-4-6"
}

variable "rag_bedrock_temperature" {
  description = "Temperature for RAG Bedrock model responses (lower for consistent JSON)"
  type        = number
  default     = 0.2
}

variable "rag_bedrock_top_p" {
  description = "Top P for RAG Bedrock model responses (lower for focused responses)"
  type        = number
  default     = 0.2
}

variable "rag_bedrock_top_k" {
  description = "Top K for RAG Bedrock model responses (lower for consistent output)"
  type        = number
  default     = 20
}

variable "api_gateway_routes" {
  description = "Map of API Gateway routes"
  type = map(object({
    route_key       = string
    integration_key = string
    auth_required   = optional(bool, true)
  }))
  default = {}
}






# MCP Search Integration Variables
variable "mcp_search_endpoint" {
  description = "MCP internet search endpoint URL"
  type        = string
  default     = ""
}

variable "mcp_api_key" {
  description = "API key for MCP internet search service"
  type        = string
  default     = ""
  sensitive   = true
}

variable "max_search_results" {
  description = "Maximum number of search results to return"
  type        = number
  default     = 10
}

variable "cache_ttl_hours" {
  description = "Cache TTL in hours for search results"
  type        = number
  default     = 24
}

data "aws_availability_zones" "available" {}

variable "frontend_image_tag" {
  description = "Frontend Docker image tag"
  type        = string
  default     = "latest"
}

# Federated SSO (OIDC) Authentication
variable "federated_sso_enabled" {
  description = "Enable Federated SSO (OIDC) authentication"
  type        = bool
  default     = false
}

variable "federated_sso_client_id" {
  description = "Federate service name / OAuth client ID"
  type        = string
  default     = ""
}

variable "federated_sso_client_secret_arn" {
  description = "ARN of Secrets Manager secret containing the Federate OIDC client secret"
  type        = string
  default     = ""
}

variable "federated_sso_issuer" {
  description = "Federate OIDC issuer URL"
  type        = string
  default     = ""
}
