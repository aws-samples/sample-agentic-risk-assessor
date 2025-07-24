resource "aws_cognito_user_pool" "this" {
  name = "${var.project_name}-user-pool"
  
  username_attributes = ["email"]
  
  verification_message_template {
    default_email_option = "CONFIRM_WITH_CODE"
    email_message = "Your verification code is {####}"
    email_subject = "Your verification code"
  }
  
  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }
  
  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }
  
  schema {
    attribute_data_type = "String"
    name                = "email"
    required            = true
    mutable             = true
  }

  tags = var.tags
}

resource "aws_cognito_user_pool_client" "this" {
  name = "${var.project_name}-client"
  
  user_pool_id = aws_cognito_user_pool.this.id
  
  generate_secret     = false
  explicit_auth_flows = ["ALLOW_USER_SRP_AUTH", "ALLOW_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"]
  
  callback_urls = var.cloudfront_domain_name != "" ? concat(
    var.callback_urls,
    ["https://${var.cloudfront_domain_name}/auth/callback"]
  ) : var.callback_urls
  
  logout_urls = var.cloudfront_domain_name != "" ? concat(
    var.logout_urls,
    ["https://${var.cloudfront_domain_name}/"]
  ) : var.logout_urls
  
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code", "implicit"]
  allowed_oauth_scopes                 = ["phone", "email", "openid", "profile"]
  supported_identity_providers         = var.federated_sso_enabled ? ["COGNITO", var.federated_sso_provider_name] : ["COGNITO"]

  # Token expiration (shorter when using federated SSO)
  refresh_token_validity = var.federated_sso_enabled ? 10 : 30  # hours
  access_token_validity  = var.federated_sso_enabled ? 10 : 60  # minutes
  id_token_validity      = var.federated_sso_enabled ? 60 : 60  # minutes

  token_validity_units {
    refresh_token = "hours"
    access_token  = "minutes"
    id_token      = "minutes"
  }

  depends_on = [aws_cognito_identity_provider.federated_sso]
}

# Read Federate client secret from Secrets Manager
data "aws_secretsmanager_secret_version" "federated_sso_client_secret" {
  count     = var.federated_sso_enabled ? 1 : 0
  secret_id = var.federated_sso_client_secret_arn
}

# Amazon Federate OIDC Identity Provider
resource "aws_cognito_identity_provider" "federated_sso" {
  count = var.federated_sso_enabled ? 1 : 0

  user_pool_id  = aws_cognito_user_pool.this.id
  provider_name = var.federated_sso_provider_name
  provider_type = "OIDC"

  provider_details = {
    client_id                = var.federated_sso_client_id
    client_secret            = data.aws_secretsmanager_secret_version.federated_sso_client_secret[0].secret_string
    oidc_issuer              = var.federated_sso_issuer
    authorize_scopes         = "openid"
    attributes_request_method = "GET"
  }

  attribute_mapping = {
    email    = "EMAIL"
    username = "sub"
  }
}

# Federate client secret is managed in Secrets Manager outside of Terraform
# Referenced via data source: data.aws_secretsmanager_secret_version.federated_sso_client_secret

resource "aws_cognito_user_pool_domain" "this" {
  domain       = var.domain_prefix != "" ? var.domain_prefix : "${var.project_name}-auth"
  user_pool_id = aws_cognito_user_pool.this.id
}

resource "aws_apigatewayv2_authorizer" "this" {
  count = var.api_gateway_id != null ? 1 : 0
  
  api_id           = var.api_gateway_id
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  name             = "${var.project_name}-cognito-authorizer"

  jwt_configuration {
    audience = [aws_cognito_user_pool_client.this.id]
    issuer   = "https://cognito-idp.${data.aws_region.current.name}.amazonaws.com/${aws_cognito_user_pool.this.id}"
  }
}

data "aws_region" "current" {}

# Create custom resource server for agent scopes
resource "aws_cognito_resource_server" "agent_resource_server" {
  identifier   = "${var.project_name}-api"
  name         = "${var.project_name} API"
  user_pool_id = aws_cognito_user_pool.this.id

  scope {
    scope_name        = "agent.access"
    scope_description = "Agent access to API"
  }
}

# Service Account Clients for Agent-to-Agent Authentication
resource "aws_cognito_user_pool_client" "orchestrator_client" {
  name = "${var.project_name}-orchestrator-client"
  user_pool_id = aws_cognito_user_pool.this.id
  
  generate_secret = true
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows = ["client_credentials"]
  allowed_oauth_scopes = ["${var.project_name}-api/agent.access"]
  
  explicit_auth_flows = [
    "ALLOW_ADMIN_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH"
  ]
  
  depends_on = [aws_cognito_resource_server.agent_resource_server]
}

resource "aws_cognito_user_pool_client" "architect_client" {
  name = "${var.project_name}-architect-client"
  user_pool_id = aws_cognito_user_pool.this.id
  
  generate_secret = true
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows = ["client_credentials"]
  allowed_oauth_scopes = ["${var.project_name}-api/agent.access"]
  
  explicit_auth_flows = [
    "ALLOW_ADMIN_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH"
  ]
  
  depends_on = [aws_cognito_resource_server.agent_resource_server]
}

