output "state_machine_arn" {
  description = "ARN of the Step Functions state machine"
  value       = aws_sfn_state_machine.service_controls_mapping.arn
}

output "state_machine_name" {
  description = "Name of the Step Functions state machine"
  value       = aws_sfn_state_machine.service_controls_mapping.name
}

output "node_controls_state_machine_arn" {
  description = "ARN of the Node Controls Step Functions state machine"
  value       = aws_sfn_state_machine.node_controls_mapping.arn
}

output "node_controls_state_machine_name" {
  description = "Name of the Node Controls Step Functions state machine"
  value       = aws_sfn_state_machine.node_controls_mapping.name
}

