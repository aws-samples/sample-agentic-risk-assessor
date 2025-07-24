variable "project_name" {
  description = "Project name"
  type        = string
}

variable "lambda_kms_key_arn" {
  description = "KMS key ARN for Lambda environment encryption"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags to apply to resources"
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
