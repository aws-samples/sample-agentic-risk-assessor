output "langfuse_url" {
  description = "Langfuse application URL"
  value       = var.langfuse_url
}

output "langfuse_db_endpoint" {
  description = "Langfuse database endpoint"
  value       = module.langfuse_db.db_instance_endpoint
  sensitive   = true
}

output "langfuse_ecs_service_name" {
  description = "Langfuse ECS service name"
  value       = aws_ecs_service.langfuse.name
}

output "langfuse_target_group_arn" {
  description = "Langfuse ALB target group ARN"
  value       = aws_lb_target_group.langfuse.arn
}

output "langfuse_ecr_repository_url" {
  description = "Langfuse ECR repository URL"
  value       = aws_ecr_repository.langfuse.repository_url
}

output "langfuse_public_key_parameter" {
  description = "SSM parameter name for Langfuse public key"
  value       = aws_ssm_parameter.langfuse_public_key.name
}

output "langfuse_secret_key_parameter" {
  description = "SSM parameter name for Langfuse secret key"
  value       = aws_ssm_parameter.langfuse_secret_key.name
}

output "langfuse_security_group_id" {
  description = "Langfuse ECS security group ID"
  value       = aws_security_group.langfuse_ecs.id
}

# Convenient aliases for ECS module integration
output "public_key_parameter" {
  description = "SSM parameter name for Langfuse public key (alias)"
  value       = aws_ssm_parameter.langfuse_public_key.name
}

output "secret_key_parameter" {
  description = "SSM parameter name for Langfuse secret key (alias)"
  value       = aws_ssm_parameter.langfuse_secret_key.name
}