resource "aws_cognito_user_pool_client" "security_architect_client" {
  name = "${var.project_name}-security-architect-client"
  user_pool_id = aws_cognito_user_pool.this.id
  
  generate_secret = true
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows = ["client_credentials"]
  allowed_oauth_scopes = ["${var.project_name}-api/agent.access"]
  
  explicit_auth_flows = [
    "ALLOW_ADMIN_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH"
  ]
  
  depends_on = [aws_cognito_resource_server.agent_resource_server]
}

resource "aws_cognito_user_pool_client" "risk_assessment_client" {
  name = "${var.project_name}-risk-assessment-client"
  user_pool_id = aws_cognito_user_pool.this.id
  
  generate_secret = true
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows = ["client_credentials"]
  allowed_oauth_scopes = ["${var.project_name}-api/agent.access"]
  
  explicit_auth_flows = [
    "ALLOW_ADMIN_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH"
  ]
  
  depends_on = [aws_cognito_resource_server.agent_resource_server]
}

resource "aws_cognito_user_pool_client" "auditor_client" {
  name = "${var.project_name}-auditor-client"
  user_pool_id = aws_cognito_user_pool.this.id
  
  generate_secret = true
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows = ["client_credentials"]
  allowed_oauth_scopes = ["${var.project_name}-api/agent.access"]
  
  explicit_auth_flows = [
    "ALLOW_ADMIN_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH"
  ]
  
  depends_on = [aws_cognito_resource_server.agent_resource_server]
}

# Store client credentials in Secrets Manager
#checkov:skip=CKV2_AWS_57: Automatic rotation not required for demo application. Production deployment must enable rotation with Lambda function.
resource "aws_secretsmanager_secret" "orchestrator_client_secret" {
  name        = "risk-agent-orchestrator-client-secret"
  description = "OAuth client credentials for orchestrator agent"
  kms_key_id  = var.secrets_manager_kms_key_id

}

resource "aws_secretsmanager_secret_version" "orchestrator_client_secret" {
  secret_id = aws_secretsmanager_secret.orchestrator_client_secret.id
  secret_string = jsonencode({
    client_id = aws_cognito_user_pool_client.orchestrator_client.id
    client_secret = aws_cognito_user_pool_client.orchestrator_client.client_secret
  })
}

#checkov:skip=CKV2_AWS_57: Automatic rotation not required for demo application. Production deployment must enable rotation with Lambda function.
resource "aws_secretsmanager_secret" "architect_client_secret" {
  name        = "risk-agent-architect-client-secret"
  description = "OAuth client credentials for architect agent"
  kms_key_id  = var.secrets_manager_kms_key_id

}

resource "aws_secretsmanager_secret_version" "architect_client_secret" {
  secret_id = aws_secretsmanager_secret.architect_client_secret.id
  secret_string = jsonencode({
    client_id = aws_cognito_user_pool_client.architect_client.id
    client_secret = aws_cognito_user_pool_client.architect_client.client_secret
  })
}

#checkov:skip=CKV2_AWS_57: Automatic rotation not required for demo application. Production deployment must enable rotation with Lambda function.
resource "aws_secretsmanager_secret" "security_architect_client_secret" {
  name        = "risk-agent-security_architect-client-secret"
  description = "OAuth client credentials for security architect agent"
  kms_key_id  = var.secrets_manager_kms_key_id

}

resource "aws_secretsmanager_secret_version" "security_architect_client_secret" {
  secret_id = aws_secretsmanager_secret.security_architect_client_secret.id
  secret_string = jsonencode({
    client_id = aws_cognito_user_pool_client.security_architect_client.id
    client_secret = aws_cognito_user_pool_client.security_architect_client.client_secret
  })
}

#checkov:skip=CKV2_AWS_57: Automatic rotation not required for demo application. Production deployment must enable rotation with Lambda function.
resource "aws_secretsmanager_secret" "risk_assessment_client_secret" {
  name        = "risk-agent-risk_assessment-client-secret"
  description = "OAuth client credentials for risk assessment agent"
  kms_key_id  = var.secrets_manager_kms_key_id

}

resource "aws_secretsmanager_secret_version" "risk_assessment_client_secret" {
  secret_id = aws_secretsmanager_secret.risk_assessment_client_secret.id
  secret_string = jsonencode({
    client_id = aws_cognito_user_pool_client.risk_assessment_client.id
    client_secret = aws_cognito_user_pool_client.risk_assessment_client.client_secret
  })
}

#checkov:skip=CKV2_AWS_57: Automatic rotation not required for demo application. Production deployment must enable rotation with Lambda function.
resource "aws_secretsmanager_secret" "auditor_client_secret" {
  name        = "risk-agent-auditor-client-secret"
  description = "OAuth client credentials for auditor agent"
  kms_key_id  = var.secrets_manager_kms_key_id

}

resource "aws_secretsmanager_secret_version" "auditor_client_secret" {
  secret_id = aws_secretsmanager_secret.auditor_client_secret.id
  secret_string = jsonencode({
    client_id = aws_cognito_user_pool_client.auditor_client.id
    client_secret = aws_cognito_user_pool_client.auditor_client.client_secret
  })
}