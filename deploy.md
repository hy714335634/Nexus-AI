# 部署与运行指南

本文档介绍当前 Nexus-AI 项目的部署方式，包括本地虚拟环境运行、Celery Worker、FastAPI 应用以及 Docker Compose 方案。

## 1. 环境准备

### 1.1 系统依赖
- Python 3.12（或与仓库 `venv` 一致的版本）
- Docker & Docker Compose（可选）
- DynamoDB（可使用 AWS 或本地 dynamodb-local）
- AWS CLI / boto3（部署到 AgentCore 时需要）
- Amazon Bedrock AgentCore Python SDK（`pip install bedrock-agentcore-starter-toolkit`）和 Strands SDK

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

### 1.5 OpenTelemetry（可选）
- 模板默认将 `OTEL_EXPORTER_OTLP_ENDPOINT` 设为 `http://localhost:4318`。若未启动 OTLP Collector，会出现 `Connection refused` 警告，但不影响主流程。
- 处理方式：
  1. **启动 Collector**（推荐）：
     - 本地安装：
       ```bash
       # 安装 otelcol 后，在仓库根目录运行
       otelcol --config otel-collector-config.yaml
       ```
     - 使用 Docker（无需本地安装）：
       ```bash
       docker run --rm -p 4318:4318 \
         -v "$(pwd)/otel-collector-config.yaml:/etc/otelcol/config.yaml" \
         otel/opentelemetry-collector:latest
       ```
     工程自带的配置会监听 `0.0.0.0:4318`，可按需修改。
  2. **禁用遥测**：在启动服务前覆盖环境变量，如
     ```bash
     export OTEL_EXPORTER_OTLP_ENDPOINT=
     export STRANDS_TELEMETRY_DISABLED=true  # 若使用 Strands SDK
     ```
     此时模板里的 `setdefault` 将不会尝试连接。

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

## 3. Amazon Bedrock AgentCore 部署

> 适用于需要在 AWS 托管环境运行 Agent 的场景，可直接复用官方教程 “Hosting Strands Agents with Amazon Bedrock models in Amazon Bedrock AgentCore Runtime”。

### 3.1 额外前置条件
- AWS 账户 & 对应 CLI 凭证（有 `bedrock:CreateAgent`、`iam:CreateRole`、`ecr:*` 等权限）
- 已配置 `aws configure`，或在 `.env` 中提供可用的 AWS Key
- 能访问 Amazon Bedrock 所在区域（默认 `us-west-2`）

### 3.2 准备部署产物
1. 生成的 Agent 代码、Prompt、工具目录（`agents/generated_agents/...`、`prompts/generated_agents_prompts/...`、`tools/generated_tools/...`）。
2. 部署用 `requirements.txt`：在根目录依赖基础上追加 Agent 专属依赖。
3. Docker 构建上下文：Starter Toolkit 会自动生成 Dockerfile；如需自定义，可参考 `01-strands-with-bedrock-model/Dockerfile`。
4. `.bedrock_agentcore.yaml`（可选）：`configure()` 会在项目根目录生成，可提交以复用统一配置。

### 3.3 Starter Toolkit 流程
```python
from bedrock_agentcore_starter_toolkit import Runtime

runtime = Runtime(project_root="/Users/xxx/Nexus-AI")
runtime.configure(
    entrypoint="agents/generated_agents/foo/foo_agent.py",
    requirements_file="requirements.txt",
    region="us-west-2",
    agent_name="foo-agent",
    image_tag="foo-agent:latest",      # 可选：自定义镜像标签
    docker_context=".",               # 默认当前目录
    auto_create_execution_role=True,
    auto_create_ecr=True,
)
launch_result = runtime.launch()        # 构建镜像 + 推送 ECR + 创建 Runtime
status = runtime.status()               # 轮询直到 READY
runtime.invoke({"prompt": "Hello"})    # 快速自测
```
- `configure()` 会生成 `.bedrock_agentcore.yaml` 与 Dockerfile，可按需调整。
- `launch()` 失败时检查 Docker 构建日志、ECR 推送和 IAM 权限。
- `status()` 返回 `READY` 才表示部署成功；其他状态需在 CloudWatch Logs 中排查。
- 成功后的 `agentRuntimeArn`、alias 等信息需要写入 DynamoDB `AgentInstances`。

