# Agent Build Workflow 快速参考

## 快速开始

### 基本命令

```bash
# 使用默认需求
python agents/system_agents/agent_build_workflow/agent_build_workflow.py

# 指定用户需求
python agents/system_agents/agent_build_workflow/agent_build_workflow.py \
  -i "你的功能需求描述"

# 从文件读取需求
python agents/system_agents/agent_build_workflow/agent_build_workflow.py \
  -i "基础需求" \
  -f /path/to/requirements.txt
```

### Python 调用

```python
from agents.system_agents.agent_build_workflow.agent_build_workflow import (
    run_workflow
)

result = run_workflow("你的功能需求描述")
```

## 工作流阶段

| 阶段 | Agent | 输出 |
|------|-------|------|
| 0. Intent Analyzer | `intent_analyzer` | 意图识别结果 |
| 1. Orchestrator | `orchestrator` | 项目目录、配置文件 |
| 2. Requirements | `requirements_analyzer` | `requirements_analyzer.json` |
| 3. System Architect | `system_architect` | `system_architect.json` |
| 4. Agent Designer | `agent_designer` | `agent_designer.json` |
| 5. Developer Manager | `agent_developer_manager` | 开发总结文档 |
| ├─ Tool Developer | `tool_developer` | 工具代码文件 |
| ├─ Prompt Engineer | `prompt_engineer` | 提示词 YAML 文件 |
| └─ Code Developer | `agent_code_developer` | Agent Python 文件 |
| 6. Agent Deployer | `agent_deployer` | 部署配置 |

## 目录结构

### 项目目录

```
projects/<project_name>/
├── config.yaml                      # 项目配置
├── status.yaml                      # 项目状态
├── README.md                        # 项目说明
├── requirements.txt                 # Python 依赖
└── agents/
    └── <agent_name>/
        ├── requirements_analyzer.json
        ├── system_architect.json
        ├── agent_designer.json
        ├── tools_developer.json
        ├── prompt_engineer.json
        ├── agent_code_developer.json
        └── agent_developer_manager.json
```

### 生成的文件位置

**Agent 代码**：
```
agents/generated_agents/<project_name>/<agent_name>.py
```

**提示词文件**：
```
prompts/generated_agents_prompts/<project_name>/<agent_name>_prompt.yaml
```

**工具文件**：
```
tools/generated_tools/<project_name>/<module>/<tool_name>.py
```

## 关键工具

### 项目管理

- `project_init(project_name, description, version)` - 初始化项目
- `update_project_config(...)` - 更新配置
- `get_project_config(project_name)` - 获取配置
- `update_project_status(...)` - 更新状态
- `get_project_status(...)` - 获取状态

### 文档管理

- `update_project_stage_content(...)` - 写入阶段文档
- `get_project_stage_content(...)` - 读取阶段文档
- `update_project_readme(...)` - 更新 README
- `get_project_readme(project_name)` - 获取 README

### 内容生成

- `generate_content(project_name, agent_name, content_type, content)` - 生成内容
  - `content_type`: "agent" | "prompt" | "tool"

### 列表查询

- `list_project_agents(project_name)` - 列出项目Agent
- `list_all_projects()` - 列出所有项目
- `list_project_tools(project_name)` - 列出项目工具

## 意图类型

- `new_project`: 创建新项目
- `existing_project`: 更新已存在项目
- `unclear`: 需求不明确

## 需求描述模板

### 好的需求

```
请创建一个<功能描述>的Agent，要求：
1. [功能点1]
2. [功能点2]
3. [功能点3]

约束条件：
- [约束1]
- [约束2]
```

### 示例

```
请创建一个新闻检索Agent，能够根据用户关注话题从多个主流媒体平台检索热门新闻，进行热度排序和摘要生成。

要求：
1. 支持从百度、新浪、澎湃等主流媒体获取新闻
2. 能够计算新闻热度并按热度排序
3. 生成新闻摘要
4. 管理用户关注话题

约束：
- 不存储新闻全文，只展示标题和摘要
- 保持客观中立，不添加个人观点
```

## 查看结果

```bash
# 查看项目目录
ls -la projects/<project_name>/

# 查看阶段文档
cat projects/<project_name>/agents/<agent_name>/*.json

# 查看项目状态
cat projects/<project_name>/status.yaml

# 查看项目配置
cat projects/<project_name>/config.yaml

# 查看 README
cat projects/<project_name>/README.md

# 查看 Agent 代码
cat agents/generated_agents/<project_name>/<agent_name>.py

# 查看提示词
cat prompts/generated_agents_prompts/<project_name>/<agent_name>_prompt.yaml

# 查看工具
ls -la tools/generated_tools/<project_name>/

# 查看工作流报告
find projects/ -name "workflow_report*.html"
```

## 故障排查

### 意图识别失败

→ 检查用户输入是否清晰，确认项目名称

### 项目已存在

→ 使用不同的项目名称，或使用 agent_update_workflow

### 工具开发失败

→ 查看 `tools_developer.json`，检查工具模板和代码规范

### 提示词生成失败

→ 查看 `prompt_engineer.json`，检查提示词模板和工具依赖路径

### 代码生成失败

→ 查看 `agent_code_developer.json`，检查 Agent 模板和导入路径

## 相关文件

- **工作流代码**: `agents/system_agents/agent_build_workflow/agent_build_workflow.py`
- **项目管理**: `tools/system_tools/agent_build_workflow/project_manager.py`
- **模板提供**: `tools/system_tools/agent_build_workflow/*_template_provider.py`
- **规则配置**: `config/nexus_ai_base_rule.yaml`
- **规则提取**: `nexus_utils/workflow_rule_extract.py`
- **报告生成**: `nexus_utils/workflow_report_generator.py`
- **提示词模板**: `prompts/system_agents_prompts/agent_build_workflow/`

## 更多信息

详细文档请参考：[agent_build_workflow_design.md](./agent_build_workflow_design.md)

