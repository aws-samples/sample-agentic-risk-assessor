output "bucket_names" {
  description = "Map of S3 bucket names"
  value       = { for k, v in aws_s3_bucket.this : k => v.bucket }
}

output "bucket_arns" {
  description = "Map of S3 bucket ARNs"
  value       = { for k, v in aws_s3_bucket.this : k => v.arn }
}

output "bucket_ids" {
  description = "Map of S3 bucket IDs"
  value       = { for k, v in aws_s3_bucket.this : k => v.id }
}