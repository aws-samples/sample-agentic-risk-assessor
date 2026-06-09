# VPC
resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(var.tags, {
    Name = "${var.project_name}-vpc"
  })
}

# Internet Gateway
resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = merge(var.tags, {
    Name = "${var.project_name}-igw"
  })
}

# Public Subnets
# Public subnets for external ALB and NAT Gateway
# checkov:skip=CKV_AWS_130:Public subnets must auto-assign IPs for internet-facing resources
resource "aws_subnet" "public" {
  count = length(var.public_subnet_cidrs)

  vpc_id                  = aws_vpc.this.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = merge(var.tags, {
    Name = "${var.project_name}-public-subnet-${count.index + 1}"
    Type = "Public"
  })
}

# Private Subnets
resource "aws_subnet" "private" {
  count = length(var.private_subnet_cidrs)

  vpc_id            = aws_vpc.this.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = merge(var.tags, {
    Name = "${var.project_name}-private-subnet-${count.index + 1}"
    Type = "Private"
  })
}

# NAT Gateways
resource "aws_eip" "nat" {
  count = var.enable_nat_gateway ? length(var.public_subnet_cidrs) : 0

  domain = "vpc"
  depends_on = [aws_internet_gateway.this]

  tags = merge(var.tags, {
    Name = "${var.project_name}-nat-eip-${count.index + 1}"
  })
}

resource "aws_nat_gateway" "this" {
  count = var.enable_nat_gateway ? length(var.public_subnet_cidrs) : 0

  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = merge(var.tags, {
    Name = "${var.project_name}-nat-gateway-${count.index + 1}"
  })

  depends_on = [aws_internet_gateway.this]
}

# Route Tables
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-public-rt"
  })
}

resource "aws_route_table" "private" {
  count = var.enable_nat_gateway ? length(var.private_subnet_cidrs) : 1

  vpc_id = aws_vpc.this.id

  dynamic "route" {
    for_each = var.enable_nat_gateway ? [1] : []
    content {
      cidr_block     = "0.0.0.0/0"
      nat_gateway_id = aws_nat_gateway.this[count.index].id
    }
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-private-rt-${count.index + 1}"
  })
}

# Route Table Associations
resource "aws_route_table_association" "public" {
  count = length(aws_subnet.public)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count = length(aws_subnet.private)

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = var.enable_nat_gateway ? aws_route_table.private[count.index].id : aws_route_table.private[0].id
}

# Application Load Balancer
# checkov:skip=CKV2_AWS_61: ALB access logging not required for demo application - adds cost and storage complexity
# A full deployment should enable access logs for security monitoring and compliance
resource "aws_lb" "this" {
  for_each = var.load_balancers

  name               = "${var.project_name}-${each.key}-alb"
  internal           = each.value.internal
  load_balancer_type = "application"
  security_groups    = [for sg_key in each.value.security_group_ids : aws_security_group.this[sg_key].id]
  subnets            = each.value.internal ? aws_subnet.private[*].id : aws_subnet.public[*].id

  enable_deletion_protection       = each.value.enable_deletion_protection
  drop_invalid_header_fields       = true  # Security: Drop invalid HTTP headers

  tags = merge(var.tags, {
    Name = "${var.project_name}-${each.key}-alb"
    Type = each.key
  })
}

# Target Groups
resource "aws_lb_target_group" "this" {
  for_each = var.target_groups

  name        = "${var.project_name}-${replace(each.key, "_", "-")}-tg"
  port        = each.value.port
  protocol    = each.value.protocol
  vpc_id      = aws_vpc.this.id
  target_type = each.value.target_type

  health_check {
    enabled             = true
    healthy_threshold   = each.value.health_check.healthy_threshold
    interval            = each.value.health_check.interval
    matcher             = each.value.health_check.matcher
    path                = each.value.health_check.path
    port                = "traffic-port"
    protocol            = each.value.health_check.protocol
    timeout             = each.value.health_check.timeout
    unhealthy_threshold = each.value.health_check.unhealthy_threshold
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-${replace(each.key, "_", "-")}-tg"
  })
}

