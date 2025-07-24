# KMS Keys for Encryption at Rest

data "aws_caller_identity" "current" {}

locals {
  kms_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow CloudWatch Logs"
        Effect = "Allow"
        Principal = {
          Service = "logs.amazonaws.com"
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:CreateGrant",
          "kms:DescribeKey"
        ]
        Resource = "*"
        Condition = {
          ArnLike = {
            "kms:EncryptionContext:aws:logs:arn" = "arn:aws:logs:*:${data.aws_caller_identity.current.account_id}:*"
          }
        }
      }
    ]
  })
}

resource "aws_kms_key" "cloudwatch" {
  description             = "${var.project_name} CloudWatch Logs encryption key"
  deletion_window_in_days = 10
  enable_key_rotation     = true
  policy                  = local.kms_policy

  tags = merge(var.tags, {
    Name = "${var.project_name}-cloudwatch-logs"
  })
}

resource "aws_kms_alias" "cloudwatch" {
  name          = "alias/${var.project_name}-cloudwatch-logs"
  target_key_id = aws_kms_key.cloudwatch.key_id
}

resource "aws_kms_key" "dynamodb" {
  description             = "${var.project_name} DynamoDB encryption key"
  deletion_window_in_days = 10
  enable_key_rotation     = true
  policy                  = local.kms_policy

  tags = merge(var.tags, {
    Name = "${var.project_name}-dynamodb"
  })
}

resource "aws_kms_alias" "dynamodb" {
  name          = "alias/${var.project_name}-dynamodb"
  target_key_id = aws_kms_key.dynamodb.key_id
}

resource "aws_kms_key" "s3" {
  description             = "${var.project_name} S3 encryption key"
  deletion_window_in_days = 10
  enable_key_rotation     = true
  policy                  = local.kms_policy

  tags = merge(var.tags, {
    Name = "${var.project_name}-s3"
  })
}

resource "aws_kms_alias" "s3" {
  name          = "alias/${var.project_name}-s3"
  target_key_id = aws_kms_key.s3.key_id
}

resource "aws_kms_key" "lambda" {
  description             = "${var.project_name} Lambda environment variables encryption key"
  deletion_window_in_days = 10
  enable_key_rotation     = true
  policy                  = local.kms_policy

  tags = merge(var.tags, {
    Name = "${var.project_name}-lambda"
  })
}

resource "aws_kms_alias" "lambda" {
  name          = "alias/${var.project_name}-lambda"
  target_key_id = aws_kms_key.lambda.key_id
}

resource "aws_kms_key" "secrets_manager" {
  description             = "${var.project_name} Secrets Manager encryption key"
  deletion_window_in_days = 10
  enable_key_rotation     = true
  policy                  = local.kms_policy

  tags = merge(var.tags, {
    Name = "${var.project_name}-secrets-manager"
  })
}

resource "aws_kms_alias" "secrets_manager" {
  name          = "alias/${var.project_name}-secrets-manager"
  target_key_id = aws_kms_key.secrets_manager.key_id
}

resource "aws_kms_key" "ecr" {
  description             = "${var.project_name} ECR encryption key"
  deletion_window_in_days = 10
  enable_key_rotation     = true
  policy                  = local.kms_policy

  tags = merge(var.tags, {
    Name = "${var.project_name}-ecr"
  })
}

resource "aws_kms_alias" "ecr" {
  name          = "alias/${var.project_name}-ecr"
  target_key_id = aws_kms_key.ecr.key_id
}

resource "aws_kms_key" "ssm" {
  description             = "${var.project_name} SSM Parameter Store encryption key"
  deletion_window_in_days = 10
  enable_key_rotation     = true
  policy                  = local.kms_policy

  tags = merge(var.tags, {
    Name = "${var.project_name}-ssm"
  })
}

resource "aws_kms_alias" "ssm" {
  name          = "alias/${var.project_name}-ssm"
  target_key_id = aws_kms_key.ssm.key_id
}
