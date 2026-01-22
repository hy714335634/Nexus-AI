# Nexus-AI 标准镜像构建方案

## 概述

本方案为 Nexus-AI 平台设计标准化的 Docker 镜像构建流程，涵盖三个核心服务：
- **API 服务** (FastAPI) - 后端 API 接口
- **Worker 服务** (Python) - 异步任务处理
- **Web 服务** (Next.js) - 前端界面

## 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                    Nexus-AI 镜像架构                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │   nexus-base     │  │   nexus-base     │  │  node:18-alpine│ │
│  │  (Python 3.13)   │  │  (Python 3.13)   │  │                │ │
│  └────────┬─────────┘  └────────┬─────────┘  └───────┬────────┘ │
│           │                     │                     │          │
│           ▼                     ▼                     ▼          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │   nexus-api      │  │  nexus-worker    │  │   nexus-web    │ │
│  │   Port: 8000     │  │   (SQS Consumer) │  │   Port: 3000   │ │
│  └──────────────────┘  └──────────────────┘  └────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 镜像分层策略

### 1. 基础镜像 (nexus-base)

共享的 Python 基础镜像，包含：
- Python 3.13 运行时
- 系统依赖 (git, curl, etc.)
- 公共 Python 依赖
- nexus_utils 核心模块

### 2. 服务镜像

| 服务 | 基础镜像 | 端口 | 入口点 |
|------|----------|------|--------|
| API | nexus-base | 8000 | uvicorn |
| Worker | nexus-base | - | python -m worker.main |
| Web | node:18-alpine | 3000 | node server.js |

## 目录结构

```
docker/
├── base/
│   └── Dockerfile           # Python 基础镜像
├── api/
│   └── Dockerfile           # API 服务镜像
├── worker/
│   └── Dockerfile           # Worker 服务镜像
├── web/
│   └── Dockerfile           # Web 服务镜像 (已存在于 web/)
├── docker-compose.yml       # 本地开发编排
├── docker-compose.prod.yml  # 生产环境编排
└── .dockerignore            # 构建排除文件
```

## 环境变量规范

### 通用环境变量

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| AWS_REGION | AWS 区域 | us-west-2 |
| AWS_ACCESS_KEY_ID | AWS 访问密钥 | - |
| AWS_SECRET_ACCESS_KEY | AWS 密钥 | - |
| LOG_LEVEL | 日志级别 | INFO |

### API 服务特有

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| APP_VERSION | 应用版本 | 2.0.0 |
| DYNAMODB_ENDPOINT_URL | DynamoDB 端点 | - |
| SQS_ENDPOINT_URL | SQS 端点 | - |
| CORS_ORIGINS | CORS 允许源 | * |

### Worker 服务特有

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| WORKER_QUEUE_TYPE | 队列类型 | build |
| POLL_INTERVAL_SECONDS | 轮询间隔 | 5 |
| VISIBILITY_TIMEOUT | 可见性超时 | 3600 |

### Web 服务特有

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| NEXT_PUBLIC_API_URL | API 地址 | http://api:8000 |
| NODE_ENV | 运行环境 | production |

## 构建命令

```bash
# 构建基础镜像
docker build -f docker/base/Dockerfile -t nexus-base:latest .

# 构建 API 镜像
docker build -f docker/api/Dockerfile -t nexus-api:latest .

# 构建 Worker 镜像
docker build -f docker/worker/Dockerfile -t nexus-worker:latest .

# 构建 Web 镜像
docker build -f web/Dockerfile -t nexus-web:latest web/

# 一键构建所有镜像
./docker/build.sh
```

## 健康检查

| 服务 | 端点 | 检查方式 |
|------|------|----------|
| API | /health | HTTP GET |
| Worker | - | 进程存活检查 |
| Web | / | HTTP GET |

## 安全最佳实践

1. **非 root 用户运行** - 所有服务使用非特权用户
2. **最小化镜像** - 使用 Alpine 基础镜像
3. **多阶段构建** - 分离构建和运行环境
4. **敏感信息** - 通过环境变量或 Secrets Manager 注入
5. **镜像扫描** - ECR 推送时自动扫描漏洞

## 快速开始

### 本地开发

```bash
# 1. 复制环境变量配置
cp .env.example .env

# 2. 编辑 .env 文件，填写 AWS 凭证

# 3. 启动所有服务
docker-compose up -d

# 4. 查看服务状态
docker-compose ps

# 5. 查看日志
docker-compose logs -f api
```

### 构建镜像

```bash
# 给构建脚本添加执行权限
chmod +x build.sh

# 构建所有镜像
./build.sh

# 只构建 API 镜像
./build.sh api

# 构建并推送到 ECR
export ECR_REGISTRY=123456789012.dkr.ecr.us-west-2.amazonaws.com
./build.sh --push
```

### 生产部署

```bash
# 设置环境变量
export ECR_REGISTRY=123456789012.dkr.ecr.us-west-2.amazonaws.com
export IMAGE_TAG=v2.0.0
export EFS_DNS_NAME=fs-xxxxxxxx.efs.us-west-2.amazonaws.com

# 使用生产配置启动
docker-compose -f docker-compose.prod.yml up -d
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `base/Dockerfile` | Python 基础镜像（共享依赖） |
| `api/Dockerfile` | API 服务镜像（基于 base） |
| `worker/Dockerfile` | Worker 服务镜像（基于 base） |
| `Dockerfile.api` | API 独立多阶段构建 |
| `Dockerfile.worker` | Worker 独立多阶段构建 |
| `docker-compose.yml` | 本地开发编排 |
| `docker-compose.prod.yml` | 生产环境编排 |
| `build.sh` | 镜像构建脚本 |
| `.dockerignore` | 构建排除文件 |
| `.env.example` | 环境变量示例 |

## 与现有 Terraform 集成

现有的 `infrastructure/basic/04-compute-docker-build.tf` 可以修改为使用这些标准 Dockerfile：

```hcl
# 修改 API 镜像构建命令
docker build --platform linux/amd64 \
  -f tests/docker/Dockerfile.api \
  -t ${aws_ecr_repository.api.repository_url}:latest .

# 添加 Worker 镜像构建
docker build --platform linux/amd64 \
  -f tests/docker/Dockerfile.worker \
  -t ${aws_ecr_repository.worker.repository_url}:latest .
```

## 下一步

1. ✅ 创建 Dockerfile 文件
2. ✅ 配置 docker-compose 本地开发环境
3. 集成 CI/CD 流水线 (GitHub Actions / CodePipeline)
4. 更新 Terraform 配置使用新镜像
5. 添加 Worker 服务的 ECR 仓库和 ECS 任务定义
