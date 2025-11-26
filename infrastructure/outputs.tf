output "sqs_queue_url" {
  description = "SQS Queue URL for notifications"
  value       = var.enable_sqs ? aws_sqs_queue.nexus_notifications[0].url : null
}

output "sqs_queue_arn" {
  description = "SQS Queue ARN"
  value       = var.enable_sqs ? aws_sqs_queue.nexus_notifications[0].arn : null
}

output "dynamodb_tables" {
  description = "DynamoDB table names"
  value = var.enable_dynamodb ? {
    agent_projects         = aws_dynamodb_table.agent_projects[0].name
    agent_instances        = aws_dynamodb_table.agent_instances[0].name
    agent_invocations      = aws_dynamodb_table.agent_invocations[0].name
    agent_sessions         = aws_dynamodb_table.agent_sessions[0].name
    agent_session_messages = aws_dynamodb_table.agent_session_messages[0].name
  } : null
}

output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = var.enable_lambda ? aws_ecr_repository.nexus_ai[0].repository_url : null
}

output "efs_file_system_id" {
  description = "EFS file system ID"
  value       = var.enable_lambda ? aws_efs_file_system.lambda_efs[0].id : null
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = var.enable_lambda ? aws_lambda_function.nexus_ai[0].function_name : null
}

output "lambda_function_arn" {
  description = "Lambda function ARN"
  value       = var.enable_lambda ? aws_lambda_function.nexus_ai[0].arn : null
}

output "lambda_function_url" {
  description = "Lambda function URL"
  value       = var.enable_lambda ? aws_lambda_function_url.nexus_ai[0].function_url : null
}

output "stepfunctions_state_machine_arn" {
  description = "Step Functions state machine ARN"
  value       = var.enable_stepfunctions ? aws_sfn_state_machine.agent_build_workflow[0].arn : null
}

output "vpc_id" {
  description = "VPC ID"
  value       = var.enable_lambda ? local.vpc_id : null
}

output "region" {
  description = "AWS region"
  value       = var.aws_region
}
