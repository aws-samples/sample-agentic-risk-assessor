variable "region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "risk-agent"
}

variable "aws_account_id" {
  description = "Target AWS Account ID for deployment"
  type        = string
}

variable "aws_profile" {
  description = "AWS CLI profile to use for deployment"
  type        = string
  default     = ""
}

variable "terraform_state_bucket" {
  description = "S3 bucket for Terraform state (account-specific)"
  type        = string
}

variable "terraform_locks_table" {
  description = "DynamoDB table for Terraform locks (account-specific)"
  type        = string
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