# Load Balancer Listeners
resource "aws_lb_listener" "this" {
  for_each = var.listeners

  load_balancer_arn = aws_lb.this[each.value.load_balancer_key].arn
  port              = each.value.port
  protocol          = each.value.protocol

  dynamic "default_action" {
    for_each = each.value.default_actions
    content {
      type             = default_action.value.type
      target_group_arn = default_action.value.type == "forward" ? aws_lb_target_group.this[default_action.value.target_group_key].arn : null

      dynamic "fixed_response" {
        for_each = default_action.value.type == "fixed-response" ? [default_action.value.fixed_response] : []
        content {
          content_type = fixed_response.value.content_type
          message_body = fixed_response.value.message_body
          status_code  = fixed_response.value.status_code
        }
      }
    }
  }

  tags = var.tags
}

# Security Groups
locals {
  security_groups = {
    frontend = {
      description = "Security group for frontend ECS tasks"
      ingress_rules = [
        {
          from_port   = 3000
          to_port     = 3000
          protocol    = "tcp"
          cidr_blocks = ["0.0.0.0/0"]
        },
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
    agents = {
      description = "Security group for agent ECS tasks (shared - legacy)"
      ingress_rules = [
        {
          from_port   = 9000
          to_port     = 9010
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
  }
}

resource "aws_security_group" "this" {
  for_each = local.security_groups

  name_prefix = "${var.project_name}-${each.key}-"
  vpc_id      = aws_vpc.this.id
  description = each.value.description

  dynamic "ingress" {
    for_each = each.value.ingress_rules
    content {
      from_port       = ingress.value.from_port
      to_port         = ingress.value.to_port
      protocol        = ingress.value.protocol
      cidr_blocks     = lookup(ingress.value, "cidr_blocks", null)
      security_groups = lookup(ingress.value, "security_groups", null)
    }
  }

  dynamic "egress" {
    for_each = each.value.egress_rules
    content {
      from_port   = egress.value.from_port
      to_port     = egress.value.to_port
      protocol    = egress.value.protocol
      cidr_blocks = egress.value.cidr_blocks
    }
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-${each.key}-sg"
  })
}

# checkov:skip=CKV2_AWS_61: ALB access logging not required for demo application - adds cost and storage complexity
# A full deployment should enable access logs for security monitoring and compliance
# Agents ALB (from backup configuration)
# Internal Agents ALB (for agent-to-agent communication)
resource "aws_lb" "agents_internal" {
  name               = "${var.project_name}-agents-int-alb"
  internal           = true
  load_balancer_type = "application"
  security_groups    = [aws_security_group.agents_alb_internal.id]
  subnets            = aws_subnet.private[*].id
  
  enable_deletion_protection       = false
  drop_invalid_header_fields       = true
  idle_timeout                     = 900
  
  tags = merge(var.tags, {
    Name = "${var.project_name}-agents-internal-alb"
  })
}

# External Agents ALB (for CloudFront access)
resource "aws_lb" "agents_external" {
  name               = "${var.project_name}-agents-ext-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.agents_alb_external.id]
  subnets            = aws_subnet.public[*].id
  
  enable_deletion_protection       = false
  drop_invalid_header_fields       = true
  idle_timeout                     = 900
  
  tags = merge(var.tags, {
    Name = "${var.project_name}-agents-external-alb"
  })
}

# Internal Agents ALB Security Group
# checkov:skip=CKV_AWS_382:ALB requires broad egress to route to multiple ECS tasks across different ports
resource "aws_security_group" "agents_alb_internal" {
  name_prefix = "${var.project_name}-agents-int-alb-"
  vpc_id      = aws_vpc.this.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.this.cidr_block]
    description = "HTTP from VPC only"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-agents-internal-alb-sg"
  })
}

# External Agents ALB Security Group
# checkov:skip=CKV_AWS_382:ALB requires broad egress to route to multiple ECS tasks, access controlled by WAF
resource "aws_security_group" "agents_alb_external" {
  name_prefix = "${var.project_name}-agents-ext-alb-"
  vpc_id      = aws_vpc.this.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-agents-external-alb-sg"
  })
}

# Per-agent security groups (Mitigation #12)
# Each agent only accepts inbound from ALBs on its specific port
locals {
  agent_ports = {
    orchestrator         = 9001
    architect            = 9002
    security-architect   = 9004
    risk-assessment      = 9005
    auditor              = 9006
    organization-profile = 9007
  }
}

