variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "langfuse_public_key" {
  description = "Langfuse SaaS public key"
  type        = string
  sensitive   = true
}

variable "langfuse_secret_key" {
  description = "Langfuse SaaS secret key"
  type        = string
  sensitive   = true
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

variable "kms_key_id" {
  description = "KMS key ID for encrypting secrets"
  type        = string
}
