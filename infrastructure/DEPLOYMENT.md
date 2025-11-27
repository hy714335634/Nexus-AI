# Nexus-AI AWS ECS Fargate 部署指南

本文档说明如何在 AWS 上使用 ECS Fargate 部署 Nexus-AI 高可用架构。

## 📋 架构概览

### 组件
- **VPC**: 包含公有和私有子网
- **Application Load Balancer (ALB)**: 负载均衡器，路由流量到前端和 API
- **ECS Fargate Cluster**: 容器编排服务
- **EFS**: 共享文件存储，所有容器挂载
- **ECR**: Docker 镜像仓库
- **DynamoDB**: 数据存储
- **SQS**: 消息队列
- **CloudWatch**: 日志和监控

### 服务
1. **Redis** (容器): Celery broker 和缓存
2. **API** (FastAPI): 后端 API 服务，多实例
3. **Frontend** (Next.js): 前端服务，多实例
4. **Celery Worker (agent_builds)**: 处理构建任务，多实例
5. **Celery Worker (status_updates)**: 处理状态更新，多实例

## 🚀 部署步骤

### 1. 前置要求

```bash
# 安装必要工具
- AWS CLI
- Terraform >= 1.0
- Docker
- jq (用于脚本)
```

### 2. 配置 Terraform

```bash
cd infrastructure

# 复制示例配置
cp terraform.tfvars.example terraform.tfvars

# 编辑配置
vim terraform.tfvars
```

配置示例：
```hcl
aws_region     = "us-east-1"
project_name   = "nexus-ai"
environment    = "prod"

# 服务配置
api_cpu                = 1024
api_memory             = 2048
api_desired_count      = 2

frontend_cpu           = 512
frontend_memory        = 1024
frontend_desired_count = 2

celery_worker_cpu      = 2048
celery_worker_memory   = 4096
celery_worker_desired_count = 2

redis_cpu              = 512
redis_memory           = 1024
```

### 3. 初始化并部署基础设施

```bash
# 初始化 Terraform
terraform init

# 预览变更
terraform plan

# 部署基础设施
terraform apply
```

### 4. 构建并推送 Docker 镜像

**方式 1: 自动构建（推荐）**

`terraform apply` 会自动构建并推送 Docker 镜像到 ECR。这是默认行为。

如果需要跳过自动构建（例如在 CI/CD 中单独处理），可以设置环境变量：

```bash
export TF_VAR_skip_docker_build=true
terraform apply
```

**方式 2: 手动构建**

如果需要手动构建和推送，可以使用提供的脚本：

```bash
./scripts/build-and-push.sh

# 或手动构建和推送
# 1. 登录 ECR
aws ecr get-login-password --region <region> | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com

# 2. 构建并推送 API 镜像
cd ../api
docker build -t <ecr-api-repo>:latest .
docker push <ecr-api-repo>:latest

# 3. 构建并推送 Frontend 镜像
cd ../web
docker build -t <ecr-frontend-repo>:latest .
docker push <ecr-frontend-repo>:latest

# 4. Celery Worker 使用与 API 相同的镜像
docker tag <ecr-api-repo>:latest <ecr-celery-repo>:latest
docker push <ecr-celery-repo>:latest
```

### 5. 部署 ECS 服务

ECS 服务会在 `terraform apply` 时自动创建。如果需要更新服务：

```bash
# 获取集群和服务名称
CLUSTER_NAME=$(terraform output -raw ecs_cluster_name)

# 强制新部署以使用最新镜像
aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service nexus-ai-api-prod \
  --force-new-deployment

aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service nexus-ai-frontend-prod \
  --force-new-deployment

aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service nexus-ai-celery-worker-builds-prod \
  --force-new-deployment

aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service nexus-ai-celery-worker-status-prod \
  --force-new-deployment
```

### 6. 访问应用

