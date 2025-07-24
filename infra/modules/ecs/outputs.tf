output "cluster_id" {
  description = "ECS cluster ID"
  value       = aws_ecs_cluster.this.id
}

output "cluster_arn" {
  description = "ECS cluster ARN"
  value       = aws_ecs_cluster.this.arn
}

output "ecr_repository_urls" {
  description = "Map of ECR repository URLs"
  value       = { for k, v in aws_ecr_repository.this : k => v.repository_url }
}

output "service_arns" {
  description = "Map of ECS service ARNs"
  value       = { for k, v in aws_ecs_service.this : k => v.id }
}

output "task_definition_arns" {
  description = "Map of ECS task definition ARNs"
  value       = { for k, v in aws_ecs_task_definition.this : k => v.arn }
}

output "log_group_names" {
  description = "Map of CloudWatch log group names"
  value       = { for k, v in aws_cloudwatch_log_group.this : k => v.name }
}