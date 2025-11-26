resource "aws_iam_role" "stepfunctions_execution" {
  count = var.enable_stepfunctions ? 1 : 0

  name = "${var.project_name}-stepfunctions-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy" "stepfunctions_lambda" {
  count = var.enable_stepfunctions && var.enable_lambda ? 1 : 0

  name = "${var.project_name}-stepfunctions-lambda-${var.environment}"
  role = aws_iam_role.stepfunctions_execution[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = [
          aws_lambda_function.nexus_ai[0].arn
        ]
      }
    ]
  })
}

resource "aws_sfn_state_machine" "agent_build_workflow" {
  count = var.enable_stepfunctions ? 1 : 0

  name     = "${var.project_name}-agent-build-workflow-${var.environment}"
  role_arn = aws_iam_role.stepfunctions_execution[0].arn

  definition = jsonencode({
    Comment = "NexusAI Agent Build Workflow"
    StartAt = "InitializeProject"
    States = {
      InitializeProject = {
        Type     = "Task"
        Resource = var.enable_lambda ? aws_lambda_function.nexus_ai[0].arn : "arn:aws:lambda:${var.aws_region}:ACCOUNT_ID:function:placeholder"
        Next     = "RequirementsAnalysis"
      }
      RequirementsAnalysis = {
        Type     = "Task"
        Resource = var.enable_lambda ? aws_lambda_function.nexus_ai[0].arn : "arn:aws:lambda:${var.aws_region}:ACCOUNT_ID:function:placeholder"
        Next     = "ArchitectureDesign"
      }
      ArchitectureDesign = {
        Type     = "Task"
        Resource = var.enable_lambda ? aws_lambda_function.nexus_ai[0].arn : "arn:aws:lambda:${var.aws_region}:ACCOUNT_ID:function:placeholder"
        Next     = "AgentImplementation"
      }
      AgentImplementation = {
        Type     = "Task"
        Resource = var.enable_lambda ? aws_lambda_function.nexus_ai[0].arn : "arn:aws:lambda:${var.aws_region}:ACCOUNT_ID:function:placeholder"
        Next     = "Testing"
      }
      Testing = {
        Type     = "Task"
        Resource = var.enable_lambda ? aws_lambda_function.nexus_ai[0].arn : "arn:aws:lambda:${var.aws_region}:ACCOUNT_ID:function:placeholder"
        Next     = "Deployment"
      }
      Deployment = {
        Type     = "Task"
        Resource = var.enable_lambda ? aws_lambda_function.nexus_ai[0].arn : "arn:aws:lambda:${var.aws_region}:ACCOUNT_ID:function:placeholder"
        End      = true
      }
    }
  })

  tags = local.common_tags
}
