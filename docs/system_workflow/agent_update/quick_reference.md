# Agent Update Workflow 快速参考

## 快速开始

### 基本命令

```bash
# 基本用法
python agents/system_agents/agent_update_workflow/agent_update_workflow.py \
  -i "更新需求描述" \
  -j "project_name"

# 示例
python agents/system_agents/agent_update_workflow/agent_update_workflow.py \
  -i "需要添加 SerpAPI 数据源支持" \
  -j "news_retrieval_agent"
```

### Python 调用

```python
from agents.system_agents.agent_update_workflow.agent_update_workflow import (
    run_update_workflow
)

result = run_update_workflow(
    "更新需求描述",
    "project_name"
)
```

## 工作流阶段

| 阶段 | Agent | 输出 |
|------|-------|------|
| 1. Orchestrator | `update_orchestrator_agent` | 版本目录、版本ID |
| 2. Requirements | `requirements_update_agent` | `stages/requirements_analysis.json` |
| 3. Tool Update | `tool_update_agent` | `tools/.../<version_id>/...` |
| 4. Prompt Update | `prompt_update_agent` | `prompts/.../<agent_name>.yaml` (新版本) |
| 5. Code Update | `code_update_agent` | `agents/.../<version_id>/<agent_name>.py` |

## 目录结构

### 版本目录

```
projects/<project_name>/<version_id>/
├── stages/                      # 阶段文档
│   ├── requirements_analysis.json
│   ├── tool_update.json
│   ├── prompt_update.json
│   └── code_update.json
├── summary.yaml                 # 版本总结
└── change_log.yaml             # 变更日志
```

### 更新后的文件位置

**工具**：
```
tools/generated_tools/<project_name>/<version_id>/<module>/<tool>.py
```

**提示词**：
```
prompts/generated_agents_prompts/<project_name>/<agent_name>_prompt.yaml
# 包含多个版本条目
```

**Agent 代码**：
```
agents/generated_agents/<project_name>/<version_id>/<agent_name>.py
```

## 关键工具

### 版本管理

- `initialize_update_version(project_name, user_request, version_prefix)` - 初始化版本
- `register_version_stage(...)` - 注册阶段状态
- `write_stage_document(...)` - 写入阶段文档
- `get_stage_document(...)` - 读取阶段文档
- `append_change_log(...)` - 追加变更日志
- `finalize_update_version(...)` - 完成版本更新

### 提示词管理

- `read_prompt_versions(project_name, agent_name)` - 读取提示词版本
- `append_prompt_version(...)` - 追加提示词版本

### 工具管理

- `create_versioned_tool(...)` - 创建版本化工具
- `list_version_tools(...)` - 列出版本工具

## 重要规则

### 目录规则

仅允许在以下目录创建和更新：

- ✅ `projects/<project_name>/<version_id>/`
- ✅ `prompts/generated_agents_prompts/<project_name>/<agent_name>.yaml`
- ✅ `tools/generated_tools/<project_name>/<version_id>/`
- ✅ `agents/generated_agents/<project_name>/<version_id>/`

### 生成规则

- ❌ **不允许修改和删除源文件**
- ✅ **仅允许在当前工作版本的目录中创建新文件**
- ✅ **提示词更新时，必须在现有文件中追加新版本**

## 更新需求模板

### 好的更新需求

```
需要更新 <agent_name>，要求：
1. [更新点1]
2. [更新点2]
3. [更新点3]

优先级：
- P0: [紧急修复]
- P1: [重要功能]
- P2: [优化改进]
```

### 示例

```
需要更新 news_retrieval_agent，要求：
1. 添加 SerpAPI 数据源支持
2. 优化热度计算算法
3. 更新提示词以包含新工具说明

优先级：
- P0: 修复 SerpAPI 功能实现
- P1: 统一热度计算逻辑
- P2: 更新 Bedrock 模型配置
```

## 查看结果

```bash
# 查看版本目录
ls -la projects/<project_name>/<version_id>/

# 查看阶段文档
cat projects/<project_name>/<version_id>/stages/*.json

# 查看版本总结
cat projects/<project_name>/<version_id>/summary.yaml

# 查看变更日志
cat projects/<project_name>/<version_id>/change_log.yaml

# 查看新版本工具
ls -la tools/generated_tools/<project_name>/<version_id>/

# 查看更新的提示词（包含所有版本）
cat prompts/generated_agents_prompts/<project_name>/<agent_name>_prompt.yaml

# 查看新版本代码
ls -la agents/generated_agents/<project_name>/<version_id>/

# 查看项目状态
cat projects/<project_name>/status.yaml
```

## 版本管理

### 版本ID格式

- 默认格式：`v<major>.<minor>` (如：v1.0, v1.1, v2.0)
- 自动递增：基于现有版本自动生成

### 版本状态

版本状态记录在 `status.yaml` 中：

```yaml
agents:
  - name: "agent_name"
    update_versions:
      - version_id: "v2.0"
        created_at: "2025-11-11T00:00:00+00:00"
        status: "completed"
        stages: [...]
```

## 故障排查

### 项目不存在

```
FileNotFoundError: 未找到项目 <project_name> 的 status.yaml
```
→ 检查项目名称，确认项目存在

### 参数缺失

```
ValueError: 缺少必要参数: user_request, project_id
```
→ 确保提供了 `-i` 和 `-j` 参数

### 版本已存在

→ 检查 `status.yaml` 中的版本记录，版本号会自动递增

### 提示词文件未找到

→ 检查文件路径和命名（支持 `_prompt.yaml` 后缀）

### 工具路径错误

→ 检查工具路径是否包含版本ID，确认文件存在于版本目录

## 相关文件

- **工作流代码**: `agents/system_agents/agent_update_workflow/agent_update_workflow.py`
- **版本管理**: `tools/system_tools/agent_update_workflow/version_manager.py`
- **提示词管理**: `tools/system_tools/agent_update_workflow/prompt_version_manager.py`
- **工具生成**: `tools/system_tools/agent_update_workflow/tool_version_generator.py`
- **规则配置**: `config/nexus_ai_base_rule.yaml`
- **规则提取**: `nexus_utils/workflow_rule_extract.py`
- **提示词模板**: `prompts/system_agents_prompts/agent_update_workflow/`

## 更多信息

详细文档请参考：[agent_update_workflow_design.md](./agent_update_workflow_design.md)

