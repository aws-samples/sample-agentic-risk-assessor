output "lambda_exec_role_arn" {
  description = "Lambda execution role ARN"
  value       = aws_iam_role.lambda_exec.arn
}

output "ecs_task_execution_role_arn" {
  description = "ECS task execution role ARN"
  value       = aws_iam_role.ecs_task_execution.arn
}

output "ecs_task_role_arn" {
  description = "ECS task role ARN"
  value       = aws_iam_role.ecs_task.arn
}

output "step_functions_role_arn" {
  description = "Step Functions execution role ARN"
  value       = aws_iam_role.step_functions.arn
}

output "lambda_exec_role_name" {
  description = "Lambda execution role name"
  value       = aws_iam_role.lambda_exec.name
}

output "step_functions_role_name" {
  description = "Step Functions execution role name"
  value       = aws_iam_role.step_functions.name
}

output "agent_task_role_arns" {
  description = "Map of per-agent task role ARNs"
  value       = { for k, v in aws_iam_role.agent_task : k => v.arn }
}
