#checkov:skip=CKV2_AWS_57: Automatic rotation not required for demo application. Production deployment must enable rotation with Lambda function.
resource "aws_secretsmanager_secret" "langfuse" {
  name        = "${var.project_name}/${var.environment}/langfuse"
  description = "Langfuse SaaS API keys for ${var.environment} environment"
  kms_key_id  = var.kms_key_id


  tags = var.tags
}

resource "aws_secretsmanager_secret_version" "langfuse" {
  secret_id = aws_secretsmanager_secret.langfuse.id
  secret_string = jsonencode({
    public_key = var.langfuse_public_key
    secret_key = var.langfuse_secret_key
  })
}
