# 从EC2切换到Fargate部署指南

## 问题诊断

如果您在ECS中只看到 `nexus-ai-frontend-prod` 服务，而API服务仍然以EC2形式部署，说明 `api_deploy_on_ec2` 变量被设置为 `true`。

### 检查当前配置

查看 `terraform.tfvars` 文件：

```bash
cat infrastructure/terraform.tfvars | grep api_deploy_on_ec2
```

如果显示 `api_deploy_on_ec2 = true`，这就是问题所在。

## 解决方案

### 步骤1：更新 terraform.tfvars

在 `infrastructure/terraform.tfvars` 文件中，确保设置：

```hcl
# 使用Fargate部署API（而不是EC2）
api_deploy_on_ec2 = false
```

### 步骤2：应用更改

```bash
cd infrastructure
terraform plan  # 查看将要创建的资源
terraform apply
```

这将：
- ✅ 创建ECS Fargate Task Definition（`nexus-ai-api-prod`）
- ✅ 创建ECS Service（`nexus-ai-api-prod`）
- ❌ 删除或保留现有的EC2 Auto Scaling Group（取决于配置）

### 步骤3：验证部署

1. **检查ECS Cluster**：
```bash
aws ecs list-services \
  --cluster nexus-ai-cluster-prod \
  --region us-west-2
```

应该看到两个服务：
- `nexus-ai-api-prod`
- `nexus-ai-frontend-prod`

2. **检查ECS Tasks**：
```bash
aws ecs list-tasks \
  --cluster nexus-ai-cluster-prod \
  --service-name nexus-ai-api-prod \
  --region us-west-2
```

3. **检查服务状态**：
```bash
aws ecs describe-services \
  --cluster nexus-ai-cluster-prod \
  --services nexus-ai-api-prod \
  --region us-west-2 \
  --query 'services[0].{status:status,runningCount:runningCount,desiredCount:desiredCount}'
```

## 关于Jaeger

### 为什么看不到Jaeger？

Jaeger需要：
1. ✅ API服务在Fargate中运行（不是EC2）
2. ✅ `enable_jaeger = true` 在terraform.tfvars中
3. ⚠️ 手动添加到Task Definition（由于Terraform限制）

### 添加Jaeger的步骤

在切换到Fargate后，按照 `jaeger-sidecar-complete.md` 文档添加Jaeger容器。

## 迁移注意事项

### 从EC2迁移到Fargate

如果API服务当前在EC2上运行：

1. **数据迁移**：
   - 项目数据已在EFS上，无需迁移
   - DynamoDB数据无需迁移

2. **服务中断**：
   - 在切换过程中会有短暂的服务中断
   - 建议在低峰期进行

3. **现有EC2实例**：
   - Terraform不会自动删除现有的EC2实例
   - 需要在切换到Fargate后手动终止EC2实例以节省成本

### 清理EC2资源（可选）

切换到Fargate后，如果不再需要EC2实例：

1. **终止Auto Scaling Group中的实例**：
```bash
# 先设置desired capacity为0
aws autoscaling set-desired-capacity \
  --auto-scaling-group-name nexus-ai-api-asg-prod \
  --desired-capacity 0 \
  --region us-west-2

# 等待实例终止后，删除Auto Scaling Group
aws autoscaling delete-auto-scaling-group \
  --auto-scaling-group-name nexus-ai-api-asg-prod \
  --region us-west-2 \
  --force-delete
```

或者在Terraform中设置：
```hcl
api_deploy_on_ec2 = false
ec2_api_min_size = 0
ec2_api_desired_capacity = 0
```

然后 `terraform apply`，Terraform会自动清理EC2资源。

## 完整配置示例

`terraform.tfvars` 完整配置：

```hcl
# AWS Configuration
aws_region = "us-west-2"

# Project Configuration
project_name = "nexus-ai"
environment  = "prod"

# 部署配置
api_deploy_on_ec2 = false  # 使用Fargate，不使用EC2

# Fargate资源配置
api_cpu = 4096           # 4 vCPU
api_memory = 8192        # 8GB
api_desired_count = 2    # 2个实例

# 工作流配置
max_workflow_workers = 5

# Jaeger配置
enable_jaeger = true

# 其他配置...
enable_sqs = true
enable_dynamodb = true
enable_bastion = true
```

## 故障排查

### 问题1：切换后ECS服务无法启动

**检查项**：
1. ECR镜像是否存在
2. Task Definition是否正确
3. 安全组配置
4. EFS挂载目标是否可达

**查看日志**：
```bash
aws logs tail /ecs/nexus-ai-api-prod --follow
```

### 问题2：ALB无法路由到API

**检查项**：
1. Target Group健康检查
2. 安全组允许ALB访问
3. 任务是否在运行

**检查Target Group**：
```bash
aws elbv2 describe-target-health \
  --target-group-arn <target-group-arn> \
  --region us-west-2
```

## 总结

✅ **切换到Fargate的步骤**：
1. 设置 `api_deploy_on_ec2 = false`
2. 运行 `terraform apply`
3. 验证ECS服务正常运行
4. （可选）清理EC2资源

✅ **添加Jaeger的步骤**：
1. 设置 `enable_jaeger = true`
2. 按照文档手动添加到Task Definition
3. 访问 `http://<alb-dns>/jaeger/`

