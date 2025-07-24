# Langfuse Observability Module
# Self-hosted LLM tracing and observability platform

data "aws_region" "current" {}

# Random passwords for security
resource "random_password" "db" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+<>:?"  # Exclude /, @, ", space, [, ], { } per RDS requirements
}

resource "random_password" "nextauth" {
  length  = 32
  special = false
}

resource "random_password" "salt" {
  length  = 32
  special = false
}

# RDS PostgreSQL Database
module "langfuse_db" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 6.0"

  identifier = "${var.project_name}-langfuse-${var.environment}"

  engine               = "postgres"
  engine_version       = "15"
  family               = "postgres15"
  major_engine_version = "15"
  instance_class       = var.db_instance_class

  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_max_allocated_storage

  db_name  = "langfuse"
  username = "langfuse"
  password = random_password.db.result
  port     = 5432
  
  manage_master_user_password = false  # Use our random password instead of AWS Secrets Manager

  multi_az               = var.environment == "prod"
  db_subnet_group_name   = var.db_subnet_group_name
  vpc_security_group_ids = [aws_security_group.langfuse_db.id]

  maintenance_window              = "Mon:00:00-Mon:03:00"
  backup_window                   = "03:00-06:00"
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  create_cloudwatch_log_group     = true

  backup_retention_period = var.environment == "prod" ? 7 : 1
  skip_final_snapshot     = var.environment != "prod"
  deletion_protection     = var.environment == "prod"

  performance_insights_enabled          = true
  performance_insights_retention_period = 7

  tags = var.tags
}

# Security Group for RDS
resource "aws_security_group" "langfuse_db" {
  name_prefix = "${var.project_name}-langfuse-db-"
  description = "Security group for Langfuse PostgreSQL database"
  vpc_id      = var.vpc_id

  ingress {
    description     = "PostgreSQL from Langfuse ECS tasks"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.langfuse_ecs.id]
  }

  egress {
    description     = "PostgreSQL responses to ECS tasks"
    from_port       = 0
    to_port         = 65535
    protocol        = "tcp"
    security_groups = [aws_security_group.langfuse_ecs.id]
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-langfuse-db"
  })
}

# Security Group for ECS Tasks
resource "aws_security_group" "langfuse_ecs" {
  name_prefix = "${var.project_name}-langfuse-ecs-"
  description = "Security group for Langfuse ECS tasks"
  vpc_id      = var.vpc_id

  ingress {
    description     = "HTTP from ALB"
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = [var.alb_security_group_id]
  }

  egress {
    description     = "PostgreSQL to RDS"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.langfuse_db.id]
  }

  egress {
    description = "HTTPS for external APIs and AWS services"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-langfuse-ecs"
  })
}

# ECR Repository
resource "aws_ecr_repository" "langfuse" {
  name                 = "${var.project_name}-langfuse"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "KMS"
    kms_key         = var.ecr_kms_key_arn
  }

  tags = var.tags
}

# ECS Task Definition
resource "aws_ecs_task_definition" "langfuse" {
  family                   = "${var.project_name}-langfuse"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn
  pid_mode                 = "task"

  container_definitions = jsonencode([{
    name  = "langfuse"
    image = "langfuse/langfuse:2"
    privileged = false
    user = "1000"

    portMappings = [{
      containerPort = 3000
      protocol      = "tcp"
    }]

    environment = [
      {
        name  = "DATABASE_URL"
        value = "postgresql://${module.langfuse_db.db_instance_username}:${urlencode(random_password.db.result)}@${module.langfuse_db.db_instance_address}:5432/langfuse"
      },
      {
        name  = "NEXTAUTH_URL"
        value = var.langfuse_url
      },
      {
        name  = "NEXTAUTH_SECRET"
        value = random_password.nextauth.result
      },
      {
        name  = "SALT"
        value = random_password.salt.result
      },
      {
        name  = "TELEMETRY_ENABLED"
        value = "false"
      },
      {
        name  = "LANGFUSE_ENABLE_EXPERIMENTAL_FEATURES"
        value = "false"
      }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.langfuse.name
        "awslogs-region"        = data.aws_region.current.name
        "awslogs-stream-prefix" = "ecs"
      }
    }

    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:3000/api/public/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])

  tags = var.tags
}

# ECS Service
resource "aws_ecs_service" "langfuse" {
  name            = "${var.project_name}-langfuse"
  cluster         = var.ecs_cluster_id
  task_definition = aws_ecs_task_definition.langfuse.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.langfuse_ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.langfuse.arn
    container_name   = "langfuse"
    container_port   = 3000
  }

  depends_on = [aws_lb_listener_rule.langfuse]

  tags = var.tags
}

# ALB Target Group
resource "aws_lb_target_group" "langfuse" {
  name        = "${var.project_name}-langfuse"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/api/public/health"
    matcher             = "200"
  }

  deregistration_delay = 30

  tags = var.tags
}

# ALB Listener Rule
resource "aws_lb_listener_rule" "langfuse" {
  listener_arn = var.alb_listener_arn
  priority     = var.listener_rule_priority

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.langfuse.arn
  }

  condition {
    path_pattern {
      values = ["/langfuse*"]
    }
  }

  tags = var.tags
}

# Port 3000 Listener for Langfuse
resource "aws_lb_listener" "langfuse_port_3000" {
  load_balancer_arn = var.alb_arn
  port              = "3000"
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }

  tags = var.tags
}

# HTTPS Listener for langfuse
resource "aws_lb_listener" "langfuse_https" {
  load_balancer_arn = var.alb_arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.langfuse.arn
  }

  tags = var.tags
}

# CloudWatch Log Group
# checkov:skip=CKV_AWS_158: Encryption with AWS-managed key is acceptable for demo environment
resource "aws_cloudwatch_log_group" "langfuse" {
  name              = "/ecs/${var.project_name}-langfuse"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

# Store secrets in SSM Parameter Store
resource "aws_ssm_parameter" "langfuse_db_password" {
  name        = "/${var.project_name}/${var.environment}/langfuse/db-password"
  description = "Langfuse database password"
  type        = "SecureString"
  value       = random_password.db.result
  key_id      = var.ssm_kms_key_id

  tags = var.tags
}

resource "aws_ssm_parameter" "langfuse_public_key" {
  name        = "/${var.project_name}/${var.environment}/langfuse/public-key"
  description = "Langfuse public API key (set after first login)"
  type        = "String"
  value       = "PLACEHOLDER_SET_AFTER_DEPLOYMENT"

  lifecycle {
    ignore_changes = [value]
  }

  tags = var.tags
}

resource "aws_ssm_parameter" "langfuse_secret_key" {
  name        = "/${var.project_name}/${var.environment}/langfuse/secret-key"
  description = "Langfuse secret API key (set after first login)"
  type        = "SecureString"
  value       = "PLACEHOLDER_SET_AFTER_DEPLOYMENT"
  key_id      = var.ssm_kms_key_id

  lifecycle {
    ignore_changes = [value]
  }

  tags = var.tags
}
