output "user_pool_id" {
  description = "Cognito User Pool ID"
  value       = aws_cognito_user_pool.this.id
}

output "user_pool_arn" {
  description = "Cognito User Pool ARN"
  value       = aws_cognito_user_pool.this.arn
}

output "user_pool_client_id" {
  description = "Cognito User Pool Client ID"
  value       = aws_cognito_user_pool_client.this.id
}

output "authorizer_id" {
  description = "API Gateway JWT Authorizer ID"
  value       = length(aws_apigatewayv2_authorizer.this) > 0 ? aws_apigatewayv2_authorizer.this[0].id : null
}

output "domain_name" {
  description = "Cognito User Pool Domain"
  value       = aws_cognito_user_pool_domain.this.domain
}

output "service_client_secrets" {
  description = "ARNs of service account client secrets"
  value = {
    orchestrator = aws_secretsmanager_secret.orchestrator_client_secret.arn
    architect = aws_secretsmanager_secret.architect_client_secret.arn
    security_architect = aws_secretsmanager_secret.security_architect_client_secret.arn
    risk_assessment = aws_secretsmanager_secret.risk_assessment_client_secret.arn
    auditor = aws_secretsmanager_secret.auditor_client_secret.arn
  }
}

output "federated_sso_enabled" {
  description = "Whether Federated SSO authentication is enabled"
  value       = var.federated_sso_enabled
}

output "cognito_domain_url" {
  description = "Full Cognito domain URL for OAuth flows"
  value       = "https://${aws_cognito_user_pool_domain.this.domain}.auth.${data.aws_region.current.name}.amazoncognito.com"
}

output "federate_redirect_uri" {
  description = "Redirect URI to register with Amazon Federate"
  value       = var.federated_sso_enabled ? "https://${aws_cognito_user_pool_domain.this.domain}.auth.${data.aws_region.current.name}.amazoncognito.com/oauth2/idpresponse" : ""
}