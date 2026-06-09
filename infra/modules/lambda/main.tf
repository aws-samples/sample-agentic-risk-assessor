locals {
  # All Lambda function configurations
  lambda_configs = {
    admin_add_service = { handler = "admin_add_service.lambda_handler", runtime = "python3.13", timeout = 30, memory_size = 256, env_vars = {} }
    admin_execution_status = { handler = "admin_execution_status.lambda_handler", runtime = "python3.13", timeout = 30, memory_size = 256, env_vars = {} }
    admin_run_mapping = { handler = "admin_run_mapping.lambda_handler", runtime = "python3.13", timeout = 300, memory_size = 512, env_vars = { STEP_FUNCTIONS_ARN = var.service_controls_step_function_arn } }
    admin_run_service_mapping = { handler = "admin_run_service_mapping.lambda_handler", runtime = "python3.13", timeout = 300, memory_size = 512, env_vars = { SERVICE_CONTROLS_STEP_FUNCTION_ARN = var.service_controls_step_function_arn } }
    admin_services = { handler = "admin_services.lambda_handler", runtime = "python3.13", timeout = 30, memory_size = 256, env_vars = {} }

    assessment_content = { handler = "assessment_content.lambda_handler", runtime = "python3.13", timeout = 30, memory_size = 256, env_vars = {} }
    assessment_downloader = { handler = "assessment_downloader.lambda_handler", runtime = "python3.13", timeout = 300, memory_size = 512, env_vars = {} }
    assessment_retriever = { handler = "assessment_retriever.lambda_handler", runtime = "python3.13", timeout = 30, memory_size = 256, env_vars = {} }
    assessment_saver = { handler = "assessment_saver.lambda_handler", runtime = "python3.13", timeout = 30, memory_size = 256, env_vars = {} }
    
    # NEW: Enhanced discovery Lambda functions
    discover_framework_controls = { handler = "discover_framework_controls.lambda_handler", runtime = "python3.13", timeout = 600, memory_size = 512, env_vars = { KNOWLEDGE_BASE_ID = var.knowledge_base_id, BEDROCK_MODEL_ID = var.bedrock_model_id } }
    discover_service_capabilities = { handler = "discover_service_capabilities.lambda_handler", runtime = "python3.11", timeout = 600, memory_size = 512, env_vars = { MCP_ENDPOINT = var.mcp_endpoint, BEDROCK_MODEL_ID = var.bedrock_model_id } }
    combine_controls_capabilities = { handler = "combine_controls_capabilities.lambda_handler", runtime = "python3.13", timeout = 60, memory_size = 256, env_vars = {} }
    retrieve_framework_s3_data = { handler = "retrieve_framework_s3_data.lambda_handler", runtime = "python3.13", timeout = 60, memory_size = 256, env_vars = {} }
    resolve_control_details = { handler = "resolve_control_details.lambda_handler", runtime = "python3.13", timeout = 120, memory_size = 256, env_vars = { KNOWLEDGE_BASE_ID = var.knowledge_base_id, BEDROCK_MODEL_ID = var.bedrock_model_id } }
    generate_control_reference = { handler = "generate_control_reference.lambda_handler", runtime = "python3.13", timeout = 120, memory_size = 512, env_vars = { APP_DATA_BUCKET = lookup(var.s3_bucket_names, "app_data", ""), SERVICE_CONTROLS_TABLE = var.service_controls_table } }
    serve_control_reference = { handler = "serve_control_reference.lambda_handler", runtime = "python3.13", timeout = 30, memory_size = 256, env_vars = { APP_DATA_BUCKET = lookup(var.s3_bucket_names, "app_data", "") } }

    
    check_batch_completion = { handler = "check_batch_completion.lambda_handler", runtime = "python3.13", timeout = 30, memory_size = 256, env_vars = {} }
    check_bedrock_jobs = { handler = "check_bedrock_jobs.lambda_handler", runtime = "python3.13", timeout = 30, memory_size = 256, env_vars = {} }
    diagram_analysis = {
      handler = "diagram_analysis.lambda_handler",
      runtime = "python3.13", 
      timeout = 300, 
      memory_size = 1024, 
      env_vars = { 
        BEDROCK_ACCOUNT_ID = var.bedrock_account_id,  # Only use if Bedrock is in a different account
        BEDROCK_MODEL_ID = var.bedrock_model_id, 
        BEDROCK_ROLE_NAME = var.bedrock_role_name     # Only use if Bedrock is in a different account
        },
      layers = ["powertools", "inspector"]
    }
    document_manager = { handler = "document_manager.lambda_handler", runtime = "python3.13", timeout = 300, memory_size = 512, env_vars = {} }
    get_batch_services = { handler = "get_batch_services.lambda_handler", runtime = "python3.13", timeout = 30, memory_size = 256, env_vars = {} }
    get_diagram_url = { handler = "get_diagram_url.lambda_handler", runtime = "python3.13", timeout = 30, memory_size = 256, env_vars = {} }
    get_node_controls = { handler = "get_node_controls.lambda_handler", runtime = "python3.13", timeout = 30, memory_size = 256, env_vars = {} }
    get_node_details = { handler = "get_node_details.lambda_handler", runtime = "python3.13", timeout = 30, memory_size = 256, env_vars = {} }
    get_sessions = { handler = "get_sessions.lambda_handler", runtime = "python3.13", timeout = 30, memory_size = 256, env_vars = {} }
    delete_session = { handler = "delete_session.lambda_handler", runtime = "python3.13", timeout = 30, memory_size = 256, env_vars = {} }
    create_session = { handler = "create_session.lambda_handler", runtime = "python3.13", timeout = 30, memory_size = 256, env_vars = {} }
    get_agent_capabilities = { handler = "get_agent_capabilities.lambda_handler", runtime = "python3.13", timeout = 30, memory_size = 256, env_vars = { AGENT_BASE_URL = var.agent_base_url } }

    health = { handler = "health.handler", runtime = "python3.13", timeout = 30, memory_size = 256, env_vars = {} }
    images = { handler = "images.handler", runtime = "python3.13", timeout = 30, memory_size = 256, env_vars = {} }

    invoke_bedrock = { handler = "invoke_bedrock.lambda_handler", runtime = "python3.13", timeout = 300, memory_size = 512, env_vars = { BEDROCK_ACCOUNT_ID = var.bedrock_account_id, BEDROCK_MODEL_ID = var.bedrock_model_id, BEDROCK_ROLE_NAME = var.bedrock_role_name, BEDROCK_MAX_TOKENS = var.bedrock_max_tokens } }
    
    # NEW: RAG integration Lambda function with Instructor support
    invoke_bedrock_rag = { 
      handler = "invoke_bedrock_rag.lambda_handler", 
      runtime = "python3.13", 
      timeout = 300, 
      memory_size = 512, 
      env_vars = { 
        KNOWLEDGE_BASE_ID = var.knowledge_base_id, 
        BEDROCK_MODEL_ID = var.bedrock_model_id, 
        BEDROCK_ACCOUNT_ID = var.bedrock_account_id, 
        BEDROCK_ROLE_NAME = var.bedrock_role_name 
      },
      layers = ["powertools", "inspector"]
    }
    
    manage_services = { handler = "manage_services.lambda_handler", runtime = "python3.13", timeout = 30, memory_size = 256, env_vars = {} }
    map_controls = { handler = "map_controls.lambda_handler", runtime = "python3.13", timeout = 300, memory_size = 512, env_vars = {} }
    perform_security_assessment = { handler = "perform_security_assessment.lambda_handler", runtime = "python3.13", timeout = 900, memory_size = 1024, env_vars = { BEDROCK_MODEL_ID = var.bedrock_model_id } }
    process_bedrock_results = { handler = "process_bedrock_results.lambda_handler", runtime = "python3.13", timeout = 300, memory_size = 512, env_vars = {} }
    process_node_controls = { handler = "process_node_controls.lambda_handler", runtime = "python3.13", timeout = 300, memory_size = 512, env_vars = {} }
    process_results = { handler = "process_results.lambda_handler", runtime = "python3.13", timeout = 300, memory_size = 512, env_vars = {} }
    process_s3_files = { handler = "process_s3_files.lambda_handler", runtime = "python3.13", timeout = 300, memory_size = 512, env_vars = {} }
    
    # NEW: Process individual controls with dynamic branching
    process_single_control = { handler = "process_single_control.lambda_handler", runtime = "python3.13", timeout = 300, memory_size = 512, env_vars = { SERVICE_CONTROLS_TABLE = var.service_controls_table, BEDROCK_ACCOUNT_ID = var.bedrock_account_id, BEDROCK_MODEL_ID = var.bedrock_model_id, BEDROCK_ROLE_NAME = var.bedrock_role_name } }
    
    # NEW: Mark service as complete after all controls processed
    mark_service_complete = { handler = "mark_service_complete.lambda_handler", runtime = "python3.13", timeout = 60, memory_size = 256, env_vars = { SERVICE_CONTROLS_TABLE = var.service_controls_table } }
    
    process_word_document = { handler = "process_word_document.lambda_handler", runtime = "python3.13", timeout = 300, memory_size = 512, env_vars = {}, layers = ["pandoc"] }
    projects = { handler = "projects.handler", runtime = "python3.13", timeout = 30, memory_size = 256, env_vars = {} }
    read_services = { handler = "read_services.lambda_handler", runtime = "python3.13", timeout = 30, memory_size = 256, env_vars = {} }
    restart_system = { handler = "restart_system.lambda_handler", runtime = "python3.13", timeout = 60, memory_size = 256, env_vars = {} }
    service_token_manager = { handler = "service_token_manager.lambda_handler", runtime = "python3.13", timeout = 30, memory_size = 256, env_vars = {} }
    update_flow = { handler = "update_flow.lambda_handler", runtime = "python3.13", timeout = 30, memory_size = 256, env_vars = {} }
    update_node = { handler = "update_node.lambda_handler", runtime = "python3.13", timeout = 30, memory_size = 256, env_vars = {} }
    upload_image = { handler = "upload_image.handler", runtime = "python3.13", timeout = 300, memory_size = 512, env_vars = {} }
    
    # Organization Profile Lambda functions
    create_profile = { handler = "create_profile.lambda_handler", runtime = "python3.13", timeout = 30, memory_size = 256, env_vars = {} }
    update_profile = { handler = "update_profile.lambda_handler", runtime = "python3.13", timeout = 30, memory_size = 256, env_vars = {} }
    get_profile = { handler = "get_profile.lambda_handler", runtime = "python3.13", timeout = 30, memory_size = 256, env_vars = {} }
    list_profiles = { handler = "list_profiles.lambda_handler", runtime = "python3.13", timeout = 30, memory_size = 256, env_vars = {} }
    delete_profile = { handler = "delete_profile.lambda_handler", runtime = "python3.13", timeout = 30, memory_size = 256, env_vars = {} }
    search_context = { handler = "search_context.lambda_handler", runtime = "python3.13", timeout = 60, memory_size = 512, env_vars = { MCP_SEARCH_ENDPOINT = var.mcp_search_endpoint, MCP_API_KEY = var.mcp_api_key, SEARCH_CACHE_TABLE = var.search_cache_table, MAX_SEARCH_RESULTS = var.max_search_results, CACHE_TTL_HOURS = var.cache_ttl_hours } }
  }
}

