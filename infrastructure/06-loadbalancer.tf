# ============================================
# Application Load Balancer
# ============================================
resource "aws_lb" "nexus_ai" {
  count = var.create_vpc ? 1 : 0

  name               = "${var.project_name}-alb-${var.environment}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb[0].id]
  subnets            = local.public_subnets

  enable_deletion_protection = false
  enable_http2              = true
  enable_cross_zone_load_balancing = true

  tags = local.common_tags
}

# Target Groups
resource "aws_lb_target_group" "api" {
  count = var.create_vpc ? 1 : 0

  name        = "${var.project_name}-api-tg-${var.environment}"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = local.vpc_id
  target_type = "ip"

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
}

