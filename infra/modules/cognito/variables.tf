variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "callback_urls" {
  description = "List of callback URLs for Cognito client"
  type        = list(string)
  default     = ["http://localhost:3000/auth/callback"]
}

variable "logout_urls" {
  description = "List of logout URLs for Cognito client"
  type        = list(string)
  default     = ["http://localhost:3000/"]
}

variable "domain_prefix" {
  description = "Cognito domain prefix (must be globally unique)"
  type        = string
  default     = ""
}

variable "api_gateway_id" {
  description = "API Gateway ID for authorizer"
  type        = string
  default     = null
}

variable "cloudfront_domain_name" {
  description = "CloudFront domain name for callback URLs"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "secrets_manager_kms_key_id" {
  description = "KMS key ID for Secrets Manager encryption"
  type        = string
}

# Federated SSO (OIDC) configuration
variable "federated_sso_enabled" {
  description = "Enable Federated SSO (OIDC) authentication"
  type        = bool
  default     = false
}

variable "federated_sso_client_id" {
  description = "Federate service name / OAuth client ID"
  type        = string
  default     = ""
}

variable "federated_sso_client_secret_arn" {
  description = "ARN of Secrets Manager secret containing the Federate OIDC client secret"
  type        = string
  default     = ""
}

variable "federated_sso_issuer" {
  description = "Federate OIDC issuer URL"
  type        = string
  default     = ""
}
variable "federated_sso_provider_name" {
  description = "Name of the OIDC identity provider in Cognito"
  type        = string
  default     = "CorporateSSO"
}