resource "aws_security_group" "agent" {
  for_each = local.agent_ports

  name_prefix = "${var.project_name}-${each.key}-"
  vpc_id      = aws_vpc.this.id
  description = "Security group for ${each.key} agent - port ${each.value} only"

  # Accept traffic only from internal and external ALBs on agent's specific port
  ingress {
    from_port       = each.value
    to_port         = each.value
    protocol        = "tcp"
    security_groups = [aws_security_group.agents_alb_internal.id, aws_security_group.agents_alb_external.id]
    description     = "From ALBs only on port ${each.value}"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-${each.key}-sg"
  })
}

# Agents Target Groups
# Internal ALB Target Groups
resource "aws_lb_target_group" "architect_internal" {
  name        = "${var.project_name}-architect-int-tg"
  port        = 9002
  protocol    = "HTTP"
  vpc_id      = aws_vpc.this.id
  target_type = "ip"
  
  health_check {
    enabled             = true
    interval            = 60
    path                = "/health"
    port                = "traffic-port"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 30
    protocol            = "HTTP"
    matcher             = "200"
  }
  
  tags = merge(var.tags, {
    Name = "${var.project_name}-architect-internal-tg"
  })
}

# External ALB Target Groups
resource "aws_lb_target_group" "architect_external" {
  name        = "${var.project_name}-architect-ext-tg"
  port        = 9002
  protocol    = "HTTP"
  vpc_id      = aws_vpc.this.id
  target_type = "ip"
  
  health_check {
    enabled             = true
    interval            = 60
    path                = "/health"
    port                = "traffic-port"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 30
    protocol            = "HTTP"
    matcher             = "200"
  }
  
  tags = merge(var.tags, {
    Name = "${var.project_name}-architect-external-tg"
  })
}

resource "aws_lb_target_group" "security_architect_internal" {
  name        = "${var.project_name}-sec-arch-int-tg"
  port        = 9004
  protocol    = "HTTP"
  vpc_id      = aws_vpc.this.id
  target_type = "ip"
  
  health_check {
    enabled             = true
    interval            = 30
    path                = "/health"
    port                = "traffic-port"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 15
    protocol            = "HTTP"
    matcher             = "200"
  }
  
  tags = merge(var.tags, {
    Name = "${var.project_name}-security-architect-internal-tg"
  })
}

resource "aws_lb_target_group" "security_architect_external" {
  name        = "${var.project_name}-sec-arch-ext-tg"
  port        = 9004
  protocol    = "HTTP"
  vpc_id      = aws_vpc.this.id
  target_type = "ip"
  
  health_check {
    enabled             = true
    interval            = 30
    path                = "/health"
    port                = "traffic-port"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 15
    protocol            = "HTTP"
    matcher             = "200"
  }
  
  tags = merge(var.tags, {
    Name = "${var.project_name}-security-architect-external-tg"
  })
}

resource "aws_lb_target_group" "risk_assessment_internal" {
  name        = "${var.project_name}-risk-assess-int-tg"
  port        = 9005
  protocol    = "HTTP"
  vpc_id      = aws_vpc.this.id
  target_type = "ip"
  
  health_check {
    enabled             = true
    interval            = 60
    path                = "/health"
    port                = "traffic-port"
    healthy_threshold   = 2
    unhealthy_threshold = 5
    timeout             = 30
    protocol            = "HTTP"
    matcher             = "200"
  }
  
  tags = merge(var.tags, {
    Name = "${var.project_name}-risk-assessment-internal-tg"
  })
}

resource "aws_lb_target_group" "risk_assessment_external" {
  name        = "${var.project_name}-risk-assess-ext-tg"
  port        = 9005
  protocol    = "HTTP"
  vpc_id      = aws_vpc.this.id
  target_type = "ip"
  
  health_check {
    enabled             = true
    interval            = 60
    path                = "/health"
    port                = "traffic-port"
    healthy_threshold   = 2
    unhealthy_threshold = 5
    timeout             = 30
    protocol            = "HTTP"
    matcher             = "200"
  }
  
  tags = merge(var.tags, {
    Name = "${var.project_name}-risk-assessment-external-tg"
  })
}

