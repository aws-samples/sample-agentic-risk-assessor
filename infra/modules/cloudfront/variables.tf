variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "cloudfront_secret" {
  description = "Secret header value for ALB WAF validation"
  type        = string
  sensitive   = true
}

variable "frontend_alb_dns_name" {
  description = "DNS name of the frontend ALB"
  type        = string
}

variable "agents_alb_dns_name" {
  description = "DNS name of the agents ALB"
  type        = string
}

variable "api_gateway_domain_name" {
  description = "Domain name of the API Gateway"
  type        = string
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}