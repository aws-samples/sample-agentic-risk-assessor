variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "step_functions_role_arn" {
  description = "IAM role ARN for Step Functions execution"
  type        = string
}



variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}