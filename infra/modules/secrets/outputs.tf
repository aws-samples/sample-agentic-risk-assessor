output "langfuse_secret_arn" {
  description = "ARN of the Langfuse secret"
  value       = aws_secretsmanager_secret.langfuse.arn
}

output "langfuse_secret_name" {
  description = "Name of the Langfuse secret"
  value       = aws_secretsmanager_secret.langfuse.name
}

output "langfuse_public_key" {
  description = "Langfuse public key from secret"
  value       = jsondecode(aws_secretsmanager_secret_version.langfuse.secret_string)["public_key"]
  sensitive   = true
}

output "langfuse_secret_key" {
  description = "Langfuse secret key from secret"
  value       = jsondecode(aws_secretsmanager_secret_version.langfuse.secret_string)["secret_key"]
  sensitive   = true
}
