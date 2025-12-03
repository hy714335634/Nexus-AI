# Agent 模板与运行时设计方案

## 1. 模板基线（Template Baseline）

所有位于 `agents/template_agents/...` 以及自动生成的 Agent 代码均遵循同一骨架：

- **统一入口**：模块必须导出 `invoke(message, *, files=None, session_state=None)`，内部通过 `get_agent()` 获取缓存的 Strands Agent，并在需要时写入 `AGENT_INPUT_FILES` 环境变量。
- **元数据输出**：提供 `get_agent_metadata()`，字段包含 `entrypoint`、`agentcore_entrypoint`、`code_path`、`prompt_path`、`tools_path`、`supported_inputs` 等，为 DynamoDB `AgentInstances` 入库做准备。
- **CLI 一致性**：`build_arg_parser()` + `main(argv=None)` 提供 `chat` 子命令，并可按场景扩展特定子命令（如 `convert`、`extract`）。所有子命令最终调用 `invoke` 或复用共享的业务函数。
- **AgentCore 适配**：默认尝试 `from bedrock_agentcore.runtime import BedrockAgentCoreApp`，存在时暴露 `agentcore_entrypoint(payload)` 与 `run_agentcore()`，与 AWS 官方 `@app.entrypoint` 规范一致。
- **环境初始化**：模板负责设置 `BYPASS_TOOL_CONSENT`、`OTEL_EXPORTER_OTLP_ENDPOINT` 等默认环境变量，并按需初始化 `StrandsTelemetry`。

> ✅ 已完成：`agents/template_agents/single_agent/*.py` 全部更新为上述骨架，示例参见 `default_agent.py` 或 `html2pptx_agent.py`。

## 2. 三条运行路径对齐

| 场景 | 触发方式 | 关键入口 | 说明 |
|------|----------|----------|------|
| 本地 CLI / Strands 调试 | `python agents/..._agent.py chat ...` 或 Strands SDK | `main()` → `invoke()` | 支持文本 & 文件输入，Strands Telemetry 自动启用。 |
| API / AgentRuntimeService | `POST /api/v1/agents/{id}/messages` | `AgentRuntimeService.invoke()` → `invoke()` | 服务端读取 DynamoDB 中的 `entrypoint`，动态加载并调用。记录日志至 `AgentInvocations`。 |
| Bedrock AgentCore Runtime | Starter Toolkit / boto3 `create_agent_runtime` | `agentcore_entrypoint(payload)` | 由 AWS 运行时拉起容器，透传 payload 中的 `prompt`/`files`。`deployment_type` 设置为 `agentcore`。 |

本地→AgentCore 的迁移遵循官方教程《Hosting Strands Agents with Amazon Bedrock models…》的两阶段思路：
1. **本地验证**：以 CLI/Strands 调试核心逻辑；模板的 `invoke` 保证与 API 行为一致。
2. **托管部署**：在容器中运行同一入口函数，由 AgentCore Runtime 管理生命周期。

## 3. 构建与部署流程

### 3.1 打包产物

生成工作流在 Stage7（`agent_code_developer`）结束后，需整理以下内容供部署使用：
- Agent 代码目录：`agents/generated_agents/<project>`
- Prompt 模板：`prompts/generated_agents_prompts/<project>`
- 工具实现：`tools/generated_tools/<project>`
- 运行依赖：自动生成/更新 `requirements.txt`（可合并公共依赖 + Agent 特殊依赖）
- 构建上下文：可选 `.dockerignore`、`Dockerfile` 模板（参考 `01-strands-with-bedrock-model/Dockerfile`）

### 3.2 Starter Toolkit 集成

结合示例仓库 `01-strands-with-bedrock-model/`，自动或手动执行以下步骤：

1. **配置**
   ```python
   from bedrock_agentcore_starter_toolkit import Runtime
   runtime = Runtime()
   runtime.configure(
       entrypoint="agents/generated_agents/foo/foo_agent.py",
       requirements_file="requirements.txt",
       region="us-west-2",
       agent_name="foo-agent",
       auto_create_execution_role=True,
       auto_create_ecr=True,
   )
   ```
   - Starter Toolkit 会生成 Dockerfile 与 `.bedrock_agentcore.yaml`，并在需要时创建 IAM Role / ECR。

2. **构建与部署**
   ```python
   launch_result = runtime.launch()
   ```
   - 构建镜像 → 推送至 ECR → 创建 AgentCore Runtime。

3. **状态轮询**
   ```python
   status = runtime.status()
   ```
   - 终态应为 `READY`，若失败需记录错误并回写 DynamoDB。

