# Nexus AI API v2 - 重构设计文档

## 架构概述

新架构将系统拆分为三个独立服务：

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Web Frontend  │────▶│   API Service   │────▶│  Worker Service │
│   (Next.js)     │     │   (FastAPI)     │     │   (Python)      │
└─────────────────┘     └────────┬────────┘     └────────┬────────┘
                                 │                       │
                        ┌────────▼────────┐     ┌────────▼────────┐
                        │    DynamoDB     │     │      SQS        │
                        │   (元数据存储)   │     │   (任务队列)     │
                        └─────────────────┘     └─────────────────┘
```

## 快速开始

### 1. 初始化资源

```bash
# 初始化所有 DynamoDB 表和 SQS 队列
python -m api.v2.scripts.init_resources

# 使用本地 DynamoDB/SQS (LocalStack)
python -m api.v2.scripts.init_resources --endpoint-url http://localhost:4566

# 清理并重新创建
python -m api.v2.scripts.init_resources --clean

# 查看资源状态
python -m api.v2.scripts.init_resources --list
```

### 2. 启动服务

```bash
# 启动 API 服务
./scripts/start_api_v2.sh

# 启动 Worker 服务
./scripts/start_worker.sh
```

### 3. 环境变量

```bash
# AWS 配置
export AWS_REGION=us-west-2
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret

