# Jaeger访问指南

## 访问方式

### 1. 通过ALB访问（推荐）

一旦Jaeger配置完成，可以通过以下URL访问：

```
http://<alb-dns-name>/jaeger/
```

#### 获取ALB DNS名称

```bash
cd infrastructure
terraform output alb_dns_name
```

或者使用AWS CLI：

```bash
aws elbv2 describe-load-balancers \
  --region us-west-2 \
  --query 'LoadBalancers[?LoadBalancerName==`nexus-ai-alb-prod`].DNSName' \
  --output text
```

### 2. 通过端口转发访问（如果ALB是内部的）

如果ALB是内部的（`alb_internal = true`），需要通过Bastion进行端口转发：

```bash
# 1. 获取Bastion IP和ALB DNS
BASTION_IP=$(terraform output -raw bastion_public_ip)
ALB_DNS=$(terraform output -raw alb_dns_name)

# 2. 建立端口转发
ssh -i ~/.ssh/Og_Normal.pem \
    -L 8088:$ALB_DNS:80 \
    ec2-user@$BASTION_IP \
    -N

# 3. 在本地浏览器访问
# http://localhost:8088/jaeger/
```

## 配置状态检查

### 1. 检查Jaeger是否启用

```bash
cd infrastructure
terraform output | grep enable_jaeger
# 或者在 terraform.tfvars 中查看
grep enable_jaeger terraform.tfvars
```

### 2. 检查ALB路由规则

```bash
aws elbv2 describe-rules \
  --listener-arn $(aws elbv2 describe-listeners \
    --load-balancer-arn $(aws elbv2 describe-load-balancers \
      --region us-west-2 \
      --query 'LoadBalancers[?LoadBalancerName==`nexus-ai-alb-prod`].LoadBalancerArn' \
      --output text) \
    --region us-west-2 \
    --query 'Listeners[0].ListenerArn' \
    --output text) \
  --region us-west-2 \
  --query 'Rules[?Priority==`90`]' \
  --output table
```

### 3. 检查Jaeger Target Group

```bash
aws elbv2 describe-target-groups \
  --region us-west-2 \
  --query 'TargetGroups[?TargetGroupName==`nexus-ai-jaeger-tg-prod`]' \
  --output table

# 检查目标健康状态
TG_ARN=$(aws elbv2 describe-target-groups \
  --region us-west-2 \
  --query 'TargetGroups[?TargetGroupName==`nexus-ai-jaeger-tg-prod`].TargetGroupArn' \
  --output text)

aws elbv2 describe-target-health \
  --target-group-arn $TG_ARN \
  --region us-west-2
```

### 4. 检查Jaeger容器状态

如果Jaeger已添加到Task Definition：

```bash
CLUSTER_NAME="nexus-ai-cluster-prod"
SERVICE_NAME="nexus-ai-api-prod"
REGION="us-west-2"

# 获取任务ARN
TASK_ARN=$(aws ecs list-tasks \
  --cluster $CLUSTER_NAME \
  --service-name $SERVICE_NAME \
  --region $REGION \
  --query 'taskArns[0]' \
  --output text)

# 检查容器状态
aws ecs describe-tasks \
  --cluster $CLUSTER_NAME \
  --tasks $TASK_ARN \
  --region $REGION \
  --query 'tasks[0].containers[?name==`jaeger`]' \
  --output table
```

## 完整访问步骤

### 步骤1：启用Jaeger配置

确保 `terraform.tfvars` 中设置了：

```hcl
enable_jaeger = true
```

### 步骤2：应用Terraform配置

```bash
cd infrastructure
terraform apply
```

这将创建：
- ✅ Jaeger Target Group
- ✅ ALB路由规则（`/jaeger/*` → Jaeger容器）

### 步骤3：添加Jaeger容器到Task Definition

由于Terraform限制，需要手动添加Jaeger容器。有两种方式：

#### 方式A：使用AWS Console（最简单）

1. 进入AWS Console → ECS → Task Definitions
2. 选择 `nexus-ai-api-prod`
3. 点击"Create new revision"
4. 在JSON编辑器中，找到 `containerDefinitions` 数组
5. 添加Jaeger容器定义（参考下面的JSON）
6. 保存新版本
7. 更新ECS Service使用新版本

#### 方式B：使用AWS CLI脚本

```bash
#!/bin/bash
TASK_DEF_NAME="nexus-ai-api-prod"
REGION="us-west-2"
LOG_GROUP="/ecs/nexus-ai-api-prod"

# 获取当前任务定义
aws ecs describe-task-definition \
  --task-definition "$TASK_DEF_NAME" \
  --region "$REGION" \
  --query 'taskDefinition' > current-task-def.json

# 使用jq添加Jaeger容器（需要安装jq）
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

# 删除不需要的字段
jq 'del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .placementConstraints, .compatibilities, .registeredAt, .registeredBy)' new-task-def.json > task-def-input.json

# 注册新任务定义
aws ecs register-task-definition \
  --cli-input-json file://task-def-input.json \
  --region "$REGION"

# 更新服务
aws ecs update-service \
  --cluster "nexus-ai-cluster-prod" \
  --service "nexus-ai-api-prod" \
  --task-definition "$TASK_DEF_NAME" \
  --region "$REGION"
```

