variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where frontend will be deployed"
  type        = string
}

variable "subnet_ids" {
  description = "Private subnet IDs for ECS tasks"
  type        = list(string)
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for ALB"
  type        = list(string)
}

variable "certificate_arn" {
  description = "ACM certificate ARN for HTTPS"
  type        = string
  default     = null
}

variable "security_group_ids" {
  description = "Security group IDs for frontend"
  type        = list(string)
}

variable "waf_web_acl_arn" {
  description = "WAF Web ACL ARN for ALB protection"
  type        = string
}

variable "execution_role_arn" {
  description = "ECS task execution role ARN"
  type        = string
}

variable "task_role_arn" {
  description = "ECS task role ARN"
  type        = string
}

variable "cpu" {
  description = "CPU units for frontend container"
  type        = number
  default     = 256
}

variable "memory" {
  description = "Memory for frontend container"
  type        = number
  default     = 512
}

variable "desired_count" {
  description = "Desired number of frontend tasks"
  type        = number
  default     = 1
}

variable "container_port" {
  description = "Port the frontend container listens on"
  type        = number
  default     = 3000
}

variable "image_tag" {
  description = "Docker image tag"
  type        = string
  default     = "latest"
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "api_gateway_url" {
  description = "API Gateway URL for backend API calls"
  type        = string
}

variable "cloudfront_url" {
  description = "CloudFront URL for agents"
  type        = string
}

variable "agents_alb_url" {
  description = "Agents ALB DNS name (deprecated, use cloudfront_url)"
  type        = string
  default     = ""
}

variable "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  type        = string
}

variable "cognito_client_id" {
  description = "Cognito User Pool Client ID"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

variable "ecr_kms_key_arn" {
  description = "KMS key ARN for ECR encryption"
  type        = string
}

variable "cloudwatch_kms_key_arn" {
  description = "KMS key ARN for CloudWatch log encryption"
  type        = string
}