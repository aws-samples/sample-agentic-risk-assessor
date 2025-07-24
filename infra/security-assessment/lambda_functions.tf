# Security Assessment Lambda Functions

# Generate Security Questions Lambda
# nosemgrep: terraform.aws.security.aws-lambda-x-ray-tracing-not-active.aws-lambda-x-ray-tracing-not-active
resource "aws_lambda_function" "generate_security_questions" {
  filename         = "../../temp/generate_security_questions.zip"
  function_name    = "risk-agent-generate-security-questions-api"
  role            = var.lambda_exec_role_arn
  handler         = "generate_security_questions.lambda_handler"
  runtime         = "python3.12"
  timeout         = 300
  memory_size     = 512
  reserved_concurrent_executions = 10

  environment {
    variables = {
      SECURITY_QUESTIONS_TABLE = aws_dynamodb_table.security_questions.name
    }
  }

  kms_key_arn = var.lambda_kms_key_arn != "" ? var.lambda_kms_key_arn : null

  depends_on = [data.archive_file.generate_security_questions_zip]
}

data "archive_file" "generate_security_questions_zip" {
  type        = "zip"
  source_file = "../../lambda/generate_security_questions.py"
  output_path = "../../temp/generate_security_questions.zip"
}

# Get Security Questions Lambda
# nosemgrep: terraform.aws.security.aws-lambda-x-ray-tracing-not-active.aws-lambda-x-ray-tracing-not-active
resource "aws_lambda_function" "get_security_questions" {
  filename         = "../../temp/get_security_questions.zip"
  function_name    = "risk-agent-get-security-questions-api"
  role            = var.lambda_exec_role_arn
  handler         = "get_security_questions.lambda_handler"
  runtime         = "python3.12"
  timeout         = 60
  memory_size     = 256
  reserved_concurrent_executions = 10

  environment {
    variables = {
      SECURITY_QUESTIONS_TABLE = aws_dynamodb_table.security_questions.name
    }
  }

  kms_key_arn = var.lambda_kms_key_arn != "" ? var.lambda_kms_key_arn : null

  depends_on = [data.archive_file.get_security_questions_zip]
}

data "archive_file" "get_security_questions_zip" {
  type        = "zip"
  source_file = "../../lambda/get_security_questions.py"
  output_path = "../../temp/get_security_questions.zip"
}

# Process Security Responses Lambda
# nosemgrep: terraform.aws.security.aws-lambda-x-ray-tracing-not-active.aws-lambda-x-ray-tracing-not-active
resource "aws_lambda_function" "process_security_responses" {
  filename         = "../../temp/process_security_responses.zip"
  function_name    = "risk-agent-process-security-responses-api"
  role            = var.lambda_exec_role_arn
  handler         = "process_security_responses.lambda_handler"
  runtime         = "python3.12"
  timeout         = 300
  memory_size     = 512
  reserved_concurrent_executions = 10

  environment {
    variables = {
      SECURITY_QUESTIONS_TABLE = aws_dynamodb_table.security_questions.name
      SECURITY_RESPONSES_TABLE = aws_dynamodb_table.security_responses.name
    }
  }

  kms_key_arn = var.lambda_kms_key_arn != "" ? var.lambda_kms_key_arn : null

  depends_on = [data.archive_file.process_security_responses_zip]
}

data "archive_file" "process_security_responses_zip" {
  type        = "zip"
  source_file = "../../lambda/process_security_responses.py"
  output_path = "../../temp/process_security_responses.zip"
}

# Perform Security Assessment Lambda
# nosemgrep: terraform.aws.security.aws-lambda-x-ray-tracing-not-active.aws-lambda-x-ray-tracing-not-active
resource "aws_lambda_function" "perform_security_assessment" {
  filename         = "../../temp/perform_security_assessment.zip"
  function_name    = "risk-agent-perform-security-assessment-api"
  role            = var.lambda_exec_role_arn
  handler         = "perform_security_assessment.lambda_handler"
  runtime         = "python3.12"
  timeout         = 600
  memory_size     = 1024
  reserved_concurrent_executions = 10

  environment {
    variables = {
      SECURITY_RESPONSES_TABLE   = aws_dynamodb_table.security_responses.name
      SECURITY_ASSESSMENTS_TABLE = aws_dynamodb_table.security_assessments.name
    }
  }

  kms_key_arn = var.lambda_kms_key_arn != "" ? var.lambda_kms_key_arn : null

  depends_on = [data.archive_file.perform_security_assessment_zip]
}

data "archive_file" "perform_security_assessment_zip" {
  type        = "zip"
  source_file = "../../lambda/perform_security_assessment.py"
  output_path = "../../temp/perform_security_assessment.zip"
}

# Get Security Assessments Lambda
# nosemgrep: terraform.aws.security.aws-lambda-x-ray-tracing-not-active.aws-lambda-x-ray-tracing-not-active
resource "aws_lambda_function" "get_security_assessments" {
  filename         = "../../temp/get_security_assessments.zip"
  function_name    = "risk-agent-get-security-assessments-api"
  role            = var.lambda_exec_role_arn
  handler         = "get_security_assessments.lambda_handler"
  runtime         = "python3.12"
  timeout         = 60
  memory_size     = 256
  reserved_concurrent_executions = 10

  environment {
    variables = {
      SECURITY_ASSESSMENTS_TABLE = aws_dynamodb_table.security_assessments.name
    }
  }

  kms_key_arn = var.lambda_kms_key_arn != "" ? var.lambda_kms_key_arn : null

  depends_on = [data.archive_file.get_security_assessments_zip]
}

data "archive_file" "get_security_assessments_zip" {
  type        = "zip"
  source_file = "../../lambda/get_security_assessments.py"
  output_path = "../../temp/get_security_assessments.zip"
}