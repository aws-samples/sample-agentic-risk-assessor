output "knowledge_base_id" {
  description = "ID of the Bedrock Knowledge Base"
  value       = aws_bedrockagent_knowledge_base.security_frameworks.id
}

output "knowledge_base_arn" {
  description = "ARN of the Bedrock Knowledge Base"
  value       = aws_bedrockagent_knowledge_base.security_frameworks.arn
}

output "opensearch_collection_arn" {
  description = "ARN of the OpenSearch Serverless collection"
  value       = aws_opensearchserverless_collection.knowledge_base.arn
}

output "opensearch_collection_endpoint" {
  description = "Endpoint of the OpenSearch Serverless collection"
  value       = aws_opensearchserverless_collection.knowledge_base.collection_endpoint
}

output "knowledge_base_role_arn" {
  description = "ARN of the Knowledge Base IAM role"
  value       = aws_iam_role.knowledge_base.arn
}

output "framework_docs_bucket_name" {
  description = "Name of the S3 bucket for framework documents"
  value       = aws_s3_bucket.framework_docs.bucket
}

output "framework_docs_bucket_arn" {
  description = "ARN of the S3 bucket for framework documents"
  value       = aws_s3_bucket.framework_docs.arn
}

output "data_source_id" {
  description = "ID of the S3 data source"
  value       = aws_bedrockagent_data_source.frameworks_s3.data_source_id
}
