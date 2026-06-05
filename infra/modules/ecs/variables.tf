variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "enable_container_insights" {
  description = "Enable CloudWatch Container Insights"
  type        = bool
  default     = true
}

variable "enable_image_scanning" {
  description = "Enable ECR image scanning"
  type        = bool
  default     = true
}

variable "execution_role_arn" {
  description = "ECS task execution role ARN"
  type        = string
}

variable "task_role_arn" {
  description = "ECS task role ARN (default, used if agent-specific role not provided)"
  type        = string
}

variable "agent_task_role_arns" {
  description = "Map of per-agent task role ARNs (agent_name => role_arn)"
  type        = map(string)
  default     = {}
}

variable "subnet_ids" {
  description = "List of subnet IDs for ECS services"
  type        = list(string)
}

variable "security_group_ids" {
  description = "List of security group IDs for ECS services"
  type        = list(string)
}

variable "assign_public_ip" {
  description = "Assign public IP to ECS tasks"
  type        = bool
  default     = false
}

variable "load_balancer_listener_arn" {
  description = "Load balancer listener ARN for dependency"
  type        = string
  default     = null
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "cloudwatch_kms_key_arn" {
  description = "KMS key ARN for CloudWatch log encryption"
  type        = string
  default     = null
}

variable "ecr_kms_key_arn" {
  description = "KMS key ARN for ECR repository encryption"
  type        = string
  default     = ""
}

variable "s3_bucket_names" {
  description = "Map of S3 bucket names"
  type        = map(string)
  default     = {}
}

variable "common_environment_variables" {
  description = "Common environment variables for all services"
  type = list(object({
    name  = string
    value = string
  }))
  default = []
}

variable "target_group_arns" {
  description = "Map of target group ARNs for each service"
  type        = map(string)
  default     = {}
}

variable "external_target_group_arns" {
  description = "Map of external target group ARNs for each service"
  type        = map(string)
  default     = {}
}

variable "cognito_user_pool_id" {
  description = "Cognito User Pool ID for JWT validation"
  type        = string
}

variable "cognito_domain_name" {
  description = "Cognito User Pool Domain for OAuth authentication"
  type        = string
}

variable "agents_alb_dns_name" {
  description = "ALB DNS name for agent-to-agent communication"
  type        = string
}

variable "allowed_origins" {
  description = "Comma-separated list of allowed CORS origins (e.g., https://example.com,https://www.example.com)"
  type        = string
  default     = "*"
}

variable "bedrock_model_id" {
  description = "Bedrock model ID for agents"
  type        = string
  default     = "us.anthropic.claude-sonnet-4-20250514-v1:0"
}

variable "bedrock_max_tokens" {
  description = "Maximum tokens for Bedrock responses"
  type        = number
  default     = 40000
}

variable "bedrock_temperature" {
  description = "Temperature for Bedrock responses"
  type        = number
  default     = 0.0
}

variable "bedrock_top_p" {
  description = "Top P for Bedrock responses"
  type        = number
  default     = 0.1
}

variable "bedrock_top_k" {
  description = "Top K for Bedrock responses"
  type        = number
  default     = 1
}

variable "bedrock_timeout" {
  description = "Timeout for Bedrock responses"
  type        = number
  default     = 120
}
variable "bedrock_role_arn" {
  description = "Bedrock role ARN for cross-account access"
  type        = string
  default     = ""
}

variable "bedrock_account_id" {
  description = "Bedrock account ID for cross-account access"
  type        = string
  default     = ""
}

variable "dynamodb_table_names" {
  description = "Map of DynamoDB table names"
  type        = map(string)
  default     = {}
}

variable "voice_audio_bucket_name" {
  description = "S3 bucket name for voice audio storage"
  type        = string
  default     = ""
}

variable "voice_services_role_arn" {
  description = "IAM role ARN for voice services"
  type        = string
  default     = ""
}

variable "transcribe_vocabulary_name" {
  description = "AWS Transcribe custom vocabulary name"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}