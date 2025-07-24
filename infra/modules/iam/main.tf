# Lambda execution role
resource "aws_iam_role" "lambda_exec" {
  name = "${var.project_name}-lambda-exec"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# Lambda execution policy
resource "aws_iam_policy" "lambda_exec" {
  name        = "${var.project_name}-lambda-exec"
  description = "Lambda execution policy for ${var.project_name}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat([
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.region}:${var.account_id}:log-group:/aws/lambda/${var.project_name}-*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:BatchWriteItem"
        ]
        Resource = flatten([
          for table_arn in var.dynamodb_table_arns : [
            table_arn,
            "${table_arn}/index/*"
          ]
        ])
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ]
        Resource = var.dynamodb_kms_key_arn
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ]
        Resource = var.s3_kms_key_arn
      },
      {
        # checkov:skip=CKV_AWS_111: S3 GetObject is constrained to project-specific buckets via var.s3_bucket_arns
        # semgrep:ignore terraform.lang.security.iam.no-iam-data-exfiltration.no-iam-data-exfiltration: S3 access is scoped to project buckets only, not all S3 resources
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        # Resource is constrained to specific project buckets (e.g., risk-agent-staging-diagrams, risk-agent-staging-documents)
        # This is NOT a wildcard allowing access to all S3 buckets
        Resource = flatten([
          for bucket_arn in var.s3_bucket_arns : [
            bucket_arn,
            "${bucket_arn}/*"
          ]
        ])
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "bedrock:RetrieveAndGenerate",
          "bedrock:Retrieve",
          "bedrock:GetInferenceProfile"
        ]
        Resource = [
          "arn:aws:bedrock:${var.region}::foundation-model/*",
          "arn:aws:bedrock:${var.region}:${var.account_id}:knowledge-base/*",
          "arn:aws:bedrock:*:*:foundation-model/*",
          "arn:aws:bedrock:*:*:inference-profile/*",
          "arn:aws:bedrock:*:*:application-inference-profile/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = "arn:aws:lambda:${var.region}:${var.account_id}:function:${var.project_name}-*"
      },
      {
        Effect = "Allow",
        # semgrep:ignore terraform.lang.security.iam.no-iam-creds-exposure.no-iam-creds-exposure: AssumeRole is scoped to specific project Bedrock role in same account
        Action = "sts:AssumeRole",
        # This is NOT a wildcard - it's a specific role: risk-agent-bedrock-role in the same AWS account
        Resource = "arn:aws:iam::${var.account_id}:role/${var.project_name}-bedrock-role"
      },
      {
        Effect = "Allow"
        Action = [
          "ecs:UpdateService",
          "ecs:DescribeServices",
          "ecs:DescribeClusters",
          "ecs:ListClusters"
        ]
        Resource = [
          "arn:aws:ecs:${var.region}:${var.account_id}:cluster/${var.project_name}-agents",
          "arn:aws:ecs:${var.region}:${var.account_id}:service/${var.project_name}-agents/${var.project_name}-*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ecs:ListClusters"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "states:StartExecution"
        ]
        Resource = "arn:aws:states:${var.region}:${var.account_id}:stateMachine:${var.project_name}-*"
      }
    ],
    # Conditionally add cross-account STS AssumeRole only if bedrock_role_arn is provided
    var.bedrock_role_arn != "" ? [{
      Effect = "Allow"
      Action = ["sts:AssumeRole"]
      Resource = var.bedrock_role_arn
    }] : []
    )
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "lambda_exec" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.lambda_exec.arn
}

# ECS task execution role
resource "aws_iam_role" "ecs_task_execution" {
  name = "${var.project_name}-ecs-task-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# semgrep:ignore terraform.lang.security.iam.no-iam-resource-exposure.no-iam-resource-exposure: AWS managed policy required for ECS task execution
# checkov:skip=CKV_AWS_111: AmazonECSTaskExecutionRolePolicy is AWS managed and includes ecr:GetAuthorizationToken with Resource=* which is an AWS requirement
resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  # This AWS managed policy includes ecr:GetAuthorizationToken with Resource="*"
  # This is an AWS limitation - ecr:GetAuthorizationToken REQUIRES Resource="*" per AWS documentation
  # See: https://docs.aws.amazon.com/AmazonECR/latest/userguide/security_iam_id-based-policy-examples.html
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Additional policy for ECS task execution role to access Langfuse SSM parameters
resource "aws_iam_policy" "ecs_task_execution_ssm" {
  name        = "${var.project_name}-ecs-task-execution-ssm"
  description = "Allow ECS task execution role to access Langfuse SSM parameters"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameters",
          "ssm:GetParameter"
        ]
        Resource = [
          "arn:aws:ssm:${var.region}:${var.account_id}:parameter/${var.project_name}/*/langfuse/*"
        ]
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_ssm" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = aws_iam_policy.ecs_task_execution_ssm.arn
}

