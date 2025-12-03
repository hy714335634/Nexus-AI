# Nexus-AI 快速部署指南

本文档提供清晰的步骤指导，帮助你快速启动 Nexus-AI 项目的所有服务。

## 📋 前置要求

- Python 3.12+
- Node.js 18+
- Docker（用于 OpenTelemetry Collector）
- Redis（Celery 消息队列）
- AWS 账户和凭证（用于 Bedrock）

## 🚀 快速启动（5 步）

### 1. 启动 Docker 服务（必需）

使用 Docker Compose 启动所有 Docker 服务：

```bash
docker-compose up -d
```

这会启动：

- **Redis 服务**（端口 6379）- Celery 消息队列
- **Redis Commander**（端口 8081）- Redis 管理界面（可选）
- **OpenTelemetry Collector**（端口 4318）- 遥测数据收集（可选）

验证服务是否启动：

```bash
docker-compose ps
# 或访问 http://localhost:8081 查看 Redis Commander
```

### 2. 环境配置

```bash
# 激活 Python 虚拟环境
source venv/bin/activate

# 配置 AWS 凭证（如果还没配置）
aws configure
```

确保 `api/.env` 文件已正确配置：

```env
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-west-2
DYNAMODB_ENDPOINT=http://localhost:8000  # 或使用 AWS DynamoDB
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### 3. 启动 Celery Worker（后台任务处理 - 必需）

在**新终端窗口**中运行：

```bash
source venv/bin/activate
celery -A api.core.celery_app.celery_app worker \
  -Q agent_builds,status_updates \
  --loglevel=info \
  --logfile=logs/celery.log
```

> 📝 确保 `logs/` 目录存在：`mkdir -p logs`

### 4. 启动 FastAPI 后端服务（必需）

在**新终端窗口**中运行：

```bash
source venv/bin/activate
uvicorn api.main:app --reload
```

服务将在 `http://localhost:8000` 启动

### 5. 启动前端开发服务器（必需）

在**新终端窗口**中运行：

```bash
cd web
npm run dev
```

前端将在 `http://localhost:3000` 启动（或其他端口，查看终端输出）

## ✅ 验证部署

### 检查后端 API

```bash
# 健康检查
curl http://localhost:8000/health

# 创建测试 Agent
curl -X POST http://localhost:8000/api/v1/agents/create \
  -H 'Content-Type: application/json' \
  -d '{
    "requirement": "创建一个简单的问答助手",
    "user_id": "test_user",
    "user_name": "测试用户"
  }'
```

### 检查服务状态

打开浏览器访问：

- 后端 API 文档：http://localhost:8000/docs
- 前端应用：http://localhost:3000

## 📊 服务概览

| 服务            | 端口 | 用途                       | 必需    | 启动方式                                          |
| --------------- | ---- | -------------------------- | ------- | ------------------------------------------------- |
| Redis           | 6379 | Celery 消息队列            | ✅ 是   | `docker-compose up -d`                            |
| Redis Commander | 8081 | Redis 管理界面             | ⚪ 可选 | `docker-compose up -d`                            |
| OpenTelemetry   | 4318 | 遥测数据收集               | ⚪ 可选 | `docker-compose up -d`                            |
| Celery Worker   | -    | 异步任务处理（Agent 构建） | ✅ 是   | `celery -A api.core.celery_app.celery_app worker` |
| FastAPI         | 8000 | 后端 API 服务              | ✅ 是   | `uvicorn api.main:app --reload`                   |
| Web Frontend    | 3000 | 前端界面                   | ✅ 是   | `cd web && npm run dev`                           |

## 🔧 常见问题

### Q: Celery Worker 无法启动？

**A:** 确保已激活虚拟环境并安装了所有依赖：

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Q: OpenTelemetry 连接失败警告？

**A:** 这不影响主要功能。如果不需要遥测，可以设置环境变量：

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=
export STRANDS_TELEMETRY_DISABLED=true
```

### Q: DynamoDB 连接失败？

**A:** 检查 `api/.env` 中的 `DYNAMODB_ENDPOINT` 配置：

- 使用本地 DynamoDB：`http://localhost:8000`
- 使用 AWS DynamoDB：留空或设置为 AWS endpoint

### Q: Redis 连接失败？

**A:** 确保 Redis 服务已通过 docker-compose 启动：

```bash
# 启动 Redis
docker-compose up -d

# 检查 Redis 状态
docker ps | grep redis

# 查看 Redis 日志
docker-compose logs redis
```

## 🛑 停止服务

### 停止 Python 服务

在每个终端窗口中按 `Ctrl+C` 停止：

- Celery Worker
- FastAPI 后端
- 前端开发服务器

### 停止 Docker 服务

```bash
# 停止所有 Docker 服务（Redis、Redis Commander、OpenTelemetry Collector）
docker-compose down

# 如果需要同时删除数据卷
docker-compose do中的容器
docker stop <container_id>  # 停止特定容器
```

## 📚 下一步

- 查看 [API 文档](http://localhost:8000/docs) 了解可用接口
- 阅读 [系统指南](../../NEXUS_AI_SYSTEM_GUIDE.md) 了解系统架构
- 查看 [Agent 运行时设计](../../architecture/agent_runtime_design.md) 了解 Agent 运行时设计

### Redis Commander

访问 http://localhost:8081 可以查看 Redis 的数据和状态，方便调试 Celery 任务。

---

**需要帮助？** 查看详细的 [本地开发指南](./LOCAL_DEVELOPMENT.md) 或提交 Issue。
