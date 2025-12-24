# Nexus-AI 手动 Vibe Coding Agent 构建指南

> 本文档帮助你通过自然语言（Vibe Coding）方式，使用 AI 助手（如 Claude Code、Cursor、Windsurf）手动构建 Nexus-AI Agent。

## 快速跳转

- [一、平台概述](#一nexus-ai-平台概述) - 了解 Nexus-AI 核心概念
- [二、手动构建流程](#二手动-vibe-coding-构建流程) - **一键启动提示词模板**
- [三、核心组件规范](#三核心组件规范) - 工具、提示词、Agent 代码模板
- [四、目录结构](#四目录结构说明) - 文件放置位置
- [五、常用工具](#五常用-strands-内置工具) - Strands 内置工具速查

---

## 一、Nexus-AI 平台概述

### 1.1 什么是 Nexus-AI

Nexus-AI 是一个基于 AWS Bedrock 构建的企业级 AI 代理开发平台，让你能够通过**自然语言**快速构建、部署和管理 AI Agent。

### 1.2 核心特性

- **智能代理构建**: 通过自然语言描述构建 AI Agent
- **多代理协作**: 支持复杂业务场景的多 Agent 协同工作
- **AWS Bedrock 集成**: 基于 AWS Bedrock 的强大 AI 推理能力
- **模块化设计**: 可扩展的插件化架构

### 1.3 技术栈

| 组件 | 技术选型 |
|------|----------|
| AI 推理引擎 | AWS Bedrock (Claude 模型) |
| Agent 框架 | Strands SDK |
| 开发语言 | Python 3.13+ |
| AWS 集成 | boto3 SDK |
| 配置管理 | YAML |

---

## 二、手动 Vibe Coding 构建流程

使用 AI 助手（如 Claude Code、Cursor、Windsurf 等）进行交互式 Agent 构建。

### 2.1 构建流程概览

```
┌─────────────────────────────────────────────────────────────┐
│                   手动 Vibe Coding 流程                      │
│                                                              │
│  Step 1: 确定项目名称和 Agent 名称                           │
│         ↓                                                    │
│  Step 2: 设计并开发工具（如需要）                            │
│         ↓                                                    │
│  Step 3: 编写提示词模板（YAML）                              │
│         ↓                                                    │
│  Step 4: 开发 Agent 代码                                     │
│         ↓                                                    │
│  Step 5: 本地测试运行                                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 标准文件路径（必须遵循）

手动创建 Agent 时，**必须**将文件放到以下位置：

| 文件类型 | 标准路径 |
|----------|----------|
| **工具代码** | `tools/generated_tools/<project_name>/<module_name>/<tool_name>.py` |
| **提示词** | `prompts/generated_agents_prompts/<project_name>/<agent_name>_prompt.yaml` |
| **Agent 代码** | `agents/generated_agents/<project_name>/<agent_name>.py` |

**示例**：项目名 `weather_agent`，Agent 名 `weather_assistant`

```
tools/generated_tools/weather_agent/
└── weather_api/
    └── weather_tools.py              # 工具代码

prompts/generated_agents_prompts/weather_agent/
└── weather_assistant_prompt.yaml     # 提示词

agents/generated_agents/weather_agent/
└── weather_assistant.py              # Agent 代码
```

### 2.3 一键启动提示词（直接复制使用）

将以下提示词发送给 AI 助手，开始构建你的 Agent：

---

#### 提示词模板 A：完整构建（工具 + 提示词 + Agent）

```markdown
请帮我基于 Nexus-AI 平台构建一个 Agent，遵循平台规范。

## 项目信息
- 项目名称：<your_project_name>（英文，snake_case 格式）
- Agent 名称：<your_agent_name>（英文，snake_case 格式）

## 需求描述
<在这里详细描述你的 Agent 需要做什么>

具体功能要求：
1. <功能点1>
2. <功能点2>
3. <功能点3>

约束条件：
- <约束1>
- <约束2>

## 文件输出要求（必须遵循）
请将生成的文件放到以下位置：
1. 工具代码 → tools/generated_tools/<project_name>/<module>/<tool>.py
2. 提示词 → prompts/generated_agents_prompts/<project_name>/<agent_name>_prompt.yaml
3. Agent 代码 → agents/generated_agents/<project_name>/<agent_name>.py

## 技术规范
- 工具必须使用 @tool 装饰器（from strands import tool）
- 工具必须返回 JSON 格式字符串
- 提示词必须是 YAML 格式，包含 tools_dependencies
- Agent 代码使用 nexus_utils.agent_factory.create_agent_from_prompt_template
- AWS 服务调用使用 boto3 SDK

请参考 docs/VIBE_CODING_AGENT_BUILD_TEMPLATE.md 中的代码模板。
```

---

#### 提示词模板 B：只需提示词和 Agent（使用现有工具）

```markdown
请帮我基于 Nexus-AI 平台构建一个 Agent，只需要提示词和 Agent 代码。

## 项目信息
- 项目名称：<your_project_name>
- Agent 名称：<your_agent_name>

## 需求描述
<在这里详细描述你的 Agent 需要做什么>

## 使用的现有工具
- strands_tools/calculator
- strands_tools/current_time
- strands_tools/use_aws
- <其他需要的工具>

## 文件输出要求
1. 提示词 → prompts/generated_agents_prompts/<project_name>/<agent_name>_prompt.yaml
2. Agent 代码 → agents/generated_agents/<project_name>/<agent_name>.py

请参考 docs/VIBE_CODING_AGENT_BUILD_TEMPLATE.md 中的代码模板。
```

---

#### 提示词模板 C：分步骤构建（推荐新手使用）

**Step 1 - 设计工具：**
```markdown
我想构建一个 <功能描述> 的 Agent。

项目名称：<project_name>
Agent 名称：<agent_name>

请先帮我设计需要的工具函数，包括：
1. 函数名称和功能描述
2. 输入参数和返回值
3. 需要调用的外部 API 或 AWS 服务

不需要写代码，先确认设计方案。
```

**Step 2 - 开发工具：**
```markdown
设计方案确认，请帮我开发工具代码。

要求：
- 使用 @tool 装饰器（from strands import tool）
- 返回 JSON 格式字符串
- 包含完整的错误处理
- 文件路径：tools/generated_tools/<project_name>/<module>/<tool>.py
```

**Step 3 - 编写提示词：**
```markdown
工具开发完成，请帮我编写提示词模板。

要求：
- YAML 格式
- 包含清晰的角色定义和工作流程
- 正确配置 tools_dependencies（包含刚才开发的工具）
- 文件路径：prompts/generated_agents_prompts/<project_name>/<agent_name>_prompt.yaml
```

**Step 4 - 开发 Agent：**
```markdown
提示词完成，请帮我开发 Agent 代码。

要求：
- 使用 create_agent_from_prompt_template 创建 Agent
- 包含本地测试入口（if __name__ == "__main__"）
- 包含 AgentCore 部署入口（handler 函数）
- 文件路径：agents/generated_agents/<project_name>/<agent_name>.py
```

---

### 2.4 完整示例：构建一个天气查询 Agent

**发送给 AI 助手的提示词：**

```markdown
请帮我基于 Nexus-AI 平台构建一个天气查询 Agent。

## 项目信息
- 项目名称：weather_agent
- Agent 名称：weather_assistant

## 需求描述
我需要一个能够查询天气的 Agent，支持：
1. 查询指定城市的当前天气
2. 查询未来 3 天的天气预报
3. 支持中英文城市名称
4. 返回温度、湿度、天气状况等信息

约束条件：
- 使用免费的天气 API（如 OpenWeatherMap）
- 输出使用中文
- 如果城市不存在，友好提示

## 文件输出要求
1. 工具代码 → tools/generated_tools/weather_agent/weather_api/weather_tools.py
2. 提示词 → prompts/generated_agents_prompts/weather_agent/weather_assistant_prompt.yaml
3. Agent 代码 → agents/generated_agents/weather_agent/weather_assistant.py

请参考 docs/VIBE_CODING_AGENT_BUILD_TEMPLATE.md 中的代码模板。
```

### 2.5 验证和测试

构建完成后，运行以下命令测试：

```bash
# 本地测试
python agents/generated_agents/<project_name>/<agent_name>.py \
  -i "你的测试输入"

# 示例
python agents/generated_agents/weather_agent/weather_assistant.py \
  -i "北京今天天气怎么样？"
```

### 2.6 需求描述技巧

| 要点 | 说明 |
|------|------|
| 具体明确 | 避免模糊描述如"创建一个 Agent" |
| 功能点清晰 | 使用编号列出所有功能需求 |
| 包含约束 | 明确技术和业务约束 |
| 场景示例 | 提供实际使用场景 |

**优秀需求示例：**

```markdown
请创建一个用于AWS产品报价的Agent，我需要他帮我完成AWS产品报价工作。
我会提供自然语言描述的资源和配置要求，请分析并推荐合理的AWS服务和配置，
然后进行实时的报价并生成报告。

具体要求如下：
1. 至少需要支持EC2、EBS、S3、网络流量、ELB、RDS这几个产品
2. 能够获取实时且真实的按需和预留实例价格
3. 在用户提出的描述不清晰时，需要能够根据用户需求推测合理配置
4. 在同系列同配置情况下，优先推荐最新一代实例
5. 能够支持根据客户指定区域进行报价，包括中国区

约束条件：
- 如果价格获取失败或无法获取，请在对应资源报价中注明
- 报价文档尽量使用中文
```

---

## 三、核心组件规范

### 3.1 工具开发规范

#### 工具代码模板

```python
"""
工具模块: <module_name>
功能描述: <description>
"""

from strands import tool
from typing import Optional
import json

@tool
def my_tool_function(
    param1: str,
    param2: int,
    optional_param: Optional[str] = None
) -> str:
    """
    工具功能描述

    Args:
        param1: 参数1说明
        param2: 参数2说明
        optional_param: 可选参数说明

    Returns:
        JSON格式的结果字符串
    """
    try:
        # 实现逻辑
        result = {
            "status": "success",
            "data": {
                # 返回数据
            }
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, ensure_ascii=False)
```

#### 工具开发要点

1. **必须使用 `@tool` 装饰器**
2. **必须包含完整的类型注解**
3. **必须返回 JSON 格式的结构化数据**
4. **必须包含详细的 docstring**
5. **必须实现健壮的错误处理**
6. **AWS 服务调用使用 boto3 SDK**

### 3.2 提示词模板规范

#### YAML 格式模板

```yaml
agent:
  name: "<agent_name>"
  description: "<agent_description>"
  category: "<category>"
  environments:
    development:
      max_tokens: 4096
      temperature: 0.3
      streaming: False
    production:
      max_tokens: 60000
      temperature: 0.3
      streaming: False
    testing:
      max_tokens: 2048
      temperature: 0.3
      streaming: False
  versions:
    - version: "latest"
      status: "stable"
      created_date: "YYYY-MM-DD"
      author: "vibe coding"
      description: "<version_description>"
      system_prompt: |
        你是一个专业的<角色描述>，专门负责<核心职责>。

        你的主要职责：
        1. <职责1>
        2. <职责2>
        3. <职责3>

        工作流程：
        1. <步骤1>
        2. <步骤2>
        3. <步骤3>

        输出格式要求：
        <明确的输出格式说明>

        注意事项：
        - <注意事项1>
        - <注意事项2>

      metadata:
        tags: ["<tag1>", "<tag2>"]
        supported_models:
          - "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
        tools_dependencies:
          - "strands_tools/current_time"
          - "generated_tools/<project_name>/<script_name>/<tool_name>"
```

#### 提示词设计要点

1. **角色定义**: 明确 Agent 的专业身份
2. **职责清单**: 详细列出核心职责
3. **工作流程**: 提供步骤化执行指导
4. **输出规范**: 定义精确的输出格式
5. **工具依赖**: 正确配置 tools_dependencies

### 3.3 Agent 代码规范

#### Agent 代码模板

```python
#!/usr/bin/env python3
"""
Agent: <agent_name>
Description: <description>
"""

import os
import json
from typing import Dict, Any
from nexus_utils.agent_factory import create_agent_from_prompt_template
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# 环境变量设置
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# Agent 参数配置
agent_params = {
    "env": "production",
    "version": "latest",
    "model_id": "default",
    "enable_logging": True
}

# 创建 Agent 实例
my_agent = create_agent_from_prompt_template(
    agent_name="generated_agents_prompts/<project_name>/<agent_name>",
    **agent_params
)

# ==================== AgentCore 入口点 ====================
app = BedrockAgentCoreApp()

@app.entrypoint
async def handler(payload: Dict[str, Any]) -> str:
    """
    AgentCore 标准入口点

    Args:
        payload: 包含 prompt, user_id, session_id, media 等字段

    Yields:
        str: 流式响应片段
    """
    prompt = payload.get("prompt") or payload.get("message") or payload.get("input", "")

    if not prompt:
        return "Error: Missing 'prompt' in request"

    try:
        stream = my_agent.stream_async(prompt)
        async for event in stream:
            yield event
    except Exception as e:
        return f"Error: {str(e)}"

# ==================== 本地运行入口 ====================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='<Agent Name>')
    parser.add_argument('-i', '--input', type=str, default=None, help='测试输入')
    args = parser.parse_args()

    is_docker = os.environ.get("DOCKER_CONTAINER") == "1"

    if is_docker:
        print("Starting AgentCore HTTP server on port 8080")
        app.run()
    elif args.input:
        print(f"Agent created: {my_agent.name}")
        print(f"Input: {args.input}")
        result = my_agent(args.input)
        print(f"Response: {result}")
    else:
        print("Starting AgentCore HTTP server on port 8080")
        app.run()
```

---

## 四、目录结构说明

### 4.1 手动构建相关目录

```
Nexus-AI/
├── agents/
│   └── generated_agents/             # 你的 Agent 代码放这里
│       └── <project_name>/
│           └── <agent_name>.py
│
├── prompts/
│   └── generated_agents_prompts/     # 你的提示词放这里
│       └── <project_name>/
│           └── <agent_name>_prompt.yaml
│
├── tools/
│   └── generated_tools/              # 你的工具代码放这里
│       └── <project_name>/
│           └── <module>/
│               └── <tool_name>.py
│
├── nexus_utils/                      # 平台工具函数（直接使用）
└── docs/                             # 文档
```

### 4.2 工具依赖路径格式

| 类型 | 路径格式 | 示例 |
|------|----------|------|
| Strands 内置工具 | `strands_tools/<tool_name>` | `strands_tools/calculator` |
| 你的自定义工具 | `generated_tools/<project>/<script>/<tool>` | `generated_tools/weather_agent/weather_api/get_weather` |

---

## 五、常用 Strands 内置工具

| 工具名 | 功能 |
|--------|------|
| `strands_tools/calculator` | 数学计算 |
| `strands_tools/current_time` | 获取当前时间 |
| `strands_tools/file_read` | 读取文件 |
| `strands_tools/use_aws` | AWS 服务问答 |
| `strands_tools/python_repl` | Python 代码执行 |
| `strands_tools/think` | 思考/推理 |
| `strands_tools/use_llm` | 调用 LLM |

---

## 六、最佳实践

### 6.1 工具开发最佳实践

- **单一职责**: 每个工具只做一件事
- **类型安全**: 使用完整的类型注解
- **错误处理**: 实现健壮的异常处理
- **文档完整**: 提供详细的 docstring

### 6.2 Agent 设计最佳实践

- **模块化**: Agent 职责清晰，接口明确
- **可扩展**: 考虑未来功能扩展
- **容错性**: 完善的错误处理和恢复
- **可观测**: 支持日志和监控

---

## 七、故障排查

| 问题 | 解决方案 |
|------|----------|
| 工具导入失败 | 检查 tools_dependencies 路径格式，确保文件在正确位置 |
| Agent 创建失败 | 确认 agent_name 路径格式为 `generated_agents_prompts/<project>/<agent>` |
| 找不到模块 | 确保文件放在正确的 `generated_*` 目录下 |
| YAML 解析错误 | 检查提示词 YAML 格式，注意缩进 |

---

## 八、相关资源

- **Agent 模板参考**: `agents/template_agents/`
- **提示词模板参考**: `prompts/template_prompts/`
- **工具模板参考**: `tools/template_tools/`

---

*最后更新: 2025-12-23*
*文档版本: 2.0 - 纯手动 Vibe Coding 版本*
