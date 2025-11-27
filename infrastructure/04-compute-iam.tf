# ============================================
# IAM Roles for ECS Tasks
# ============================================

# ECS Task Execution Role (used by all services)
resource "aws_iam_role" "ecs_task_execution" {
  count = var.create_vpc ? 1 : 0

  name = "${var.project_name}-ecs-task-execution-${var.environment}"

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

  tags = local.common_tags
}

# Attach AWS managed policy for ECS task execution
resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  count = var.create_vpc ? 1 : 0

  role       = aws_iam_role.ecs_task_execution[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECS Task Role (for application permissions)
resource "aws_iam_role" "ecs_task" {
  count = var.create_vpc ? 1 : 0

  name = "${var.project_name}-ecs-task-${var.environment}"

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

  tags = local.common_tags
}

# Policy for DynamoDB access
resource "aws_iam_role_policy" "ecs_dynamodb" {
  count = var.create_vpc && var.enable_dynamodb ? 1 : 0

  name = "${var.project_name}-ecs-dynamodb-${var.environment}"
  role = aws_iam_role.ecs_task[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem"
        ]
        Resource = [
          var.enable_dynamodb ? aws_dynamodb_table.agent_projects[0].arn : "*",
          var.enable_dynamodb ? "${aws_dynamodb_table.agent_projects[0].arn}/index/*" : "*",
          var.enable_dynamodb ? aws_dynamodb_table.agent_instances[0].arn : "*",
          var.enable_dynamodb ? "${aws_dynamodb_table.agent_instances[0].arn}/index/*" : "*",
          var.enable_dynamodb ? aws_dynamodb_table.agent_invocations[0].arn : "*",
          var.enable_dynamodb ? "${aws_dynamodb_table.agent_invocations[0].arn}/index/*" : "*",
          var.enable_dynamodb ? aws_dynamodb_table.agent_sessions[0].arn : "*",
          var.enable_dynamodb ? "${aws_dynamodb_table.agent_sessions[0].arn}/index/*" : "*",
          var.enable_dynamodb ? aws_dynamodb_table.agent_session_messages[0].arn : "*",
          var.enable_dynamodb ? "${aws_dynamodb_table.agent_session_messages[0].arn}/index/*" : "*"
        ]
      }
    ]
  })
}

# Policy for SQS access
resource "aws_iam_role_policy" "ecs_sqs" {
  count = var.create_vpc && var.enable_sqs ? 1 : 0

  name = "${var.project_name}-ecs-sqs-${var.environment}"
  role = aws_iam_role.ecs_task[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:ChangeMessageVisibility"
        ]
        Resource = var.enable_sqs ? aws_sqs_queue.nexus_notifications[0].arn : "*"
      }
    ]
  })
}

# Policy for Bedrock access
resource "aws_iam_role_policy" "ecs_bedrock" {
  count = var.create_vpc ? 1 : 0

  name = "${var.project_name}-ecs-bedrock-${var.environment}"
  role = aws_iam_role.ecs_task[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "*"
      }
    ]
  })
}

# Policy for EFS access
resource "aws_iam_role_policy" "ecs_efs" {
  count = var.create_vpc ? 1 : 0

  name = "${var.project_name}-ecs-efs-${var.environment}"
  role = aws_iam_role.ecs_task[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "elasticfilesystem:ClientMount",
          "elasticfilesystem:ClientWrite",
          "elasticfilesystem:ClientRootAccess",
          "elasticfilesystem:DescribeMountTargets"
        ]
        Resource = var.create_vpc ? aws_efs_file_system.nexus_ai[0].arn : "*"
      }
    ]
  })
}

# Policy for ECR access (for pulling images)
resource "aws_iam_role_policy" "ecs_ecr" {
  count = var.create_vpc ? 1 : 0

  name = "${var.project_name}-ecs-ecr-${var.environment}"
  role = aws_iam_role.ecs_task_execution[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = "*"
      }
    ]
  })
}

