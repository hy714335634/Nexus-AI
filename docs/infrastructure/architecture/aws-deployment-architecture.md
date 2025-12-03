# Nexus-AI AWS 部署架构图

## 架构概览

本文档描述了 Nexus-AI 平台在 AWS 上的完整部署架构，包括网络、存储、计算和消息传递组件。

## 架构图

```mermaid
graph TB
    subgraph "Internet"
        Users[用户/客户端]
        Dev[开发者]
    end

    subgraph "AWS VPC (10.0.0.0/16)"
        subgraph "Public Subnets (10.0.10.0/24, 10.0.11.0/24)"
            ALB[Application Load Balancer<br/>ALB]
            IGW[Internet Gateway]
            NAT[NAT Gateway]
            Bastion[Bastion Host<br/>EC2 t4g.nano<br/>可选]
        end

        subgraph "Private Subnets (10.0.20.0/24, 10.0.21.0/24)"
            subgraph "ECS Fargate Cluster"
                subgraph "API Service (可选ECS模式)"
                    API1[API Container 1<br/>FastAPI :8000]
                    API2[API Container N<br/>FastAPI :8000]
                end
                
                subgraph "Frontend Service"
                    FE1[Frontend Container 1<br/>Next.js :3000]
                    FE2[Frontend Container N<br/>Next.js :3000]
                end
                
                subgraph "Celery Workers"
                    CW1[Celery Worker 1<br/>agent_builds队列]
                    CW2[Celery Worker 2<br/>status_updates队列]
                end
                
                Redis[Redis Container<br/>:6379]
            end
            
            subgraph "EC2 API Service (可选EC2模式)"
                EC2_API1[EC2 Instance 1<br/>FastAPI :8000<br/>Docker-in-Docker]
                EC2_API2[EC2 Instance N<br/>FastAPI :8000<br/>Docker-in-Docker]
            end
            
            EFS[EFS File System<br/>共享存储<br/>/mnt/efs]
        end

        subgraph "AWS Managed Services"
            subgraph "DynamoDB Tables"
                DDB1[AgentProjects<br/>项目记录]
                DDB2[AgentInstances<br/>Agent实例]
                DDB3[AgentInvocations<br/>调用记录]
                DDB4[AgentSessions<br/>会话记录]
                DDB5[AgentSessionMessages<br/>会话消息]
            end
            
            SQS[SQS Queue<br/>通知队列]
            SQS_DLQ[SQS DLQ<br/>死信队列]
            
            subgraph "ECR Repositories"
                ECR_API[nexus-ai-api]
                ECR_FE[nexus-ai-frontend]
                ECR_CW[nexus-ai-celery-worker]
            end
            
            CloudWatch[CloudWatch Logs<br/>日志收集]
            
            SD[Service Discovery<br/>nexus-ai.local<br/>内部服务发现]
        end
    end

    %% 用户访问流
    Users -->|HTTP/HTTPS| ALB
    Dev -->|SSH :22| Bastion
    
    %% ALB路由
    ALB -->|/api/*, /docs/*| API1
    ALB -->|/api/*, /docs/*| API2
    ALB -->|/api/*, /docs/* (EC2模式)| EC2_API1
    ALB -->|/api/*, /docs/* (EC2模式)| EC2_API2
    ALB -->|其他路径| FE1
    ALB -->|其他路径| FE2
    
    %% 网络连接
    IGW -.->|出站| NAT
    NAT -.->|出站| API1
    NAT -.->|出站| API2
    NAT -.->|出站| FE1
    NAT -.->|出站| FE2
    NAT -.->|出站| CW1
    NAT -.->|出站| CW2
    
    %% API服务连接 (ECS模式)
    API1 -->|读写| DDB1
    API1 -->|读写| DDB2
    API1 -->|读写| DDB3
    API1 -->|读写| DDB4
    API1 -->|读写| DDB5
    API1 -->|发送消息| SQS
    API1 -->|任务队列| Redis
    API1 -->|挂载| EFS
    API1 -->|服务发现| SD
    
    API2 -->|读写| DDB1
    API2 -->|读写| DDB2
    API2 -->|读写| DDB3
    API2 -->|读写| DDB4
    API2 -->|读写| DDB5
    API2 -->|发送消息| SQS
    API2 -->|任务队列| Redis
    API2 -->|挂载| EFS
    API2 -->|服务发现| SD
    
    %% EC2 API服务连接
    EC2_API1 -->|读写| DDB1
    EC2_API1 -->|读写| DDB2
    EC2_API1 -->|读写| DDB3
    EC2_API1 -->|读写| DDB4
    EC2_API1 -->|读写| DDB5
    EC2_API1 -->|发送消息| SQS
    EC2_API1 -->|任务队列| Redis
    EC2_API1 -->|挂载| EFS
    EC2_API1 -->|构建镜像| ECR
    
    EC2_API2 -->|读写| DDB1
    EC2_API2 -->|读写| DDB2
    EC2_API2 -->|读写| DDB3
    EC2_API2 -->|读写| DDB4
    EC2_API2 -->|读写| DDB5
    EC2_API2 -->|发送消息| SQS
    EC2_API2 -->|任务队列| Redis
    EC2_API2 -->|挂载| EFS
    EC2_API2 -->|构建镜像| ECR
    
    %% Frontend连接
    FE1 -->|API调用| ALB
    FE1 -->|挂载| EFS
    FE2 -->|API调用| ALB
    FE2 -->|挂载| EFS
    
    %% Celery Worker连接
    CW1 -->|消费任务| Redis
    CW1 -->|读写| DDB1
    CW1 -->|读写| DDB2
    CW1 -->|发送消息| SQS
    CW1 -->|挂载| EFS
    CW1 -->|服务发现| SD
    
    CW2 -->|消费任务| Redis
    CW2 -->|读写| DDB1
    CW2 -->|读写| DDB2
    CW2 -->|发送消息| SQS
    CW2 -->|挂载| EFS
    CW2 -->|服务发现| SD
    
    %% Redis连接
    API1 -->|缓存/消息队列| Redis
    API2 -->|缓存/消息队列| Redis
    CW1 -->|缓存/消息队列| Redis
    CW2 -->|缓存/消息队列| Redis
    
    %% SQS死信队列
    SQS -.->|失败消息| SQS_DLQ
    
    %% ECR镜像
    ECR_API -.->|拉取镜像| API1
    ECR_API -.->|拉取镜像| API2
    ECR_FE -.->|拉取镜像| FE1
    ECR_FE -.->|拉取镜像| FE2
    ECR_CW -.->|拉取镜像| CW1
    ECR_CW -.->|拉取镜像| CW2
    
    %% 日志
    API1 -->|日志| CloudWatch
    API2 -->|日志| CloudWatch
    FE1 -->|日志| CloudWatch
    FE2 -->|日志| CloudWatch
    CW1 -->|日志| CloudWatch
    CW2 -->|日志| CloudWatch
    Redis -->|日志| CloudWatch
    
    %% 样式
    classDef publicSubnet fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef privateSubnet fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef compute fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef storage fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef network fill:#fff9c4,stroke:#f57f17,stroke-width:2px
    
    class ALB,IGW,NAT,Bastion publicSubnet
    class API1,API2,FE1,FE2,CW1,CW2,Redis,EFS privateSubnet
    class DDB1,DDB2,DDB3,DDB4,DDB5,SQS,SQS_DLQ,ECR_API,ECR_FE,ECR_CW storage
    class CloudWatch,SD network
```

