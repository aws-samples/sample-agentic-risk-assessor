locals {
  s3_buckets = {
    project_images = {
      versioning = false
      encryption = true
      use_kms    = false
      lifecycle_rules = []
    }
    project_documents = {
      versioning = true
      encryption = true
      use_kms    = true
      lifecycle_rules = []
    }
    app_data = {
      versioning = false
      encryption = true
      use_kms    = true
      lifecycle_rules = []
    }
    temp_data = {
      versioning = false
      encryption = true
      use_kms    = true
      lifecycle_rules = [
        {
          id     = "cleanup_temp_data"
          status = "Enabled"
          expiration = {
            days = 7
          }
        }
      ]
    }
  }
}

# checkov:skip=CKV_AWS_21: S3 versioning not required for this application - data is regenerated and not critical for recovery
# checkov:skip=CKV_AWS_18: S3 access logging not required for demo application - adds cost and complexity
# Production deployment should enable access logging for audit compliance and security monitoring
resource "aws_s3_bucket" "this" {
  for_each = local.s3_buckets

  bucket = "${var.project_name}-${replace(each.key, "_", "-")}-${random_id.bucket_suffix[each.key].hex}"

  tags = var.tags
}

resource "random_id" "bucket_suffix" {
  for_each = local.s3_buckets

  byte_length = 4
}

# Versioning is optional and controlled per bucket via configuration
# Most buckets contain temporary/regenerable data (diagrams, documents, profiles)
# Versioning adds storage costs without significant benefit for this use case
resource "aws_s3_bucket_versioning" "this" {
  for_each = { for k, v in local.s3_buckets : k => v if v.versioning }

  bucket = aws_s3_bucket.this[each.key].id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  for_each = local.s3_buckets

  bucket = aws_s3_bucket.this[each.key].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = each.value.use_kms ? "aws:kms" : "AES256"
      kms_master_key_id = each.value.use_kms ? var.s3_kms_key_arn : null
    }
    bucket_key_enabled = each.value.use_kms
  }
}

resource "aws_s3_bucket_public_access_block" "this" {
  for_each = local.s3_buckets

  bucket = aws_s3_bucket.this[each.key].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# checkov:skip=CKV_AWS_300: S3 lifecycle abort incomplete multipart upload not required for demo
resource "aws_s3_bucket_lifecycle_configuration" "this" {
  for_each = { for k, v in local.s3_buckets : k => v if length(v.lifecycle_rules) > 0 }

  bucket = aws_s3_bucket.this[each.key].id

  dynamic "rule" {
    for_each = each.value.lifecycle_rules
    content {
      id     = rule.value.id
      status = rule.value.status

      dynamic "expiration" {
        for_each = lookup(rule.value, "expiration", null) != null ? [rule.value.expiration] : []
        content {
          days = expiration.value.days
        }
      }

      dynamic "noncurrent_version_expiration" {
        for_each = lookup(rule.value, "noncurrent_version_expiration", null) != null ? [rule.value.noncurrent_version_expiration] : []
        content {
          noncurrent_days = noncurrent_version_expiration.value.days
        }
      }
    }
  }
}