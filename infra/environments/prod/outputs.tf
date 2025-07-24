output "lambda_functions" {
  description = "Lambda function details"
  value       = module.lambda.lambda_functions
}

output "dynamodb_tables" {
  description = "DynamoDB table names"
  value       = module.dynamodb.table_names
}

output "s3_buckets" {
  description = "S3 bucket names"
  value       = module.s3.bucket_names
}

output "iam_roles" {
  description = "IAM role ARNs"
  value = {
    lambda_exec_role_arn        = module.iam.lambda_exec_role_arn
    ecs_task_execution_role_arn = module.iam.ecs_task_execution_role_arn
    ecs_task_role_arn           = module.iam.ecs_task_role_arn
  }
}

output "networking" {
  description = "Networking details"
  value = {
    vpc_id                  = module.networking.vpc_id
    public_subnet_ids       = module.networking.public_subnet_ids
    private_subnet_ids      = module.networking.private_subnet_ids
    load_balancer_dns_names = module.networking.load_balancer_dns_names
    security_group_ids      = module.networking.security_group_ids
  }
}

output "ecs_cluster" {
  description = "ECS cluster details"
  value = {
    cluster_id          = module.ecs.cluster_id
    ecr_repository_urls = module.ecs.ecr_repository_urls
    service_arns        = module.ecs.service_arns
  }
}

output "api_gateway" {
  description = "API Gateway details"
  value = {
    api_id       = module.api_gateway.api_id
    api_endpoint = module.api_gateway.api_endpoint
    vpc_link_id  = module.api_gateway.vpc_link_id
  }
}

output "cognito" {
  description = "Cognito details"
  value = {
    user_pool_id  = module.cognito.user_pool_id
    client_id     = module.cognito.user_pool_client_id
    authorizer_id = module.cognito.authorizer_id
    domain_name   = module.cognito.domain_name
  }
}

output "cloudfront" {
  description = "CloudFront details"
  value = {
    distribution_id = module.cloudfront.distribution_id
    domain_name     = module.cloudfront.domain_name
    waf_web_acl_arn = module.cloudfront.waf_web_acl_arn
  }
}

output "frontend_url" {
  description = "Frontend HTTPS URL"
  value       = "https://${module.cloudfront.domain_name}"
}