## 组件说明

### 1. 网络层 (Networking)

#### VPC
- **CIDR**: 10.0.0.0/16
- **用途**: 隔离的虚拟网络环境

#### 公共子网 (Public Subnets)
- **CIDR**: 10.0.10.0/24, 10.0.11.0/24
- **用途**: 
  - 托管 Application Load Balancer (ALB)
  - 托管 NAT Gateway
  - 可选：Bastion Host (跳板机)

#### 私有子网 (Private Subnets)
- **CIDR**: 10.0.20.0/24, 10.0.21.0/24
- **用途**: 
  - 托管所有 ECS Fargate 任务
  - 提供网络隔离，增强安全性

#### 网络组件
- **Internet Gateway**: 提供 VPC 与互联网的连接
- **NAT Gateway**: 允许私有子网中的资源访问互联网（用于拉取 Docker 镜像等）
- **Security Groups**: 
  - ALB Security Group: 允许 HTTP (80) 流量
  - ECS Security Group: 允许来自 ALB 的流量 (8000, 3000)
  - EFS Security Group: 允许来自 ECS 的 NFS 流量 (2049)
  - Bastion Security Group: 允许 SSH (22) 流量

### 2. 计算层 (Compute)

#### ECS Fargate Cluster
- **集群名称**: `nexus-ai-cluster-{environment}`
- **启动类型**: Fargate (无服务器容器)

#### API Service
- **部署方式**: EC2 实例（默认）
  - 使用 Auto Scaling Group 进行自动扩缩容
  - 通过 Launch Template 统一管理实例配置
  - 支持在运行时构建 Docker 镜像（Docker-in-Docker）
  - 使用 host 网络模式访问 EC2 IAM 角色凭证
- **容器/实例**: FastAPI 应用
- **端口**: 8000
- **功能**:
  - 提供 RESTful API
  - 处理 Agent 管理、项目创建、会话管理等
  - 与 DynamoDB 交互存储数据
  - 通过 SQS 发送通知
  - 使用 Redis 作为缓存和 Celery 消息队列
  - 支持在实例上构建 Docker 镜像（Docker-in-Docker）

