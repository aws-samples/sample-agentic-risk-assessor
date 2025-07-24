output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.this.id
}

output "vpc_cidr_block" {
  description = "VPC CIDR block"
  value       = aws_vpc.this.cidr_block
}

output "public_subnet_ids" {
  description = "List of public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "List of private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "internet_gateway_id" {
  description = "Internet Gateway ID"
  value       = aws_internet_gateway.this.id
}

output "nat_gateway_ids" {
  description = "List of NAT Gateway IDs"
  value       = aws_nat_gateway.this[*].id
}

output "load_balancer_arns" {
  description = "Map of load balancer ARNs"
  value       = { for k, v in aws_lb.this : k => v.arn }
}

output "load_balancer_dns_names" {
  description = "Map of load balancer DNS names"
  value       = { for k, v in aws_lb.this : k => v.dns_name }
}

output "target_group_arns" {
  description = "Map of target group ARNs"
  value       = { for k, v in aws_lb_target_group.this : k => v.arn }
}

output "listener_arns" {
  description = "Map of listener ARNs"
  value       = { for k, v in aws_lb_listener.this : k => v.arn }
}

output "security_group_ids" {
  description = "Map of security group IDs"
  value       = { for k, v in aws_security_group.this : k => v.id }
}

output "agents_alb_dns_name" {
  description = "Agents ALB DNS name (internal)"
  value       = aws_lb.agents_internal.dns_name
}

output "agents_alb_arn" {
  description = "Agents ALB ARN (internal)"
  value       = aws_lb.agents_internal.arn
}

output "agents_target_group_arns" {
  description = "Map of agents target group ARNs (internal)"
  value = {
    architect = aws_lb_target_group.architect_internal.arn
    security_architect = aws_lb_target_group.security_architect_internal.arn
    risk_assessment = aws_lb_target_group.risk_assessment_internal.arn
    auditor = aws_lb_target_group.auditor_internal.arn
    organization_profile = aws_lb_target_group.organization_profile_internal.arn
  }
}

output "agents_external_target_group_arns" {
  description = "Map of agents target group ARNs (external)"
  value = {
    architect = aws_lb_target_group.architect_external.arn
    security_architect = aws_lb_target_group.security_architect_external.arn
    risk_assessment = aws_lb_target_group.risk_assessment_external.arn
    auditor = aws_lb_target_group.auditor_external.arn
    organization_profile = aws_lb_target_group.organization_profile_external.arn
  }
}

output "db_subnet_group_name" {
  description = "Database subnet group name"
  value       = aws_db_subnet_group.this.name
}

output "agents_alb_listener_arn" {
  description = "Agents ALB listener ARN (internal)"
  value       = aws_lb_listener.agents_internal.arn
}

output "agents_alb_security_group_id" {
  description = "Agents ALB security group ID (internal)"
  value       = aws_security_group.agents_alb_internal.id
}

output "agents_alb_external_arn" {
  description = "External Agents ALB ARN"
  value       = aws_lb.agents_external.arn
}

output "agents_alb_external_dns_name" {
  description = "External Agents ALB DNS name"
  value       = aws_lb.agents_external.dns_name
}

output "agents_alb_internal_dns_name" {
  description = "Internal Agents ALB DNS name"
  value       = aws_lb.agents_internal.dns_name
}

output "alb_waf_arn" {
  description = "Frontend ALB WAF ARN"
  value       = aws_wafv2_web_acl.alb.arn
}

output "agent_security_group_ids" {
  description = "Map of per-agent security group IDs"
  value       = { for k, v in aws_security_group.agent : k => v.id }
}
