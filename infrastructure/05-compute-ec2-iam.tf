# ============================================
# IAM Role for EC2 API Service
# ============================================

# EC2 Instance Role
resource "aws_iam_role" "ec2_api" {
  count = var.create_vpc && var.api_deploy_on_ec2 ? 1 : 0

  name = "${var.project_name}-ec2-api-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

# Attach AWS managed policy for EC2 instance
resource "aws_iam_role_policy_attachment" "ec2_ssm" {
  count = var.create_vpc && var.api_deploy_on_ec2 ? 1 : 0

  role       = aws_iam_role.ec2_api[0].name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Comprehensive IAM Policy for EC2 API Service (merged all policies into one)
# This reduces policy count from 9+ to 1, avoiding potential IAM policy limits
# Added DescribeTable permission for DynamoDB connection validation
resource "aws_iam_role_policy" "ec2_api_comprehensive" {
  count = var.create_vpc && var.api_deploy_on_ec2 ? 1 : 0

  name = "${var.project_name}-ec2-api-comprehensive-${var.environment}"
  role = aws_iam_role.ec2_api[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = flatten([
      # DynamoDB access (with DescribeTable for connection validation)
      var.enable_dynamodb ? [
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
            "dynamodb:DescribeTable"
          ]
          Resource = [
            aws_dynamodb_table.agent_projects[0].arn,
            "${aws_dynamodb_table.agent_projects[0].arn}/index/*",
            aws_dynamodb_table.agent_instances[0].arn,
            "${aws_dynamodb_table.agent_instances[0].arn}/index/*",
            aws_dynamodb_table.agent_invocations[0].arn,
            "${aws_dynamodb_table.agent_invocations[0].arn}/index/*",
            aws_dynamodb_table.agent_sessions[0].arn,
            "${aws_dynamodb_table.agent_sessions[0].arn}/index/*",
            aws_dynamodb_table.agent_session_messages[0].arn,
            "${aws_dynamodb_table.agent_session_messages[0].arn}/index/*"
          ]
        }
      ] : [],
      # DynamoDB ListTables (required for health checks)
      var.enable_dynamodb ? [
        {
          Effect = "Allow"
          Action = ["dynamodb:ListTables"]
          Resource = "*"
        }
      ] : [],
      # SQS access
      var.enable_sqs ? [
        {
          Effect = "Allow"
          Action = [
            "sqs:SendMessage",
            "sqs:ReceiveMessage",
            "sqs:DeleteMessage",
            "sqs:GetQueueAttributes",
            "sqs:ChangeMessageVisibility"
          ]
          Resource = aws_sqs_queue.nexus_notifications[0].arn
        }
      ] : [],
      # Bedrock access
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "bedrock:ListFoundationModels",
          "bedrock:GetFoundationModel"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock-agentcore:CreateAgentRuntime",
          "bedrock-agentcore:GetAgentRuntime",
          "bedrock-agentcore:UpdateAgentRuntime",
          "bedrock-agentcore:DeleteAgentRuntime",
          "bedrock-agentcore:ListAgentRuntimes",
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
      # IAM access (for AgentCore execution roles)
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
          "iam:PassRole",
          "iam:TagRole",
          "iam:UntagRole"
        ]
        Resource = [
          "arn:aws:iam::*:role/agentcore*",
          "arn:aws:iam::*:role/AmazonBedrockAgentCoreSDKRuntime-*",
          "arn:aws:iam::*:role/AmazonBedrockAgentCoreSDKCodeBuild-*"
        ]
      },
      # Service Linked Role permissions for Bedrock AgentCore
      # Required when creating Agent Runtime - Bedrock needs to create service-linked roles
      {
        Effect = "Allow"
        Action = [
          "iam:CreateServiceLinkedRole",
          "iam:GetServiceLinkedRoleDeletionStatus",
          "iam:DeleteServiceLinkedRole"
        ]
        Resource = "arn:aws:iam::*:role/aws-service-role/*"
      },
      # S3 access
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetObjectVersion",
          "s3:PutObjectAcl",
          "s3:GetObjectAcl"
        ]
        Resource = [
          "arn:aws:s3:::*",
          "arn:aws:s3:::*/*"
        ]
      },
      # EFS access
      {
        Effect = "Allow"
        Action = [
          "elasticfilesystem:ClientMount",
          "elasticfilesystem:ClientWrite",
          "elasticfilesystem:ClientRootAccess",
          "elasticfilesystem:DescribeMountTargets"
        ]
        Resource = aws_efs_file_system.nexus_ai[0].arn
      },
      # ECR access
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = "*"
      },
      # CloudWatch Logs access
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = [
          "${aws_cloudwatch_log_group.api[0].arn}:*",
          aws_cloudwatch_log_group.api[0].arn
        ]
      }
    ])
  })
}

# Note: All individual policies have been merged into the comprehensive policy above
# This reduces the number of inline policies from 9 to 1, avoiding IAM policy limits

# Instance Profile for EC2
resource "aws_iam_instance_profile" "ec2_api" {
  count = var.create_vpc && var.api_deploy_on_ec2 ? 1 : 0

  name = "${var.project_name}-ec2-api-profile-${var.environment}"
  role = aws_iam_role.ec2_api[0].name

  tags = local.common_tags
}

