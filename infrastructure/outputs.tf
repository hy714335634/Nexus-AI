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


output "region" {
  description = "AWS region"
  value       = var.aws_region
}

# ECS Outputs
output "ecs_cluster_name" {
  description = "ECS Cluster name"
  value       = var.create_vpc ? aws_ecs_cluster.nexus_ai[0].name : null
}

output "ecr_repositories" {
  description = "ECR repository URLs"
  value = var.create_vpc ? {
    api          = aws_ecr_repository.api.repository_url
    frontend     = aws_ecr_repository.frontend.repository_url
    celery_worker = aws_ecr_repository.celery_worker.repository_url
  } : null
}

output "alb_dns_name" {
  description = "Application Load Balancer DNS name"
  value       = var.create_vpc ? aws_lb.nexus_ai[0].dns_name : null
}

output "alb_zone_id" {
  description = "Application Load Balancer zone ID"
  value       = var.create_vpc ? aws_lb.nexus_ai[0].zone_id : null
}

output "efs_file_system_id" {
  description = "EFS file system ID"
  value       = var.create_vpc ? aws_efs_file_system.nexus_ai[0].id : null
}

output "vpc_id" {
  description = "VPC ID"
  value       = var.create_vpc ? local.vpc_id : null
}

output "private_subnets" {
  description = "Private subnet IDs"
  value       = var.create_vpc ? local.private_subnets : []
}

output "public_subnets" {
  description = "Public subnet IDs"
  value       = var.create_vpc ? local.public_subnets : []
}
