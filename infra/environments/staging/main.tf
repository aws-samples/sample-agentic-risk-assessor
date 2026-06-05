terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.9"
    }
    opensearch = {
      source  = "opensearch-project/opensearch"
      version = "= 2.2.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }

  backend "s3" {
    # Configuration provided via backend.hcl
  }
}

provider "aws" {
  region  = var.region
  profile = var.aws_profile

  allowed_account_ids = [var.aws_account_id]

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

provider "opensearch" {
  url         = module.bedrock_knowledge_base.opensearch_collection_endpoint
  healthcheck = false
  aws_region  = var.region
  aws_assume_role_arn = ""
  sign_aws_requests   = true
}

data "aws_caller_identity" "current" {}

# KMS Keys for Encryption
module "kms" {
  source = "../../modules/kms"

  project_name = var.project_name
  environment  = var.environment

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Random password for CloudFront secret header
resource "random_password" "cloudfront_secret" {
  length  = 32
  special = true
}

# Secrets Management
module "secrets" {
  source = "../../modules/secrets"

  project_name = var.project_name
  environment  = var.environment

  kms_key_id          = module.kms.lambda_key_id

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Bedrock Knowledge Base for Security Framework Mapping
module "bedrock_knowledge_base" {
  source = "../../modules/bedrock-knowledge-base"

  project_name             = var.project_name
  aws_region               = var.region
  bedrock_model_id         = var.bedrock_model_id
  bedrock_parsing_model_id = var.bedrock_parsing_model_id
  s3_kms_key_arn           = module.kms.s3_key_arn
  vpc_id                   = module.networking.vpc_id
  private_subnet_ids       = module.networking.private_subnet_ids
  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Create aws-core layer
resource "aws_lambda_layer_version" "aws_core" {
  layer_name          = "${var.project_name}-aws-core-layer"
  filename            = "../../../temp/lambda_packages/aws_core_layer.zip"
  compatible_runtimes = ["python3.9", "python3.11", "python3.12", "python3.13"]
  description         = "AWS core layer with boto3 and python-dateutil"
}

# Create pandoc layer
resource "aws_lambda_layer_version" "pandoc" {
  layer_name          = "${var.project_name}-pandoc-layer"
  filename            = "../../../temp/lambda_packages/pandoc_layer.zip"
  compatible_runtimes = ["python3.9", "python3.11", "python3.12", "python3.13"]
}

# Create inspector layer
resource "aws_lambda_layer_version" "inspector" {
  layer_name          = "${var.project_name}-inspector-layer"
  filename            = "../../../lambda/layers/inspector_layer.zip"
  compatible_runtimes = ["python3.11", "python3.12", "python3.13"]
  description         = "inspector layer for model structure output"
}

# S3 Module
module "s3" {
  source = "../../modules/s3"

  project_name   = var.project_name
  environment    = var.environment
  s3_kms_key_arn = module.kms.s3_key_arn

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# DynamoDB Module
module "dynamodb" {
  source = "../../modules/dynamodb"

  project_name         = var.project_name
  environment          = var.environment
  dynamodb_kms_key_arn = module.kms.dynamodb_key_arn

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# IAM Module
module "iam" {
  source = "../../modules/iam"

  project_name   = var.project_name
  environment    = var.environment
  region         = var.region
  account_id     = data.aws_caller_identity.current.account_id
  aws_region     = var.region
  aws_account_id = data.aws_caller_identity.current.account_id

  dynamodb_table_arns    = values(module.dynamodb.table_arns)
  dynamodb_kms_key_arn   = module.kms.dynamodb_key_arn
  s3_bucket_arns         = values(module.s3.bucket_arns)
  s3_kms_key_arn         = module.kms.s3_key_arn
  voice_audio_bucket_arn = module.voice_services.voice_audio_bucket_arn
  bedrock_role_arn       = var.bedrock_role_arn

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Step Functions Module
module "step_functions" {
  source = "../../modules/step-functions"

  project_name            = var.project_name
  step_functions_role_arn = module.iam.step_functions_role_arn

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Lambda Module
module "lambda" {
  source = "../../modules/lambda"

  project_name = var.project_name
  environment  = var.environment

  lambda_role_arn                    = module.iam.lambda_exec_role_arn
  lambda_package_path                = "../../../temp/lambda_packages/"
  api_gateway_execution_arn          = "arn:aws:execute-api:${var.region}:${data.aws_caller_identity.current.account_id}:*"
  pandoc_layer_arn                   = aws_lambda_layer_version.pandoc.arn
  region                             = var.region
  powertools_layer_arn               = "arn:aws:lambda:${var.region}:017000801446:layer:AWSLambdaPowertoolsPythonV3-python313-x86_64:18"
  inspector_layer_arn                = aws_lambda_layer_version.inspector.arn
  service_controls_step_function_arn = module.step_functions.state_machine_arn
  cloudwatch_kms_key_arn             = module.kms.cloudwatch_key_arn
  lambda_kms_key_arn                 = module.kms.lambda_key_arn

  # RAG-specific configuration
  rag_bedrock_model_id    = var.rag_bedrock_model_id
  rag_bedrock_temperature = var.rag_bedrock_temperature
  rag_bedrock_top_p       = var.rag_bedrock_top_p
  rag_bedrock_top_k       = var.rag_bedrock_top_k


  dynamodb_table_names = module.dynamodb.table_names
  s3_bucket_names      = module.s3.bucket_ids

  bedrock_account_id       = var.bedrock_account_id
  bedrock_model_id         = var.bedrock_model_id
  bedrock_parsing_model_id = var.bedrock_parsing_model_id
  bedrock_role_name        = var.bedrock_role_name
  bedrock_max_tokens       = var.bedrock_max_tokens
  agent_base_url           = "http://${module.networking.agents_alb_dns_name}"

  # NEW: Enhanced discovery variables
  knowledge_base_id      = module.bedrock_knowledge_base.knowledge_base_id
  rag_model_id           = var.rag_model_id
  mcp_endpoint           = "https://docs.aws.amazon.com"
  service_controls_table = module.dynamodb.table_names["service_controls"]

  # MCP Search Integration
  mcp_search_endpoint = var.mcp_search_endpoint
  mcp_api_key         = var.mcp_api_key
  search_cache_table  = module.dynamodb.table_names["search_cache"]
  max_search_results  = var.max_search_results
  cache_ttl_hours     = var.cache_ttl_hours

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Networking Module
module "networking" {
  source = "../../modules/networking"

  project_name = var.project_name
  environment  = var.environment

  cloudfront_custom_header_name  = "x-custom-cloudfront-secret"
  cloudfront_custom_header_value = random_password.cloudfront_secret.result

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# API Gateway Module
module "api_gateway" {
  source = "../../modules/api-gateway"

  project_name = var.project_name
  environment  = var.environment
  stage_name   = "prod"

  lambda_integrations = {
    for name, func in module.lambda.lambda_functions : name => {
      invoke_arn = func.invoke_arn
    }
  }

  cognito_user_pool_id = module.cognito.user_pool_id
  cognito_client_id    = module.cognito.user_pool_client_id

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Voice Services Module
module "voice_services" {
  source = "../../modules/voice-services"

  project_name   = var.project_name
  environment    = var.environment
  aws_region     = var.region
  aws_account_id = data.aws_caller_identity.current.account_id

  log_retention_days           = 14
  audio_storage_lifecycle_days = 7
  s3_kms_key_arn               = module.kms.s3_key_arn

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ECS Module (Agents)
module "ecs" {
  source = "../../modules/ecs"

  project_name = var.project_name
  environment  = var.environment

  execution_role_arn   = module.iam.ecs_task_execution_role_arn
  task_role_arn        = module.iam.ecs_task_role_arn
  agent_task_role_arns = module.iam.agent_task_role_arns

  subnet_ids         = module.networking.private_subnet_ids
  security_group_ids = [module.networking.security_group_ids["agents"]]

  target_group_arns          = module.networking.agents_target_group_arns
  external_target_group_arns = module.networking.agents_external_target_group_arns
  cognito_user_pool_id       = module.cognito.user_pool_id
  cognito_domain_name    = module.cognito.domain_name
  agents_alb_dns_name    = module.networking.agents_alb_dns_name
  allowed_origins        = "https://${module.cloudfront.cloudfront_domain_name}"
  cloudwatch_kms_key_arn = module.kms.cloudwatch_key_arn
  ecr_kms_key_arn        = module.kms.cloudwatch_key_arn # Reuse CloudWatch KMS key for ECR

  s3_bucket_names      = module.s3.bucket_ids
  dynamodb_table_names = module.dynamodb.table_names

  # Voice services integration
  voice_audio_bucket_name    = module.voice_services.voice_audio_bucket_name
  voice_services_role_arn    = module.voice_services.voice_services_role_arn
  transcribe_vocabulary_name = module.voice_services.transcribe_vocabulary_name

  bedrock_model_id    = var.bedrock_model_id
  bedrock_max_tokens  = var.bedrock_max_tokens
  bedrock_temperature = var.bedrock_temperature
  bedrock_top_p       = var.bedrock_top_p
  bedrock_top_k       = var.bedrock_top_k
  bedrock_timeout     = var.bedrock_timeout
  bedrock_role_arn    = var.bedrock_role_arn
  bedrock_account_id  = var.bedrock_account_id

  # Langfuse SaaS integration

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Cognito Module
module "cognito" {
  source = "../../modules/cognito"

  project_name = var.project_name
  environment  = var.environment

  domain_prefix              = "${var.project_name}-${var.aws_account_id}"
  callback_urls              = var.cognito_callback_urls
  logout_urls                = var.cognito_logout_urls
  cloudfront_domain_name     = module.cloudfront.cloudfront_domain_name
  secrets_manager_kms_key_id = module.kms.secrets_manager_key_id

  # Federated SSO (OIDC) Authentication
  federated_sso_enabled       = var.federated_sso_enabled
  federated_sso_client_id     = var.federated_sso_client_id
  federated_sso_client_secret_arn = var.federated_sso_client_secret_arn
  federated_sso_issuer        = var.federated_sso_issuer

  depends_on = [module.cloudfront]

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Self-signed TLS certificate for internal ALB HTTPS
resource "tls_private_key" "internal" {
  algorithm = "RSA"
  rsa_bits  = 2048
}

resource "tls_self_signed_cert" "internal" {
  private_key_pem = tls_private_key.internal.private_key_pem

  subject {
    common_name  = "*.${var.project_name}.internal"
    organization = var.project_name
  }

  validity_period_hours = 87600 # 10 years

  allowed_uses = [
    "key_encipherment",
    "digital_signature",
    "server_auth",
  ]
}

resource "aws_acm_certificate" "internal" {
  private_key      = tls_private_key.internal.private_key_pem
  certificate_body = tls_self_signed_cert.internal.cert_pem

  tags = {
    Name        = "${var.project_name}-internal-cert"
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Frontend Module
module "frontend" {
  source = "../../modules/frontend"

  project_name = var.project_name
  environment  = var.environment

  vpc_id                 = module.networking.vpc_id
  subnet_ids             = module.networking.private_subnet_ids
  public_subnet_ids      = module.networking.public_subnet_ids
  security_group_ids     = [module.networking.security_group_ids["frontend"]]
  waf_web_acl_arn        = module.networking.alb_waf_arn
  cloudwatch_kms_key_arn = module.kms.cloudwatch_key_arn
  ecr_kms_key_arn        = module.kms.ecr_key_arn
  cloudfront_url         = module.cloudfront.cloudfront_url

  execution_role_arn = module.iam.ecs_task_execution_role_arn
  task_role_arn      = module.iam.ecs_task_role_arn

  api_gateway_url = module.api_gateway.api_endpoint
  agents_alb_url  = module.networking.agents_alb_dns_name

  cognito_user_pool_id = module.cognito.user_pool_id
  cognito_client_id    = module.cognito.user_pool_client_id

  certificate_arn = aws_acm_certificate.internal.arn

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}



# CloudFront Module (HTTPS for authentication)
module "cloudfront" {
  source = "../../modules/cloudfront"

  project_name            = var.project_name
  environment             = var.environment
  cloudfront_secret       = random_password.cloudfront_secret.result
  frontend_alb_dns_name   = module.frontend.alb_dns_name
  agents_alb_dns_name     = module.networking.agents_alb_external_dns_name
  api_gateway_domain_name = "${module.api_gateway.api_id}.execute-api.us-east-1.amazonaws.com"

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# WAF Association for External Agents ALB
# Langfuse Module (LLM Observability) - DISABLED: Migrated to SaaS
#   
#   tags = {
#     Project     = var.project_name
#     Environment = var.environment
#     ManagedBy   = "Terraform"
#   }
# }
