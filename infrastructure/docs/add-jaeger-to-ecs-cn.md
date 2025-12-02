# 在ECS集群中添加Jaeger容器

## 问题

在ECS集群 `nexus-ai-cluster-prod` 中看不到Jaeger容器。

## 原因

Jaeger需要作为sidecar容器添加到API服务的Task Definition中。由于Terraform在处理动态容器数组时的复杂性，需要手动添加。

## 解决方案

### 方式1：使用自动化脚本（推荐）

我们提供了一个自动化脚本来添加Jaeger容器：

```bash
cd infrastructure/scripts
./add-jaeger-sidecar.sh
```

脚本会自动：
1. ✅ 获取当前的Task Definition
2. ✅ 检查是否已有Jaeger容器
3. ✅ 添加Jaeger容器定义
4. ✅ 注册新的Task Definition版本
5. ✅ 更新ECS服务使用新版本
6. ✅ 强制重新部署任务

### 方式2：使用AWS Console手动添加

1. **进入AWS Console**
   - 导航到 ECS → Task Definitions
   - 找到 `nexus-ai-api-prod` 任务定义

2. **创建新版本**
   - 点击任务定义名称
   - 点击"Create new revision"

3. **添加Jaeger容器**
   - 在JSON编辑器中，找到 `containerDefinitions` 数组
   - 添加以下Jaeger容器定义：

```json
{
  "name": "jaeger",
  "image": "jaegertracing/all-in-one:latest",
  "essential": false,
  "portMappings": [
    {
      "containerPort": 16686,
      "protocol": "tcp"
    },
    {
      "containerPort": 4317,
      "protocol": "tcp"
    },
    {
      "containerPort": 4318,
      "protocol": "tcp"
    }
  ],
  "environment": [
    {
      "name": "COLLECTOR_ZIPKIN_HOST_PORT",
      "value": ":9411"
    },
    {
      "name": "COLLECTOR_OTLP_ENABLED",
      "value": "true"
    }
  ],
  "logConfiguration": {
    "logDriver": "awslogs",
    "options": {
      "awslogs-group": "/ecs/nexus-ai-api-prod",
      "awslogs-region": "us-west-2",
      "awslogs-stream-prefix": "jaeger"
    }
  }
}
```

4. **保存并更新服务**
   - 点击"Create"保存新版本
   - 进入 ECS → Services → `nexus-ai-api-prod`
   - 点击"Update" → 选择新创建的Task Definition版本
   - 勾选"Force new deployment"
   - 点击"Update"

### 方式3：使用AWS CLI

```bash
# 设置变量
TASK_DEF_NAME="nexus-ai-api-prod"
REGION="us-west-2"
CLUSTER_NAME="nexus-ai-cluster-prod"
SERVICE_NAME="nexus-ai-api-prod"
LOG_GROUP="/ecs/nexus-ai-api-prod"

# 1. 获取当前Task Definition
aws ecs describe-task-definition \
  --task-definition "$TASK_DEF_NAME" \
  --region "$REGION" \
  --query 'taskDefinition' > current-task-def.json

# 2. 使用jq添加Jaeger容器（需要安装jq: brew install jq）
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
      "awslogs-group": "'$LOG_GROUP'",
      "awslogs-region": "'$REGION'",
      "awslogs-stream-prefix": "jaeger"
    }
  }
}]' current-task-def.json > new-task-def.json

# 3. 删除只读字段
jq 'del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .placementConstraints, .compatibilities, .registeredAt, .registeredBy)' new-task-def.json > task-def-input.json

# 4. 注册新Task Definition
aws ecs register-task-definition \
  --cli-input-json file://task-def-input.json \
  --region "$REGION"

# 5. 更新服务
aws ecs update-service \
  --cluster "$CLUSTER_NAME" \
  --service "$SERVICE_NAME" \
  --task-definition "$TASK_DEF_NAME" \
  --force-new-deployment \
  --region "$REGION"

# 清理临时文件
rm -f current-task-def.json new-task-def.json task-def-input.json
```

## 验证步骤

### 1. 检查Task Definition

```bash
aws ecs describe-task-definition \
  --task-definition nexus-ai-api-prod \
  --region us-west-2 \
  --query 'taskDefinition.containerDefinitions[?name==`jaeger`]'
```

