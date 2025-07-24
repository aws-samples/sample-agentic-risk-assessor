output "cloudwatch_key_arn" {
  description = "ARN of CloudWatch Logs KMS key"
  value       = aws_kms_key.cloudwatch.arn
}

output "dynamodb_key_arn" {
  description = "ARN of DynamoDB KMS key"
  value       = aws_kms_key.dynamodb.arn
}

output "s3_key_arn" {
  description = "ARN of S3 KMS key"
  value       = aws_kms_key.s3.arn
}

output "lambda_key_arn" {
  description = "ARN of Lambda KMS key"
  value       = aws_kms_key.lambda.arn
}

output "lambda_key_id" {
  description = "ID of Lambda KMS key"
  value       = aws_kms_key.lambda.id
}

output "secrets_manager_key_arn" {
  description = "ARN of Secrets Manager KMS key"
  value       = aws_kms_key.secrets_manager.arn
}

output "secrets_manager_key_id" {
  description = "ID of Secrets Manager KMS key"
  value       = aws_kms_key.secrets_manager.id
}

output "ecr_key_arn" {
  description = "ARN of ECR KMS key"
  value       = aws_kms_key.ecr.arn
}

output "ecr_key_id" {
  description = "ID of ECR KMS key"
  value       = aws_kms_key.ecr.id
}

output "ssm_key_arn" {
  description = "ARN of SSM KMS key"
  value       = aws_kms_key.ssm.arn
}

output "ssm_key_id" {
  description = "ID of SSM KMS key"
  value       = aws_kms_key.ssm.id
}
