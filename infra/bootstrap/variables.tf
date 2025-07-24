variable "aws_account_id" {
  description = "AWS Account ID"
  type        = string
}

variable "aws_profile" {
  description = "AWS Profile to use"
  type        = string
}

variable "region" {
  description = "AWS Region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "risk-agent"
}

variable "terraform_state_bucket" {
  description = "S3 bucket name for Terraform state"
  type        = string
}

variable "terraform_locks_table" {
  description = "DynamoDB table name for Terraform locks"
  type        = string
}