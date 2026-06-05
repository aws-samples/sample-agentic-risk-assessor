# Bedrock Knowledge Base Outputs
output "knowledge_base_id" {
  description = "ID of the Bedrock Knowledge Base"
  value       = module.bedrock_knowledge_base.knowledge_base_id
}

output "knowledge_base_arn" {
  description = "ARN of the Bedrock Knowledge Base"
  value       = module.bedrock_knowledge_base.knowledge_base_arn
}

output "api_gateway_endpoint" {
  description = "API Gateway endpoint URL"
  value       = module.api_gateway.api_endpoint
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name (HTTPS frontend URL)"
  value       = module.cloudfront.distribution_domain_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = module.cloudfront.distribution_id
}

output "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  value       = module.cognito.user_pool_id
}

output "cognito_client_id" {
  description = "Cognito User Pool Client ID"
  value       = module.cognito.user_pool_client_id
}

output "federated_sso_enabled" {
  description = "Whether Federated SSO authentication is enabled"
  value       = module.cognito.federated_sso_enabled
}

output "cognito_domain_url" {
  description = "Full Cognito domain URL for OAuth flows"
  value       = module.cognito.cognito_domain_url
}

output "vpc_id" {
  description = "VPC ID"
  value       = module.networking.vpc_id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = module.networking.private_subnet_ids
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = module.networking.public_subnet_ids
}

output "lambda_function_names" {
  description = "Map of Lambda function names"
  value       = module.lambda.lambda_function_names
}

output "dynamodb_table_names" {
  description = "Map of DynamoDB table names"
  value       = module.dynamodb.table_names
}

output "s3_bucket_names" {
  description = "Map of S3 bucket names"
  value       = module.s3.bucket_names
}

output "agents_cluster_id" {
  description = "ECS cluster ID for agents"
  value       = module.ecs.cluster_id
}

output "frontend_cluster_id" {
  description = "ECS cluster ID for frontend"
  value       = module.frontend.cluster_id
}

output "frontend_ecr_repository_url" {
  description = "ECR repository URL for frontend"
  value       = module.frontend.ecr_repository_url
}

output "frontend_alb_dns_name" {
  description = "Frontend ALB DNS name"
  value       = module.frontend.alb_dns_name
}

output "agents_alb_dns_name" {
  description = "Agents ALB DNS name"
  value       = module.networking.agents_alb_dns_name
}

# Langfuse outputs - DISABLED: Migrated to SaaS



# Voice Services outputs
output "voice_audio_bucket_name" {
  description = "S3 bucket name for voice audio storage"
  value       = module.voice_services.voice_audio_bucket_name
}

output "voice_services_role_arn" {
  description = "IAM role ARN for voice services"
  value       = module.voice_services.voice_services_role_arn
}

output "transcribe_vocabulary_name" {
  description = "AWS Transcribe custom vocabulary name"
  value       = module.voice_services.transcribe_vocabulary_name
}

# SaaS Langfuse outputs


output "knowledge_base_bucket_name" {
  description = "S3 bucket for Knowledge Base framework documents"
  value       = module.bedrock_knowledge_base.framework_docs_bucket_name
}

output "knowledge_base_data_source_id" {
  description = "Knowledge Base data source ID"
  value       = module.bedrock_knowledge_base.data_source_id
}
