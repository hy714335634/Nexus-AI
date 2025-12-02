# Jaeger Sidecar容器配置说明

## 概述

本文档说明如何在Fargate中配置Jaeger作为API服务的sidecar容器，使API可以通过localhost:4318访问Jaeger，并通过ALB暴露Jaeger UI。

## 架构设计

### Sidecar模式

在ECS Fargate中，sidecar容器是指在同一个Task Definition中定义的多个容器：
- 它们共享网络命名空间（awsvpc模式）
- 可以通过localhost互相访问
- 可以共享存储卷

### 当前设计

```
ECS Task (Fargate)
├── API容器 (8000端口)
│   └── 通过localhost:4318访问Jaeger
└── Jaeger容器 (sidecar)
    ├── 16686端口：UI界面
    ├── 4317端口：OTLP gRPC
    └── 4318端口：OTLP HTTP
```

### ALB路由

- `/api/*` → API容器 (8000端口)
- `/jaeger/*` → Jaeger容器 (16686端口，UI)
- `/` → Frontend (默认路由)

## 配置步骤

### 1. 启用Jaeger

在 `terraform.tfvars` 中设置：

```hcl
enable_jaeger = true
```

### 2. 环境变量

API容器会自动设置：
- `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318`

### 3. 访问Jaeger UI

通过ALB访问：
```
http://<alb-dns-name>/jaeger/
```

## 注意事项

1. **资源消耗**：Jaeger容器会占用额外CPU和内存资源
2. **网络限制**：两个容器共享网络，但ALB只能路由到主要端口
3. **数据持久化**：Jaeger数据默认存储在内存中，任务重启会丢失

## 故障排查

1. 检查容器日志：CloudWatch Logs
2. 验证网络连接：在API容器中测试 `curl http://localhost:4318`
3. 检查ALB路由：验证/jaeger/*路由规则

