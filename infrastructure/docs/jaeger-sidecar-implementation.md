# Jaeger Sidecar容器完整实现指南

## 概述

由于Terraform在处理动态容器定义时的复杂性，本文档提供两种方式来实现Jaeger sidecar容器：

1. **推荐方式**：修改Task Definition JSON，手动添加Jaeger容器定义
2. **自动化方式**：使用Terraform模板文件动态生成

## 方案1：手动修改Task Definition（推荐用于快速测试）

### 步骤

1. 在 `terraform.tfvars` 中启用Jaeger：
```hcl
enable_jaeger = true
```

2. 在 `05-compute-ecs.tf` 的 `container_definitions` JSON数组中，添加Jaeger容器定义：

```hcl
container_definitions = jsonencode(concat([
  {
    # API容器定义...
  }
], var.enable_jaeger ? [{
  name      = "jaeger"
  image     = "jaegertracing/all-in-one:latest"
  essential = false
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
      "awslogs-group"         = aws_cloudwatch_log_group.api[0].name
      "awslogs-region"        = var.aws_region
      "awslogs-stream-prefix" = "jaeger"
    }
  }
}] : []))
```

但由于Terraform的限制，这种方法在jsonencode中不太容易实现。

## 方案2：使用独立的Jaeger配置（推荐用于生产）

创建一个单独的文件 `05-compute-ecs-jaeger.tf`：

```hcl
# Jaeger Sidecar Container Definition
locals {
  jaeger_container = var.enable_jaeger ? {
    name      = "jaeger"
    image     = "jaegertracing/all-in-one:latest"
    essential = false
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
        "awslogs-group"         = aws_cloudwatch_log_group.api[0].name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "jaeger"
      }
    }
  } : null
}
```

然后修改Task Definition使用这个local。

## 方案3：完整Terraform实现（最完整）

由于复杂性，建议使用terraform文件模板。我已经为您创建了基础配置，您可以在部署后手动添加Jaeger容器，或者使用AWS Console/CLI添加。

## ALB路由配置

需要添加Jaeger UI的Target Group和路由规则：

1. **创建Jaeger Target Group**（在`06-loadbalancer.tf`中添加）：
```hcl
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

  tags = local.common_tags
}
```

2. **添加路由规则**：
```hcl
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
}
```

## 快速实现步骤

由于完整的Terraform实现比较复杂，建议按以下步骤：

1. 先部署基础API服务
2. 使用AWS Console在Task Definition中添加Jaeger容器
3. 创建Jaeger Target Group和ALB路由规则
4. 更新ECS Service使用新的Task Definition

或者，我可以为您创建一个完整的Terraform模板文件，您可以直接使用。

## 访问方式

启用后，通过以下方式访问：

- **Jaeger UI**: `http://<alb-dns-name>/jaeger/`
- **API访问Jaeger**: `http://localhost:4318`（容器内部）

