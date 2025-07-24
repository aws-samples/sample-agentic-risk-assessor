output "cluster_id" {
  description = "ECS cluster ID"
  value       = aws_ecs_cluster.frontend.id
}

output "cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.frontend.name
}

output "service_name" {
  description = "ECS service name"
  value       = aws_ecs_service.frontend.name
}

output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = aws_ecr_repository.frontend.repository_url
}

output "task_definition_arn" {
  description = "Task definition ARN"
  value       = aws_ecs_task_definition.frontend.arn
}

output "alb_dns_name" {
  description = "ALB DNS name"
  value       = aws_lb.frontend.dns_name
}

output "alb_zone_id" {
  description = "ALB zone ID"
  value       = aws_lb.frontend.zone_id
}