4. **自测调用**
   ```python
   runtime.invoke({"prompt": "Hello"})
   ```
   - 依据返回类型解析 EventStream 或 JSON 文本。

5. **boto3 调用**（供 `AgentRuntimeService` 运行时使用）
   ```python
   import boto3, json
   client = boto3.client("bedrock-agentcore", region_name="us-west-2")
   response = client.invoke_agent_runtime(
       agentRuntimeArn=launch_result.agent_arn,
       qualifier="DEFAULT",
       payload=json.dumps({"prompt": "What is 2+2?"})
   )
   ```
   - 解析方法与 Starter Toolkit 一致，适配文本或流式输出。

### 3.3 Pipeline 节点

1. **构建阶段**：写入 `AgentProjects` 状态，并调用 `get_agent_metadata()` 生成 `AgentInstances` 记录：
   - `deployment_type` 初始为 `local`
   - `deployment_status` 记为 `pending`
   - `artifacts_base_path` 指向 `projects/<project>`

2. **部署阶段（可选开关）**：
   - 通过 API flag、管理后台或 Celery 任务触发。
   - 成功后更新 `AgentInstances`：`deployment_type=agentcore`、`agentcore_arn`、`agentcore_alias`、`deployment_status=deployed`、`last_deployed_at`。
   - 失败时写入 `deployment_status=failed`、`last_error`。

3. **运行阶段**：
   - `AgentRuntimeService.invoke()` 根据 `deployment_type` 选择本地调用或 AgentCore 调用。
   - 统一写 `AgentInvocations`（caller=api/agentcore/cli 等），并可扩展持续观测指标。

## 4. DynamoDB 数据模型

| 表 | 关键字段 | 说明 |
|----|----------|------|
| `AgentProjects` | `agents`、`artifacts_base_path`、`status`、`stages_snapshot` | 跟踪项目整体进度，记录生成的 Agent 列表。 |
| `AgentInstances` | `agent_id`、`entrypoint`、`agentcore_entrypoint`、`deployment_type`、`agentcore_arn`、`agentcore_alias`、`deployment_status`、`supported_inputs` | Agent 元数据与部署信息，供运行时查询。 |
| `AgentArtifacts` | `artifact_id`、`project_id`、`agent_id`、`file_path`、`stage` | 可选：记录阶段产物与工具/模板路径。 |
| `AgentInvocations` | `invocation_id`、`agent_id`、`caller`、`request_payload`、`response_payload`、`duration_ms`、`status` | 运行期调用审计与统计。 |

> 当前 `api/models/schemas.py` / `api/database/dynamodb_client.py` 已包含这些字段定义，后续只需在构建与运行链路中写入。

## 5. 验证与运维

- **端到端测试清单**
  1. 通过 CLI `chat` 命令验证模板基础行为。
  2. 调用 `POST /api/v1/agents/create` 创建项目 → 检查 DynamoDB 中 `AgentProjects`、`AgentInstances` 是否写入元数据。
  3. 若启用部署：执行 Starter Toolkit `configure → launch → status`，确认 `AgentInstances` 更新 `agentcore_arn` 与 `deployment_status`。
  4. 调用 `AgentRuntimeService.invoke()` 两种路径：本地 / AgentCore，检查 `AgentInvocations` 日志。
  5. 回收或清理：如需停止 AgentCore Runtime，可执行 Toolkit `delete()` 或 boto3 `delete_agent_runtime`，同步更新 DynamoDB。

- **日志与可观测性**
  - 本地/CLI：标准输出 + `logs/celery.log`
  - API：FastAPI + Celery 日志
  - AgentCore：通过 CloudWatch Logs（Starter Toolkit 创建时自动配置）

## 6. 后续自动化建议

1. **CI/CD 集成**：在仓库新增部署脚本或 GitHub Actions，自动完成 `runtime.configure → launch`，并在失败时回滚到本地模式。
2. **部署配置中心**：在 `config/default_config.yaml` 增加 AgentCore/Strands 运行时参数（region、timeout、镜像标签策略等）。
3. **安全与鉴权**：为 API 层增加调用鉴权、速率限制，并对 AgentCore 调用加签或绑定角色。
4. **回滚策略**：保存上一次成功部署的 `agentcore_arn`，出现问题时快速切换 alias 或恢复到本地部署。

---
以上方案使得 Agent 在本地、API 服务及 Amazon Bedrock AgentCore 之间实现一致的运行体验，并为后续的自动化部署与运维扩展奠定基础。
