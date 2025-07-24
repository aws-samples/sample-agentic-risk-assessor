data "aws_region" "current" {}

resource "aws_apigatewayv2_api" "this" {
  name          = "${var.project_name}-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = var.cors_origins
    allow_methods = var.cors_methods
    allow_headers = var.cors_headers
  }

  tags = var.tags
}

resource "aws_apigatewayv2_stage" "this" {
  api_id      = aws_apigatewayv2_api.this.id
  name        = var.stage_name
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_logs.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
    })
  }

  default_route_settings {
    detailed_metrics_enabled = true
    logging_level            = "OFF"
    data_trace_enabled       = false
    throttling_burst_limit   = var.throttling_burst_limit
    throttling_rate_limit    = var.throttling_rate_limit
  }

  tags = var.tags
}

# checkov:skip=CKV_AWS_158: Encryption with AWS-managed key is acceptable for demo environment
resource "aws_cloudwatch_log_group" "api_logs" {
  name              = "/aws/apigateway/${var.project_name}-api"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

# JWT Authorizer for Cognito
resource "aws_apigatewayv2_authorizer" "jwt" {
  api_id           = aws_apigatewayv2_api.this.id
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  name             = "${var.project_name}-jwt-authorizer"

  jwt_configuration {
    audience = [var.cognito_client_id]
    issuer   = "https://cognito-idp.${data.aws_region.current.name}.amazonaws.com/${var.cognito_user_pool_id}"
  }
}

# Lambda integrations
resource "aws_apigatewayv2_integration" "lambda" {
  for_each = var.lambda_integrations

  api_id                 = aws_apigatewayv2_api.this.id
  integration_type       = "AWS_PROXY"
  integration_uri        = each.value.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

# All API Routes from backup configuration
locals {
  api_routes = {
    # Health routes
    "health_get"     = { route_key = "GET /api/health", integration_key = "health", auth_required = false }
    "health_options" = { route_key = "OPTIONS /api/health", integration_key = "health", auth_required = false }

    # Projects routes
    "projects_get_all"    = { route_key = "GET /api/projects", integration_key = "projects", auth_required = true }
    "projects_get_one"    = { route_key = "GET /api/projects/{id}", integration_key = "projects", auth_required = true }
    "projects_post"       = { route_key = "POST /api/projects", integration_key = "projects", auth_required = true }
    "projects_put"        = { route_key = "PUT /api/projects/{id}", integration_key = "projects", auth_required = true }
    "projects_options"    = { route_key = "OPTIONS /api/projects", integration_key = "projects", auth_required = false }
    "projects_options_id" = { route_key = "OPTIONS /api/projects/{id}", integration_key = "projects", auth_required = false }

    # Images routes
    "images_get"     = { route_key = "GET /api/images/{filename}", integration_key = "images", auth_required = false }
    "images_options" = { route_key = "OPTIONS /api/images/{filename}", integration_key = "images", auth_required = false }

    # Document routes
    "document_post"            = { route_key = "POST /api/document", integration_key = "document_manager", auth_required = true }
    "document_options"         = { route_key = "OPTIONS /api/document", integration_key = "document_manager", auth_required = false }
    "document_word_post"       = { route_key = "POST /api/document/word", integration_key = "process_word_document", auth_required = true }
    "document_word_options"    = { route_key = "OPTIONS /api/document/word", integration_key = "process_word_document", auth_required = false }
    "project_document_get"     = { route_key = "GET /api/projects/{id}/document", integration_key = "document_manager", auth_required = true }
    "project_document_options" = { route_key = "OPTIONS /api/projects/{id}/document", integration_key = "document_manager", auth_required = false }
    "document_content_get"     = { route_key = "GET /api/projects/{id}/document/content", integration_key = "document_manager", auth_required = true }
    "document_content_options" = { route_key = "OPTIONS /api/projects/{id}/document/content", integration_key = "document_manager", auth_required = false }

    # Diagram Analysis routes
    "diagram_analysis_get"     = { route_key = "GET /api/projects/{id}/diagram-analysis", integration_key = "diagram_analysis", auth_required = true }
    "diagram_analysis_post"    = { route_key = "POST /api/projects/{id}/diagram-analysis", integration_key = "diagram_analysis", auth_required = true }
    "diagram_analysis_put"     = { route_key = "PUT /api/projects/{id}/diagram-analysis", integration_key = "diagram_analysis", auth_required = true }
    "diagram_analysis_options" = { route_key = "OPTIONS /api/projects/{id}/diagram-analysis", integration_key = "diagram_analysis", auth_required = false }

    # Diagram URL routes
    "diagram_url_get"     = { route_key = "GET /api/projects/{id}/diagram-url", integration_key = "get_diagram_url", auth_required = true }
    "diagram_url_options" = { route_key = "OPTIONS /api/projects/{id}/diagram-url", integration_key = "get_diagram_url", auth_required = false }

    # Node Controls routes
    "node_controls_get"     = { route_key = "GET /api/projects/{id}/node-controls", integration_key = "get_node_controls", auth_required = true }
    "node_controls_options" = { route_key = "OPTIONS /api/projects/{id}/node-controls", integration_key = "get_node_controls", auth_required = false }

    # Node Details routes
    "node_details_get"     = { route_key = "GET /api/projects/{id}/nodes/{nodeId}", integration_key = "get_node_details", auth_required = true }
    "node_details_options" = { route_key = "OPTIONS /api/projects/{id}/nodes/{nodeId}", integration_key = "get_node_details", auth_required = false }

    # Map Controls routes
    "map_controls_post"    = { route_key = "POST /api/map-controls", integration_key = "map_controls", auth_required = true }
    "map_controls_options" = { route_key = "OPTIONS /api/map-controls", integration_key = "map_controls", auth_required = false }

    # Risk Assessment routes
    "risk_assessments_get"            = { route_key = "GET /api/projects/{id}/risk-assessments", integration_key = "assessment_retriever", auth_required = true }
    "risk_assessments_post"           = { route_key = "POST /api/projects/{id}/risk-assessments", integration_key = "assessment_saver", auth_required = true }
    "risk_assessments_options"        = { route_key = "OPTIONS /api/projects/{id}/risk-assessments", integration_key = "assessment_retriever", auth_required = false }
    "risk_assessment_get"             = { route_key = "GET /api/projects/{id}/risk-assessments/{assessment_id}", integration_key = "assessment_downloader", auth_required = true }
    "risk_assessment_options"         = { route_key = "OPTIONS /api/projects/{id}/risk-assessments/{assessment_id}", integration_key = "assessment_downloader", auth_required = false }
    "risk_assessment_content_get"     = { route_key = "GET /api/projects/{id}/risk-assessments/{assessment_id}/content", integration_key = "assessment_content", auth_required = true }
    "risk_assessment_content_options" = { route_key = "OPTIONS /api/projects/{id}/risk-assessments/{assessment_id}/content", integration_key = "assessment_content", auth_required = false }

    # Security Assessment routes
    "security_assessments_get"            = { route_key = "GET /api/projects/{id}/security-assessments", integration_key = "assessment_retriever", auth_required = true }
    "security_assessments_post"           = { route_key = "POST /api/projects/{id}/security-assessments", integration_key = "assessment_saver", auth_required = true }
    "security_assessments_options"        = { route_key = "OPTIONS /api/projects/{id}/security-assessments", integration_key = "assessment_retriever", auth_required = false }
    "security_assessment_content_get"     = { route_key = "GET /api/projects/{id}/security-assessments/{assessment_id}/content", integration_key = "assessment_content", auth_required = true }
    "security_assessment_content_options" = { route_key = "OPTIONS /api/projects/{id}/security-assessments/{assessment_id}/content", integration_key = "assessment_content", auth_required = false }

    # Architecture Review routes
    "architecture_reviews_get"            = { route_key = "GET /api/projects/{id}/architecture-reviews", integration_key = "assessment_retriever", auth_required = true }
    "architecture_reviews_options"        = { route_key = "OPTIONS /api/projects/{id}/architecture-reviews", integration_key = "assessment_retriever", auth_required = false }
    "architecture_review_content_get"     = { route_key = "GET /api/projects/{id}/architecture-reviews/{review_id}/content", integration_key = "assessment_content", auth_required = true }
    "architecture_review_content_options" = { route_key = "OPTIONS /api/projects/{id}/architecture-reviews/{review_id}/content", integration_key = "assessment_content", auth_required = false }

    # System restart routes
    "restart_system_post"    = { route_key = "POST /restart-system", integration_key = "restart_system", auth_required = true }
    "restart_system_options" = { route_key = "OPTIONS /restart-system", integration_key = "restart_system", auth_required = false }

    # Sessions routes
    "sessions_get"            = { route_key = "GET /api/sessions", integration_key = "get_sessions", auth_required = true }
    "sessions_options"        = { route_key = "OPTIONS /api/sessions", integration_key = "get_sessions", auth_required = false }
    "sessions_create"         = { route_key = "POST /api/sessions/create", integration_key = "create_session", auth_required = true }
    "sessions_create_options" = { route_key = "OPTIONS /api/sessions/create", integration_key = "create_session", auth_required = false }
    "sessions_delete"         = { route_key = "DELETE /api/sessions/{session_id}", integration_key = "delete_session", auth_required = true }
    "sessions_delete_options" = { route_key = "OPTIONS /api/sessions/{session_id}", integration_key = "delete_session", auth_required = false }

    # Agent Capabilities routes
    "agent_capabilities_get"     = { route_key = "GET /api/agent-capabilities", integration_key = "get_agent_capabilities", auth_required = false }
    "agent_capabilities_options" = { route_key = "OPTIONS /api/agent-capabilities", integration_key = "get_agent_capabilities", auth_required = false }

    # Control Reference routes
    "control_reference_get"     = { route_key = "GET /api/reference/{framework}/{service}", integration_key = "serve_control_reference", auth_required = true }
    "control_reference_options" = { route_key = "OPTIONS /api/reference/{framework}/{service}", integration_key = "serve_control_reference", auth_required = false }

    # Admin routes
    "admin_services_get"                = { route_key = "GET /admin/services", integration_key = "admin_services", auth_required = true }
    "admin_services_post"               = { route_key = "POST /admin/services", integration_key = "admin_add_service", auth_required = true }
    "admin_services_options"            = { route_key = "OPTIONS /admin/services", integration_key = "admin_services", auth_required = false }
    "admin_run_mapping_post"            = { route_key = "POST /admin/run-mapping", integration_key = "admin_run_mapping", auth_required = true }
    "admin_run_mapping_options"         = { route_key = "OPTIONS /admin/run-mapping", integration_key = "admin_run_mapping", auth_required = false }
    "admin_run_service_mapping_post"    = { route_key = "POST /admin/run-service-mapping", integration_key = "admin_run_service_mapping", auth_required = true }
    "admin_run_service_mapping_options" = { route_key = "OPTIONS /admin/run-service-mapping", integration_key = "admin_run_service_mapping", auth_required = false }
    "admin_execution_status_get"        = { route_key = "GET /admin/execution-status/{executionArn+}", integration_key = "admin_execution_status", auth_required = true }
    "admin_execution_status_options"    = { route_key = "OPTIONS /admin/execution-status/{executionArn+}", integration_key = "admin_execution_status", auth_required = false }

    # Organization Profile routes
    "profiles_get"           = { route_key = "GET /api/profiles", integration_key = "list_profiles", auth_required = true }
    "profiles_post"          = { route_key = "POST /api/profiles", integration_key = "create_profile", auth_required = true }
    "profiles_options"       = { route_key = "OPTIONS /api/profiles", integration_key = "list_profiles", auth_required = false }
    "profile_get"            = { route_key = "GET /api/profiles/{id}", integration_key = "get_profile", auth_required = true }
    "profile_put"            = { route_key = "PUT /api/profiles/{id}", integration_key = "update_profile", auth_required = true }
    "profile_delete"         = { route_key = "DELETE /api/profiles/{id}", integration_key = "delete_profile", auth_required = true }
    "profile_options"        = { route_key = "OPTIONS /api/profiles/{id}", integration_key = "get_profile", auth_required = false }
    "search_context_post"    = { route_key = "POST /api/search-context", integration_key = "search_context", auth_required = true }
    "search_context_options" = { route_key = "OPTIONS /api/search-context", integration_key = "search_context", auth_required = false }

  }
}

# Routes
#checkov:skip=CKV_AWS_309:Authorization type is configured based on auth_required flag
resource "aws_apigatewayv2_route" "lambda_routes" {
  for_each = local.api_routes

  api_id    = aws_apigatewayv2_api.this.id
  route_key = each.value.route_key
  target    = "integrations/${aws_apigatewayv2_integration.lambda[each.value.integration_key].id}"

  authorization_type = each.value.auth_required ? "JWT" : "NONE"
  authorizer_id      = each.value.auth_required ? aws_apigatewayv2_authorizer.jwt.id : null
}

# VPC Link for ALB integration
resource "aws_apigatewayv2_vpc_link" "this" {
  count = var.vpc_link_config != null ? 1 : 0

  name               = "${var.project_name}-vpc-link"
  security_group_ids = var.vpc_link_config.security_group_ids
  subnet_ids         = var.vpc_link_config.subnet_ids

  tags = var.tags
}

# ALB integration
resource "aws_apigatewayv2_integration" "alb" {
  count = var.alb_integration != null ? 1 : 0

  api_id             = aws_apigatewayv2_api.this.id
  integration_type   = "HTTP_PROXY"
  integration_uri    = var.alb_integration.listener_arn
  integration_method = "ANY"
  connection_type    = "VPC_LINK"
  connection_id      = aws_apigatewayv2_vpc_link.this[0].id
}

# ALB routes
resource "aws_apigatewayv2_route" "alb_routes" {
  for_each = var.alb_routes

  api_id    = aws_apigatewayv2_api.this.id
  route_key = each.value.route_key
  target    = "integrations/${aws_apigatewayv2_integration.alb[0].id}"

  authorization_type = lookup(each.value, "auth_required", true) ? "JWT" : "NONE"
  authorizer_id      = lookup(each.value, "auth_required", true) ? aws_apigatewayv2_authorizer.jwt.id : null
}