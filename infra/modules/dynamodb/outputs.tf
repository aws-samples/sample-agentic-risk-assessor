output "table_names" {
  description = "Map of DynamoDB table names"
  value       = { for k, v in aws_dynamodb_table.this : k => v.name }
}

output "table_arns" {
  description = "Map of DynamoDB table ARNs"
  value       = { for k, v in aws_dynamodb_table.this : k => v.arn }
}