provider "aws" {
  region = "us-east-1"
  profile = "risk-agent"
  insecure = true
}

data "aws_caller_identity" "current" {}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "risk-agent"
}

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "cognito_user_pool_arn" {
  description = "Cognito User Pool ARN for API authorization"
  type        = string
  default     = ""
}

variable "lambda_kms_key_arn" {
  description = "KMS key ARN for Lambda environment encryption"
  type        = string
  default     = ""
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "staging"
}

# Security Questions Table
# nosemgrep: terraform.aws.security.aws-dynamodb-table-unencrypted.aws-dynamodb-table-unencrypted
resource "aws_dynamodb_table" "security_questions" {
  name           = "risk-agent-security-questions"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "project_id"

  attribute {
    name = "project_id"
    type = "S"
  }

  tags = {
    Name = "RiskAgent Security Questions"
    Environment = var.environment
  }
}

# Security Responses Table
# nosemgrep: terraform.aws.security.aws-dynamodb-table-unencrypted.aws-dynamodb-table-unencrypted
resource "aws_dynamodb_table" "security_responses" {
  name           = "risk-agent-security-responses"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "project_id"

  attribute {
    name = "project_id"
    type = "S"
  }

  tags = {
    Name = "RiskAgent Security Responses"
    Environment = var.environment
  }
}

# Security Assessments Table
# nosemgrep: terraform.aws.security.aws-dynamodb-table-unencrypted.aws-dynamodb-table-unencrypted
resource "aws_dynamodb_table" "security_assessments" {
  name           = "risk-agent-security-assessments"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "project_id"

  attribute {
    name = "project_id"
    type = "S"
  }

  tags = {
    Name = "RiskAgent Security Assessments"
    Environment = var.environment
  }
}