# checkov:skip=CKV_AWS_116: Lambda DLQ not required for demo application - errors logged to CloudWatch
# checkov:skip=CKV_AWS_117: Lambda VPC not required - functions access public AWS services only (DynamoDB, S3, Bedrock)
# checkov:skip=CKV_AWS_272: Lambda code signing not required for internal demo application
# A full deployment should enable: DLQ for error tracking, VPC for network isolation, code signing for integrity
# nosemgrep: terraform.aws.security.aws-lambda-x-ray-tracing-not-active.aws-lambda-x-ray-tracing-not-active
resource "aws_lambda_function" "this" {
  for_each = local.lambda_configs

  function_name                  = "${var.project_name}-${each.key}"
  handler                        = each.value.handler
  runtime                        = each.value.runtime
  role                           = var.lambda_role_arn
  filename                       = "${var.lambda_package_path}${replace(each.key, "-", "_")}.zip"
  timeout                        = each.value.timeout
  memory_size                    = each.value.memory_size
  reserved_concurrent_executions = lookup(each.value, "concurrency_limit", 10)  # Default limit of 10 concurrent executions
  
  # Add layers if specified
  layers = lookup(each.value, "layers", null) != null ? [
    for layer in each.value.layers : 
    layer == "pandoc" ? var.pandoc_layer_arn : 
    layer == "powertools" ? var.powertools_layer_arn : 
    layer == "inspector" ? var.inspector_layer_arn : layer
  ] : null

  environment {
    variables = merge(
      var.common_env_vars,
      each.value.env_vars,
      {
        PROJECTS_TABLE = lookup(var.dynamodb_table_names, "projects", "")
        NODE_CONTROLS_TABLE = lookup(var.dynamodb_table_names, "node_controls", "")
        SERVICES_TABLE = lookup(var.dynamodb_table_names, "services", "")
        SERVICE_CONTROLS_TABLE = lookup(var.dynamodb_table_names, "service_controls", "")
        DIAGRAM_ANALYSIS_TABLE = lookup(var.dynamodb_table_names, "diagram_analysis", "")
        SESSIONS_TABLE = lookup(var.dynamodb_table_names, "sessions", "")
        SEARCH_CACHE_TABLE = lookup(var.dynamodb_table_names, "search_cache", "")



        IMAGES_BUCKET = lookup(var.s3_bucket_names, "project_images", "")
        DIAGRAMS_BUCKET = lookup(var.s3_bucket_names, "project_images", "")
        DOCUMENTS_BUCKET = lookup(var.s3_bucket_names, "project_documents", "")
        APP_DATA_BUCKET = lookup(var.s3_bucket_names, "app_data", "")
        PROMPTS_BUCKET = lookup(var.s3_bucket_names, "app_data", "")
        TEMP_DATA_BUCKET = lookup(var.s3_bucket_names, "temp_data", "")
        SERVICE_CONTROLS_STEP_FUNCTION_ARN = var.service_controls_step_function_arn != null ? var.service_controls_step_function_arn : ""
        
        # MCP Search Integration
        SEARCH_RESULTS_BUCKET = lookup(var.s3_bucket_names, "app_data", "")
        
        # RAG-specific configuration for discover_framework_controls
        RAG_BEDROCK_MODEL_ID = var.rag_bedrock_model_id
        RAG_BEDROCK_TEMPERATURE = tostring(var.rag_bedrock_temperature)
        RAG_BEDROCK_TOP_P = tostring(var.rag_bedrock_top_p)
        RAG_BEDROCK_TOP_K = tostring(var.rag_bedrock_top_k)

      }
    )
  }

  kms_key_arn = var.lambda_kms_key_arn

  tags = var.tags

  depends_on = [aws_cloudwatch_log_group.lambda_logs]
}

resource "aws_cloudwatch_log_group" "lambda_logs" {
  for_each = local.lambda_configs

  name              = "/aws/lambda/${var.project_name}-${each.key}"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.cloudwatch_kms_key_arn

  tags = var.tags
}

# Lambda permissions for API Gateway
resource "aws_lambda_permission" "api_gateway" {
  for_each = local.lambda_configs

  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.this[each.key].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*"
}