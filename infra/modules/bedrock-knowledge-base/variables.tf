variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "bedrock_parsing_model_id" {
  description = "Bedrock model ID to use for knowledge base parsing (must support on-demand)"
  type        = string
  default     = "us.anthropic.claude-sonnet-4-6"
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# Optimal chunking configuration for compliance mapping
variable "chunk_size" {
  description = "Optimal chunk size for compliance content"
  type        = number
  default     = 750
}

variable "chunk_overlap" {
  description = "Optimal chunk overlap for technical content (30%)"
  type        = number
  default     = 150
}

variable "parent_chunk_size" {
  description = "Parent chunk size for hierarchical chunking"
  type        = number
  default     = 1500
}

variable "bedrock_model_id" {
  description = "Bedrock model ID for parsing configuration"
  type        = string
}


variable "s3_kms_key_arn" {
  description = "KMS key ARN for S3 encryption"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID for OpenSearch Serverless VPC endpoint"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for OpenSearch Serverless VPC endpoint"
  type        = list(string)
}
