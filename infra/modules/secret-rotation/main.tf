# Lambda function for rotating Secrets Manager secrets
# nosemgrep: terraform.aws.security.aws-lambda-x-ray-tracing-not-active.aws-lambda-x-ray-tracing-not-active
resource "aws_lambda_function" "secret_rotation" {
  filename      = "${path.module}/lambda/secret_rotation.zip"
  function_name = "${var.project_name}-secret-rotation"
  role          = aws_iam_role.secret_rotation.arn
  handler       = "index.handler"
  runtime       = "python3.12"
  timeout       = 30
  reserved_concurrent_executions = 10

  environment {
    variables = {
      PROJECT_NAME = var.project_name
    }
  }

  kms_key_arn = var.lambda_kms_key_arn != "" ? var.lambda_kms_key_arn : null

  tags = var.tags
}

# IAM role for rotation Lambda
resource "aws_iam_role" "secret_rotation" {
  name = "${var.project_name}-secret-rotation-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = var.tags
}

# IAM policy for rotation Lambda
resource "aws_iam_role_policy" "secret_rotation" {
  name = "secret-rotation-policy"
  role = aws_iam_role.secret_rotation.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:DescribeSecret",
          "secretsmanager:GetSecretValue",
          "secretsmanager:PutSecretValue",
          "secretsmanager:UpdateSecretVersionStage"
        ]
        Resource = "arn:aws:secretsmanager:*:*:secret:*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:log-group:/aws/lambda/*"
      }
    ]
  })
}

# Lambda permission for Secrets Manager
resource "aws_lambda_permission" "secret_rotation" {
  statement_id  = "AllowSecretsManagerInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.secret_rotation.function_name
  principal     = "secretsmanager.amazonaws.com"
  source_arn    = "arn:aws:secretsmanager:${var.aws_region}:${var.aws_account_id}:secret:*"
}

output "rotation_lambda_arn" {
  description = "ARN of the secret rotation Lambda function"
  value       = aws_lambda_function.secret_rotation.arn
}
