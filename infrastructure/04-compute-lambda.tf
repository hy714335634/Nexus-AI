resource "aws_lambda_function" "nexus_ai" {
  count = var.enable_lambda ? 1 : 0

  function_name = "${var.project_name}-agent-${var.environment}"
  role          = aws_iam_role.lambda_execution[0].arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.nexus_ai[0].repository_url}:latest"
  timeout       = 900
  memory_size   = 3008

  vpc_config {
    subnet_ids         = local.subnet_ids
    security_group_ids = [aws_security_group.lambda_sg[0].id]
  }

  file_system_config {
    arn              = aws_efs_access_point.lambda_ap[0].arn
    local_mount_path = "/mnt/efs"
  }

  environment {
    variables = {
      ENVIRONMENT              = var.environment
      DYNAMODB_REGION          = var.aws_region
      SQS_QUEUE_URL            = var.enable_sqs ? aws_sqs_queue.nexus_notifications[0].url : ""
      AGENT_PROJECTS_TABLE     = var.enable_dynamodb ? aws_dynamodb_table.agent_projects[0].name : ""
      AGENT_INSTANCES_TABLE    = var.enable_dynamodb ? aws_dynamodb_table.agent_instances[0].name : ""
      EFS_MOUNT_PATH           = "/mnt/efs"
    }
  }

  depends_on = [
    aws_efs_mount_target.lambda_efs_mt,
    null_resource.docker_image
  ]

  tags = local.common_tags

  lifecycle {
    ignore_changes = [image_uri]
  }
}

resource "aws_lambda_function_url" "nexus_ai" {
  count = var.enable_lambda ? 1 : 0

  function_name      = aws_lambda_function.nexus_ai[0].function_name
  authorization_type = "NONE"

  cors {
    allow_credentials = true
    allow_origins     = ["*"]
    allow_methods     = ["*"]
    allow_headers     = ["*"]
    max_age          = 86400
  }
}

resource "aws_cloudwatch_log_group" "lambda_logs" {
  count = var.enable_lambda ? 1 : 0

  name              = "/aws/lambda/${aws_lambda_function.nexus_ai[0].function_name}"
  retention_in_days = 7

  tags = local.common_tags
}
