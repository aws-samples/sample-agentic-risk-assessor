# Voice Services Module for AWS Transcribe and Polly
# Provides infrastructure for voice-interactive profile builder

# S3 bucket for temporary audio storage
resource "aws_s3_bucket" "voice_audio_storage" {
  bucket = "${var.project_name}-voice-audio-${random_string.bucket_suffix.result}"
  
  tags = var.tags
}

resource "random_string" "bucket_suffix" {
  length  = 8
  special = false
  upper   = false
}

# S3 bucket versioning
resource "aws_s3_bucket_versioning" "voice_audio_versioning" {
  bucket = aws_s3_bucket.voice_audio_storage.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 bucket encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "voice_audio_encryption" {
  bucket = aws_s3_bucket.voice_audio_storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.s3_kms_key_arn
    }
    bucket_key_enabled = true
  }
}

# S3 bucket lifecycle policy for temporary audio files
# checkov:skip=CKV_AWS_300: S3 lifecycle abort incomplete multipart upload not required for demo
resource "aws_s3_bucket_lifecycle_configuration" "voice_audio_lifecycle" {
  bucket = aws_s3_bucket.voice_audio_storage.id

  rule {
    id     = "voice_audio_cleanup"
    status = "Enabled"

    expiration {
      days = 7  # Delete audio files after 7 days
    }

    noncurrent_version_expiration {
      noncurrent_days = 1
    }
  }
}

# S3 bucket public access block
resource "aws_s3_bucket_public_access_block" "voice_audio_pab" {
  bucket = aws_s3_bucket.voice_audio_storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Note: CORS configuration removed - frontend receives audio via WebSocket streaming
# Frontend never accesses S3 directly, maintaining proper architecture separation

# IAM role for voice services
resource "aws_iam_role" "voice_services_role" {
  name = "${var.project_name}-voice-services-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = [
            "ecs-tasks.amazonaws.com"
          ]
        }
      }
    ]
  })

  tags = var.tags
}

# IAM policy for Transcribe access
resource "aws_iam_policy" "transcribe_policy" {
  name        = "${var.project_name}-transcribe-policy"
  description = "Policy for AWS Transcribe streaming access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "transcribe:StartStreamTranscription",
          "transcribe:StartStreamTranscriptionWebSocket"
        ]
        Resource = "*"
      }
    ]
  })

  tags = var.tags
}

# IAM policy for Polly access
resource "aws_iam_policy" "polly_policy" {
  name        = "${var.project_name}-polly-policy"
  description = "Policy for AWS Polly text-to-speech access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "polly:SynthesizeSpeech"
        ]
        Resource = "arn:aws:polly:*:*:lexicon/*"
      },
      {
        Effect = "Allow"
        Action = [
          "polly:DescribeVoices",
          "polly:GetLexicon",
          "polly:ListLexicons"
        ]
        Resource = "arn:aws:polly:${var.aws_region}:${var.aws_account_id}:*"
      }
    ]
  })

  tags = var.tags
}

# IAM policy for S3 voice audio storage access
resource "aws_iam_policy" "voice_s3_policy" {
  name        = "${var.project_name}-voice-s3-policy"
  description = "Policy for voice audio S3 bucket access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.voice_audio_storage.arn,
          "${aws_s3_bucket.voice_audio_storage.arn}/*"
        ]
      }
    ]
  })

  tags = var.tags
}

# Attach policies to the voice services role
resource "aws_iam_role_policy_attachment" "transcribe_policy_attachment" {
  role       = aws_iam_role.voice_services_role.name
  policy_arn = aws_iam_policy.transcribe_policy.arn
}

resource "aws_iam_role_policy_attachment" "polly_policy_attachment" {
  role       = aws_iam_role.voice_services_role.name
  policy_arn = aws_iam_policy.polly_policy.arn
}

resource "aws_iam_role_policy_attachment" "voice_s3_policy_attachment" {
  role       = aws_iam_role.voice_services_role.name
  policy_arn = aws_iam_policy.voice_s3_policy.arn
}

# Custom vocabulary for organization profile terms
resource "aws_transcribe_vocabulary" "organization_profile_vocabulary" {
  vocabulary_name   = "${var.project_name}-org-profile-vocab"
  language_code     = "en-US"
  
  phrases = [
    "organization-profile",
    "risk-assessment",
    "compliance-framework",
    "security-controls",
    "NIST",
    "ISO",
    "SOX",
    "PCI",
    "GDPR",
    "CCPA",
    "cybersecurity",
    "data-classification",
    "threat-landscape",
    "business-continuity",
    "incident-response",
    "vulnerability-management",
    "access-control",
    "encryption",
    "multi-factor-authentication",
    "SIEM",
    "DLP",
    "endpoint-detection",
    "cloud-security",
    "AWS",
    "Azure",
    "hybrid-cloud",
    "on-premises"
  ]

  tags = var.tags
}

# CloudWatch log group for voice services
# checkov:skip=CKV_AWS_158: Encryption with AWS-managed key is acceptable for demo environment
resource "aws_cloudwatch_log_group" "voice_services_logs" {
  name              = "/aws/voice-services/${var.project_name}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}