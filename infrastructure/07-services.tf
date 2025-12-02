# ============================================
# ECS Services
# ============================================

# API Service (ECS Fargate - only when not using EC2)
resource "aws_ecs_service" "api" {
  count = var.create_vpc && !var.api_deploy_on_ec2 ? 1 : 0

  name            = "${var.project_name}-api-${var.environment}"
  cluster         = aws_ecs_cluster.nexus_ai[0].id
  task_definition = aws_ecs_task_definition.api[0].arn
  desired_count   = var.api_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = local.private_subnets
    security_groups  = [aws_security_group.ecs[0].id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api[0].arn
    container_name   = "api"
    container_port   = 8000
  }

  service_registries {
    registry_arn = aws_service_discovery_service.api[0].arn
  }

  tags = local.common_tags

  depends_on = [
    aws_lb_listener.http,
    aws_service_discovery_private_dns_namespace.main,
    aws_efs_mount_target.nexus_ai,
    null_resource.docker_build_and_push
  ]
}

# Frontend Service
resource "aws_ecs_service" "frontend" {
  count = var.create_vpc ? 1 : 0

  name            = "${var.project_name}-frontend-${var.environment}"
  cluster         = aws_ecs_cluster.nexus_ai[0].id
  task_definition = aws_ecs_task_definition.frontend[0].arn
  desired_count   = var.frontend_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = local.private_subnets
    security_groups  = [aws_security_group.ecs[0].id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend[0].arn
    container_name   = "frontend"
    container_port   = 3000
  }

  tags = local.common_tags

  depends_on = [
    aws_lb_listener.http,
    aws_efs_mount_target.nexus_ai,
    null_resource.docker_build_and_push
  ]
}

# ============================================
# Service Discovery (for internal service communication)
# ============================================
resource "aws_service_discovery_private_dns_namespace" "main" {
  count = var.create_vpc ? 1 : 0

  name        = "${var.project_name}.local"
  description = "Service discovery namespace for ${var.project_name}"
  vpc         = local.vpc_id

  tags = local.common_tags
}

resource "aws_service_discovery_service" "api" {
  count = var.create_vpc ? 1 : 0

  name = "api"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main[0].id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  tags = local.common_tags
}

