# Jaeger Sidecar完整配置指南

## 概述

本文档提供在Fargate中配置Jaeger作为API服务sidecar容器的完整方案。由于Fargate中一个Service只能有一个主要Target Group的限制，我们采用以下方案：

- **Sidecar模式**：Jaeger与API容器运行在同一个Task中
- **内部访问**：API通过 `localhost:4318` 访问Jaeger
- **UI访问**：通过ALB路由 `/jaeger/*` 到Jaeger UI端口

## 当前已完成的配置

### 1. ✅ 变量定义
- `enable_jaeger` 变量已添加
- API容器的 `OTEL_EXPORTER_OTLP_ENDPOINT` 环境变量已配置

### 2. ✅ ALB配置
- Jaeger Target Group已创建（`aws_lb_target_group.jaeger`）
- ALB路由规则已添加（`/jaeger/*` → Jaeger容器）

### 3. ⚠️ Task Definition配置

由于Terraform在处理动态容器数组时的复杂性，需要手动添加Jaeger容器到Task Definition。有两种方式：

## 方式1：使用Terraform（推荐，但需要修改）

在 `05-compute-ecs.tf` 中，需要修改 `container_definitions` 使用动态构建。由于JSON的复杂性，建议使用以下模板：

创建一个新文件 `infrastructure/05-compute-ecs-jaeger.tf`：

```hcl
# 注意：由于Terraform限制，需要手动修改container_definitions JSON
# 或者使用external data source来动态构建

# 当enable_jaeger=true时，需要在Task Definition的container_definitions中添加：
# 
# {
#   "name": "jaeger",
#   "image": "jaegertracing/all-in-one:latest",
#   "essential": false,
#   "portMappings": [
#     {
#       "containerPort": 16686,
#       "protocol": "tcp"
#     },
#     {
#       "containerPort": 4317,
#       "protocol": "tcp"
#     },
#     {
#       "containerPort": 4318,
#       "protocol": "tcp"
#     }
#   ],
#   "environment": [
#     {
#       "name": "COLLECTOR_ZIPKIN_HOST_PORT",
#       "value": ":9411"
#     },
#     {
#       "name": "COLLECTOR_OTLP_ENABLED",
#       "value": "true"
#     }
#   ],
#   "logConfiguration": {
#     "logDriver": "awslogs",
#     "options": {
#       "awslogs-group": "/ecs/${var.project_name}-api-${var.environment}",
#       "awslogs-region": "${var.aws_region}",
#       "awslogs-stream-prefix": "jaeger"
#     }
#   }
# }
```

## 方式2：使用AWS Console手动添加（快速测试）

1. 部署基础配置：
```bash
terraform apply
```

2. 在AWS Console中：
   - 进入ECS → Task Definitions
   - 找到 `${project_name}-api-${environment}` 任务定义
   - 创建新版本
   - 在JSON编辑器中，找到 `containerDefinitions` 数组
   - 添加Jaeger容器定义（参考上面的JSON）
   - 保存新版本

3. 更新ECS Service使用新版本：
   - 进入ECS → Services
   - 选择API服务
   - 更新 → 选择新的Task Definition版本
   - 更新服务

## 方式3：使用AWS CLI脚本

创建一个脚本 `scripts/add-jaeger-sidecar.sh`：

```bash
#!/bin/bash
TASK_DEF_NAME="${PROJECT_NAME}-api-${ENVIRONMENT}"
REGION="${AWS_REGION}"

# 获取当前任务定义
aws ecs describe-task-definition \
  --task-definition "$TASK_DEF_NAME" \
  --region "$REGION" \
  --query 'taskDefinition' > current-task-def.json

# 使用jq添加Jaeger容器
jq '.containerDefinitions += [{
  "name": "jaeger",
  "image": "jaegertracing/all-in-one:latest",
  "essential": false,
  "portMappings": [
    {"containerPort": 16686, "protocol": "tcp"},
    {"containerPort": 4317, "protocol": "tcp"},
    {"containerPort": 4318, "protocol": "tcp"}
  ],
  "environment": [
    {"name": "COLLECTOR_ZIPKIN_HOST_PORT", "value": ":9411"},
    {"name": "COLLECTOR_OTLP_ENABLED", "value": "true"}
  ],
  "logConfiguration": {
    "logDriver": "awslogs",
    "options": {
      "awslogs-group": "/ecs/'${PROJECT_NAME}'-api-'${ENVIRONMENT}'",
      "awslogs-region": "'${REGION}'",
      "awslogs-stream-prefix": "jaeger"
    }
  }
}]' current-task-def.json > new-task-def.json

# 注册新任务定义
aws ecs register-task-definition \
  --cli-input-json file://new-task-def.json \
  --region "$REGION"

# 更新服务
aws ecs update-service \
  --cluster "${PROJECT_NAME}-cluster-${ENVIRONMENT}" \
  --service "${PROJECT_NAME}-api-${ENVIRONMENT}" \
  --task-definition "$TASK_DEF_NAME" \
  --region "$REGION"
```

## 访问Jaeger UI

配置完成后，通过以下方式访问：

```
http://<alb-dns-name>/jaeger/
```

## 验证配置

1. **检查容器状态**：
```bash
aws ecs describe-tasks \
  --cluster "${PROJECT_NAME}-cluster-${ENVIRONMENT}" \
  --tasks $(aws ecs list-tasks --cluster "${PROJECT_NAME}-cluster-${ENVIRONMENT}" --service-name "${PROJECT_NAME}-api-${ENVIRONMENT}" --query 'taskArns[0]' --output text) \
  --query 'tasks[0].containers[*].{name:name,status:lastStatus}' \
  --region "${AWS_REGION}"
```

2. **检查Jaeger UI可访问性**：
```bash
curl -I http://<alb-dns-name>/jaeger/
```

3. **检查API到Jaeger的连接**：
在API容器中执行：
```bash
curl http://localhost:4318
```

## 注意事项

1. **资源消耗**：Jaeger容器会占用额外的CPU和内存，可能需要调整Task的资源配置
2. **数据持久化**：默认Jaeger数据存储在内存中，任务重启会丢失
3. **网络访问**：确保安全组允许ALB访问ECS任务的16686端口
4. **Target Group**：Jaeger Target Group需要能够访问Task的16686端口，由于Fargate的限制，可能需要使用NLB或通过API容器代理

## 推荐的生产方案

对于生产环境，建议：
1. 使用独立的Jaeger服务（单独的ECS Service或托管服务）
2. 或者使用AWS X-Ray替代Jaeger
3. 如果需要Jaeger，考虑使用Jaeger Cloud或自托管在EC2

## 故障排查

1. **Jaeger容器无法启动**：检查日志 `aws logs tail /ecs/${project_name}-api-${environment} --follow`
2. **无法访问UI**：检查ALB Target Group健康状态
3. **API无法连接Jaeger**：验证容器在同一Task中，检查网络配置

## 下一步

1. 启用Jaeger：`terraform apply -var="enable_jaeger=true"`
2. 按照上述方式之一添加Jaeger容器
3. 验证配置并访问UI