# 本地开发 (可选)
export DYNAMODB_ENDPOINT_URL=http://localhost:4566
export SQS_ENDPOINT_URL=http://localhost:4566
```

## 核心表结构设计

### 1. Projects 表 (nexus_projects)
项目/构建任务的主表

| 字段 | 类型 | 说明 |
|------|------|------|
| project_id (PK) | String | 项目唯一标识 |
| project_name | String | 项目名称 |
| status | String | pending/queued/building/completed/failed/paused |
| requirement | String | 原始需求描述 |
| user_id | String | 创建用户ID |
| user_name | String | 创建用户名 |
| priority | Number | 优先级 1-5 |
| tags | List | 标签列表 |
| progress | Number | 进度百分比 0-100 |
| current_stage | String | 当前阶段 |
| error_info | Map | 错误信息 |
| created_at | String | 创建时间 |
| updated_at | String | 更新时间 |
| started_at | String | 开始构建时间 |
| completed_at | String | 完成时间 |
| metrics | Map | 构建指标 |

GSI:
- UserIndex: user_id (PK), created_at (SK)
- StatusIndex: status (PK), created_at (SK)

### 2. Stages 表 (nexus_stages)
构建阶段详情表

| 字段 | 类型 | 说明 |
|------|------|------|
| project_id (PK) | String | 项目ID |
| stage_name (SK) | String | 阶段名称 |
| stage_number | Number | 阶段序号 |
| display_name | String | 显示名称 |
| status | String | pending/running/completed/failed |
| agent_name | String | 执行Agent名称 |
| started_at | String | 开始时间 |
| completed_at | String | 完成时间 |
| duration_seconds | Number | 耗时秒数 |
| input_tokens | Number | 输入token数 |
| output_tokens | Number | 输出token数 |
| tool_calls | Number | 工具调用次数 |
| output_data | Map | 阶段输出数据 |
| error_message | String | 错误信息 |
| logs | List | 日志列表 |

### 3. Agents 表 (nexus_agents)
已部署的Agent实例表

| 字段 | 类型 | 说明 |
|------|------|------|
| agent_id (PK) | String | Agent唯一标识 |
| project_id | String | 关联项目ID |
| agent_name | String | Agent名称 |
| description | String | Agent描述 |
| category | String | Agent类别 |
| version | String | 版本号 |
| status | String | running/offline/error |
| deployment_type | String | local/agentcore |
| agentcore_config | Map | AgentCore配置 |
| capabilities | List | 能力列表 |
| tools | List | 工具列表 |
| prompt_path | String | 提示词路径 |
| code_path | String | 代码路径 |
| created_at | String | 创建时间 |
| updated_at | String | 更新时间 |
| deployed_at | String | 部署时间 |

GSI:
- ProjectIndex: project_id (PK), created_at (SK)
- StatusIndex: status (PK), created_at (SK)
- CategoryIndex: category (PK), created_at (SK)

### 4. Agent Invocations 表 (nexus_invocations)
Agent调用记录表

| 字段 | 类型 | 说明 |
|------|------|------|
| invocation_id (PK) | String | 调用唯一标识 |
| agent_id | String | Agent ID |
| session_id | String | 会话ID |
| user_id | String | 用户ID |
| input_text | String | 输入文本 |
| output_text | String | 输出文本 |
| status | String | success/failed |
| duration_ms | Number | 耗时毫秒 |
| input_tokens | Number | 输入token数 |
| output_tokens | Number | 输出token数 |
| error_message | String | 错误信息 |
| created_at | String | 创建时间 |
| metadata | Map | 元数据 |

GSI:
- AgentIndex: agent_id (PK), created_at (SK)
- SessionIndex: session_id (PK), created_at (SK)

### 5. Sessions 表 (nexus_sessions)
Agent对话会话表

| 字段 | 类型 | 说明 |
|------|------|------|
| session_id (PK) | String | 会话唯一标识 |
| agent_id | String | Agent ID |
| user_id | String | 用户ID |
| display_name | String | 会话显示名称 |
| status | String | active/closed |
| message_count | Number | 消息数量 |
| created_at | String | 创建时间 |
| last_active_at | String | 最后活跃时间 |
| metadata | Map | 元数据 |

GSI:
- AgentIndex: agent_id (PK), last_active_at (SK)
- UserIndex: user_id (PK), last_active_at (SK)

### 6. Messages 表 (nexus_messages)
会话消息表

| 字段 | 类型 | 说明 |
|------|------|------|
| session_id (PK) | String | 会话ID |
| message_id (SK) | String | 消息ID (ULID格式，自带时间排序) |
| role | String | user/assistant/system |
| content | String | 消息内容 |
| created_at | String | 创建时间 |
| metadata | Map | 元数据 |

### 7. Tasks 表 (nexus_tasks)
异步任务状态表

| 字段 | 类型 | 说明 |
|------|------|------|
| task_id (PK) | String | 任务唯一标识 |
| task_type | String | build_agent/deploy_agent/invoke_agent |
| project_id | String | 关联项目ID |
| status | String | pending/queued/running/completed/failed |
| priority | Number | 优先级 |
| payload | Map | 任务载荷 |
| result | Map | 执行结果 |
| error_message | String | 错误信息 |
| retry_count | Number | 重试次数 |
| created_at | String | 创建时间 |
| started_at | String | 开始时间 |
| completed_at | String | 完成时间 |
| worker_id | String | 执行Worker ID |

GSI:
- StatusIndex: status (PK), created_at (SK)
- ProjectIndex: project_id (PK), created_at (SK)

### 8. Tools 表 (nexus_tools)
工具库表

| 字段 | 类型 | 说明 |
|------|------|------|
| tool_id (PK) | String | 工具唯一标识 |
| tool_name | String | 工具名称 |
| display_name | String | 显示名称 |
| description | String | 工具描述 |
| category | String | 工具类别 |
| source | String | system/generated/imported |
| version | String | 版本号 |
| code_path | String | 代码路径 |
| schema | Map | 工具Schema |
| dependencies | List | 依赖列表 |
| usage_count | Number | 使用次数 |
| created_at | String | 创建时间 |
| updated_at | String | 更新时间 |

GSI:
- CategoryIndex: category (PK), usage_count (SK)
- SourceIndex: source (PK), created_at (SK)

## SQS 队列设计

### 1. nexus-build-queue
Agent构建任务队列
- 消息格式: { task_id, project_id, requirement, user_id, priority }
- 可见性超时: 3600秒 (1小时)
- 消息保留期: 7天
- 死信队列: nexus-build-dlq

### 2. nexus-deploy-queue
Agent部署任务队列
- 消息格式: { task_id, project_id, agent_id, deployment_config }
- 可见性超时: 600秒 (10分钟)
- 消息保留期: 3天
- 死信队列: nexus-deploy-dlq

### 3. nexus-notification-queue
通知队列 (可选)
- 消息格式: { type, target, payload }
- 用于WebSocket推送、邮件通知等

## API 端点设计

### Projects API
- POST /api/v2/projects - 创建项目
- GET /api/v2/projects - 列表项目
- GET /api/v2/projects/{project_id} - 获取项目详情
- GET /api/v2/projects/{project_id}/stages - 获取阶段列表
- GET /api/v2/projects/{project_id}/build - 获取构建仪表板
- POST /api/v2/projects/{project_id}/control - 控制项目 (pause/resume/stop)
- DELETE /api/v2/projects/{project_id} - 删除项目

### Agents API
- GET /api/v2/agents - 列表Agent
- GET /api/v2/agents/{agent_id} - 获取Agent详情
- POST /api/v2/agents/{agent_id}/invoke - 调用Agent
- PUT /api/v2/agents/{agent_id} - 更新Agent
- DELETE /api/v2/agents/{agent_id} - 删除Agent

### Sessions API
- POST /api/v2/agents/{agent_id}/sessions - 创建会话
- GET /api/v2/agents/{agent_id}/sessions - 列表会话
- GET /api/v2/sessions/{session_id} - 获取会话详情
- GET /api/v2/sessions/{session_id}/messages - 获取消息列表
- POST /api/v2/sessions/{session_id}/messages - 发送消息
- POST /api/v2/sessions/{session_id}/stream - 流式对话
- DELETE /api/v2/sessions/{session_id} - 删除会话

### Tasks API
- GET /api/v2/tasks/{task_id} - 获取任务状态
- GET /api/v2/projects/{project_id}/tasks - 获取项目任务列表

### Tools API
- GET /api/v2/tools - 列表工具
- GET /api/v2/tools/{tool_id} - 获取工具详情

### Statistics API
- GET /api/v2/statistics/overview - 获取概览统计
- GET /api/v2/statistics/builds - 获取构建统计
- GET /api/v2/statistics/invocations - 获取调用统计

## 服务职责划分

### API Service (api-service)
- 接收前端请求
- 参数验证
- 创建任务记录
- 发送消息到SQS
- 查询DynamoDB返回数据
- WebSocket连接管理 (可选)

### Worker Service (worker-service)
- 监听SQS队列
- 执行Agent构建工作流
- 更新任务状态到DynamoDB
- 执行Agent部署
- 处理失败重试

## 目录结构

```
Nexus-AI/
├── api/
│   └── v2/
│       ├── __init__.py
│       ├── main.py              # FastAPI 应用入口
│       ├── config.py            # 配置管理
│       ├── database/
│       │   ├── __init__.py
│       │   ├── dynamodb.py      # DynamoDB 客户端
│       │   └── sqs.py           # SQS 客户端
│       ├── models/
│       │   ├── __init__.py
│       │   └── schemas.py       # Pydantic 模型
│       ├── routers/
│       │   ├── __init__.py
│       │   ├── projects.py
│       │   ├── agents.py
│       │   ├── sessions.py
│       │   ├── tasks.py
│       │   ├── tools.py
│       │   └── statistics.py
│       ├── services/
│       │   ├── __init__.py
│       │   ├── project_service.py
│       │   ├── agent_service.py
│       │   ├── session_service.py
│       │   ├── task_service.py
│       │   └── statistics_service.py
│       └── scripts/
│           ├── init_resources.py  # 初始化 DynamoDB + SQS
│           └── cleanup.py         # 清理资源
├── worker/
│   ├── __init__.py
│   ├── main.py                  # Worker 入口
│   ├── config.py
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── build_handler.py     # 构建任务处理
│   │   └── deploy_handler.py    # 部署任务处理
│   └── utils/
│       └── stage_tracker.py     # 阶段追踪
└── web/
    └── ... (前端代码)
```
