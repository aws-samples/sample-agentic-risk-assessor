output "lambda_functions" {
  description = "Map of Lambda function details"
  value = {
    for k, v in aws_lambda_function.this : k => {
      arn           = v.arn
      function_name = v.function_name
      invoke_arn    = v.invoke_arn
    }
  }
}

output "lambda_function_names" {
  description = "List of Lambda function names"
  value       = [for f in aws_lambda_function.this : f.function_name]
}

output "lambda_log_groups" {
  description = "Map of CloudWatch log group names"
  value       = { for k, v in aws_cloudwatch_log_group.lambda_logs : k => v.name }
}