# ECS task role
resource "aws_iam_role" "ecs_task" {
  name = "${var.project_name}-agents-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# Per-agent task roles with scoped secrets access
resource "aws_iam_role" "agent_task" {
  for_each = toset(var.agent_names)

  name = "${var.project_name}-${each.key}-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(var.tags, { Agent = each.key })
}

# Attach common policy to all per-agent roles
resource "aws_iam_role_policy_attachment" "agent_task_common" {
  for_each = toset(var.agent_names)

  role       = aws_iam_role.agent_task[each.key].name
  policy_arn = aws_iam_policy.ecs_task.arn
}

# Per-agent secrets policy (scoped to own secret only)
resource "aws_iam_policy" "agent_secrets" {
  for_each = toset(var.agent_names)

  name = "${var.project_name}-${each.key}-secrets"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = "arn:aws:secretsmanager:${var.region}:${var.account_id}:secret:${var.project_name}-${each.key}-client-secret-*"
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "agent_secrets" {
  for_each = toset(var.agent_names)

  role       = aws_iam_role.agent_task[each.key].name
  policy_arn = aws_iam_policy.agent_secrets[each.key].arn
}

resource "aws_iam_policy" "ecs_task" {
  name        = "${var.project_name}-agents-task-role"
  description = "ECS task policy for ${var.project_name}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat([
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = "arn:aws:lambda:${var.region}:${var.account_id}:function:${var.project_name}-*"
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          "arn:aws:bedrock:*:*:foundation-model/*",
          "arn:aws:bedrock:*:*:inference-profile/*",
          "arn:aws:bedrock:*:*:application-inference-profile/*"
        ]
        
      },
      {
        # semgrep:ignore terraform.lang.security.iam.no-iam-data-exfiltration.no-iam-data-exfiltration: S3 access is scoped to project buckets only, not all S3 resources
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        # Resource is constrained to specific project buckets (e.g., risk-agent-staging-diagrams, risk-agent-staging-voice-audio)
        # This is NOT a wildcard allowing access to all S3 buckets
        Resource = flatten([
          [for bucket_arn in var.s3_bucket_arns : [
            bucket_arn,
            "${bucket_arn}/*"
          ]],
          # Add voice audio bucket for Transcribe access
          var.voice_audio_bucket_arn != "" ? [
            var.voice_audio_bucket_arn,
            "${var.voice_audio_bucket_arn}/*"
          ] : []
        ])
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = flatten([
          [for table_arn in var.dynamodb_table_arns : table_arn],
          [for table_arn in var.dynamodb_table_arns : "${table_arn}/index/*"]
        ])
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ]
        Resource = [
          var.s3_kms_key_arn,
          var.dynamodb_kms_key_arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "polly:SynthesizeSpeech",
          "polly:DescribeVoices"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "transcribe:StartTranscriptionJob",
          "transcribe:GetTranscriptionJob",
          "transcribe:StartStreamTranscription",
          "transcribe:CreateVocabulary",
          "transcribe:GetVocabulary"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:PutObjectAcl"
        ]
        Resource = flatten([
          # Voice prefixes in existing buckets
          [for bucket_arn in var.s3_bucket_arns : "${bucket_arn}/voice-*" if !strcontains(bucket_arn, "voice-audio")],
          # Full access to dedicated voice audio bucket
          var.voice_audio_bucket_arn != "" ? ["${var.voice_audio_bucket_arn}/*"] : []
        ])
      }
    ],
    # Conditionally add cross-account STS AssumeRole only if bedrock_role_arn is provided
    var.bedrock_role_arn != "" ? [{
      Effect = "Allow"
      Action = ["sts:AssumeRole"]
      Resource = var.bedrock_role_arn
    }] : []
    )
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "ecs_task" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = aws_iam_policy.ecs_task.arn
}

# Step Functions execution role
resource "aws_iam_role" "step_functions" {
  name = "${var.project_name}-step-functions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_policy" "step_functions" {
  name        = "${var.project_name}-step-functions-policy"
  description = "Step Functions execution policy for ${var.project_name}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = "arn:aws:lambda:${var.region}:${var.account_id}:function:${var.project_name}-*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:UpdateItem"
        ]
        Resource = [
          for table_arn in var.dynamodb_table_arns : table_arn
        ]
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "step_functions" {
  role       = aws_iam_role.step_functions.name
  policy_arn = aws_iam_policy.step_functions.arn
}

# Bedrock execution role
resource "aws_iam_role" "bedrock_role" {
  name = "${var.project_name}-bedrock-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.ecs_task.arn
        }
      },
      {
        Action = "sts:AssumeRole"
        Effect = "Allow",
        Principal = {
          "AWS": "arn:aws:iam::${var.account_id}:role/${var.project_name}-lambda-exec"
      },
      
    }
    ]
  })

  tags = var.tags
}

resource "aws_iam_policy" "bedrock_role" {
  name        = "${var.project_name}-bedrock-policy"
  description = "Amazon Bedrock policy for ${var.project_name}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          "arn:aws:bedrock:*:*:inference-profile/us.anthropic.claude-*",
          "arn:aws:bedrock:*::foundation-model/anthropic.claude-*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:ListFoundationModels",
          "bedrock:GetInferenceProfile"
        ]
        Resource = "*"
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "bedrock_role" {
  role       = aws_iam_role.bedrock_role.name
  policy_arn = aws_iam_policy.bedrock_role.arn
}