resource "aws_lb_target_group" "auditor_internal" {
  name        = "${var.project_name}-auditor-int-tg"
  port        = 9006
  protocol    = "HTTP"
  vpc_id      = aws_vpc.this.id
  target_type = "ip"
  
  health_check {
    enabled             = true
    interval            = 30
    path                = "/health"
    port                = "traffic-port"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 15
    protocol            = "HTTP"
    matcher             = "200"
  }
  
  tags = merge(var.tags, {
    Name = "${var.project_name}-auditor-internal-tg"
  })
}

resource "aws_lb_target_group" "auditor_external" {
  name        = "${var.project_name}-auditor-ext-tg"
  port        = 9006
  protocol    = "HTTP"
  vpc_id      = aws_vpc.this.id
  target_type = "ip"
  
  health_check {
    enabled             = true
    interval            = 30
    path                = "/health"
    port                = "traffic-port"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 15
    protocol            = "HTTP"
    matcher             = "200"
  }
  
  tags = merge(var.tags, {
    Name = "${var.project_name}-auditor-external-tg"
  })
}

resource "aws_lb_target_group" "organization_profile_internal" {
  name        = "${var.project_name}-org-prof-int-tg"
  port        = 9007
  protocol    = "HTTP"
  vpc_id      = aws_vpc.this.id
  target_type = "ip"
  
  health_check {
    enabled             = true
    interval            = 30
    path                = "/health"
    port                = "traffic-port"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 15
    protocol            = "HTTP"
    matcher             = "200"
  }
  
  tags = merge(var.tags, {
    Name = "${var.project_name}-organization-profile-internal-tg"
  })
}

resource "aws_lb_target_group" "organization_profile_external" {
  name        = "${var.project_name}-org-prof-ext-tg"
  port        = 9007
  protocol    = "HTTP"
  vpc_id      = aws_vpc.this.id
  target_type = "ip"
  
  health_check {
    enabled             = true
    interval            = 30
    path                = "/health"
    port                = "traffic-port"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 15
    protocol            = "HTTP"
    matcher             = "200"
  }
  
  tags = merge(var.tags, {
    Name = "${var.project_name}-org-profile-tg"
  })
}

# Internal Agents ALB Listener (HTTP — TLS not possible without public domain for ACM validation)
# Risk accepted: traffic is VPC-internal only, SG restricts to VPC CIDR
resource "aws_lb_listener" "agents_internal" {
  load_balancer_arn = aws_lb.agents_internal.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "text/plain"
      message_body = "RiskAgent Internal Agents ALB"
      status_code  = "200"
    }
  }
}

# External Agents ALB Listener
resource "aws_lb_listener" "agents_external" {
  load_balancer_arn = aws_lb.agents_external.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "text/plain"
      message_body = "RiskAgent External Agents ALB"
      status_code  = "200"
    }
  }
}

# Listener rules for each agent (internal)
resource "aws_lb_listener_rule" "architect_internal" {
  listener_arn = aws_lb_listener.agents_internal.arn
  priority     = 200

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.architect_internal.arn
  }

  condition {
    path_pattern {
      values = ["/architect/*", "/architect"]
    }
  }
}

# Listener rules for each agent (external)
resource "aws_lb_listener_rule" "architect_external" {
  listener_arn = aws_lb_listener.agents_external.arn
  priority     = 200

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.architect_external.arn
  }

  condition {
    path_pattern {
      values = ["/architect/*", "/architect"]
    }
  }
}

resource "aws_lb_listener_rule" "security_architect_internal" {
  listener_arn = aws_lb_listener.agents_internal.arn
  priority     = 400

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.security_architect_internal.arn
  }

  condition {
    path_pattern {
      values = ["/security-architect/*", "/security-architect"]
    }
  }
}

resource "aws_lb_listener_rule" "security_architect_external" {
  listener_arn = aws_lb_listener.agents_external.arn
  priority     = 400

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.security_architect_external.arn
  }

  condition {
    path_pattern {
      values = ["/security-architect/*", "/security-architect"]
    }
  }
}

resource "aws_lb_listener_rule" "risk_assessment_internal" {
  listener_arn = aws_lb_listener.agents_internal.arn
  priority     = 500

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.risk_assessment_internal.arn
  }

  condition {
    path_pattern {
      values = ["/risk-assessment/*", "/risk-assessment"]
    }
  }
}

