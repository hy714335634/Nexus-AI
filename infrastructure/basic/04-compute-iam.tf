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

# Add full permissions to ECS execution role
resource "aws_iam_role_policy" "ecs_execution_full" {
  count = var.create_vpc ? 1 : 0

  name = "${var.project_name}-ecs-execution-full-${var.environment}"
  role = aws_iam_role.ecs_task_execution[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "iam:*"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:*",
          "bedrock-agentcore:*"
        ]
        Resource = "*"
      }
    ]
  })
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
          "dynamodb:BatchWriteItem",
          "dynamodb:DescribeTable",
          "dynamodb:ListTables",
          "dynamodb:CreateTable"
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
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:ListTables"
        ]
        Resource = "*"
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
      },
      {
        Effect = "Allow"
        Action = [
          "logs:*"
        ]
        Resource = "*"
      }
    ]
  })
}

# Policy for Bedrock access (including AgentCore)
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
          "bedrock:*"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock-agentcore:CreateAgent",
          "bedrock-agentcore:GetAgent",
          "bedrock-agentcore:UpdateAgent",
          "bedrock-agentcore:DeleteAgent",
          "bedrock-agentcore:ListAgents",
          "bedrock-agentcore:CreateAgentAlias",
          "bedrock-agentcore:GetAgentAlias",
          "bedrock-agentcore:UpdateAgentAlias",
          "bedrock-agentcore:ListAgentAliases",
          "bedrock-agentcore:DeleteAgentAlias",
          "bedrock-agent-runtime:InvokeAgent",
          "bedrock-agent-runtime:InvokeAgentWithResponseStream"
        ]
        Resource = "*"
      },
      {
        # AgentCore Runtime operations (for deploying agents)
        # Using "*" for Resource to allow all runtime operations
        Effect = "Allow"
        Action = [
          "bedrock-agentcore:CreateAgentRuntime",
          "bedrock-agentcore:UpdateAgentRuntime",
          "bedrock-agentcore:DeleteAgentRuntime",
          "bedrock-agentcore:GetAgentRuntime",
          "bedrock-agentcore:ListAgentRuntimes",
          "bedrock-agentcore:TagResource",
          "bedrock-agentcore:UntagResource"
        ]
        Resource = "*"
      }
    ]
  })
}

# Policy for IAM access (for AgentCore execution roles)
resource "aws_iam_role_policy" "ecs_iam_agentcore" {
  count = var.create_vpc ? 1 : 0

  name = "${var.project_name}-ecs-iam-agentcore-${var.environment}"
  role = aws_iam_role.ecs_task[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "iam:CreateRole",
          "iam:GetRole",
          "iam:UpdateRole",
          "iam:DeleteRole",
          "iam:AttachRolePolicy",
          "iam:DetachRolePolicy",
          "iam:PutRolePolicy",
          "iam:DeleteRolePolicy",
          "iam:GetRolePolicy",
          "iam:ListRolePolicies",
          "iam:ListAttachedRolePolicies",
          "iam:TagRole",
          "iam:UntagRole"
        ]
        Resource = [
          "arn:aws:iam::*:role/agentcore*",
          "arn:aws:iam::*:role/AmazonBedrockAgentCoreSDKRuntime-*",
          "arn:aws:iam::*:role/AmazonBedrockAgentCoreSDKCodeBuild-*"
        ]
      },
      {
        # PassRole permission for AgentCore execution roles
        # This allows passing roles to bedrock-agentcore.amazonaws.com service
        Effect = "Allow"
        Action = [
          "iam:PassRole"
        ]
        Resource = [
          "arn:aws:iam::*:role/agentcore*",
          "arn:aws:iam::*:role/AmazonBedrockAgentCoreSDKRuntime-*",
          "arn:aws:iam::*:role/AmazonBedrockAgentCoreSDKCodeBuild-*"
        ]
        Condition = {
          StringEquals = {
            "iam:PassedToService" = "bedrock-agentcore.amazonaws.com"
          }
        }
      },
      {
        # PassRole permission for CodeBuild execution roles
        # This allows passing CodeBuild roles to codebuild.amazonaws.com service
        # Required when creating CodeBuild projects for AgentCore ARM64 deployments
        Effect = "Allow"
        Action = [
          "iam:PassRole"
        ]
        Resource = [
          "arn:aws:iam::*:role/AmazonBedrockAgentCoreSDKCodeBuild-*"
        ]
        Condition = {
          StringEquals = {
            "iam:PassedToService" = "codebuild.amazonaws.com"
          }
        }
      },
      {
        # Full IAM permissions for Bedrock AgentCore
        Effect = "Allow"
        Action = [
          "iam:CreateServiceLinkedRole",
          "iam:GetServiceLinkedRoleDeletionStatus",
          "iam:DeleteServiceLinkedRole",
          "iam:CreateRole",
          "iam:DeleteRole",
          "iam:GetRole",
          "iam:PassRole",
          "iam:AttachRolePolicy",
          "iam:DetachRolePolicy",
          "iam:PutRolePolicy",
          "iam:DeleteRolePolicy",
          "iam:GetRolePolicy",
          "iam:ListRolePolicies",
          "iam:ListAttachedRolePolicies",
          "iam:TagRole",
          "iam:UntagRole"
        ]
        Resource = "*"
      }
    ]
  })
}