```bash
# 获取 ALB DNS 名称
ALB_DNS=$(terraform output -raw alb_dns_name)
echo "访问地址: http://$ALB_DNS"
```

## 🔧 配置说明

### 环境变量

所有服务通过 ECS Task Definition 中的环境变量配置：

- **API 服务**:
  - `DYNAMODB_REGION`: AWS 区域
  - `AGENT_PROJECTS_TABLE`: DynamoDB 表名
  - `REDIS_HOST`: Redis 服务发现名称 (`redis`)
  - `CELERY_BROKER_URL`: Redis 连接 URL
  - `EFS_MOUNT_PATH`: EFS 挂载路径 (`/mnt/efs`)

- **Frontend 服务**:
  - `NEXT_PUBLIC_API_URL`: API 服务 URL
  - `NODE_ENV`: 环境 (production/development)

- **Celery Workers**:
  - 与 API 服务相同的环境变量
  - 通过 `command` 指定队列名称

### EFS 挂载

所有容器都挂载同一个 EFS 文件系统到 `/mnt/efs`，用于：
- 共享构建产物
- 持久化数据
- 跨容器文件访问

### 服务发现

使用 AWS Service Discovery，服务间通过 DNS 名称通信：
- Redis: `redis.nexus-ai.local`
- API: `api.nexus-ai.local`

## 📊 监控和日志

### CloudWatch Logs

所有服务的日志都发送到 CloudWatch：
- `/ecs/nexus-ai-api-{env}`
- `/ecs/nexus-ai-frontend-{env}`
- `/ecs/nexus-ai-celery-worker-{env}`
- `/ecs/nexus-ai-redis-{env}`

### 查看日志

```bash
# 查看 API 日志
aws logs tail /ecs/nexus-ai-api-prod --follow

# 查看 Celery Worker 日志
aws logs tail /ecs/nexus-ai-celery-worker-prod --follow
```

### Container Insights

ECS Cluster 启用了 Container Insights，可在 CloudWatch 控制台查看：
- CPU/内存使用率
- 任务数量
- 网络指标

## 🔄 更新部署

### 更新代码

1. 修改代码
2. 构建新镜像并推送到 ECR
3. 更新 ECS 服务强制新部署

```bash
./scripts/build-and-push.sh
aws ecs update-service --cluster <cluster> --service <service> --force-new-deployment
```

### 扩缩容

```bash
# 扩展 API 服务
aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service nexus-ai-api-prod \
  --desired-count 4

# 缩减服务
aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service nexus-ai-api-prod \
  --desired-count 1
```

## 🐛 故障排查

### 服务无法启动

1. 检查 CloudWatch Logs
2. 检查 ECS 任务状态: `aws ecs describe-tasks --cluster <cluster> --tasks <task-id>`
3. 检查安全组规则
4. 检查 EFS 挂载点

### Redis 连接失败

1. 确认 Redis 服务正在运行
2. 检查服务发现配置
3. 检查安全组允许 6379 端口
4. 查看 Redis 容器日志

### EFS 挂载失败

1. 检查 EFS 挂载目标状态
2. 检查安全组规则（端口 2049）
3. 检查 IAM 角色权限
4. 确认 EFS 访问点配置

## 💰 成本估算

基于默认配置的预估月成本（us-east-1）：
- ECS Fargate (API: 2x 1vCPU/2GB, Frontend: 2x 0.5vCPU/1GB, Workers: 4x 2vCPU/4GB, Redis: 1x 0.5vCPU/1GB): ~$150-200
- ALB: ~$20
- EFS (10GB): ~$3
- NAT Gateway: ~$32
- DynamoDB: ~$12
- CloudWatch Logs: ~$5-10

**总计**: ~$230-280/月

## 📚 相关文档

- [ECS Fargate 文档](https://docs.aws.amazon.com/ecs/latest/developerguide/AWS_Fargate.html)
- [EFS 文档](https://docs.aws.amazon.com/efs/)
- [Application Load Balancer](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/)

