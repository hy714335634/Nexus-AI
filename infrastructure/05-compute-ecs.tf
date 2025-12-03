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

resource "aws_cloudwatch_log_group" "jaeger" {
  count = var.create_vpc && var.enable_jaeger ? 1 : 0

  name              = "/ecs/${var.project_name}-jaeger-${var.environment}"
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
          value = var.enable_jaeger ? "http://jaeger.${var.project_name}.local:4318" : ""
        },
        {
          name  = "GITHUB_REPO_URL"
          value = var.github_repo_url
        },
        {
          name  = "GITHUB_BRANCH"
          value = var.github_branch
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

      # Override command to initialize EFS repo, setup symlink and start uvicorn
      command = [
        "sh",
        "-c",
        <<-EOT
          set -e
          # Wait for EFS to be fully mounted (up to 30 seconds)
          echo "Waiting for EFS mount..."
          for i in $(seq 1 30); do
            if [ -d /mnt/efs ] && mountpoint -q /mnt/efs 2>/dev/null || [ -d /mnt/efs/nexus-ai-repo ] || [ -w /mnt/efs ]; then
              echo "EFS mount detected"
              break
            fi
            if [ $i -eq 30 ]; then
              echo "⚠️  Warning: EFS mount may not be ready, continuing anyway..."
            fi
            sleep 1
          done
          
          # Initialize repository in EFS if it doesn't exist
          REPO_DIR="/mnt/efs/nexus-ai-repo"
          LOCK_FILE="/mnt/efs/.git-clone-in-progress"
          
          if [ ! -d "$REPO_DIR/.git" ]; then
            echo "Repository not found in EFS, will clone from GitHub..."
            echo "Current user: $(id)"
            echo "EFS mount permissions: $(ls -ld /mnt/efs 2>&1 || echo 'Cannot check permissions')"
            
            # Check if another Fargate task is already cloning
            if [ -f "$LOCK_FILE" ]; then
              echo "⚠️  Another Fargate task is cloning the repository, waiting..."
              # Wait for clone to complete (up to 10 minutes)
              MAX_WAIT=600
              WAIT_COUNT=0
              while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
                if [ ! -f "$LOCK_FILE" ] && [ -d "$REPO_DIR/.git" ]; then
                  echo "✅ Repository found (cloned by another task)"
                  break
                fi
                sleep 5
                WAIT_COUNT=$((WAIT_COUNT + 5))
                if [ $WAIT_COUNT -ge $MAX_WAIT ]; then
                  echo "⚠️  Warning: Repository still not found after $MAX_WAIT seconds"
                  echo "Service will start but may have limited functionality."
                fi
              done
            else
              # Try to create lock file and clone
              if touch "$LOCK_FILE" 2>/dev/null; then
                echo "✅ Lock file created, starting git clone..."
                echo "Cloning $${GITHUB_REPO_URL} (branch: $${GITHUB_BRANCH}) to $REPO_DIR..."
                
                if git clone -b "$${GITHUB_BRANCH}" "$${GITHUB_REPO_URL}" "$REPO_DIR" 2>&1; then
                  echo "✅ Repository cloned successfully to EFS"
                  # Set permissions to allow all users
                  find "$REPO_DIR" -type d -exec chmod 777 {} \; 2>/dev/null || true
                  find "$REPO_DIR" -type f -exec chmod 666 {} \; 2>/dev/null || true
                  # Keep .git directory writable for git operations
                  chmod -R u+w "$REPO_DIR/.git" 2>/dev/null || true
                  # Verify clone was successful
                  if [ ! -d "$REPO_DIR/.git" ] || [ ! -d "$REPO_DIR/api" ] || [ ! -d "$REPO_DIR/agents" ]; then
                    echo "❌ Error: Repository clone incomplete or invalid"
                    rm -f "$LOCK_FILE" 2>/dev/null || true
                  else
                    echo "✅ Repository structure verified"
                  fi
                  # Remove lock file on success
                  rm -f "$LOCK_FILE" 2>/dev/null || true
                else
                  echo "❌ Error: Failed to clone repository"
                  echo "Removing lock file..."
                  rm -f "$LOCK_FILE" 2>/dev/null || true
                  echo "Service will start but may have limited functionality."
                fi
              else
                echo "⚠️  Cannot create lock file (may be permission issue), waiting for another task..."
                # Wait for another task to clone (up to 10 minutes)
                MAX_WAIT=600
                WAIT_COUNT=0
                while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
                  if [ -d "$REPO_DIR/.git" ]; then
                    echo "✅ Repository found (cloned by another task)"
                    break
                  fi
                  sleep 5
                  WAIT_COUNT=$((WAIT_COUNT + 5))
                  if [ $WAIT_COUNT -ge $MAX_WAIT ]; then
                    echo "⚠️  Warning: Repository still not found after $MAX_WAIT seconds"
                  fi
                done
              fi
            fi
          else
            echo "✅ Repository already exists in EFS"
          fi
          
          # Verify repository structure
          if [ -d "$REPO_DIR/.git" ]; then
            if [ ! -d "$REPO_DIR/api" ] || [ ! -d "$REPO_DIR/agents" ]; then
              echo "⚠️  Warning: Repository structure incomplete, but continuing..."
            else
              echo "✅ Repository structure verified"
            fi
          fi
          
          # Create projects directory symlink to EFS if it doesn't exist
          if [ ! -d /app/projects ] && [ -d "$REPO_DIR/projects" ]; then
            ln -sf "$REPO_DIR/projects" /app/projects || true
            echo "✅ Created symlink: /app/projects -> $REPO_DIR/projects"
          fi
          
          # Ensure projects directory exists (create if symlink failed)
          mkdir -p /app/projects
          
          # Start uvicorn server
          echo "Starting uvicorn server..."
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
      file_system_id          = aws_efs_file_system.nexus_ai[0].id
      root_directory          = "/"
      transit_encryption      = "ENABLED"
      authorization_config {
        access_point_id = aws_efs_access_point.nexus_ai[0].id
        iam             = "DISABLED"
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
      file_system_id          = aws_efs_file_system.nexus_ai[0].id
      root_directory          = "/"
      transit_encryption      = "ENABLED"
      authorization_config {
        access_point_id = aws_efs_access_point.nexus_ai[0].id
        iam             = "DISABLED"
      }
    }
  }

  tags = local.common_tags
}

# Jaeger Task Definition (standalone service)
resource "aws_ecs_task_definition" "jaeger" {
  count = var.create_vpc && var.enable_jaeger ? 1 : 0

  family                   = "${var.project_name}-jaeger-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.jaeger_cpu
  memory                   = var.jaeger_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution[0].arn
  task_role_arn            = aws_iam_role.ecs_task[0].arn

  container_definitions = jsonencode([
    {
      name      = "jaeger"
      image     = "jaegertracing/all-in-one:latest"
      essential = true

      portMappings = [
        {
          containerPort = 16686
          protocol      = "tcp"
        },
        {
          containerPort = 4317
          protocol      = "tcp"
        },
        {
          containerPort = 4318
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "COLLECTOR_ZIPKIN_HOST_PORT"
          value = ":9411"
        },
        {
          name  = "COLLECTOR_OTLP_ENABLED"
          value = "true"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.jaeger[0].name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "jaeger"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost:16686 || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])

  tags = local.common_tags
}

