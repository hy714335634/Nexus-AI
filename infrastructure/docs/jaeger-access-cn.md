# Jaeger访问方式

## 快速访问

### 方式1：使用便捷脚本（推荐）

```bash
cd infrastructure/scripts
./access-jaeger.sh
```

脚本会自动检测ALB类型并提供相应的访问方式。

### 方式2：手动获取URL

```bash
cd infrastructure
ALB_DNS=$(terraform output -raw alb_dns_name)
echo "Jaeger访问地址: http://$ALB_DNS/jaeger/"
```

## 访问地址格式

```
http://<alb-dns-name>/jaeger/
```

## ALB类型说明

### 外部ALB（互联网可访问）

如果 `alb_internal = false`（默认），可以直接从互联网访问：

```
http://<alb-dns-name>/jaeger/
```

### 内部ALB（仅VPC内访问）

如果 `alb_internal = true`，需要通过以下方式访问：

#### 选项1：通过Bastion端口转发

```bash
# 1. 获取Bastion IP和ALB DNS
BASTION_IP=$(terraform output -raw bastion_public_ip)
ALB_DNS=$(terraform output -raw alb_dns_name)

# 2. 建立端口转发
ssh -i ~/.ssh/Og_Normal.pem \
    -L 8088:$ALB_DNS:80 \
    ec2-user@$BASTION_IP \
    -N

# 3. 在浏览器访问
# http://localhost:8088/jaeger/
```

#### 选项2：从VPC内部访问

如果已在VPC内部（如通过VPN或从Bastion），可以直接访问：

```
http://<alb-dns-name>/jaeger/
```

## 前提条件

1. ✅ **Jaeger已启用**：在 `terraform.tfvars` 中设置 `enable_jaeger = true`
2. ✅ **Terraform已应用**：已运行 `terraform apply` 创建了Target Group和路由规则
3. ✅ **Jaeger容器已添加**：已手动添加Jaeger容器到API Task Definition（参见 `jaeger-sidecar-complete.md`）
4. ✅ **ECS服务已更新**：ECS服务已使用包含Jaeger容器的Task Definition

## 验证步骤

### 1. 检查Jaeger是否启用

```bash
cd infrastructure
grep enable_jaeger terraform.tfvars
# 应该显示: enable_jaeger = true
```

### 2. 检查ALB路由规则

```bash
# 获取Listener ARN
LISTENER_ARN=$(aws elbv2 describe-listeners \
  --load-balancer-arn $(aws elbv2 describe-load-balancers \
    --region us-west-2 \
    --query 'LoadBalancers[?LoadBalancerName==`nexus-ai-alb-prod`].LoadBalancerArn' \
    --output text) \
  --region us-west-2 \
  --query 'Listeners[0].ListenerArn' \
  --output text)

# 检查路由规则
aws elbv2 describe-rules \
  --listener-arn $LISTENER_ARN \
  --region us-west-2 \
  --query 'Rules[?Priority==`90`]' \
  --output table
```

### 3. 检查Jaeger容器状态

```bash
CLUSTER_NAME="nexus-ai-cluster-prod"
SERVICE_NAME="nexus-ai-api-prod"

# 获取任务ARN
TASK_ARN=$(aws ecs list-tasks \
  --cluster $CLUSTER_NAME \
  --service-name $SERVICE_NAME \
  --region us-west-2 \
  --query 'taskArns[0]' \
  --output text)

# 检查Jaeger容器
aws ecs describe-tasks \
  --cluster $CLUSTER_NAME \
  --tasks $TASK_ARN \
  --region us-west-2 \
  --query 'tasks[0].containers[?name==`jaeger`]' \
  --output table
```

### 4. 测试访问

```bash
ALB_DNS=$(terraform output -raw alb_dns_name)
curl -I http://$ALB_DNS/jaeger/
# 应该返回: HTTP/1.1 200 OK
```

## 常见问题

### 问题1：404 Not Found

**可能原因**：
- Jaeger容器未添加到Task Definition
- ALB路由规则未创建

**解决方法**：
1. 检查是否运行了 `terraform apply`
2. 检查是否手动添加了Jaeger容器到Task Definition
3. 参考 `jaeger-access-guide.md` 的完整配置步骤

### 问题2：502 Bad Gateway

**可能原因**：
- Jaeger容器未运行
- Target Group中没有健康的目标

**解决方法**：
1. 检查Jaeger容器状态（见上面的验证步骤）
2. 查看Task日志：`aws logs tail /ecs/nexus-ai-api-prod --follow`
3. 检查Target Group健康状态

### 问题3：无法访问（超时）

**可能原因**：
- ALB是内部的，需要端口转发
- 安全组规则未配置

**解决方法**：
1. 检查ALB类型：`terraform output alb_internal`
2. 如果是内部的，使用端口转发方式访问
3. 检查ECS安全组是否允许ALB访问16686端口

## 快速参考

```bash
# 获取访问URL
cd infrastructure
ALB_DNS=$(terraform output -raw alb_dns_name)
echo "Jaeger: http://$ALB_DNS/jaeger/"

# 或者使用脚本
cd scripts
./access-jaeger.sh
```

## 详细文档

- 完整配置指南：`infrastructure/docs/jaeger-access-guide.md`
- Sidecar配置：`infrastructure/docs/jaeger-sidecar-complete.md`

