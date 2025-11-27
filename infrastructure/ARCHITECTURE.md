# Nexus-AI AWS 高可用架构设计

## 🏗️ 架构图

```
Internet
   │
   ▼
[Application Load Balancer]
   │
   ├─── /api/* ──────► [API Service] (ECS Fargate, 多实例)
   │                      │
   │                      ├─── DynamoDB
   │                      ├─── SQS
   │                      └─── Redis (容器)
   │
   └─── /* ──────────► [Frontend Service] (ECS Fargate, 多实例)
                           │
                           └─── EFS (共享存储)

[Celery Worker - agent_builds] (ECS Fargate, 多实例)
   │
   ├─── Redis (容器)
   ├─── DynamoDB
   └─── EFS (共享存储)

[Celery Worker - status_updates] (ECS Fargate, 多实例)
   │
   ├─── Redis (容器)
   ├─── DynamoDB
   └─── EFS (共享存储)

[Redis Service] (ECS Fargate, 单实例)
   │
   └─── EFS (持久化数据)
```

## 📦 组件说明

### 网络层
- **VPC**: 10.0.0.0/16
  - 公有子网: 10.0.10.0/24, 10.0.11.0/24 (ALB)
  - 私有子网: 10.0.20.0/24, 10.0.21.0/24 (ECS)
- **NAT Gateway**: 私有子网访问互联网
- **Internet Gateway**: 公有子网访问互联网

### 计算层
- **ECS Fargate Cluster**: 容器编排
- **服务**:
  - API: FastAPI 应用，2+ 实例
  - Frontend: Next.js 应用，2+ 实例
  - Celery Worker (agent_builds): 构建任务处理，2+ 实例
  - Celery Worker (status_updates): 状态更新处理，2+ 实例
  - Redis: 缓存和消息队列，1 实例

### 存储层
- **EFS**: 共享文件系统
  - 所有容器挂载到 `/mnt/efs`
  - 用于共享构建产物和数据
- **DynamoDB**: 结构化数据存储
- **SQS**: 异步消息队列

### 负载均衡
- **Application Load Balancer**:
  - `/api/*` → API 服务
  - `/docs`, `/redoc` → API 服务
  - `/*` → Frontend 服务

## 🔐 安全

### 安全组
- **ALB SG**: 允许 80/443 入站
- **ECS SG**: 
  - 允许来自 ALB 的流量 (8000, 3000)
  - 允许容器间通信 (6379 for Redis)
- **EFS SG**: 允许来自 ECS 的流量 (2049)

### IAM 角色
- **ECS Task Execution Role**: 
  - ECR 拉取镜像
  - CloudWatch Logs 写入
  - EFS 挂载
- **ECS Task Role**:
  - DynamoDB 访问
  - SQS 访问
  - Bedrock 访问
  - EFS 访问

## 🔄 服务发现

使用 AWS Service Discovery，服务间通过 DNS 名称通信：
- `redis.nexus-ai.local:6379`
- `api.nexus-ai.local:8000`

## 📊 高可用设计

1. **多可用区部署**: 所有资源跨 2 个可用区
2. **多实例服务**: API、Frontend、Workers 都运行多个实例
3. **负载均衡**: ALB 自动分发流量
4. **自动恢复**: ECS 自动重启失败的任务
5. **健康检查**: 所有服务都有健康检查

## 🚨 注意事项

### 代码兼容性
- ✅ **未修改业务代码**: 所有 Terraform 配置和 Dockerfile 都是新增的
- ✅ **环境变量兼容**: 使用现有的环境变量配置
- ✅ **EFS 路径**: 代码中使用 `/mnt/efs` 路径，与配置一致

### 潜在问题
1. **Redis 服务发现**: 确保服务启动顺序（Redis 先启动）
2. **EFS 性能**: 大量小文件可能影响性能，考虑使用 EFS IA
3. **ALB SSL**: 当前配置使用 HTTP，生产环境需要配置 SSL 证书
4. **Redis 持久化**: Redis 数据存储在 EFS，注意备份策略

### 待完善
- [ ] SSL/TLS 证书配置（ACM）
- [ ] 自动扩缩容策略（Auto Scaling）
- [ ] 备份策略
- [ ] 监控告警
- [ ] CI/CD 流水线

## 📝 文件结构

```
infrastructure/
├── 01-networking.tf          # VPC, 子网, 安全组
├── 02-storage-dynamodb.tf    # DynamoDB 表
├── 02-storage-efs.tf         # EFS 文件系统
├── 03-messaging-sqs.tf       # SQS 队列
├── 04-compute-ecr.tf         # ECR 仓库
├── 04-compute-iam.tf         # IAM 角色和策略
├── 05-compute-ecs.tf         # ECS Cluster 和 Task Definitions
├── 06-loadbalancer.tf        # Application Load Balancer
├── 07-services.tf            # ECS Services 和 Service Discovery
├── main.tf                   # Provider 配置
├── variables.tf              # 变量定义
├── outputs.tf                # 输出值
├── versions.tf               # 版本约束
└── scripts/
    └── build-and-push.sh     # 构建和推送镜像脚本
```

## 🔗 相关文件

- `api/Dockerfile`: API 服务 Dockerfile（已更新，添加 curl）
- `web/Dockerfile`: Frontend 服务 Dockerfile（新建）
- `web/next.config.mjs`: Next.js 配置（已更新，启用 standalone）

