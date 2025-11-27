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

resource "aws_cloudwatch_log_group" "celery_worker" {
  count = var.create_vpc ? 1 : 0

  name              = "/ecs/${var.project_name}-celery-worker-${var.environment}"
  retention_in_days = 7

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "redis" {
  count = var.create_vpc ? 1 : 0

  name              = "/ecs/${var.project_name}-redis-${var.environment}"
  retention_in_days = 3

  tags = local.common_tags
}

# ============================================
# ECS Task Definitions
# ============================================

# API Backend Task Definition
resource "aws_ecs_task_definition" "api" {
  count = var.create_vpc ? 1 : 0

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
          name  = "REDIS_HOST"
          value = "redis"
        },
        {
          name  = "REDIS_PORT"
          value = "6379"
        },
        {
          name  = "CELERY_BROKER_URL"
          value = "redis://redis:6379/0"
        },
        {
          name  = "CELERY_RESULT_BACKEND"
          value = "redis://redis:6379/0"
        },
        {
          name  = "EFS_MOUNT_PATH"
          value = "/mnt/efs"
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

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
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

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:3000 || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
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

# Celery Worker Task Definition (Agent Builds Queue)
resource "aws_ecs_task_definition" "celery_worker_builds" {
  count = var.create_vpc ? 1 : 0

  family                   = "${var.project_name}-celery-worker-builds-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.celery_worker_cpu
  memory                   = var.celery_worker_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution[0].arn
  task_role_arn            = aws_iam_role.ecs_task[0].arn

  container_definitions = jsonencode([
    {
      name      = "celery-worker"
      image     = "${aws_ecr_repository.celery_worker.repository_url}:latest"
      essential = true

      command = [
        "celery",
        "-A", "api.core.celery_app.celery_app",
        "worker",
        "-Q", "agent_builds",
        "--loglevel=info"
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
          name  = "REDIS_HOST"
          value = "redis"
        },
        {
          name  = "REDIS_PORT"
          value = "6379"
        },
        {
          name  = "CELERY_BROKER_URL"
          value = "redis://redis:6379/0"
        },
        {
          name  = "CELERY_RESULT_BACKEND"
          value = "redis://redis:6379/0"
        },
        {
          name  = "EFS_MOUNT_PATH"
          value = "/mnt/efs"
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
          "awslogs-group"         = aws_cloudwatch_log_group.celery_worker[0].name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix"  = "celery-builds"
        }
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

# Celery Worker Task Definition (Status Updates Queue)
resource "aws_ecs_task_definition" "celery_worker_status" {
  count = var.create_vpc ? 1 : 0

  family                   = "${var.project_name}-celery-worker-status-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.celery_worker_cpu
  memory                   = var.celery_worker_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution[0].arn
  task_role_arn            = aws_iam_role.ecs_task[0].arn

  container_definitions = jsonencode([
    {
      name      = "celery-worker"
      image     = "${aws_ecr_repository.celery_worker.repository_url}:latest"
      essential = true

      command = [
        "celery",
        "-A", "api.core.celery_app.celery_app",
        "worker",
        "-Q", "status_updates",
        "--loglevel=info"
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
          name  = "REDIS_HOST"
          value = "redis"
        },
        {
          name  = "REDIS_PORT"
          value = "6379"
        },
        {
          name  = "CELERY_BROKER_URL"
          value = "redis://redis:6379/0"
        },
        {
          name  = "CELERY_RESULT_BACKEND"
          value = "redis://redis:6379/0"
        },
        {
          name  = "EFS_MOUNT_PATH"
          value = "/mnt/efs"
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
          "awslogs-group"         = aws_cloudwatch_log_group.celery_worker[0].name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "celery-status"
        }
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

# Redis Task Definition
resource "aws_ecs_task_definition" "redis" {
  count = var.create_vpc ? 1 : 0

  family                   = "${var.project_name}-redis-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.redis_cpu
  memory                   = var.redis_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution[0].arn
  task_role_arn            = aws_iam_role.ecs_task[0].arn

  container_definitions = jsonencode([
    {
      name      = "redis"
      image     = "redis:7-alpine"
      essential = true

      portMappings = [
        {
          containerPort = 6379
          protocol      = "tcp"
        }
      ]

      command = [
        "redis-server",
        "--appendonly", "yes",
        "--maxmemory-policy", "allkeys-lru"
      ]

      mountPoints = [
        {
          sourceVolume  = "efs-storage"
          containerPath = "/data"
          readOnly      = false
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.redis[0].name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "redis"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "redis-cli ping"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 30
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

