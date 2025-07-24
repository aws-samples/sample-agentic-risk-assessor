variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "stage_name" {
  description = "API Gateway stage name"
  type        = string
  default     = "prod"
}

variable "cors_origins" {
  description = "CORS allowed origins"
  type        = list(string)
  default     = ["*"]
}

variable "cors_methods" {
  description = "CORS allowed methods"
  type        = list(string)
  default     = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
}

variable "cors_headers" {
  description = "CORS allowed headers"
  type        = list(string)
  default     = ["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key", "X-Amz-Security-Token", "Origin", "Accept"]
}

variable "throttling_burst_limit" {
  description = "API Gateway throttling burst limit"
  type        = number
  default     = 5000
}

variable "throttling_rate_limit" {
  description = "API Gateway throttling rate limit"
  type        = number
  default     = 10000
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "lambda_integrations" {
  description = "Map of Lambda function integrations"
  type = map(object({
    invoke_arn = string
  }))
  default = {}
}

variable "lambda_routes" {
  description = "Map of Lambda routes"
  type = map(object({
    route_key       = string
    integration_key = string
    auth_required   = optional(bool, true)
  }))
  default = {}
}

variable "cognito_user_pool_id" {
  description = "Cognito User Pool ID for JWT authorizer"
  type        = string
  default     = null
}

variable "cognito_client_id" {
  description = "Cognito User Pool Client ID for JWT authorizer"
  type        = string
  default     = null
}

variable "vpc_link_config" {
  description = "VPC Link configuration for ALB integration"
  type = object({
    security_group_ids = list(string)
    subnet_ids         = list(string)
  })
  default = null
}

variable "alb_integration" {
  description = "ALB integration configuration"
  type = object({
    listener_arn = string
  })
  default = null
}

variable "alb_routes" {
  description = "Map of ALB routes"
  type = map(object({
    route_key     = string
    auth_required = optional(bool, true)
  }))
  default = {}
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}