应该返回Jaeger容器的定义。

### 2. 检查运行中的任务

```bash
# 获取任务ARN
TASK_ARN=$(aws ecs list-tasks \
  --cluster nexus-ai-cluster-prod \
  --service-name nexus-ai-api-prod \
  --region us-west-2 \
  --query 'taskArns[0]' \
  --output text)

# 检查容器
aws ecs describe-tasks \
  --cluster nexus-ai-cluster-prod \
  --tasks $TASK_ARN \
  --region us-west-2 \
  --query 'tasks[0].containers[*].{Name:name,Status:lastStatus}'
```

应该看到两个容器：
- `api` (状态: RUNNING)
- `jaeger` (状态: RUNNING)

### 3. 检查Jaeger容器日志

```bash
aws logs tail /ecs/nexus-ai-api-prod \
  --filter-pattern "jaeger" \
  --follow \
  --region us-west-2
```

### 4. 访问Jaeger UI

```bash
# 获取ALB DNS
ALB_DNS=$(cd infrastructure && terraform output -raw alb_dns_name)

echo "Jaeger UI: http://${ALB_DNS}/jaeger/"
```

## 注意事项

1. **资源消耗**
   - Jaeger容器会占用额外的CPU和内存
   - 当前Task配置：4 vCPU, 8GB内存（应该足够）

2. **部署时间**
   - 添加容器后，ECS会重新部署任务
   - 通常需要1-2分钟

3. **网络访问**
   - API容器通过 `localhost:4318` 访问Jaeger
   - Jaeger UI通过ALB路由 `/jaeger/*` 访问

4. **数据持久化**
   - 默认Jaeger数据存储在内存中
   - 任务重启会丢失数据
   - 生产环境建议使用外部存储

## 故障排查

### 问题1：Jaeger容器无法启动

**检查日志**：
```bash
aws logs tail /ecs/nexus-ai-api-prod \
  --filter-pattern "jaeger" \
  --region us-west-2
```

**可能原因**：
- 端口冲突（但16686, 4317, 4318不应冲突）
- 镜像拉取失败
- 资源不足

### 问题2：无法访问Jaeger UI

**检查ALB路由**：
```bash
# 检查Target Group
aws elbv2 describe-target-groups \
  --region us-west-2 \
  --query 'TargetGroups[?TargetGroupName==`nexus-ai-jaeger-tg-prod`]'

# 检查路由规则
aws elbv2 describe-rules \
  --listener-arn <listener-arn> \
  --region us-west-2 \
  --query 'Rules[?Priority==`90`]'
```

**检查健康状态**：
```bash
TG_ARN=$(aws elbv2 describe-target-groups \
  --region us-west-2 \
  --query 'TargetGroups[?TargetGroupName==`nexus-ai-jaeger-tg-prod`].TargetGroupArn' \
  --output text)

aws elbv2 describe-target-health \
  --target-group-arn $TG_ARN \
  --region us-west-2
```

### 问题3：API无法连接Jaeger

**在API容器中测试**：
```bash
# 通过ECS Exec进入容器（需要启用ECS Exec）
aws ecs execute-command \
  --cluster nexus-ai-cluster-prod \
  --task <task-id> \
  --container api \
  --command "curl http://localhost:4318" \
  --interactive \
  --region us-west-2
```

## 快速检查清单

- [ ] `enable_jaeger = true` 在 `terraform.tfvars` 中
- [ ] 运行了 `terraform apply`（创建了Target Group和路由）
- [ ] Jaeger容器已添加到Task Definition
- [ ] ECS服务已更新使用新Task Definition
- [ ] 新任务已部署并运行
- [ ] Jaeger容器状态为RUNNING
- [ ] ALB路由规则已配置
- [ ] Jaeger UI可访问

## 下一步

添加Jaeger容器后，您应该能够：

1. ✅ 在ECS集群中看到Jaeger容器
2. ✅ 访问Jaeger UI: `http://<alb-dns>/jaeger/`
3. ✅ API的追踪数据会发送到Jaeger

如果还有问题，请运行诊断脚本：
```bash
cd infrastructure/scripts
./diagnose-dynamodb-connection.sh  # 这个脚本也可以检查Jaeger相关配置
```