#### Frontend Service
- **容器**: Next.js 应用
- **端口**: 3000
- **健康检查**: 仅依赖 ALB 健康检查（已移除容器级健康检查）
- **功能**:
  - 提供 Web 用户界面
  - 通过 ALB 调用后端 API

#### Celery Worker Services
- **队列1**: `agent_builds` - 处理 Agent 构建任务
- **队列2**: `status_updates` - 处理状态更新任务
- **功能**:
  - 异步处理长时间运行的任务
  - Agent 代码生成和构建
  - 项目状态更新

#### Redis Service
- **容器**: Redis 7 Alpine
- **端口**: 6379
- **功能**:
  - Celery 消息代理 (Broker)
  - Celery 结果后端 (Result Backend)
  - 应用缓存

### 3. 存储层 (Storage)

#### DynamoDB Tables
1. **AgentProjects**: 存储项目记录
   - 主键: `project_id`
   - GSI: `UserIndex`, `StatusIndex`

2. **AgentInstances**: 存储 Agent 实例
   - 主键: `agent_id`
   - GSI: `ProjectIndex`, `StatusIndex`, `CategoryIndex`

3. **AgentInvocations**: 存储 Agent 调用记录
   - 主键: `invocation_id`
   - GSI: `AgentInvocationIndex`

4. **AgentSessions**: 存储 Agent 会话
   - 主键: `agent_id` + `session_id`
   - GSI: `LastActiveIndex`

5. **AgentSessionMessages**: 存储会话消息
   - 主键: `session_id` + `created_at`

#### EFS (Elastic File System)
- **用途**: 共享文件存储
- **挂载点**: `/mnt/efs`
- **存储内容**:
  - `/mnt/efs/nexus-ai-repo/` - 完整的 git 仓库（所有 EC2 实例共享）
  - `/mnt/efs/projects/` - 用户项目数据
- **优势**:
  - 所有 EC2 实例共享同一份代码，只需 clone 一次
  - 统一代码版本，便于更新和维护
  - 节省磁盘空间和网络带宽

### 4. 消息传递层 (Messaging)

#### SQS Queue
- **队列名称**: `nexus-ai-notifications-{environment}`
- **用途**: 异步通知
- **配置**:
  - Visibility Timeout: 300秒
  - Message Retention: 4天

#### SQS Dead Letter Queue (DLQ)
- **队列名称**: `nexus-ai-notifications-dlq-{environment}`
- **用途**: 存储处理失败的消息
- **配置**:
  - Message Retention: 14天
  - Max Receive Count: 3

### 5. 容器镜像 (Container Images)

#### ECR Repositories
1. **nexus-ai-api-{environment}**: API 后端镜像
2. **nexus-ai-frontend-{environment}**: 前端镜像
3. **nexus-ai-celery-worker-{environment}**: Celery Worker 镜像

#### 生命周期策略
- 保留最近 10 个镜像
- 自动清理旧镜像

### 6. 负载均衡 (Load Balancing)

#### Application Load Balancer (ALB)
- **类型**: Application Load Balancer
- **监听器**: HTTP (80)
- **路由规则**:
  - `/api/*` → API Service
  - `/docs`, `/docs/*`, `/openapi.json`, `/redoc` → API Service
  - 其他路径 → Frontend Service
- **健康检查**:
  - API: `/health` 端点
  - Frontend: `/` 端点

### 7. 监控和日志 (Monitoring & Logging)

#### CloudWatch Logs
- **日志组**:
  - `/ecs/nexus-ai-api-{environment}`
  - `/ecs/nexus-ai-frontend-{environment}`
  - `/ecs/nexus-ai-celery-worker-{environment}`
  - `/ecs/nexus-ai-redis-{environment}`
- **保留期**: 7天 (Redis 3天)

#### ECS Container Insights
- 启用容器级别的监控和指标

### 8. 服务发现 (Service Discovery)

#### Cloud Map
- **命名空间**: `nexus-ai.local`
- **服务**:
  - `redis.nexus-ai.local`
  - `api.nexus-ai.local`
- **用途**: 容器间内部通信

### 9. 可选组件 (Optional)

#### Bastion Host
- **实例类型**: t4g.nano (ARM架构)
- **用途**: 
  - SSH 跳板机
  - 访问私有子网中的资源
  - 端口转发到 ALB 或 ECS 服务
- **配置**: 
  - 公共 IP (Elastic IP)
  - SSH 密钥认证

## 数据流

### 1. 用户请求流
```
用户 → Internet → ALB → API Service → DynamoDB
                              ↓
                          Redis (缓存)
                              ↓
                          SQS (通知)
```

