variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "lambda_role_arn" {
  description = "IAM role ARN for Lambda functions"
  type        = string
}

variable "lambda_package_path" {
  description = "Path to Lambda deployment package"
  type        = string
}

variable "common_env_vars" {
  description = "Common environment variables for all Lambda functions"
  type        = map(string)
  default     = {}
}

variable "dynamodb_table_names" {
  description = "Map of DynamoDB table names"
  type        = map(string)
  default     = {}
}

variable "s3_bucket_names" {
  description = "Map of S3 bucket names"
  type        = map(string)
  default     = {}
}

variable "api_gateway_execution_arn" {
  description = "API Gateway execution ARN for Lambda permissions"
  type        = string
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 14
}

variable "cloudwatch_kms_key_arn" {
  description = "KMS key ARN for CloudWatch log encryption"
  type        = string
  default     = null
}

variable "lambda_kms_key_arn" {
  description = "KMS key ARN for Lambda environment variables encryption"
  type        = string
  default     = null
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

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "pandoc_layer_arn" {
  description = "ARN of the pandoc layer for Lambda functions"
  type        = string
  default     = null
}


variable "powertools_layer_arn" {
  description = "ARN of the AWS Lambda Powertools layer"
  type        = string
  default     = null
}

variable "region" {
  description = "AWS region for constructing layer ARNs"
  type        = string
}

variable "inspector_layer_arn" {
  description = "ARN of the inspector layer for Lambda functions"
  type        = string
  default     = null
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

variable "service_controls_step_function_arn" {
  description = "Service Controls Step Functions state machine ARN for admin operations"
  type        = string
  default     = null
}



variable "bedrock_max_tokens" {
  description = "Maximum tokens for Bedrock model responses"
  type        = number
  default     = 40000
}

variable "agent_base_url" {
  description = "Base URL for agent endpoints"
  type        = string
  default     = ""
}

variable "mcp_endpoint" {
  description = "MCP endpoint for service capability discovery"
  type        = string
  default     = "https://docs.aws.amazon.com"
}

variable "service_controls_table" {
  description = "DynamoDB table name for service controls"
  type        = string
  default     = "risk-agent-service_controls"
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

variable "search_cache_table" {
  description = "DynamoDB table name for search result caching"
  type        = string
  default     = ""
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


