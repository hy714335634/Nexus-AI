resource "aws_iam_role" "lambda_execution" {
  count = var.enable_lambda ? 1 : 0

  name = "${var.project_name}-lambda-execution-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy" "lambda_dynamodb" {
  count = var.enable_lambda ? 1 : 0

  name = "${var.project_name}-lambda-dynamodb-${var.environment}"
  role = aws_iam_role.lambda_execution[0].id

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
          "dynamodb:Scan"
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

resource "aws_iam_role_policy" "lambda_sqs" {
  count = var.enable_lambda && var.enable_sqs ? 1 : 0

  name = "${var.project_name}-lambda-sqs-${var.environment}"
  role = aws_iam_role.lambda_execution[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = [
          aws_sqs_queue.nexus_notifications[0].arn
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  count = var.enable_lambda ? 1 : 0

  role       = aws_iam_role.lambda_execution[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  count = var.enable_lambda ? 1 : 0

  role       = aws_iam_role.lambda_execution[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy" "lambda_bedrock" {
  count = var.enable_lambda ? 1 : 0

  name = "${var.project_name}-lambda-bedrock-${var.environment}"
  role = aws_iam_role.lambda_execution[0].id

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

resource "aws_iam_role_policy" "lambda_efs" {
  count = var.enable_lambda ? 1 : 0

  name = "${var.project_name}-lambda-efs-${var.environment}"
  role = aws_iam_role.lambda_execution[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "elasticfilesystem:ClientMount",
          "elasticfilesystem:ClientWrite",
          "elasticfilesystem:DescribeMountTargets"
        ]
        Resource = var.enable_lambda ? aws_efs_file_system.lambda_efs[0].arn : "*"
      }
    ]
  })
}