# Policy for S3 access (for AgentCore deployments and artifacts)
resource "aws_iam_role_policy" "ecs_s3" {
  count = var.create_vpc ? 1 : 0

  name = "${var.project_name}-ecs-s3-${var.environment}"
  role = aws_iam_role.ecs_task[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # Bucket management operations (for AgentCore CodeBuild sources)
        Effect = "Allow"
        Action = [
          "s3:CreateBucket",
          "s3:PutBucketPolicy",
          "s3:GetBucketPolicy",
          "s3:DeleteBucket",
          "s3:ListBucket",
          "s3:GetBucketLocation",
          "s3:GetBucketVersioning",
          "s3:PutBucketVersioning"
        ]
        Resource = [
          "arn:aws:s3:::bedrock-agentcore-codebuild-sources-*",
          "arn:aws:s3:::bedrock-agentcore-*"
        ]
      },
      {
        # Object operations (for all S3 buckets)
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:GetObjectVersion",
          "s3:PutObjectAcl",
          "s3:GetObjectAcl"
        ]
        Resource = [
          "arn:aws:s3:::*",
          "arn:aws:s3:::*/*"
        ]
      },
      {
        # List all buckets (needed for bucket operations)
        Effect = "Allow"
        Action = [
          "s3:ListAllMyBuckets"
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
          "elasticfilesystem:DescribeMountTargets",
          "elasticfilesystem:DescribeFileSystems"
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

# Policy for ECR access (for pushing images to bedrock-agentcore repositories)
# This is attached to task role as containers need to push images
resource "aws_iam_role_policy" "ecs_ecr_push" {
  count = var.create_vpc ? 1 : 0

  name = "${var.project_name}-ecs-ecr-push-${var.environment}"
  role = aws_iam_role.ecs_task[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # DescribeRepositories and CreateRepository need broader permissions
        # Support all regions for AgentCore deployments
        Effect = "Allow"
        Action = [
          "ecr:DescribeRepositories",
          "ecr:CreateRepository"
        ]
        Resource = [
          "arn:aws:ecr:*:*:repository/bedrock-agentcore-*"
        ]
      },
      {
        # Image operations on specific repositories
        # Support all regions for AgentCore deployments
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
        Resource = [
          "arn:aws:ecr:*:*:repository/bedrock-agentcore-*"
        ]
      },
      {
        # GetAuthorizationToken is a global operation, no resource restriction
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken"
        ]
        Resource = "*"
      }
    ]
  })
}

# Policy for CodeBuild access
resource "aws_iam_role_policy" "ecs_codebuild" {
  count = var.create_vpc ? 1 : 0

  name = "${var.project_name}-ecs-codebuild-${var.environment}"
  role = aws_iam_role.ecs_task[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "codebuild:*"
        ]
        Resource = "*"
      }
    ]
  })
}

# Policy for AgentCore full access (extends existing bedrock policy)
# Note: This policy uses bedrock-agentcore:* for comprehensive access
resource "aws_iam_role_policy" "ecs_agentcore_full" {
  count = var.create_vpc ? 1 : 0

  name = "${var.project_name}-ecs-agentcore-full-${var.environment}"
  role = aws_iam_role.ecs_task[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock-agentcore:*"
        ]
        Resource = "*"
      }
    ]
  })
}

# Policy for X-Ray and CloudWatch Observability (for AgentCore observability features)
resource "aws_iam_role_policy" "ecs_observability" {
  count = var.create_vpc ? 1 : 0

  name = "${var.project_name}-ecs-observability-${var.environment}"
  role = aws_iam_role.ecs_task[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # X-Ray permissions for trace segment destination configuration
        Effect = "Allow"
        Action = [
          "xray:UpdateTraceSegmentDestination",
          "xray:GetTraceSegmentDestination",
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords",
          "xray:GetSamplingRules",
          "xray:GetSamplingTargets"
        ]
        Resource = "*"
      },
      {
        # CloudWatch Logs permissions for observability delivery
        Effect = "Allow"
        Action = [
          "logs:CreateLogDelivery",
          "logs:GetLogDelivery",
          "logs:UpdateLogDelivery",
          "logs:DeleteLogDelivery",
          "logs:ListLogDeliveries",
          "logs:PutResourcePolicy",
          "logs:DescribeResourcePolicies",
          "logs:DescribeLogGroups",
          "logs:CreateLogGroup",
          "logs:PutRetentionPolicy"
        ]
        Resource = "*"
      },
      {
        # CloudWatch Logs destination permissions
        Effect = "Allow"
        Action = [
          "logs:PutDestination",
          "logs:PutDestinationPolicy",
          "logs:GetDestination",
          "logs:DeleteDestination",
          "logs:DescribeDestinations"
        ]
        Resource = "*"
      },
      {
        # CloudWatch Logs subscription filter permissions
        Effect = "Allow"
        Action = [
          "logs:PutSubscriptionFilter",
          "logs:DeleteSubscriptionFilter",
          "logs:DescribeSubscriptionFilters"
        ]
        Resource = "*"
      }
    ]
  })
}

