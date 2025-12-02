# ============================================
# ECS Cluster
# ============================================
resource "aws_ecs_cluster" "nexus_ai" {
  count = var.create_vpc ? 1 : 0

  name = "${var.project_name}-cluster-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = local.common_tags
}

# ============================================
# CloudWatch Log Groups
# ============================================
resource "aws_cloudwatch_log_group" "api" {
  count = var.create_vpc ? 1 : 0

  name              = "/ecs/${var.project_name}-api-${var.environment}"
  retention_in_days = 7

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "frontend" {
  count = var.create_vpc ? 1 : 0

  name              = "/ecs/${var.project_name}-frontend-${var.environment}"
  retention_in_days = 7

  tags = local.common_tags
}

# ============================================
# ECS Task Definitions
# ============================================

# API Backend Task Definition (only when not using EC2)
resource "aws_ecs_task_definition" "api" {
  count = var.create_vpc && !var.api_deploy_on_ec2 ? 1 : 0

  family                   = "${var.project_name}-api-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution[0].arn
  task_role_arn            = aws_iam_role.ecs_task[0].arn

  container_definitions = jsonencode([
    {
      name      = "api"
      image     = "${aws_ecr_repository.api.repository_url}:latest"
      essential = true

      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "ENVIRONMENT"
          value = var.environment
        },
        {
          name  = "DYNAMODB_REGION"
          value = var.aws_region
        },
        {
          name  = "AGENT_PROJECTS_TABLE"
          value = var.enable_dynamodb ? aws_dynamodb_table.agent_projects[0].name : ""
        },
        {
          name  = "AGENT_INSTANCES_TABLE"
          value = var.enable_dynamodb ? aws_dynamodb_table.agent_instances[0].name : ""
        },
        {
          name  = "SQS_QUEUE_URL"
          value = var.enable_sqs ? aws_sqs_queue.nexus_notifications[0].url : ""
        },
        {
          name  = "EFS_MOUNT_PATH"
          value = "/mnt/efs"
        },
        {
          name  = "REPO_ROOT"
          value = "/mnt/efs/nexus-ai-repo"
        },
        {
          name  = "PROJECTS_ROOT"
          value = "/mnt/efs/nexus-ai-repo/projects"
        },
        {
          name  = "PYTHONPATH"
          value = "/app:/app/nexus_utils"
        },
        {
          name  = "MAX_WORKFLOW_WORKERS"
          value = tostring(var.max_workflow_workers)
        },
        {
          name  = "OTEL_EXPORTER_OTLP_ENDPOINT"
          value = var.enable_jaeger ? "http://localhost:4318" : ""
        }
      ]

      mountPoints = [
        {
          sourceVolume  = "efs-storage"
          containerPath = "/mnt/efs"
          readOnly      = false
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.api[0].name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "api"
        }
      }

      # Override command to setup EFS symlink and start uvicorn
      command = [
        "sh",
        "-c",
        <<-EOT
          # Create projects directory symlink to EFS if it doesn't exist
          if [ ! -d /app/projects ] && [ -d /mnt/efs/nexus-ai-repo/projects ]; then
            ln -sf /mnt/efs/nexus-ai-repo/projects /app/projects || true
          fi
          # Ensure projects directory exists (create if symlink failed)
          mkdir -p /app/projects
          # Start uvicorn server
          exec uvicorn api.main:app --host 0.0.0.0 --port 8000
        EOT
      ]

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 90
      }
    }
  ])

  volume {
    name = "efs-storage"

    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.nexus_ai[0].id
      root_directory     = "/"
      transit_encryption = "ENABLED"

      authorization_config {
        access_point_id = aws_efs_access_point.app_data[0].id
        iam             = "ENABLED"
      }
    }
  }

  tags = local.common_tags
}

# Frontend Task Definition
resource "aws_ecs_task_definition" "frontend" {
  count = var.create_vpc ? 1 : 0

  family                   = "${var.project_name}-frontend-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.frontend_cpu
  memory                   = var.frontend_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution[0].arn
  task_role_arn            = aws_iam_role.ecs_task[0].arn

  container_definitions = jsonencode([
    {
      name      = "frontend"
      image     = "${aws_ecr_repository.frontend.repository_url}:latest"
      essential = true

      portMappings = [
        {
          containerPort = 3000
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "NODE_ENV"
          value = var.environment == "prod" ? "production" : "development"
        },
        {
          name  = "NEXT_PUBLIC_API_URL"
          value = "http://${aws_lb.nexus_ai[0].dns_name}"
        },
        {
          name  = "NEXT_PUBLIC_API_BASE_URL"
          value = "http://${aws_lb.nexus_ai[0].dns_name}"
        }
      ]

      mountPoints = [
        {
          sourceVolume  = "efs-storage"
          containerPath = "/mnt/efs"
          readOnly      = false
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.frontend[0].name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "frontend"
        }
      }

      # Removed container health check - rely on ALB health check only
      # This avoids issues with missing curl/wget in container
    }
  ])

  volume {
    name = "efs-storage"

    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.nexus_ai[0].id
      root_directory     = "/"
      transit_encryption = "ENABLED"

      authorization_config {
        access_point_id = aws_efs_access_point.app_data[0].id
        iam             = "ENABLED"
      }
    }
  }

  tags = local.common_tags
}

