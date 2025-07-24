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
    tags = local.common_tags
  }
}

# Provider for CloudFront WAF (must be us-east-1)
provider "aws" {
  alias   = "us_east_1"
  region  = "us-east-1"
  profile = var.aws_profile

  allowed_account_ids = [var.aws_account_id]

  default_tags {
    tags = local.common_tags
  }
}

# Include shared configuration
locals {
  # Import shared locals
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    Owner       = "RiskAgent"
  }

  name_prefix = var.project_name

  common_lambda_env_vars = {
    ENVIRONMENT  = var.environment
    PROJECT_NAME = var.project_name
    AWS_REGION   = var.region
  }

  # Production-specific Lambda configurations
  lambda_functions = {
    projects-api = {
      handler     = "projects.handler"
      runtime     = "python3.11"
      timeout     = 30
      memory_size = 256
      env_vars = {
        DYNAMODB_TABLE = module.dynamodb.table_names["projects"]
        S3_BUCKET      = module.s3.bucket_names["project_images"]
      }
    }
    diagram-analysis-api = {
      handler     = "diagram_analysis.lambda_handler"
      runtime     = "python3.11"
      timeout     = 300
      memory_size = 1024
      env_vars = {
        PROJECTS_TABLE  = module.dynamodb.table_names["projects"]
        DIAGRAMS_BUCKET = module.s3.bucket_names["project_images"]
      }
    }
    invoke-bedrock = {
      handler     = "invoke_bedrock.lambda_handler"
      runtime     = "python3.11"
      timeout     = 900
      memory_size = 512
      env_vars = {
        BEDROCK_REGION = var.region
      }
    }
    read-services = {
      handler     = "read_services.lambda_handler"
      runtime     = "python3.11"
      timeout     = 60
      memory_size = 256
      env_vars = {
        SERVICES_TABLE = module.dynamodb.table_names["services"]
      }
    }
    process-node-controls = {
      handler     = "process_node_controls.lambda_handler"
      runtime     = "python3.11"
      timeout     = 300
      memory_size = 512
      env_vars = {
        NODE_CONTROLS_TABLE = module.dynamodb.table_names["node_controls"]
      }
    }
    get-node-details-api = {
      handler     = "get_node_details.lambda_handler"
      runtime     = "python3.11"
      timeout     = 60
      memory_size = 256
      env_vars = {
        PROJECTS_TABLE = module.dynamodb.table_names["projects"]
      }
    }
    get-node-controls-api = {
      handler     = "get_node_controls.lambda_handler"
      runtime     = "python3.11"
      timeout     = 60
      memory_size = 256
      env_vars = {
        NODE_CONTROLS_TABLE = module.dynamodb.table_names["node_controls"]
      }
    }
    process-bedrock-results = {
      handler     = "process_bedrock_results.lambda_handler"
      runtime     = "python3.11"
      timeout     = 300
      memory_size = 512
      env_vars = {
        PROJECTS_TABLE = module.dynamodb.table_names["projects"]
      }
    }
    # Document processing functions
    get-document = {
      handler     = "get_document.lambda_handler"
      runtime     = "python3.11"
      timeout     = 60
      memory_size = 256
      env_vars = {
        PROJECTS_TABLE   = module.dynamodb.table_names["projects"]
        DOCUMENTS_BUCKET = module.s3.bucket_names["project_documents"]
      }
    }
    get-document-content = {
      handler     = "get_document_content.lambda_handler"
      runtime     = "python3.11"
      timeout     = 60
      memory_size = 256
      env_vars = {
        PROJECTS_TABLE   = module.dynamodb.table_names["projects"]
        DOCUMENTS_BUCKET = module.s3.bucket_names["project_documents"]
      }
    }
    process-document = {
      handler     = "process_document.lambda_handler"
      runtime     = "python3.11"
      timeout     = 300
      memory_size = 512
      env_vars = {
        PROJECTS_TABLE   = module.dynamodb.table_names["projects"]
        DOCUMENTS_BUCKET = module.s3.bucket_names["project_documents"]
        DIAGRAMS_BUCKET  = module.s3.bucket_names["project_images"]
      }
    }
    # Assessment functions
    get-risk-assessments = {
      handler     = "get_risk_assessments.lambda_handler"
      runtime     = "python3.11"
      timeout     = 60
      memory_size = 256
      env_vars = {
        PROJECTS_TABLE = module.dynamodb.table_names["projects"]
      }
    }
    get-security-assessments = {
      handler     = "get_security_assessments.lambda_handler"
      runtime     = "python3.11"
      timeout     = 60
      memory_size = 256
      env_vars = {
        PROJECTS_TABLE = module.dynamodb.table_names["projects"]
      }
    }
    save-risk-assessment = {
      handler     = "save_risk_assessment.lambda_handler"
      runtime     = "python3.11"
      timeout     = 60
      memory_size = 256
      env_vars = {
        PROJECTS_TABLE = module.dynamodb.table_names["projects"]
      }
    }
    save-security-assessment = {
      handler     = "save_security_assessment.lambda_handler"
      runtime     = "python3.11"
      timeout     = 60
      memory_size = 256
      env_vars = {
        PROJECTS_TABLE = module.dynamodb.table_names["projects"]
      }
    }
    # Admin functions
    manage-services = {
      handler     = "manage_services.lambda_handler"
      runtime     = "python3.11"
      timeout     = 60
      memory_size = 256
      env_vars = {
        SERVICES_TABLE = module.dynamodb.table_names["services"]
      }
    }
    images = {
      handler     = "images.handler"
      runtime     = "python3.11"
      timeout     = 30
      memory_size = 256
      env_vars = {
        S3_BUCKET = module.s3.bucket_names["project_images"]
      }
    }
    health = {
      handler     = "health.handler"
      runtime     = "python3.11"
      timeout     = 10
      memory_size = 128
      env_vars    = {}
    }
  }

  # DynamoDB table configurations
  dynamodb_tables = {
    projects = {
      hash_key = "project_id"
      attributes = [
        {
          name = "project_id"
          type = "S"
        }
      ]
    }
    services = {
      hash_key = "service_name"
      attributes = [
        {
          name = "service_name"
          type = "S"
        }
      ]
    }
    controls = {
      hash_key = "control_id"
      attributes = [
        {
          name = "control_id"
          type = "S"
        }
      ]
    }
    node_controls = {
      hash_key  = "node_id"
      range_key = "control_id"
      attributes = [
        {
          name = "node_id"
          type = "S"
        },
        {
          name = "control_id"
          type = "S"
        }
      ]
    }
  }

  # S3 bucket configurations
  s3_buckets = {
    project_images = {
      versioning = true
      encryption = true
      lifecycle_rules = [
        {
          id     = "delete_old_versions"
          status = "Enabled"
          noncurrent_version_expiration = {
            days = 30
          }
        }
      ]
    }
    project_documents = {
      versioning = true
      encryption = true
      lifecycle_rules = [
        {
          id     = "delete_old_versions"
          status = "Enabled"
          noncurrent_version_expiration = {
            days = 90
          }
        }
      ]
    }
    terraform_state = {
      versioning      = true
      encryption      = true
      lifecycle_rules = []
    }
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Cognito Authentication
module "cognito" {
  source = "../../modules/cognito"

  project_name = var.project_name
  environment  = var.environment

  callback_urls = [
    "http://localhost:3000/auth/callback",
    "https://placeholder-cloudfront-domain/auth/callback"
  ]
  logout_urls = [
    "http://localhost:3000/",
    "https://placeholder-cloudfront-domain/"
  ]

  domain_prefix = "${var.project_name}-auth"

  tags = local.common_tags
}

# Networking
module "networking" {
  source = "../../modules/networking"

  project_name = var.project_name
  environment  = var.environment

  vpc_cidr             = "10.0.0.0/16"
  public_subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24"]
  private_subnet_cidrs = ["10.0.10.0/24", "10.0.20.0/24"]
  enable_nat_gateway   = true

  security_groups = {
    agents_alb = {
      description = "Security group for agents ALB"
      ingress_rules = [
        {
          from_port   = 80
          to_port     = 80
          protocol    = "tcp"
          cidr_blocks = ["0.0.0.0/0"]
        },
        {
          from_port   = 443
          to_port     = 443
          protocol    = "tcp"
          cidr_blocks = ["0.0.0.0/0"]
        }
      ]
      egress_rules = [
        {
          from_port   = 0
          to_port     = 0
          protocol    = "-1"
          cidr_blocks = ["0.0.0.0/0"]
        }
      ]
    }
    frontend_alb = {
      description = "Security group for frontend ALB"
      ingress_rules = [
        {
          from_port   = 80
          to_port     = 80
          protocol    = "tcp"
          cidr_blocks = ["0.0.0.0/0"]
        },
        {
          from_port   = 443
          to_port     = 443
          protocol    = "tcp"
          cidr_blocks = ["0.0.0.0/0"]
        }
      ]
      egress_rules = [
        {
          from_port   = 0
          to_port     = 0
          protocol    = "-1"
          cidr_blocks = ["0.0.0.0/0"]
        }
      ]
    }
    frontend = {
      description = "Security group for frontend containers"
      ingress_rules = [
        {
          from_port   = 3000
          to_port     = 3000
          protocol    = "tcp"
          cidr_blocks = ["10.0.0.0/16"]
        }
      ]
      egress_rules = [
        {
          from_port   = 0
          to_port     = 0
          protocol    = "-1"
          cidr_blocks = ["0.0.0.0/0"]
        }
      ]
    }
    agents = {
      description = "Security group for agent containers"
      ingress_rules = [
        {
          from_port   = 9001
          to_port     = 9006
          protocol    = "tcp"
          cidr_blocks = ["10.0.0.0/16"]
        }
      ]
      egress_rules = [
        {
          from_port   = 0
          to_port     = 0
          protocol    = "-1"
          cidr_blocks = ["0.0.0.0/0"]
        }
      ]
    }
  }

  load_balancers = {
    agents = {
      internal                   = true
      security_group_ids         = ["agents_alb"]
      enable_deletion_protection = false
    }
    frontend = {
      internal                   = false
      security_group_ids         = ["frontend_alb"]
      enable_deletion_protection = false
    }
  }

  target_groups = {
    orchestrator = {
      port        = 9001
      protocol    = "HTTP"
      target_type = "ip"
      health_check = {
        healthy_threshold   = 2
        interval            = 30
        matcher             = "200"
        path                = "/health"
        protocol            = "HTTP"
        timeout             = 5
        unhealthy_threshold = 2
      }
    }
    architect = {
      port        = 9002
      protocol    = "HTTP"
      target_type = "ip"
      health_check = {
        healthy_threshold   = 2
        interval            = 30
        matcher             = "200"
        path                = "/health"
        protocol            = "HTTP"
        timeout             = 5
        unhealthy_threshold = 2
      }
    }
    risk_framework = {
      port        = 9003
      protocol    = "HTTP"
      target_type = "ip"
      health_check = {
        healthy_threshold   = 2
        interval            = 30
        matcher             = "200"
        path                = "/health"
        protocol            = "HTTP"
        timeout             = 5
        unhealthy_threshold = 2
      }
    }
    security_architect = {
      port        = 9004
      protocol    = "HTTP"
      target_type = "ip"
      health_check = {
        healthy_threshold   = 2
        interval            = 30
        matcher             = "200"
        path                = "/health"
        protocol            = "HTTP"
        timeout             = 5
        unhealthy_threshold = 2
      }
    }
    risk_assessment = {
      port        = 9005
      protocol    = "HTTP"
      target_type = "ip"
      health_check = {
        healthy_threshold   = 2
        interval            = 30
        matcher             = "200"
        path                = "/health"
        protocol            = "HTTP"
        timeout             = 5
        unhealthy_threshold = 2
      }
    }
    auditor = {
      port        = 9006
      protocol    = "HTTP"
      target_type = "ip"
      health_check = {
        healthy_threshold   = 2
        interval            = 30
        matcher             = "200"
        path                = "/health"
        protocol            = "HTTP"
        timeout             = 5
        unhealthy_threshold = 2
      }
    }
    frontend = {
      port        = 3000
      protocol    = "HTTP"
      target_type = "ip"
      health_check = {
        healthy_threshold   = 2
        interval            = 30
        matcher             = "200"
        path                = "/"
        protocol            = "HTTP"
        timeout             = 5
        unhealthy_threshold = 2
      }
    }
  }

  listeners = {
    agents_http = {
      load_balancer_key = "agents"
      port              = 80
      protocol          = "HTTP"
      default_actions = [
        {
          type             = "forward"
          target_group_key = "orchestrator"
        }
      ]
    }
    frontend_http = {
      load_balancer_key = "frontend"
      port              = 80
      protocol          = "HTTP"
      default_actions = [
        {
          type             = "forward"
          target_group_key = "frontend"
        }
      ]
    }
  }

  tags = local.common_tags
}



# S3 buckets
module "s3" {
  source = "../../modules/s3"

  project_name = var.project_name
  environment  = var.environment
  s3_buckets   = local.s3_buckets
  tags         = local.common_tags
}

# DynamoDB tables
module "dynamodb" {
  source = "../../modules/dynamodb"

  project_name    = var.project_name
  environment     = var.environment
  dynamodb_tables = local.dynamodb_tables
  tags            = local.common_tags
}

# IAM roles and policies
module "iam" {
  source = "../../modules/iam"

  project_name        = var.project_name
  environment         = var.environment
  region              = var.region
  account_id          = data.aws_caller_identity.current.account_id
  dynamodb_table_arns = values(module.dynamodb.table_arns)
  s3_bucket_arns      = values(module.s3.bucket_arns)
  tags                = local.common_tags
}

# ECS Agents - Full Configuration
module "ecs" {
  source = "../../modules/ecs"

  project_name       = var.project_name
  environment        = var.environment
  cluster_name       = "agents"
  execution_role_arn = module.iam.ecs_task_execution_role_arn
  task_role_arn      = module.iam.ecs_task_role_arn
  subnet_ids         = module.networking.private_subnet_ids
  security_group_ids = [module.networking.security_group_ids["agents"]]
  assign_public_ip   = false

  load_balancer_listener_arn = module.networking.listener_arns["agents_http"]

  common_environment_variables = [
    { name = "PROJECT_NAME", value = var.project_name },
    { name = "AWS_REGION", value = var.region },
    { name = "ENVIRONMENT", value = var.environment },
    { name = "AGENT_STATE_TABLE", value = module.dynamodb.table_names["projects"] },
    { name = "COGNITO_USER_POOL_ID", value = "${var.project_name}-user-pool" }
  ]

  services = {
    orchestrator = {
      cpu              = "256"
      memory           = "512"
      port             = 9001
      desired_count    = 1
      image_tag        = "latest"
      command          = ["python", "-m", "agents.orchestrator.main"]
      target_group_arn = module.networking.target_group_arns["orchestrator"]
      environment_variables = [
        { name = "AGENT_TYPE", value = "orchestrator" },
        { name = "AGENT_NAME", value = "orchestrator" }
      ]
    }
    architect = {
      cpu              = "256"
      memory           = "512"
      port             = 9002
      desired_count    = 1
      image_tag        = "latest"
      command          = ["python", "-m", "agents.architect.server"]
      target_group_arn = module.networking.target_group_arns["architect"]
      environment_variables = [
        { name = "AGENT_TYPE", value = "architect" },
        { name = "AGENT_NAME", value = "architect" }
      ]
    }
    risk_framework = {
      cpu              = "512"
      memory           = "1024"
      port             = 9003
      desired_count    = 1
      image_tag        = "latest"
      command          = ["python", "-m", "agents.risk_framework.server"]
      target_group_arn = module.networking.target_group_arns["risk_framework"]
      environment_variables = [
        { name = "AGENT_TYPE", value = "risk_framework" },
        { name = "AGENT_NAME", value = "risk-framework" }
      ]
    }
    security_architect = {
      cpu              = "256"
      memory           = "512"
      port             = 9004
      desired_count    = 1
      image_tag        = "latest"
      command          = ["python", "-m", "agents.security_architect.server"]
      target_group_arn = module.networking.target_group_arns["security_architect"]
      environment_variables = [
        { name = "AGENT_TYPE", value = "security_architect" },
        { name = "AGENT_NAME", value = "security-architect" }
      ]
    }
    risk_assessment = {
      cpu              = "256"
      memory           = "512"
      port             = 9005
      desired_count    = 1
      image_tag        = "latest"
      command          = ["python", "-m", "agents.risk_assessment.server"]
      target_group_arn = module.networking.target_group_arns["risk_assessment"]
      environment_variables = [
        { name = "AGENT_TYPE", value = "risk_assessment" },
        { name = "AGENT_NAME", value = "risk-assessment" }
      ]
    }
    auditor = {
      cpu              = "256"
      memory           = "512"
      port             = 9006
      desired_count    = 1
      image_tag        = "latest"
      command          = ["python", "-m", "agents.auditor.server"]
      target_group_arn = module.networking.target_group_arns["auditor"]
      environment_variables = [
        { name = "AGENT_TYPE", value = "auditor" },
        { name = "AGENT_NAME", value = "auditor" }
      ]
    }
    frontend = {
      cpu              = "256"
      memory           = "512"
      port             = 3000
      desired_count    = 1
      image_tag        = "latest"
      command          = ["npm", "start"]
      target_group_arn = module.networking.target_group_arns["frontend"]
      environment_variables = [
        { name = "REACT_APP_API_URL", value = module.api_gateway.api_endpoint },
        { name = "REACT_APP_COGNITO_USER_POOL_ID", value = module.cognito.user_pool_id },
        { name = "REACT_APP_COGNITO_CLIENT_ID", value = module.cognito.user_pool_client_id }
      ]
    }
  }

  tags = local.common_tags

  depends_on = [module.iam, module.networking]
}

# Lambda functions
module "lambda" {
  source = "../../modules/lambda"

  project_name              = var.project_name
  environment               = var.environment
  lambda_functions          = local.lambda_functions
  lambda_role_arn           = module.iam.lambda_exec_role_arn
  lambda_package_path       = "../../temp/lambda_packages/lambda_functions.zip"
  common_env_vars           = local.common_lambda_env_vars
  api_gateway_execution_arn = "arn:aws:execute-api:${var.region}:${data.aws_caller_identity.current.account_id}:*"
  tags                      = local.common_tags

  depends_on = [module.iam, module.dynamodb, module.s3]
}

# API Gateway
module "api_gateway" {
  source = "../../modules/api-gateway"

  project_name = var.project_name
  environment  = var.environment
  stage_name   = "prod"

  # Set authorizer after Cognito is created
  authorizer_id = module.cognito.authorizer_id

  lambda_integrations = {
    for k, v in module.lambda.lambda_functions : k => {
      invoke_arn = v.invoke_arn
    }
  }

  lambda_routes = {
    # Projects routes
    "projects_get_all" = {
      route_key       = "GET /api/projects"
      integration_key = "projects-api"
      auth_required   = true
    }
    "projects_get_one" = {
      route_key       = "GET /api/projects/{id}"
      integration_key = "projects-api"
      auth_required   = true
    }
    "projects_post" = {
      route_key       = "POST /api/projects"
      integration_key = "projects-api"
      auth_required   = true
    }
    "projects_put" = {
      route_key       = "PUT /api/projects/{id}"
      integration_key = "projects-api"
      auth_required   = true
    }
    "projects_options" = {
      route_key       = "OPTIONS /api/projects"
      integration_key = "projects-api"
      auth_required   = false
    }
    "projects_options_id" = {
      route_key       = "OPTIONS /api/projects/{id}"
      integration_key = "projects-api"
      auth_required   = false
    }

    # Diagram Analysis routes
    "diagram_analysis_get" = {
      route_key       = "GET /api/projects/{id}/diagram-analysis"
      integration_key = "diagram-analysis-api"
      auth_required   = true
    }
    "diagram_analysis_post" = {
      route_key       = "POST /api/projects/{id}/diagram-analysis"
      integration_key = "diagram-analysis-api"
      auth_required   = true
    }
    "diagram_analysis_put" = {
      route_key       = "PUT /api/projects/{id}/diagram-analysis"
      integration_key = "diagram-analysis-api"
      auth_required   = true
    }
    "diagram_analysis_options" = {
      route_key       = "OPTIONS /api/projects/{id}/diagram-analysis"
      integration_key = "diagram-analysis-api"
      auth_required   = false
    }

    # Node Controls routes
    "node_controls_get" = {
      route_key       = "GET /api/projects/{id}/node-controls"
      integration_key = "get-node-controls-api"
      auth_required   = true
    }
    "node_controls_options" = {
      route_key       = "OPTIONS /api/projects/{id}/node-controls"
      integration_key = "get-node-controls-api"
      auth_required   = false
    }

    # Node Details routes
    "node_details_get" = {
      route_key       = "GET /api/projects/{id}/nodes/{nodeId}"
      integration_key = "get-node-details-api"
      auth_required   = true
    }
    "node_details_options" = {
      route_key       = "OPTIONS /api/projects/{id}/nodes/{nodeId}"
      integration_key = "get-node-details-api"
      auth_required   = false
    }

    # Health routes
    "health_get" = {
      route_key       = "GET /api/health"
      integration_key = "health"
      auth_required   = false
    }
    "health_options" = {
      route_key       = "OPTIONS /api/health"
      integration_key = "health"
      auth_required   = false
    }

    # Document routes
    "document_post" = {
      route_key       = "POST /api/document"
      integration_key = "process-document"
      auth_required   = true
    }
    "document_get" = {
      route_key       = "GET /api/projects/{id}/document"
      integration_key = "get-document"
      auth_required   = true
    }
    "document_content_get" = {
      route_key       = "GET /api/projects/{id}/document/content"
      integration_key = "get-document-content"
      auth_required   = true
    }

    # Assessment routes
    "risk_assessments_get" = {
      route_key       = "GET /api/projects/{id}/risk-assessments"
      integration_key = "get-risk-assessments"
      auth_required   = true
    }
    "risk_assessments_post" = {
      route_key       = "POST /api/projects/{id}/risk-assessments"
      integration_key = "save-risk-assessment"
      auth_required   = true
    }
    "security_assessments_get" = {
      route_key       = "GET /api/projects/{id}/security-assessments"
      integration_key = "get-security-assessments"
      auth_required   = true
    }
    "security_assessments_post" = {
      route_key       = "POST /api/projects/{id}/security-assessments"
      integration_key = "save-security-assessment"
      auth_required   = true
    }

    # Services routes
    "services_get" = {
      route_key       = "GET /services"
      integration_key = "manage-services"
      auth_required   = true
    }
    "services_post" = {
      route_key       = "POST /services"
      integration_key = "manage-services"
      auth_required   = true
    }

    # Images routes
    "images_get" = {
      route_key       = "GET /api/images/{filename}"
      integration_key = "images"
      auth_required   = false
    }
  }

  vpc_link_config = {
    security_group_ids = [module.networking.security_group_ids["agents_alb"]]
    subnet_ids         = module.networking.private_subnet_ids
  }

  alb_integration = {
    listener_arn = module.networking.listener_arns["agents_http"]
  }

  alb_routes = {
    "agent_post" = {
      route_key     = "POST /api/agent"
      auth_required = true
    },
    "agent_options" = {
      route_key     = "OPTIONS /api/agent"
      auth_required = false
    }
  }

  tags = local.common_tags

  depends_on = [module.lambda, module.networking, module.cognito]
}

# Update Cognito with API Gateway ID
module "cognito_authorizer" {
  source = "../../modules/cognito"

  project_name = var.project_name
  environment  = var.environment

  callback_urls = [
    "http://localhost:3000/auth/callback",
    "https://${module.cloudfront.domain_name}/auth/callback"
  ]
  logout_urls = [
    "http://localhost:3000/",
    "https://${module.cloudfront.domain_name}/"
  ]

  domain_prefix  = "${var.project_name}-auth"
  api_gateway_id = module.api_gateway.api_id

  tags = local.common_tags

  depends_on = [module.api_gateway]
}

# CloudFront Distribution
module "cloudfront" {
  source = "../../modules/cloudfront"

  providers = {
    aws.us_east_1 = aws.us_east_1
  }

  project_name = var.project_name
  environment  = var.environment
  comment      = "RiskAgent Frontend Distribution"

  origins = [
    {
      domain_name            = module.networking.load_balancer_dns_names["frontend"]
      origin_id              = "ALB-frontend"
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    },
    {
      domain_name            = module.networking.load_balancer_dns_names["agents"]
      origin_id              = "ALB-agents"
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  ]

  cache_behaviors = [
    {
      path_pattern           = "/orchestrator/*"
      allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
      cached_methods         = ["GET", "HEAD"]
      target_origin_id       = "ALB-agents"
      compress               = true
      viewer_protocol_policy = "redirect-to-https"
      forwarded_values = {
        query_string    = true
        headers         = ["*"]
        cookies_forward = "all"
      }
    },
    {
      path_pattern           = "/architect/*"
      allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
      cached_methods         = ["GET", "HEAD"]
      target_origin_id       = "ALB-agents"
      compress               = true
      viewer_protocol_policy = "redirect-to-https"
      forwarded_values = {
        query_string    = true
        headers         = ["*"]
        cookies_forward = "all"
      }
    },
    {
      path_pattern           = "/risk-framework/*"
      allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
      cached_methods         = ["GET", "HEAD"]
      target_origin_id       = "ALB-agents"
      compress               = true
      viewer_protocol_policy = "redirect-to-https"
      forwarded_values = {
        query_string    = true
        headers         = ["*"]
        cookies_forward = "all"
      }
    },
    {
      path_pattern           = "/security-architect/*"
      allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
      cached_methods         = ["GET", "HEAD"]
      target_origin_id       = "ALB-agents"
      compress               = true
      viewer_protocol_policy = "redirect-to-https"
      forwarded_values = {
        query_string    = true
        headers         = ["*"]
        cookies_forward = "all"
      }
    },
    {
      path_pattern             = "/risk-assessment/*"
      allowed_methods          = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
      cached_methods           = ["GET", "HEAD"]
      target_origin_id         = "ALB-agents"
      compress                 = false
      viewer_protocol_policy   = "redirect-to-https"
      cache_policy_id          = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
      origin_request_policy_id = "88a5eaf4-2fd4-4709-b370-b4c650ea3fcf"
    },
    {
      path_pattern           = "/auditor/*"
      allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
      cached_methods         = ["GET", "HEAD"]
      target_origin_id       = "ALB-agents"
      compress               = true
      viewer_protocol_policy = "redirect-to-https"
      forwarded_values = {
        query_string    = true
        headers         = ["*"]
        cookies_forward = "all"
      }
    }
  ]

  default_cache_behavior = {
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "ALB-frontend"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"
    forwarded_values = {
      query_string    = true
      headers         = ["*"]
      cookies_forward = "all"
    }
    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0
  }

  create_waf = true
  rate_limit = 2000

  tags = local.common_tags

  depends_on = [module.networking]
}