### 步骤4：获取访问URL

```bash
# 获取ALB DNS名称
ALB_DNS=$(cd infrastructure && terraform output -raw alb_dns_name)

echo "Jaeger UI访问地址:"
echo "http://$ALB_DNS/jaeger/"
```

### 步骤5：验证访问

```bash
# 测试Jaeger UI是否可访问
curl -I http://$ALB_DNS/jaeger/

# 应该返回 200 OK
```

## Jaeger容器定义JSON

完整的Jaeger容器定义（添加到Task Definition的 `containerDefinitions` 数组中）：

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

## 注意事项

### 1. Fargate的限制

Fargate中的sidecar容器：
- ✅ 可以通过localhost互相访问
- ✅ 共享网络命名空间
- ⚠️ 但ALB只能路由到一个容器的主要端口

**解决方案**：
- 使用不同的路由规则路由到不同的容器
- Jaeger UI在16686端口，通过 `/jaeger/*` 路由访问

### 2. 安全组配置

确保ECS安全组允许ALB访问Jaeger端口：

```bash
# 检查安全组规则
aws ec2 describe-security-groups \
  --filters "Name=tag:Name,Values=nexus-ai-ecs-sg-prod" \
  --region us-west-2 \
  --query 'SecurityGroups[0].IpPermissions'
```

如果缺少16686端口的规则，需要添加（但通常通过Target Group路由不需要额外的安全组规则）。

### 3. Target Group健康检查

Jaeger Target Group的健康检查：
- 路径：`/`
- 端口：16686
- 协议：HTTP

如果健康检查失败，检查：
1. Jaeger容器是否在运行
2. 端口映射是否正确
3. Task是否注册到Target Group

### 4. 访问权限

如果ALB是内部的（`alb_internal = true`）：
- 只能从VPC内部访问
- 需要通过Bastion进行端口转发
- 或通过VPN/直接连接访问

如果ALB是外部的（`alb_internal = false`）：
- 可以从互联网直接访问
- 确保安全组允许访问

## 快速访问脚本

创建一个便捷脚本 `scripts/access-jaeger.sh`：

```bash
#!/bin/bash
cd "$(dirname "$0")/../infrastructure"

ALB_DNS=$(terraform output -raw alb_dns_name 2>/dev/null)
REGION=$(terraform output -raw region 2>/dev/null || echo "us-west-2")

if [ -z "$ALB_DNS" ]; then
    echo "❌ 无法获取ALB DNS名称"
    exit 1
fi

ALB_INTERNAL=$(terraform output -raw alb_internal 2>/dev/null || echo "false")

if [ "$ALB_INTERNAL" = "true" ]; then
    echo "📡 ALB是内部的，需要通过端口转发访问"
    echo ""
    echo "1. 获取Bastion IP和SSH Key："
    BASTION_IP=$(terraform output -raw bastion_public_ip 2>/dev/null)
    KEY_NAME=$(terraform output -raw bastion_key_name 2>/dev/null || echo "Og_Normal")
    
    echo "2. 运行端口转发："
    echo "ssh -i ~/.ssh/$KEY_NAME.pem \\"
    echo "    -L 8088:$ALB_DNS:80 \\"
    echo "    ec2-user@$BASTION_IP \\"
    echo "    -N"
    echo ""
    echo "3. 在浏览器访问："
    echo "http://localhost:8088/jaeger/"
else
    echo "🌐 Jaeger UI访问地址："
    echo "http://$ALB_DNS/jaeger/"
    echo ""
    echo "直接打开浏览器访问上述地址"
fi
```

## 故障排查

### 问题1：404 Not Found

**原因**：路由规则未配置或Jaeger容器未运行

**解决**：
1. 检查ALB路由规则：`aws elbv2 describe-rules --listener-arn <arn>`
2. 检查Jaeger容器状态
3. 验证Target Group中有健康的目标

### 问题2：502 Bad Gateway

**原因**：Target Group中没有健康的目标

**解决**：
1. 检查Task是否注册到Target Group
2. 检查Jaeger容器是否在运行
3. 查看Task日志：`aws logs tail /ecs/nexus-ai-api-prod --follow`

### 问题3：无法访问（超时）

**原因**：网络配置问题或安全组限制

**解决**：
1. 检查安全组规则
2. 检查ALB是内部还是外部
3. 如果内部，使用端口转发

## 总结

✅ **Jaeger访问URL**：`http://<alb-dns-name>/jaeger/`

✅ **前提条件**：
1. `enable_jaeger = true` 在terraform.tfvars中
2. Terraform配置已应用（创建Target Group和路由）
3. Jaeger容器已添加到Task Definition
4. ECS Service已更新使用新Task Definition

✅ **验证步骤**：
1. 检查ALB DNS名称：`terraform output alb_dns_name`
2. 检查路由规则是否创建
3. 检查Jaeger容器是否运行
4. 访问URL验证

