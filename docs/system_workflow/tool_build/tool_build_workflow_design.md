# Tool Build Workflow 设计文档

## 目录

- [概述](#概述)
- [架构设计](#架构设计)
- [工作流阶段](#工作流阶段)
- [工具系统](#工具系统)
- [规则系统](#规则系统)
- [目录结构](#目录结构)
- [使用指南](#使用指南)
- [示例](#示例)
- [最佳实践](#最佳实践)
- [故障排查](#故障排查)

---

## 概述

### 什么是 Tool Build Workflow

Tool Build Workflow 是 Nexus-AI 平台中用于自动化构建工具的系统工作流。它接受用户自然语言描述的功能需求，通过多个 AI Agent 协作，自动完成从需求分析到工具开发、验证和文档生成的完整流程。

### 核心特性

- **自动化工具开发**：基于自然语言需求自动生成符合 Strands SDK 规范的工具代码
- **多阶段协作**：6 个专业 Agent 按顺序协作完成工具构建
- **规则驱动**：严格遵循 Nexus-AI 平台规则和目录规范
- **完整生命周期**：覆盖需求分析、设计、开发、验证、文档生成全流程
- **状态跟踪**：实时跟踪各阶段状态和进度

### 适用场景

- 需要快速开发符合 Strands SDK 规范的工具
- 需要将功能需求转换为可复用的工具代码
- 需要自动生成工具文档和使用说明
- 需要确保工具代码质量和规范性

---

## 架构设计

### 整体架构

```
用户输入（自然语言需求）
    ↓
Tool Build Workflow 编排器
    ↓
┌─────────────────────────────────────┐
│  Strands Graph 工作流编排            │
│                                       │
│  Orchestrator → Requirements →        │
│  Designer → Developer → Validator →   │
│  Documenter                          │
└─────────────────────────────────────┘
    ↓
工具项目目录（tools/generated_tools/）
```

### 技术栈

- **编排框架**：Strands Multi-Agent Graph
- **Agent 创建**：nexus_utils.agent_factory
- **规则管理**：nexus_utils.workflow_rule_extract
- **工具规范**：Strands SDK @tool 装饰器
- **配置管理**：YAML 格式配置文件

### 组件说明

#### 1. 工作流编排器 (`tool_build_workflow.py`)

**职责**：
- 初始化工作流环境
- 加载 Base 和 Tool Build 规则
- 构建 Strands Graph
- 执行工作流并监控进度

**关键函数**：
- `initialize_tool_build_workflow()`: 初始化工作流图
- `run_tool_build_workflow()`: 执行完整工作流
- `_load_tool_build_rules()`: 加载规则系统

#### 2. Agent 系统

工作流包含 6 个专业 Agent，每个 Agent 负责特定阶段：

| Agent | 职责 | 输出 |
|-------|------|------|
| Orchestrator | 项目初始化、工作流协调 | 项目目录结构、配置文件 |
| Requirements Analyzer | 需求分析、功能分解 | 需求文档（JSON） |
| Tool Designer | 工具架构设计、接口设计 | 设计文档（JSON） |
| Tool Developer | 工具代码实现 | Python 工具文件 |
| Tool Validator | 代码验证、质量检查 | 验证报告（JSON） |
| Tool Documenter | 文档生成 | README.md |

#### 3. 工具管理系统 (`tool_project_manager.py`)

提供完整的工具项目管理功能：

- **项目初始化**：`initialize_tool_project()`
- **配置管理**：`get_tool_project_config()`
- **状态跟踪**：`get_tool_project_status()`, `update_tool_project_stage()`
- **文档管理**：`write_tool_stage_document()`, `get_tool_stage_document()`
- **工具注册**：`register_tool()`
- **文件生成**：`generate_tool_file()`, `generate_tool_readme()`

---

## 工作流阶段

### 阶段 1: Orchestrator（编排器）

**Agent**: `tool_build_orchestrator_agent.py`

**职责**：
1. 接收用户需求
2. 生成符合命名规范的工具项目名称（`tool_build_xxxx`）
3. 初始化项目目录结构
4. 创建配置文件和状态文件
5. 将上下文传递给需求分析器

**输出**：
- `tools/generated_tools/tool_build_<name>/config.yaml`
- `tools/generated_tools/tool_build_<name>/status.yaml`
- `tools/generated_tools/tool_build_<name>/stages/` 目录

**关键工具调用**：
- `initialize_tool_project()`: 创建项目目录
- `update_tool_project_stage()`: 更新阶段状态

### 阶段 2: Requirements Analyzer（需求分析器）

**Agent**: `requirements_analyzer_agent.py`

**职责**：
1. 深入理解用户功能需求
2. 将需求分解为具体功能点
3. 识别输入参数和输出格式
4. 分析依赖关系和约束条件
5. 生成标准化需求文档

**输出**：
- `stages/requirements_analyzer.json`: 结构化需求文档

**文档格式**：
```json
{
  "requirements_document": {
    "tool_name": "工具名称",
    "functional_requirements": [
      {
        "id": "FR-001",
        "title": "功能标题",
        "input_parameters": [...],
        "output_format": {...},
        "use_cases": [...],
        "error_handling": [...]
      }
    ],
    "dependencies": [...],
    "constraints": {...}
  }
}
```

### 阶段 3: Tool Designer（工具设计师）

**Agent**: `tool_designer_agent.py`

**职责**：
1. 基于需求文档设计工具架构
2. 设计函数签名和接口
3. 设计实现逻辑和算法
4. 设计错误处理机制
5. 设计代码组织结构

**输出**：
- `stages/tool_designer.json`: 工具设计文档

**文档格式**：
```json
{
  "design_document": {
    "architecture": {
      "file_structure": [
        {
          "file_name": "文件名.py",
          "functions": [
            {
              "function_name": "函数名",
              "parameters": [...],
              "return_type": "...",
              "implementation_logic": "..."
            }
          ]
        }
      ]
    },
    "implementation_plan": {...},
    "dependencies": [...],
    "testing_strategy": {...}
  }
}
```

### 阶段 4: Tool Developer（工具开发者）

**Agent**: `tool_developer_agent.py`

**职责**：
1. 根据设计文档实现工具代码
2. 确保代码符合 Strands SDK 规范
3. 实现完善的错误处理
4. 添加文档字符串和注释
5. 注册工具到项目

**输出**：
- `tool_build_<name>/*.py`: 工具代码文件
- `stages/tool_developer.json`: 开发文档

**代码规范**：
- 必须使用 `@tool` 装饰器
- 使用 Python 类型提示
- 返回 JSON 字符串或错误信息
- 包含完整的 docstring

**示例代码结构**：
```python
#!/usr/bin/env python3
from strands import tool
from typing import Optional
import json

@tool
def tool_function(param1: str, param2: Optional[int] = None) -> str:
    """
    工具函数说明
    
    Args:
        param1: 参数1说明
        param2: 参数2说明
        
    Returns:
        str: JSON格式的返回值
    """
    try:
        # 实现逻辑
        result = {}
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"错误: {str(e)}"
```

### 阶段 5: Tool Validator（工具验证器）

**Agent**: `tool_validator_agent.py`

**职责**：
1. 验证代码语法正确性
2. 检查 Strands SDK 规范 compliance
3. 验证类型提示和文档字符串
4. 检查错误处理完整性
5. 验证功能需求符合性

**输出**：
- `stages/tool_validator.json`: 验证报告

**验证报告格式**：
```json
{
  "validation_report": {
    "validation_status": "passed|failed|warning",
    "syntax_check": {...},
    "code_quality": {
      "strands_compliance": true,
      "type_hints": true,
      "docstrings": true,
      "error_handling": true,
      "pep8_compliance": true
    },
    "functional_validation": {...},
    "recommendations": [...]
  }
}
```

### 阶段 6: Tool Documenter（文档生成器）

**Agent**: `tool_documenter_agent.py`

**职责**：
1. 生成完整的 README.md 文档
2. 编写工具使用说明
3. 生成 API 文档
4. 提供使用示例代码
5. 说明依赖安装方法

**输出**：
- `README.md`: 工具使用文档

**文档内容**：
- 工具概述
- 功能特性
- 安装说明
- 使用方法
- API 文档
- 参数说明
- 返回值说明
- 使用示例
- 错误处理
- 注意事项

---

## 工具系统

### 工具项目管理工具

所有工具位于 `tools/system_tools/tool_build_workflow/tool_project_manager.py`

#### 1. `initialize_tool_project(tool_name, description)`

初始化工具项目目录结构。

**参数**：
- `tool_name` (str): 工具项目名称，必须以 `tool_build_` 开头
- `description` (str, 可选): 工具项目描述

**返回**：JSON 字符串，包含项目路径和创建的文件列表

**创建内容**：
- 项目根目录
- `config.yaml`: 项目配置文件
- `status.yaml`: 项目状态文件
- `stages/`: 阶段文档目录

#### 2. `get_tool_project_config(tool_name)`

获取工具项目配置信息。

**参数**：
- `tool_name` (str): 工具项目名称

**返回**：JSON 字符串，包含配置数据

#### 3. `get_tool_project_status(tool_name)`

获取工具项目状态信息。

**参数**：
- `tool_name` (str): 工具项目名称

**返回**：JSON 字符串，包含状态数据和进度信息

#### 4. `update_tool_project_stage(tool_name, stage_name, status, doc_path, summary)`

更新工具项目阶段状态。

**参数**：
- `tool_name` (str): 工具项目名称
- `stage_name` (str): 阶段名称
- `status` (bool): 阶段状态（True 表示完成）
- `doc_path` (str, 可选): 阶段文档路径
- `summary` (str, 可选): 阶段总结

**返回**：JSON 字符串，包含更新结果和进度信息

#### 5. `write_tool_stage_document(tool_name, stage_name, content)`

将阶段文档写入工具项目的 stages 目录。

**参数**：
- `tool_name` (str): 工具项目名称
- `stage_name` (str): 阶段名称
- `content` (str): 文档内容（JSON 字符串）

**返回**：JSON 字符串，包含文件路径和写入结果

#### 6. `get_tool_stage_document(tool_name, stage_name)`

读取工具项目的阶段文档。

**参数**：
- `tool_name` (str): 工具项目名称
- `stage_name` (str): 阶段名称

**返回**：JSON 字符串，包含文档内容

#### 7. `register_tool(tool_name, tool_function_name, tool_file_path, description, parameters)`

注册工具到工具项目。

**参数**：
- `tool_name` (str): 工具项目名称
- `tool_function_name` (str): 工具函数名称
- `tool_file_path` (str): 工具文件路径（相对于项目根目录）
- `description` (str, 可选): 工具描述
- `parameters` (List[Dict], 可选): 工具参数列表

**返回**：JSON 字符串，包含注册结果

#### 8. `generate_tool_file(tool_name, file_name, content)`

在工具项目目录中生成工具文件。

**参数**：
- `tool_name` (str): 工具项目名称
- `file_name` (str): 文件名（如：my_tool.py）
- `content` (str): 文件内容

**返回**：JSON 字符串，包含文件路径和创建结果

#### 9. `generate_tool_readme(tool_name, readme_content)`

生成工具项目的 README.md 文件。

**参数**：
- `tool_name` (str): 工具项目名称
- `readme_content` (str): README 内容（Markdown 格式）

**返回**：JSON 字符串，包含文件路径和创建结果

---

## 规则系统

### 规则来源

Tool Build Workflow 遵循 Nexus-AI 平台规则系统：

1. **Base 规则**：所有工作流都必须遵守的基础规则
2. **Tool Build 规则**：工具构建工作流特定规则

规则定义在 `config/nexus_ai_base_rule.yaml` 中。

### Base 规则

**目录规则**：
- Nexus-AI 顶层目录结构：`agents/`, `prompts/`, `tools/`, `projects/`, `nexus_utils/`
- `tools/` 目录分为：`system_tools/`, `template_tools/`, `generated_tools/`

**生成规则**：
- 无特殊要求

**缓存规则**：
- 默认缓存路径：`.cache/<agent_name>/`

### Tool Build 规则

**目录规则**：
- 工具项目必须存储在 `tools/generated_tools/tool_build_<tool_name>/`
- 命名规范：必须以 `tool_build_` 开头，后跟描述性英文名称（小写，下划线分隔）
- 允许的目录和文件：
  - 项目根目录：`tool_build_<tool_name>/`
  - 阶段文档目录：`stages/`
  - 配置文件：`config.yaml`, `status.yaml`
  - 文档文件：`README.md`
  - 代码文件：`*.py`

**生成规则**：
- 每个用户的功能需求，无论开发多少个工具，都应存储在同一工具项目目录的脚本中
- 工具代码必须使用 `@tool` 装饰器，符合 Strands SDK 规范
- 工具函数应返回 JSON 字符串或错误信息字符串
- 所有工具必须注册到项目的 `status.yaml` 中
- 必须生成完整的 README.md 文档

### 规则加载

规则通过 `nexus_utils.workflow_rule_extract` 模块加载：

```python
from nexus_utils.workflow_rule_extract import (
    get_base_rules,
    get_tool_build_workflow_rules,
)

base_rules = get_base_rules()
tool_build_rules = get_tool_build_workflow_rules()
```

规则在工作流启动时加载，并通过 `kickoff_payload` 传递给所有 Agent。

---

## 目录结构

### 工具项目目录结构

```
tools/generated_tools/
└── tool_build_<tool_name>/
    ├── config.yaml              # 项目配置文件
    ├── status.yaml              # 项目状态文件
    ├── README.md                # 工具使用文档
    ├── stages/                  # 阶段文档目录
    │   ├── requirements_analyzer.json
    │   ├── tool_designer.json
    │   ├── tool_developer.json
    │   ├── tool_validator.json
    │   └── tool_documenter.json
    └── *.py                     # 工具代码文件
```

### 配置文件格式

#### config.yaml

```yaml
tool_project:
  name: tool_build_<tool_name>
  description: 工具项目描述
  version: "1.0.0"
  created_date: "2025-11-11T00:00:00+00:00"
  status: initialized
```

#### status.yaml

```yaml
tool_project: tool_build_<tool_name>
status: initialized
created_at: "2025-11-11T00:00:00+00:00"
last_updated: "2025-11-11T00:00:00+00:00"
progress:
  total: 5
  completed: 0
  percentage: 0.0
stages:
  requirements_analyzer:
    status: false
    doc_path: ""
  tool_designer:
    status: false
    doc_path: ""
  tool_developer:
    status: false
    doc_path: ""
  tool_validator:
    status: false
    doc_path: ""
  tool_documenter:
    status: false
    doc_path: ""
tools: []
```

---

## 使用指南

### 基本使用

#### 1. 命令行使用

```bash
# 使用默认需求
python agents/system_agents/tool_build_workflow/tool_build_workflow.py

# 指定用户需求
python agents/system_agents/tool_build_workflow/tool_build_workflow.py \
  -i "我需要一个工具，能够从指定的URL下载文件并保存到本地"

# 从文件读取需求
python agents/system_agents/tool_build_workflow/tool_build_workflow.py \
  -i "基础需求" \
  -f /path/to/requirements.txt
```

#### 2. Python 代码调用

```python
from agents.system_agents.tool_build_workflow.tool_build_workflow import (
    run_tool_build_workflow
)

user_input = "我需要一个工具，能够从指定的URL下载文件并保存到本地"
result = run_tool_build_workflow(user_input)

print(f"工作流状态: {result['workflow_result'].status}")
print(f"执行时间: {result['execution_time']:.2f}秒")
```

### 需求描述指南

#### 好的需求描述

✅ **清晰具体**：
```
我需要一个工具，能够：
1. 从指定的URL下载文件
2. 支持HTTP和HTTPS协议
3. 保存到指定的本地路径
4. 显示下载进度
5. 处理网络错误和文件系统错误
```

✅ **包含约束**：
```
我需要一个PDF处理工具，要求：
- 能够提取PDF文本内容
- 支持中英文混合文本
- 处理加密PDF时返回错误信息
- 使用PyPDF2库实现
```

#### 不好的需求描述

❌ **过于模糊**：
```
我需要一个文件工具
```

❌ **缺少细节**：
```
下载文件
```

### 工作流执行流程

1. **初始化阶段**
   - 加载规则系统
   - 创建 Strands Graph
   - 准备环境变量

2. **执行阶段**
   - Orchestrator 初始化项目
   - Requirements Analyzer 分析需求
   - Tool Designer 设计工具
   - Tool Developer 实现代码
   - Tool Validator 验证代码
   - Tool Documenter 生成文档

3. **完成阶段**
   - 输出执行结果
   - 显示统计信息
   - 返回工作流结果

### 查看结果

工作流完成后，工具项目位于：

```
tools/generated_tools/tool_build_<tool_name>/
```

查看各阶段文档：

```bash
# 查看需求文档
cat tools/generated_tools/tool_build_<tool_name>/stages/requirements_analyzer.json

# 查看设计文档
cat tools/generated_tools/tool_build_<tool_name>/stages/tool_designer.json

# 查看验证报告
cat tools/generated_tools/tool_build_<tool_name>/stages/tool_validator.json

# 查看工具代码
ls tools/generated_tools/tool_build_<tool_name>/*.py

# 查看文档
cat tools/generated_tools/tool_build_<tool_name>/README.md
```

---

## 示例

### 示例 1: 文件下载工具

**用户需求**：
```
我需要一个工具，能够从指定的URL下载文件并保存到本地。
要求支持HTTP和HTTPS协议，能够显示下载进度，并处理各种错误情况。
```

**工作流执行**：

```bash
python agents/system_agents/tool_build_workflow/tool_build_workflow.py \
  -i "我需要一个工具，能够从指定的URL下载文件并保存到本地。要求支持HTTP和HTTPS协议，能够显示下载进度，并处理各种错误情况。"
```

**生成结果**：

1. **项目目录**：`tools/generated_tools/tool_build_file_downloader/`

2. **工具代码**：`file_downloader.py`
   ```python
   @tool
   def download_file(url: str, save_path: str, show_progress: bool = True) -> str:
       """从URL下载文件并保存到本地"""
       # 实现代码...
   ```

3. **README.md**：包含完整的使用说明和示例

### 示例 2: 数据转换工具

**用户需求**：
```
我需要一个工具，能够将JSON数据转换为CSV格式。
支持自定义字段映射和分隔符配置。
```

**工作流执行**：

```bash
python agents/system_agents/tool_build_workflow/tool_build_workflow.py \
  -i "我需要一个工具，能够将JSON数据转换为CSV格式。支持自定义字段映射和分隔符配置。"
```

**生成结果**：

1. **项目目录**：`tools/generated_tools/tool_build_json_to_csv/`

2. **工具代码**：`json_to_csv_converter.py`
   ```python
   @tool
   def json_to_csv(json_data: str, output_path: str, 
                   field_mapping: Optional[Dict] = None,
                   delimiter: str = ",") -> str:
       """将JSON数据转换为CSV格式"""
       # 实现代码...
   ```

---

## 最佳实践

### 1. 需求描述

- ✅ **详细具体**：提供足够的功能细节和约束条件
- ✅ **结构化**：使用列表或编号组织需求点
- ✅ **包含示例**：提供使用场景和示例
- ❌ **避免模糊**：不要使用过于抽象的描述

### 2. 工具命名

- ✅ **描述性**：名称应清晰描述工具功能
- ✅ **符合规范**：必须以 `tool_build_` 开头
- ✅ **小写下划线**：使用小写字母和下划线
- ❌ **避免缩写**：除非是通用缩写

### 3. 代码质量

- ✅ **类型提示**：所有函数参数和返回值都应使用类型提示
- ✅ **文档字符串**：每个函数都应有完整的 docstring
- ✅ **错误处理**：实现完善的异常处理
- ✅ **代码风格**：遵循 PEP 8 规范

### 4. 文档编写

- ✅ **完整示例**：提供完整的使用示例代码
- ✅ **参数说明**：详细说明每个参数的含义和类型
- ✅ **错误处理**：说明可能的错误情况和处理方式
- ✅ **依赖说明**：列出所有外部依赖和安装方法

---

## 故障排查

### 常见问题

#### 1. 工具名称不符合规范

**错误信息**：
```
错误：工具名称必须以 'tool_build_' 开头
```

**解决方案**：
- 确保工具项目名称以 `tool_build_` 开头
- 使用小写字母和下划线
- 避免使用路径分隔符

#### 2. 项目目录已存在

**现象**：工作流提示项目已存在

**解决方案**：
- 检查 `tools/generated_tools/` 目录
- 删除或重命名现有项目
- 或使用不同的项目名称

#### 3. 工具代码验证失败

**现象**：Validator 阶段报告代码质量问题

**解决方案**：
- 查看 `stages/tool_validator.json` 了解具体问题
- 检查是否使用了 `@tool` 装饰器
- 确保类型提示和文档字符串完整
- 检查错误处理是否完善

#### 4. 规则加载失败

**错误信息**：
```
WorkflowRuleError: 未找到工作流 `tool_build` 的规则定义
```

**解决方案**：
- 检查 `config/nexus_ai_base_rule.yaml` 中是否有 `tool_build` 规则
- 确认规则版本为 `latest`
- 检查 `nexus_utils/workflow_rule_extract.py` 中的函数实现

#### 5. Agent 创建失败

**错误信息**：
```
Tool 'system_tools/tool_build_workflow/...' not found
```

**解决方案**：
- 检查工具路径是否正确
- 确认工具文件存在于 `tools/system_tools/tool_build_workflow/`
- 检查提示词 YAML 中的 `tools_dependencies` 配置

### 调试技巧

#### 1. 查看阶段文档

每个阶段的输出都保存在 `stages/` 目录中，可以查看了解各阶段的执行情况：

```bash
# 查看所有阶段文档
ls -la tools/generated_tools/tool_build_<name>/stages/

# 查看特定阶段文档
cat tools/generated_tools/tool_build_<name>/stages/requirements_analyzer.json | jq
```

#### 2. 查看状态文件

状态文件记录了项目的整体进度和各阶段状态：

```bash
cat tools/generated_tools/tool_build_<name>/status.yaml
```

#### 3. 查看工作流日志

工作流执行时会输出详细的日志信息，包括：
- 各阶段执行状态
- 工具调用结果
- 错误信息

#### 4. 单独测试 Agent

可以单独测试每个 Agent：

```bash
# 测试 Orchestrator
python agents/system_agents/tool_build_workflow/tool_build_orchestrator_agent.py \
  -i "初始化工具项目"

# 测试 Requirements Analyzer
python agents/system_agents/tool_build_workflow/requirements_analyzer_agent.py \
  -i "分析用户需求"
```

---

## 总结

Tool Build Workflow 是 Nexus-AI 平台中强大的工具自动化构建系统。通过 6 个专业 Agent 的协作，能够将用户自然语言需求转换为符合 Strands SDK 规范的高质量工具代码。

### 核心优势

1. **自动化**：从需求到代码全流程自动化
2. **规范化**：严格遵循平台规则和代码规范
3. **可追溯**：完整的阶段文档和状态跟踪
4. **高质量**：自动验证和文档生成

### 适用场景

- 快速原型开发
- 工具标准化开发
- 批量工具生成
- 工具文档自动生成

### 未来改进

- 支持工具版本管理
- 支持工具测试用例生成
- 支持工具性能分析
- 支持工具依赖管理

---

**文档版本**: 1.0  
**最后更新**: 2025-11-11  
**作者**: Nexus-AI Team

