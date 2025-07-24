# Security Assessment API Gateway Resources

# Import existing API Gateway
data "aws_api_gateway_rest_api" "existing" {
  name = "TestAPI2"
}

# Cognito Authorizer for REST API
resource "aws_api_gateway_authorizer" "cognito" {
  name            = "cognito-authorizer"
  rest_api_id     = data.aws_api_gateway_rest_api.existing.id
  type            = "COGNITO_USER_POOLS"
  provider_arns   = [var.cognito_user_pool_arn]
  identity_source = "method.request.header.Authorization"
}

# Create projects resource if it doesn't exist
resource "aws_api_gateway_resource" "projects" {
  rest_api_id = data.aws_api_gateway_rest_api.existing.id
  parent_id   = data.aws_api_gateway_rest_api.existing.root_resource_id
  path_part   = "projects"
}

# Create projects/{id} resource
resource "aws_api_gateway_resource" "projects_id" {
  rest_api_id = data.aws_api_gateway_rest_api.existing.id
  parent_id   = aws_api_gateway_resource.projects.id
  path_part   = "{id}"
}

# Security Questions Resource
resource "aws_api_gateway_resource" "security_questions" {
  rest_api_id = data.aws_api_gateway_rest_api.existing.id
  parent_id   = aws_api_gateway_resource.projects_id.id
  path_part   = "security-questions"
}

# POST /projects/{id}/security-questions
resource "aws_api_gateway_method" "generate_security_questions" {
  rest_api_id   = data.aws_api_gateway_rest_api.existing.id
  resource_id   = aws_api_gateway_resource.security_questions.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "generate_security_questions" {
  rest_api_id = data.aws_api_gateway_rest_api.existing.id
  resource_id = aws_api_gateway_resource.security_questions.id
  http_method = aws_api_gateway_method.generate_security_questions.http_method
  
  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.generate_security_questions.invoke_arn
}

resource "aws_lambda_permission" "generate_security_questions" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.generate_security_questions.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${data.aws_api_gateway_rest_api.existing.execution_arn}/*/*"
}

# GET /projects/{id}/security-questions
resource "aws_api_gateway_method" "get_security_questions" {
  rest_api_id   = data.aws_api_gateway_rest_api.existing.id
  resource_id   = aws_api_gateway_resource.security_questions.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "get_security_questions" {
  rest_api_id = data.aws_api_gateway_rest_api.existing.id
  resource_id = aws_api_gateway_resource.security_questions.id
  http_method = aws_api_gateway_method.get_security_questions.http_method
  
  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.get_security_questions.invoke_arn
}

resource "aws_lambda_permission" "get_security_questions" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_security_questions.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${data.aws_api_gateway_rest_api.existing.execution_arn}/*/*"
}

# Security Assessment Resource
resource "aws_api_gateway_resource" "security_assessment" {
  rest_api_id = data.aws_api_gateway_rest_api.existing.id
  parent_id   = aws_api_gateway_resource.projects_id.id
  path_part   = "security-assessment"
}

# POST /projects/{id}/security-assessment
resource "aws_api_gateway_method" "perform_security_assessment" {
  rest_api_id   = data.aws_api_gateway_rest_api.existing.id
  resource_id   = aws_api_gateway_resource.security_assessment.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "perform_security_assessment" {
  rest_api_id = data.aws_api_gateway_rest_api.existing.id
  resource_id = aws_api_gateway_resource.security_assessment.id
  http_method = aws_api_gateway_method.perform_security_assessment.http_method
  
  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.perform_security_assessment.invoke_arn
}

resource "aws_lambda_permission" "perform_security_assessment" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.perform_security_assessment.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${data.aws_api_gateway_rest_api.existing.execution_arn}/*/*"
}

# GET /projects/{id}/security-assessment
resource "aws_api_gateway_method" "get_security_assessment" {
  rest_api_id   = data.aws_api_gateway_rest_api.existing.id
  resource_id   = aws_api_gateway_resource.security_assessment.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "get_security_assessment" {
  rest_api_id = data.aws_api_gateway_rest_api.existing.id
  resource_id = aws_api_gateway_resource.security_assessment.id
  http_method = aws_api_gateway_method.get_security_assessment.http_method
  
  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.get_security_assessments.invoke_arn
}

resource "aws_lambda_permission" "get_security_assessment" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_security_assessments.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${data.aws_api_gateway_rest_api.existing.execution_arn}/*/*"
}

# Deploy API Gateway
resource "aws_api_gateway_deployment" "security_assessment" {
  depends_on = [
    aws_api_gateway_integration.generate_security_questions,
    aws_api_gateway_integration.get_security_questions,
    aws_api_gateway_integration.perform_security_assessment,
    aws_api_gateway_integration.get_security_assessment,
  ]

  rest_api_id = data.aws_api_gateway_rest_api.existing.id

  lifecycle {
    create_before_destroy = true
  }
}

