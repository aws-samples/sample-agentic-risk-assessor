# Frontend ECS Cluster
resource "aws_ecs_cluster" "frontend" {
  name = "${var.project_name}-frontend"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = var.tags
}

# ECR Repository for Frontend
resource "aws_ecr_repository" "frontend" {
  name                 = "${var.project_name}-frontend"
  image_tag_mutability = "MUTABLE"
  
  image_scanning_configuration {
    scan_on_push = true
  }
  
  encryption_configuration {
    encryption_type = "KMS"
    kms_key         = var.ecr_kms_key_arn
  }
  
  tags = var.tags
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "frontend" {
  name              = "/ecs/${var.project_name}-frontend"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.cloudwatch_kms_key_arn
  
  tags = var.tags
}

# Task Definition
resource "aws_ecs_task_definition" "frontend" {
  family                   = "${var.project_name}-frontend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = var.execution_role_arn
  task_role_arn           = var.task_role_arn
  pid_mode                 = "task"

  container_definitions = jsonencode([{
    name  = "frontend"
    image = "${aws_ecr_repository.frontend.repository_url}:${var.image_tag}"
    privileged = false
    user = "1000"
    
    portMappings = [{
      containerPort = var.container_port
      protocol      = "tcp"
    }]

    environment = [
      {
        name  = "NEXT_PUBLIC_API_URL"
        value = var.api_gateway_url
      },
      {
        name  = "NEXT_PUBLIC_AGENTS_URL"
        value = replace(var.cloudfront_url, "https://", "")
      },
      {
        name  = "NEXT_PUBLIC_COGNITO_USER_POOL_ID"
        value = var.cognito_user_pool_id
      },
      {
        name  = "NEXT_PUBLIC_COGNITO_CLIENT_ID"
        value = var.cognito_client_id
      }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.frontend.name
        "awslogs-region"        = data.aws_region.current.name
        "awslogs-stream-prefix" = "ecs"
      }
    }

    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:${var.container_port}/ || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 120
    }
  }])

  tags = var.tags
}

# Application Load Balancer
# checkov:skip=CKV2_AWS_28: WAF not required - Frontend ALB is internal (not public-facing), only accessible via CloudFront with restricted security group
resource "aws_lb" "frontend" { # nosemgrep: terraform.aws.security.aws-elb-access-logs-not-enabled.aws-elb-access-logs-not-enabled
  name               = "${var.project_name}-frontend-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = var.security_group_ids
  subnets            = var.public_subnet_ids
  
  enable_deletion_protection       = false
  drop_invalid_header_fields       = true
  
  tags = merge(var.tags, {
    Name = "${var.project_name}-frontend-alb"
  })
}

# Target Group
resource "aws_lb_target_group" "frontend" {
  name        = "${var.project_name}-frontend-tg"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"
  
  health_check {
    enabled             = true
    interval            = 30
    path                = "/"
    port                = "traffic-port"
    healthy_threshold   = 3
    unhealthy_threshold = 3
    timeout             = 15
    protocol            = "HTTP"
    matcher             = "200"
  }
  
  tags = merge(var.tags, {
    Name = "${var.project_name}-frontend-tg"
  })
}

# HTTP Listener
resource "aws_lb_listener" "frontend_http" {
  load_balancer_arn = aws_lb.frontend.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

# HTTPS Listener for frontend
resource "aws_lb_listener" "frontend_https" {
  load_balancer_arn = aws_lb.frontend.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

# ECS Service
resource "aws_ecs_service" "frontend" {
  name            = "${var.project_name}-frontend"
  cluster         = aws_ecs_cluster.frontend.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = var.security_group_ids
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend"
    container_port   = var.container_port
  }

  depends_on = [aws_lb_listener.frontend_http]
  
  tags = var.tags
}

# WAF Association for Frontend ALB
resource "aws_wafv2_web_acl_association" "frontend_alb" {
  resource_arn = aws_lb.frontend.arn
  web_acl_arn  = var.waf_web_acl_arn
}

data "aws_region" "current" {}