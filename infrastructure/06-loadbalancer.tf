# ============================================
# Application Load Balancer
# ============================================
resource "aws_lb" "nexus_ai" {
  count = var.create_vpc ? 1 : 0

  name               = "${var.project_name}-alb-${var.environment}"
  internal           = var.alb_internal # true = internal, false = internet-facing
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb[0].id]
  # Use private subnets for internal ALB, public subnets for internet-facing ALB
  subnets = var.alb_internal ? local.private_subnets : local.public_subnets

  enable_deletion_protection       = false
  enable_http2                     = true
  enable_cross_zone_load_balancing = true

  tags = local.common_tags
}

# Target Groups
resource "aws_lb_target_group" "api" {
  count = var.create_vpc ? 1 : 0

  # Include target_type in name to force replacement when switching between EC2 and ECS
  name        = "${var.project_name}-api-tg-${var.environment}-${var.api_deploy_on_ec2 ? "ec2" : "ecs"}"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = local.vpc_id
  # Use "instance" type when deploying on EC2, "ip" type when deploying on ECS
  target_type = var.api_deploy_on_ec2 ? "instance" : "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/health"
    protocol            = "HTTP"
    matcher             = "200"
  }

  deregistration_delay = 30

  # Force replacement when target_type changes
  lifecycle {
    create_before_destroy = true
  }

  tags = local.common_tags
}

resource "aws_lb_target_group" "frontend" {
  count = var.create_vpc ? 1 : 0

  name        = "${var.project_name}-frontend-tg-${var.environment}"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = local.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 5
    timeout             = 10
    interval            = 30
    path                = "/"
    protocol            = "HTTP"
    # Accept 200-399 status codes (Next.js may return 200 or redirects)
    matcher             = "200-399"
  }

  deregistration_delay = 30

  tags = local.common_tags
}

# Listeners
# HTTP Listener - Default to frontend, route /api/* to API service
resource "aws_lb_listener" "http" {
  count = var.create_vpc ? 1 : 0

  load_balancer_arn = aws_lb.nexus_ai[0].arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend[0].arn
  }
}

# Listener Rules - Route API requests to API service
resource "aws_lb_listener_rule" "api" {
  count = var.create_vpc ? 1 : 0

  listener_arn = aws_lb_listener.http[0].arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api[0].arn
  }

  condition {
    path_pattern {
      values = ["/api/*"]
    }
  }

  # Ensure listener rule is updated before target group is replaced
  depends_on = [aws_lb_target_group.api]
}

resource "aws_lb_listener_rule" "api_docs" {
  count = var.create_vpc ? 1 : 0

  listener_arn = aws_lb_listener.http[0].arn
  priority     = 101

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api[0].arn
  }

  condition {
    path_pattern {
      values = ["/docs", "/docs/*", "/openapi.json", "/redoc", "/redoc/*"]
    }
  }

  # Ensure listener rule is updated before target group is replaced
  depends_on = [aws_lb_target_group.api]
}

# Jaeger Target Group (when enabled)
resource "aws_lb_target_group" "jaeger" {
  count = var.create_vpc && var.enable_jaeger ? 1 : 0

  name        = "${var.project_name}-jaeger-tg-${var.environment}"
  port        = 16686
  protocol    = "HTTP"
  vpc_id      = local.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/"
    protocol            = "HTTP"
    matcher             = "200"
  }

  deregistration_delay = 30

  tags = local.common_tags
}

# ALB Listener Rule for Jaeger UI
resource "aws_lb_listener_rule" "jaeger" {
  count = var.create_vpc && var.enable_jaeger ? 1 : 0

  listener_arn = aws_lb_listener.http[0].arn
  priority     = 90

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.jaeger[0].arn
  }

  condition {
    path_pattern {
      values = ["/jaeger", "/jaeger/*"]
    }
  }

  depends_on = [aws_lb_target_group.jaeger]
}

