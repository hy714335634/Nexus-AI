# Tool Build Workflow 快速参考

## 快速开始

### 基本命令

```bash
# 使用默认需求
python agents/system_agents/tool_build_workflow/tool_build_workflow.py

# 指定用户需求
python agents/system_agents/tool_build_workflow/tool_build_workflow.py \
  -i "你的功能需求描述"

# 从文件读取需求
python agents/system_agents/tool_build_workflow/tool_build_workflow.py \
  -i "基础需求" -f /path/to/file.txt
```

### Python 调用

```python
from agents.system_agents.tool_build_workflow.tool_build_workflow import (
    run_tool_build_workflow
)

result = run_tool_build_workflow("你的功能需求描述")
```

## 工作流阶段

| 阶段 | Agent | 输出 |
|------|-------|------|
| 1. Orchestrator | `tool_build_orchestrator_agent` | 项目目录、配置文件 |
| 2. Requirements | `requirements_analyzer_agent` | `stages/requirements_analyzer.json` |
| 3. Designer | `tool_designer_agent` | `stages/tool_designer.json` |
| 4. Developer | `tool_developer_agent` | `*.py` 工具文件 |
| 5. Validator | `tool_validator_agent` | `stages/tool_validator.json` |
| 6. Documenter | `tool_documenter_agent` | `README.md` |

## 目录结构

```
tools/generated_tools/tool_build_<name>/
├── config.yaml              # 项目配置
├── status.yaml              # 项目状态
├── README.md                # 使用文档
├── stages/                  # 阶段文档
│   ├── requirements_analyzer.json
│   ├── tool_designer.json
│   ├── tool_developer.json
│   ├── tool_validator.json
│   └── tool_documenter.json
└── *.py                     # 工具代码
```

## 关键工具

### 项目管理

- `initialize_tool_project(tool_name, description)` - 初始化项目
- `get_tool_project_config(tool_name)` - 获取配置
- `get_tool_project_status(tool_name)` - 获取状态
- `update_tool_project_stage(...)` - 更新阶段状态

### 文档管理

- `write_tool_stage_document(tool_name, stage_name, content)` - 写入阶段文档
- `get_tool_stage_document(tool_name, stage_name)` - 读取阶段文档

### 文件生成

- `generate_tool_file(tool_name, file_name, content)` - 生成工具文件
- `register_tool(...)` - 注册工具
- `generate_tool_readme(tool_name, readme_content)` - 生成 README

## 命名规范

- 工具项目名称：`tool_build_<描述性名称>`
- 必须小写，使用下划线分隔
- 示例：`tool_build_file_downloader`, `tool_build_json_parser`

## 代码规范

### 必须使用

```python
from strands import tool

@tool
def your_tool_function(param: str) -> str:
    """工具函数说明"""
    try:
        # 实现逻辑
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"错误: {str(e)}"
```

### 要求

- ✅ 使用 `@tool` 装饰器
- ✅ Python 类型提示
- ✅ 完整的 docstring
- ✅ 返回 JSON 字符串或错误信息
- ✅ 完善的错误处理

## 规则系统

### Base 规则

- 目录结构：`agents/`, `prompts/`, `tools/`, `projects/`, `nexus_utils/`
- 工具目录：`system_tools/`, `template_tools/`, `generated_tools/`

### Tool Build 规则

- 项目位置：`tools/generated_tools/tool_build_<name>/`
- 命名规范：`tool_build_` 开头
- 代码规范：Strands SDK `@tool` 装饰器
- 文档要求：必须生成 README.md

## 需求描述模板

### 好的需求

```
我需要一个工具，能够：
1. [功能1描述]
2. [功能2描述]
3. [功能3描述]

要求：
- [约束1]
- [约束2]
- [约束3]
```

### 示例

```
我需要一个工具，能够：
1. 从指定的URL下载文件
2. 支持HTTP和HTTPS协议
3. 保存到指定的本地路径
4. 显示下载进度

要求：
- 处理网络错误
- 处理文件系统错误
- 支持大文件下载
```

## 查看结果

```bash
# 查看项目目录
ls -la tools/generated_tools/tool_build_<name>/

# 查看工具代码
cat tools/generated_tools/tool_build_<name>/*.py

# 查看文档
cat tools/generated_tools/tool_build_<name>/README.md

# 查看状态
cat tools/generated_tools/tool_build_<name>/status.yaml

# 查看阶段文档
cat tools/generated_tools/tool_build_<name>/stages/*.json
```

## 故障排查

### 工具名称错误

```
错误：工具名称必须以 'tool_build_' 开头
```
→ 确保名称以 `tool_build_` 开头

### 项目已存在

→ 删除或重命名现有项目，或使用不同名称

### 验证失败

→ 查看 `stages/tool_validator.json` 了解具体问题

### 规则加载失败

→ 检查 `config/nexus_ai_base_rule.yaml` 中的 `tool_build` 规则

## 相关文件

- **工作流代码**: `agents/system_agents/tool_build_workflow/tool_build_workflow.py`
- **工具管理**: `tools/system_tools/tool_build_workflow/tool_project_manager.py`
- **规则配置**: `config/nexus_ai_base_rule.yaml`
- **规则提取**: `nexus_utils/workflow_rule_extract.py`
- **提示词模板**: `prompts/system_agents_prompts/tool_build_workflow/`

## 更多信息

详细文档请参考：[tool_build_workflow_design.md](./tool_build_workflow_design.md)

