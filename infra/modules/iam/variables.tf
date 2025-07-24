variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "region" {
  description = "AWS region"
  type        = string
}

variable "account_id" {
  description = "AWS account ID"
  type        = string
}

variable "dynamodb_table_arns" {
  description = "List of DynamoDB table ARNs"
  type        = list(string)
  default     = []
}

variable "dynamodb_kms_key_arn" {
  description = "KMS key ARN for DynamoDB encryption"
  type        = string
}

variable "s3_bucket_arns" {
  description = "List of S3 bucket ARNs"
  type        = list(string)
  default     = []
}

variable "voice_audio_bucket_arn" {
  description = "ARN of the dedicated voice audio S3 bucket"
  type        = string
  default     = ""
}

variable "s3_kms_key_arn" {
  description = "KMS key ARN for S3 bucket encryption"
  type        = string
}

variable "bedrock_role_arn" {
  description = "Cross-account Bedrock role ARN to assume"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "aws_account_id" {
  description = "AWS account ID"
  type        = string
}

variable "agent_names" {
  description = "List of agent names for per-agent IAM role creation (must match ECS service keys)"
  type        = list(string)
  default     = ["orchestrator", "architect", "security_architect", "risk_assessment", "auditor", "organization_profile"]
}
