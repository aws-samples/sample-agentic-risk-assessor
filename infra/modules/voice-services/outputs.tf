# Voice Services Module Outputs

output "voice_audio_bucket_name" {
  description = "Name of the S3 bucket for voice audio storage"
  value       = aws_s3_bucket.voice_audio_storage.bucket
}

output "voice_audio_bucket_arn" {
  description = "ARN of the S3 bucket for voice audio storage"
  value       = aws_s3_bucket.voice_audio_storage.arn
}

output "voice_services_role_arn" {
  description = "ARN of the IAM role for voice services"
  value       = aws_iam_role.voice_services_role.arn
}

output "voice_services_role_name" {
  description = "Name of the IAM role for voice services"
  value       = aws_iam_role.voice_services_role.name
}

output "transcribe_vocabulary_name" {
  description = "Name of the custom Transcribe vocabulary"
  value       = aws_transcribe_vocabulary.organization_profile_vocabulary.vocabulary_name
}

output "voice_services_log_group_name" {
  description = "Name of the CloudWatch log group for voice services"
  value       = aws_cloudwatch_log_group.voice_services_logs.name
}

output "transcribe_policy_arn" {
  description = "ARN of the Transcribe IAM policy"
  value       = aws_iam_policy.transcribe_policy.arn
}

output "polly_policy_arn" {
  description = "ARN of the Polly IAM policy"
  value       = aws_iam_policy.polly_policy.arn
}

output "voice_s3_policy_arn" {
  description = "ARN of the voice S3 IAM policy"
  value       = aws_iam_policy.voice_s3_policy.arn
}