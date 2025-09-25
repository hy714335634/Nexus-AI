# 部署与运行指南

本文档介绍当前 Nexus-AI 项目的部署方式，包括本地虚拟环境运行、Celery Worker、FastAPI 应用以及 Docker Compose 方案。

## 1. 环境准备

### 1.1 系统依赖
- Python 3.12（或与仓库 `venv` 一致的版本）
- Docker & Docker Compose（可选）
- DynamoDB（可使用 AWS 或本地 dynamodb-local）

### 1.2 克隆仓库
```bash
git clone <repo-url>
cd Nexus-AI
```

### 1.3 虚拟环境
项目根目录已有 `venv/`，建议直接启用：
```bash
source venv/bin/activate
```

若需自建虚拟环境，可运行：
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 1.4 环境变量（.env）
`api/.env` 包含 API、数据库等配置，关键条目包括：
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `DYNAMODB_ENDPOINT`（指向本地或云端 DynamoDB）
- `CELERY_BROKER_URL`、`CELERY_RESULT_BACKEND`
- 其他业务相关变量

确保 `.env` 已正确填写；若使用本地 DynamoDB，可例如使用：
```env
DYNAMODB_ENDPOINT=http://localhost:8000
AWS_ACCESS_KEY_ID=dummy
AWS_SECRET_ACCESS_KEY=dummy
AWS_REGION=us-east-1
```

## 2. 本地运行服务

### 2.1 启动 FastAPI
```bash
source venv/bin/activate
uvicorn api.main:app --reload
```
- 默认监听 `http://127.0.0.1:8000`
- 支持热更新，适合开发调试

### 2.2 启动 Celery Worker
使用虚拟环境中的 `celery` 命令，避免缺包问题：
```bash
source venv/bin/activate
celery -A api.core.celery_app.celery_app worker \
       -Q agent_builds,status_updates \
       --loglevel=info \
       --logfile=logs/celery.log
```
说明：
- `-Q agent_builds,status_updates`：监听构建任务队列
- `--logfile=logs/celery.log`：将 Worker 日志写入 `logs/celery.log`
- 若日志目录不存在，可先 `mkdir -p logs`

### 2.3 任务流程
1. `POST /api/v1/agents/create` → 创建构建任务
2. Celery Worker 读取任务，执行 CLI 工作流
3. 构建期间，阶段进度同步到 DynamoDB `projects_table`
4. 可通过 `/api/v1/agents/{task_id}/status` 查询任务状态

## 3. Docker Compose 方案

项目提供 `docker-compose.yml` 以支持容器化部署。典型文件结构：
- `api` 服务：运行 FastAPI 应用
- `worker` 服务：运行 Celery Worker
- `redis` / `rabbitmq`：消息队列（视配置而定）
- `dynamodb`（可选）：本地 DynamoDB

### 3.1 启动 Compose
```bash
docker compose up -d
```
说明：
- 确保 `.env` 文件对容器可见（如通过 `env_file` 或 bind mount）
- 若需查看日志：`docker compose logs -f api`、`docker compose logs -f worker`
- 可用 `docker compose down` 停止服务

### 3.2 常见挂载与网络
- 源码通常以 `volumes: - ./:/app` 的方式挂载进容器，便于热更新
- 若使用本地 DynamoDB，可在 Compose 中暴露端口 8000，并在 `.env` 中配置 `DYNAMODB_ENDPOINT=http://dynamodb:8000`

## 4. 验证流程

1. **创建 Agent**
   ```bash
   curl -X POST http://localhost:8000/api/v1/agents/create \
        -H 'Content-Type: application/json' \
        -d '{"requirement": "创建一个健身顾问 Agent", "user_id": "tester"}'
   ```
2. **查询任务状态**
   ```bash
   curl http://localhost:8000/api/v1/agents/<task_id>/status
   ```
3. **查看阶段快照**
   ```bash
   curl http://localhost:8000/api/v1/agents/<project_id>/stages
   ```
4. **与 Agent 对话**（需在后续实现 API / 元数据写入后）
   - 通过 `agents_table` 获取 Agent 的 `entrypoint`
   - 向 `/api/v1/agents/{agent_id}/messages` 之类的接口发送请求（待开发）

## 5. 故障排查

- **Celery Worker 无法导入模块**：确保使用虚拟环境里的 `celery` 命令；检查 `PYTHONPATH`
- **DynamoDB 连接失败**：确认 `.env` 的 endpoint、AWS 凭证；若本地运行 DynamoDB Local，确保端口 8000 已开放
- **阶段进度一直停留在 pending**：确认 `tools/system_tools/agent_build_workflow/project_manager.py` 的 `_sync_stage_progress` 是否被触发
- **/api/v1/agents 空列表**：当前构建流程尚未写入 `agents_table`；需补充元数据写入逻辑

## 6. 后续工作

- 在构建流程结束后，写入 Agent 元数据（entrypoint、能力等）
- 封装统一的 `AgentRuntimeService`，提供 `/agents/{agent_id}/messages` 等接口
- 模板化生成的 Agent 代码，确保新产物都具备统一接口

---

以上为当前部署与使用指南，后续如引入新的服务或部署方式，可在此文档基础上补充更新。
