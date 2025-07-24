output "api_id" {
  description = "API Gateway ID"
  value       = aws_apigatewayv2_api.this.id
}

output "api_endpoint" {
  description = "API Gateway endpoint URL"
  value       = "https://${aws_apigatewayv2_api.this.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/${aws_apigatewayv2_stage.this.name}"
}

output "execution_arn" {
  description = "API Gateway execution ARN"
  value       = aws_apigatewayv2_api.this.execution_arn
}

output "vpc_link_id" {
  description = "VPC Link ID"
  value       = length(aws_apigatewayv2_vpc_link.this) > 0 ? aws_apigatewayv2_vpc_link.this[0].id : null
}

output "lambda_integration_ids" {
  description = "Lambda integration IDs"
  value       = { for k, v in aws_apigatewayv2_integration.lambda : k => v.id }
}

output "alb_integration_id" {
  description = "ALB integration ID"
  value       = length(aws_apigatewayv2_integration.alb) > 0 ? aws_apigatewayv2_integration.alb[0].id : null
}