### 3.4 boto3 调用示例
```python
import boto3, json

client = boto3.client("bedrock-agentcore", region_name="us-west-2")
response = client.invoke_agent_runtime(
    agentRuntimeArn=launch_result.agent_arn,
    qualifier="DEFAULT",
    payload=json.dumps({"prompt": "What is 2+2?"})
)
# 视 contentType 解析文本或流式事件
```

### 3.5 部署信息回写
- `deployment_type` → `agentcore`
- `deployment_status` → `deployed`
- `agentcore_arn`、`agentcore_alias`、`region`、`last_deployed_at` → 存入 DynamoDB
- 部署失败时，记录 `deployment_status=failed` 及 `last_deployment_error`
- 建议封装 Celery 任务或后台操作，确保部署结束后数据库状态与实际一致

## 4. Docker Compose 方案

项目提供 `docker-compose.yml` 以支持容器化部署。典型文件结构：
- `api` 服务：运行 FastAPI 应用
- `worker` 服务：运行 Celery Worker
- `redis` / `rabbitmq`：消息队列（视配置而定）
- `dynamodb`（可选）：本地 DynamoDB

### 4.1 启动 Compose
```bash
docker compose up -d
```
说明：
- 确保 `.env` 文件对容器可见（如通过 `env_file` 或 bind mount）
- 若需查看日志：`docker compose logs -f api`、`docker compose logs -f worker`
- 可用 `docker compose down` 停止服务

### 4.2 常见挂载与网络
- 源码通常以 `volumes: - ./:/app` 的方式挂载进容器，便于热更新
- 若使用本地 DynamoDB，可在 Compose 中暴露端口 8000，并在 `.env` 中配置 `DYNAMODB_ENDPOINT=http://dynamodb:8000`

## 5. 验证流程

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
4. **与 Agent 对话**（在运行时服务完成后）
   - 通过 `AgentInstances` 读取 `deployment_type`
   - 若为 `local`：加载 `entrypoint` 模块调用 `invoke`
   - 若为 `agentcore`：使用 boto3 `invoke_agent_runtime`
5. **AgentCore 验证**
   - `runtime.invoke()` 或 boto3 调用返回正确响应
   - DynamoDB 中 `deployment_status` 更新为 `deployed`
   - CloudWatch Logs（或 Starter Toolkit 控制台）无报错

## 6. 故障排查

- **Celery Worker 无法导入模块**：确保使用虚拟环境里的 `celery` 命令；检查 `PYTHONPATH`
- **DynamoDB 连接失败**：确认 `.env` 的 endpoint、AWS 凭证；若本地运行 DynamoDB Local，确保端口 8000 已开放
- **阶段进度一直停留在 pending**：确认 `tools/system_tools/agent_build_workflow/project_manager.py` 的 `_sync_stage_progress` 是否被触发
- **/api/v1/agents 空列表**：当前构建流程尚未写入 `AgentInstances`；需补充元数据写入逻辑
- **AgentCore 部署失败**：检查 Starter Toolkit 输出的 Docker 构建日志、ECR 推送、IAM 权限，以及 `runtime.status()` 返回的错误消息
- **AgentCore 调用无返回**：确认 payload JSON、`qualifier`、Region 设置，必要时在 CloudWatch Logs 中排查容器日志

## 7. 后续工作

- 在构建流程结束后，写入 Agent 元数据（entrypoint、能力等）
- 封装统一的 `AgentRuntimeService`，提供 `/agents/{agent_id}/messages` 等接口
- 模板化生成的 Agent 代码，确保新产物都具备统一接口
- 在构建/部署流程中增加 `deployment_status`、`agentcore_arn` 等字段的写入
- 完成 `AgentRuntimeService` 对 AgentCore 调用路径的整合与鉴权

---

以上为当前部署与使用指南，后续如引入新的服务或部署方式，可在此文档基础上补充更新。