### 2. Agent 构建流
```
API Service → Redis (Celery Queue) → Celery Worker
                                          ↓
                                    EFS (存储代码)
                                          ↓
                                    DynamoDB (更新状态)
                                          ↓
                                    SQS (发送通知)
```

### 3. 前端请求流
```
用户 → Internet → ALB → Frontend Service
                              ↓
                          ALB → API Service
```

### 4. 内部服务通信
```
API Service → Service Discovery → Redis
Celery Worker → Service Discovery → Redis
```

## 安全特性

1. **网络隔离**: 所有应用容器运行在私有子网
2. **安全组**: 严格控制入站和出站流量
3. **EFS 加密**: 传输加密启用
4. **IAM 角色**: 最小权限原则
5. **VPC 端点**: 可选的 AWS 服务私有连接

## 扩展性

1. **水平扩展**: ECS 服务可根据负载自动扩展
2. **多可用区**: 子网分布在多个可用区，提供高可用性
3. **DynamoDB**: 自动扩展读写容量
4. **EFS**: 自动扩展存储容量

## 部署流程

### 标准部署（ECS Fargate）

1. **Terraform 部署基础设施**
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

2. **构建和推送 Docker 镜像**
   - API 镜像 → ECR
   - Frontend 镜像 → ECR
   - Celery Worker 镜像 → ECR

3. **ECS 服务部署**
   - 自动从 ECR 拉取最新镜像
   - 创建任务定义
   - 启动服务

4. **验证**
   - 检查 ALB 健康检查
   - 验证 DynamoDB 连接
   - 测试 API 端点

### EC2 部署模式（默认）

1. **配置 Terraform 变量**
   ```hcl
   api_deploy_on_ec2 = true  # 默认值
   ec2_api_instance_type = "t3.xlarge"
   ec2_api_desired_capacity = 2
   ec2_api_key_name = "your-key-pair-name"  # 可选，用于 SSH 访问
   github_repo_url = "https://github.com/your-org/Nexus-AI.git"
   github_branch = "main"
   ```

2. **Terraform 部署基础设施**
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

3. **EC2 实例自动初始化**
   - 自动安装 Docker 和 Docker Compose
   - 自动挂载 EFS 文件系统
   - 第一个实例自动 clone git 仓库到 EFS
   - 后续实例直接使用 EFS 中的共享代码
   - 自动从 ECR 拉取 API 镜像
   - 自动启动 API 服务容器（host 网络模式）
   - 自动注册到 ALB Target Group

4. **验证**
   - 检查 ALB 健康检查
   - 验证 EC2 实例状态
   - 验证 DynamoDB 连接
   - 测试 API 端点
   - 验证 Docker 构建功能（如需要）

### EC2 部署的优势

- **Docker-in-Docker 支持**: EC2 实例可以运行 Docker daemon，支持在运行时构建 Docker 镜像
- **IAM 角色访问**: 使用 host 网络模式，容器可以直接访问 EC2 IAM 角色凭证
- **共享代码仓库**: 所有实例共享 EFS 中的 git 仓库，只需 clone 一次
- **更大的灵活性**: 可以直接访问文件系统，安装额外工具
- **更好的性能**: 对于需要大量计算资源的任务，可以使用更大的实例类型
- **自动扩缩容**: 通过 Auto Scaling Group 根据 CPU 使用率自动调整实例数量

## 配置变量

主要 Terraform 变量：
- `aws_region`: AWS 区域（默认 us-west-2）
- `project_name`: 项目名称前缀（默认 nexus-ai）
- `environment`: 环境 (dev/staging/prod)
- `api_deploy_on_ec2`: 是否在 EC2 上部署 API 服务（默认 true）
- `ec2_api_instance_type`: EC2 实例类型（默认 t3.xlarge）
- `ec2_api_min_size`: EC2 Auto Scaling 最小实例数（默认 1）
- `ec2_api_max_size`: EC2 Auto Scaling 最大实例数（默认 4）
- `ec2_api_desired_capacity`: EC2 Auto Scaling 期望实例数（默认 2）
- `ec2_api_key_name`: SSH 密钥对名称（用于访问 EC2 实例）
- `frontend_desired_count`: Frontend 服务实例数
- `celery_worker_desired_count`: Celery Worker 实例数
- `alb_allowed_cidr_blocks`: ALB 允许访问的 CIDR 块（默认 VPC CIDR）
- `github_repo_url`: Git 仓库 URL（用于 clone 到 EFS）
- `github_branch`: Git 分支（默认 main）

## 相关文件

- Terraform 配置: `infrastructure/*.tf`
- API 代码: `api/`
- Frontend 代码: `web/`
- Docker 配置: `api/Dockerfile`, `web/Dockerfile`

