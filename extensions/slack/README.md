# Nexus-AI Slack Extension

企业级 Slack 集成模块，为 Nexus-AI 提供 Slack 消息处理和智能 Agent 路由能力。

## 架构设计

```
Slack 用户消息
    ↓
SlackBot (消息监听和处理)
    ↓
AgentRouter (智能路由)
    ↓
Agent Factory (从 YAML 初始化)
    ↓
Agent 实例 (处理请求)
    ↓
响应返回 Slack
```

## 核心模块

### 1. SlackBot (`slack_bot.py`)
- Slack 消息监听和事件处理
- 命令解析和路由
- 错误处理和日志记录
- Socket Mode 支持（无需公网 URL）

### 2. AgentRouter (`agent_router.py`)
- Agent 配置管理
- 自动查找和加载 YAML prompt
- Agent 实例缓存
- 智能路由和调用

### 3. 配置文件 (`config.yaml`)
- Agent 列表配置
- Bot 行为配置
- 超时和免责声明设置

## 快速开始

### 1. 配置 Agent

编辑 `extensions/slack/config.yaml`:

```yaml
agents:
  - name: "aws_pricing_agent"
    description: "AWS 定价查询助手"
    enabled: true
```

**要求**:
- Agent 名称必须与 `prompts/generated_agents_prompts/{name}/` 目录对应
- 该目录下必须包含 YAML prompt 文件

### 2. 设置环境变量

```bash
export SLACK_BOT_TOKEN="xoxb-your-bot-token"
export SLACK_APP_TOKEN="xapp-your-app-token"
```

### 3. 启动服务

```bash
# 方式 1: 使用启动脚本（推荐）
./extensions/slack/start.sh

# 方式 2: 作为 Python 模块运行
source .nexus-ai/bin/activate && python -m extensions.slack.main

# 方式 3: 直接运行
source .nexus-ai/bin/activate && python extensions/slack/main.py
```

### 4. 在 Slack 中使用

```
@nexus-ai-agent help                    # 查看可用 Agent
@nexus-ai-agent AWS m5.large 价格      # 使用默认 Agent
@nexus-ai-agent clear cache            # 清除 Agent 缓存
```

## 编程接口

### 作为模块使用

```python
from extensions.slack import SlackBot

# 创建 Bot 实例
bot = SlackBot(
    bot_token="xoxb-...",
    app_token="xapp-...",
    config_path="path/to/config.yaml"  # 可选
)

# 启动服务
bot.start()
```

### 自定义 Agent Router

```python
from extensions.slack import AgentRouter

# 创建 Router
router = AgentRouter(config_path="config.yaml")

# 调用 Agent
response = router.call_agent("AWS 价格查询")

# 列出可用 Agent
agents_list = router.list_agents()

# 清除缓存
router.clear_cache()
```

## 配置说明

### config.yaml 结构

```yaml
# Agent 配置
agents:
  - name: "agent_name"           # Agent 名称（必需）
    description: "描述"           # Agent 描述（可选）
    enabled: true                 # 是否启用（默认 true）

# Bot 配置
bot:
  timeout: 60                     # Agent 执行超时时间（秒）
  verbose: true                   # 详细日志
  disclaimer: "免责声明文本"       # AI 免责声明
```

## 日志管理

日志文件位置: `logs/slack_bot.log`

日志级别:
- INFO: 正常操作日志
- WARNING: 警告信息
- ERROR: 错误信息（包含堆栈跟踪）

查看实时日志:
```bash
tail -f logs/slack_bot.log
```

## 后台运行

```bash
# 使用 nohup 后台运行
nohup ./extensions/slack/start.sh > logs/slack_bot_console.log 2>&1 &

# 查看进程
ps aux | grep "extensions.slack.main"

# 停止服务
pkill -f "extensions.slack.main"
```

## 添加新 Agent

### 步骤 1: 确保 Agent Prompt 存在

```
prompts/generated_agents_prompts/my_new_agent/
└── my_new_agent.yaml
```

### 步骤 2: 添加到配置

编辑 `extensions/slack/config.yaml`:

```yaml
agents:
  - name: "my_new_agent"
    description: "我的新 Agent"
    enabled: true
```

### 步骤 3: 重启服务

```bash
./extensions/slack/start.sh
```

## 故障排查

### Agent 初始化失败

检查:
1. Agent 名称是否与 prompt 目录名一致
2. Prompt YAML 文件是否存在
3. 查看启动日志中的 prompt 路径

### Bot 不响应

检查:
1. Token 是否正确设置
2. Bot 是否在频道中（`/invite @bot-name`）
3. Socket Mode 是否启用
4. 查看日志文件

### 性能优化

- Agent 实例会被缓存，首次调用较慢
- 使用 `clear cache` 命令清除缓存
- 调整 `timeout` 配置适应不同 Agent

## 安全考虑

- Token 通过环境变量管理，不要硬编码
- 日志文件可能包含敏感信息，注意权限
- 定期审查 Agent 配置和权限
- 使用 AI 免责声明提醒用户

## 依赖项

- `slack-bolt`: Slack Bot 框架
- `pyyaml`: YAML 配置解析
- Nexus-AI 核心模块 (`utils.agent_factory`)

## 版本信息

- 版本: 1.0.0
- 兼容: Nexus-AI v1.0+
- Python: 3.12+

## 贡献指南

欢迎提交 Issue 和 Pull Request！

## 许可证

与 Nexus-AI 主项目保持一致