resource "aws_lb_listener_rule" "risk_assessment_external" {
  listener_arn = aws_lb_listener.agents_external.arn
  priority     = 500

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.risk_assessment_external.arn
  }

  condition {
    path_pattern {
      values = ["/risk-assessment/*", "/risk-assessment"]
    }
  }
}

resource "aws_lb_listener_rule" "auditor_internal" {
  listener_arn = aws_lb_listener.agents_internal.arn
  priority     = 600

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.auditor_internal.arn
  }

  condition {
    path_pattern {
      values = ["/auditor/*", "/auditor"]
    }
  }
}

resource "aws_lb_listener_rule" "auditor_external" {
  listener_arn = aws_lb_listener.agents_external.arn
  priority     = 600

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.auditor_external.arn
  }

  condition {
    path_pattern {
      values = ["/auditor/*", "/auditor"]
    }
  }
}

resource "aws_lb_listener_rule" "organization_profile_internal" {
  listener_arn = aws_lb_listener.agents_internal.arn
  priority     = 700

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.organization_profile_internal.arn
  }

  condition {
    path_pattern {
      values = ["/organization_profile/*", "/organization_profile"]
    }
  }
}

resource "aws_lb_listener_rule" "organization_profile_external" {
  listener_arn = aws_lb_listener.agents_external.arn
  priority     = 700

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.organization_profile_external.arn
  }

  condition {
    path_pattern {
      values = ["/organization_profile/*", "/organization_profile"]
    }
  }
}

resource "aws_lb_listener_rule" "voice_api_internal" {
  listener_arn = aws_lb_listener.agents_internal.arn
  priority     = 701

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.organization_profile_internal.arn
  }

  condition {
    path_pattern {
      values = ["/api/voice/*"]
    }
  }
}

resource "aws_lb_listener_rule" "voice_api_external" {
  listener_arn = aws_lb_listener.agents_external.arn
  priority     = 701

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.organization_profile_external.arn
  }

  condition {
    path_pattern {
      values = ["/api/voice/*"]
    }
  }
}

# DB Subnet Group for RDS
resource "aws_db_subnet_group" "this" {
  name       = "${var.project_name}-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = merge(var.tags, {
    Name = "${var.project_name}-db-subnet-group"
  })
}

# WAF IP Set for VPC CIDR
resource "aws_wafv2_ip_set" "vpc_cidr" {
  name               = "${var.project_name}-vpc-cidr"
  scope              = "REGIONAL"
  ip_address_version = "IPV4"
  addresses          = [var.vpc_cidr]

  tags = var.tags
}

# WAF Web ACL for Frontend ALB
resource "aws_wafv2_web_acl" "alb" {
  name  = "${var.project_name}-alb-waf"
  scope = "REGIONAL"

  default_action {
    block {}
  }

  # Rule 1: Allow CloudFront traffic with custom header
  rule {
    name     = "AllowCloudFrontTraffic"
    priority = 1

    action {
      allow {}
    }

    statement {
      byte_match_statement {
        search_string         = var.cloudfront_custom_header_value
        field_to_match {
          single_header {
            name = var.cloudfront_custom_header_name
          }
        }
        text_transformation {
          priority = 0
          type     = "NONE"
        }
        positional_constraint = "EXACTLY"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AllowCloudFrontTraffic"
      sampled_requests_enabled   = true
    }
  }

  # Rule 2: Allow VPC traffic for health checks
  rule {
    name     = "AllowVPCTraffic"
    priority = 2

    action {
      allow {}
    }

    statement {
      ip_set_reference_statement {
        arn = aws_wafv2_ip_set.vpc_cidr.arn
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AllowVPCTraffic"
      sampled_requests_enabled   = true
    }
  }

  # Rule 3: AWS Managed Rules - Core Rule Set
  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 3

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesCommonRuleSet"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesCommonRuleSet"
      sampled_requests_enabled   = true
    }
  }

  # Rule 4: AWS Managed Rules - Known Bad Inputs
  rule {
    name     = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 4

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesKnownBadInputsRuleSet"
      sampled_requests_enabled   = true
    }
  }

  # Rule 5: Rate limiting
  rule {
    name     = "RateLimitRule"
    priority = 5

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "RateLimitRule"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.project_name}-waf"
    sampled_requests_enabled   = true
  }

  tags = var.tags
}

data "aws_availability_zones" "available" {
  state = "available"
}