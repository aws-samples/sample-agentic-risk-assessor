variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "List of public subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "List of private subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.20.0/24"]
}

variable "enable_nat_gateway" {
  description = "Enable NAT Gateway for private subnets"
  type        = bool
  default     = true
}

variable "load_balancers" {
  description = "Map of load balancer configurations"
  type = map(object({
    internal                   = bool
    security_group_ids        = list(string)
    enable_deletion_protection = bool
  }))
  default = {}
}

variable "target_groups" {
  description = "Map of target group configurations"
  type = map(object({
    port        = number
    protocol    = string
    target_type = string
    health_check = object({
      healthy_threshold   = number
      interval           = number
      matcher            = string
      path               = string
      protocol           = string
      timeout            = number
      unhealthy_threshold = number
    })
  }))
  default = {}
}

variable "listeners" {
  description = "Map of load balancer listener configurations"
  type = map(object({
    load_balancer_key = string
    port              = number
    protocol          = string
    default_actions = list(object({
      type             = string
      target_group_key = optional(string)
      fixed_response = optional(object({
        content_type = string
        message_body = string
        status_code  = string
      }))
    }))
  }))
  default = {}
}

variable "security_groups" {
  description = "Map of security group configurations"
  type = map(object({
    description = string
    ingress_rules = list(object({
      from_port       = number
      to_port         = number
      protocol        = string
      cidr_blocks     = optional(list(string))
      security_groups = optional(list(string))
    }))
    egress_rules = list(object({
      from_port   = number
      to_port     = number
      protocol    = string
      cidr_blocks = list(string)
    }))
  }))
  default = {}
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "cloudfront_custom_header_name" {
  description = "Name of the custom header CloudFront adds to requests"
  type        = string
  default     = "X-Custom-Header"
}

variable "cloudfront_custom_header_value" {
  description = "Value of the custom header CloudFront adds to requests"
  type        = string
  sensitive   = true
}