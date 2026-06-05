locals {
  cluster_name = "agents"
  services = {
    architect = {
      cpu = 256
      memory = 512
      port = 9002
      desired_count = 1
      image_tag = "latest"
      command = ["python", "agents/architect/server.py"]
      environment_variables = []
    }
    security_architect = {
      cpu = 256
      memory = 512
      port = 9004
      desired_count = 1
      image_tag = "latest"
      command = ["python", "agents/security_architect/server.py"]
      environment_variables = []
    }
    risk_assessment = {
      cpu = 512
      memory = 1024
      port = 9005
      desired_count = 1
      image_tag = "latest"
      command = ["python", "agents/risk_assessment/server.py"]
      environment_variables = []
    }
    auditor = {
      cpu = 256
      memory = 512
      port = 9006
      desired_count = 1
      image_tag = "latest"
      command = ["python", "agents/auditor/server.py"]
      environment_variables = []
    }
    organization_profile = {
      cpu = 256
      memory = 512
      port = 9007
      desired_count = 1
      image_tag = "latest"
      command = ["python", "agents/organization_profile/server.py"]
      environment_variables = [
        {
          name  = "VOICE_AUDIO_BUCKET"
          value = var.voice_audio_bucket_name
        },
        {
          name  = "VOICE_SERVICES_ROLE_ARN"
          value = var.voice_services_role_arn
        },
        {
          name  = "TRANSCRIBE_VOCABULARY_NAME"
          value = var.transcribe_vocabulary_name
        }
      ]
    }
  }
}

resource "aws_ecs_cluster" "this" {
  name = "${var.project_name}-${local.cluster_name}"

  setting {
    name  = "containerInsights"
    value = var.enable_container_insights ? "enabled" : "disabled"
  }

  tags = var.tags
}

# ECR Repositories
# nosemgrep: terraform.lang.security.ecr-image-scan-on-push.ecr-image-scan-on-push
resource "aws_ecr_repository" "this" {
  for_each = local.services

  name                 = "${var.project_name}-${each.key}"
  image_tag_mutability = "MUTABLE"
  force_delete         = true  # Allow deletion even with images present
  
  image_scanning_configuration {
    scan_on_push = var.enable_image_scanning
  }
  
  encryption_configuration {
    encryption_type = "KMS"
    kms_key         = var.ecr_kms_key_arn
  }
  
  tags = merge(var.tags, {
    Service = each.key
  })
}

# Task Definitions
resource "aws_ecs_task_definition" "this" {
  for_each = local.services

  family                   = "${var.project_name}-${each.key}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = each.value.cpu
  memory                   = each.value.memory
  execution_role_arn       = var.execution_role_arn
  task_role_arn           = lookup(var.agent_task_role_arns, each.key, var.task_role_arn)
  pid_mode                 = "task"

  container_definitions = jsonencode([{
    name  = each.key
    image = "${aws_ecr_repository.this[each.key].repository_url}:${each.value.image_tag}"
    command = each.value.command
    privileged = false
    user = "1000"
    
    portMappings = [{
      containerPort = each.value.port
      protocol      = "tcp"
    }]

    environment = concat(
      var.common_environment_variables,
      each.value.environment_variables,
      [
        { name = "AGENT_TYPE", value = each.key },
        { name = "AGENT_NAME", value = each.key },
        { name = "AGENT_PORT", value = tostring(each.value.port) },
        { name = "APP_DATA_BUCKET", value = lookup(var.s3_bucket_names, "app_data", "") },
        { name = "DOCUMENTS_BUCKET", value = lookup(var.s3_bucket_names, "project_documents", "") },
        { name = "COGNITO_USER_POOL_ID", value = var.cognito_user_pool_id },
        { name = "COGNITO_DOMAIN_PREFIX", value = var.cognito_domain_name },
        { name = "AGENTS_ALB_URL", value = "http://${var.agents_alb_dns_name}" },
        { name = "ALLOWED_ORIGINS", value = var.allowed_origins },
        { name = "BEDROCK_MODEL_ID", value = var.bedrock_model_id },
        { name = "BEDROCK_MAX_TOKENS", value = tostring(var.bedrock_max_tokens) },
        { name = "BEDROCK_TEMPERATURE", value = tostring(var.bedrock_temperature) },
        { name = "BEDROCK_TOP_P", value = tostring(var.bedrock_top_p) },
        { name = "BEDROCK_TOP_K", value = tostring(var.bedrock_top_k) },
        { name = "BEDROCK_TIMEOUT", value = tostring(var.bedrock_timeout) },
        { name = "BEDROCK_ROLE_ARN", value = var.bedrock_role_arn },
        { name = "BEDROCK_ACCOUNT_ID", value = var.bedrock_account_id },
        { name = "SESSIONS_TABLE", value = lookup(var.dynamodb_table_names, "sessions", "") },
      ]
    )

    secrets = []

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.this[each.key].name
        "awslogs-region"        = data.aws_region.current.name
        "awslogs-stream-prefix" = "ecs"
      }
    }

    healthCheck = lookup(each.value, "health_check", null) != null ? {
      command     = each.value.health_check.command
      interval    = each.value.health_check.interval
      timeout     = each.value.health_check.timeout
      retries     = each.value.health_check.retries
      startPeriod = each.value.health_check.start_period
    } : null
  }])

  tags = merge(var.tags, {
    Service = each.key
  })
}

# ECS Services
resource "aws_ecs_service" "this" {
  for_each = local.services

  name            = "${var.project_name}-${each.key}"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.this[each.key].arn
  desired_count   = each.value.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = var.security_group_ids
    assign_public_ip = var.assign_public_ip
  }

  dynamic "load_balancer" {
    for_each = lookup(var.target_group_arns, each.key, null) != null ? [1] : []
    content {
      target_group_arn = var.target_group_arns[each.key]
      container_name   = each.key
      container_port   = each.value.port
    }
  }

  dynamic "load_balancer" {
    for_each = lookup(var.external_target_group_arns, each.key, null) != null ? [1] : []
    content {
      target_group_arn = var.external_target_group_arns[each.key]
      container_name   = each.key
      container_port   = each.value.port
    }
  }

  depends_on = [var.load_balancer_listener_arn]
  
  tags = merge(var.tags, {
    Service = each.key
  })
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "this" {
  for_each = local.services

  name              = "/ecs/${var.project_name}-${each.key}"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.cloudwatch_kms_key_arn
  
  tags = merge(var.tags, {
    Service = each.key
  })
}

data "aws_region" "current" {}