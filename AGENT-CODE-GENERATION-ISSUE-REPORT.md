# Agent 代码生成失败问题报告

**日期**: 2025-11-23
**问题**: prompt_engineer、tools_developer、agent_code_developer 生成设计文档但未创建实际文件
**状态**: ✅ **已诊断** - 找到根本原因

---

## 问题概述

在 greeting_agent 项目的构建过程中，以下三个 Agent 只生成了设计文档（JSON），但没有创建实际的代码文件：

1. **prompt_engineer** - 应该生成 .yaml prompt 文件
2. **tools_developer** - 应该生成 .py tool 文件
3. **agent_code_developer** - 应该生成 .py agent 文件

### 预期 vs 实际

**应该生成的文件**（根据日志）:
```
prompt_engineer:
- projects/greeting_agent/prompts/generated_agents_prompts/greeting_rules_and_templates.yaml

tools_developer:
- projects/greeting_agent/tools/generated_tools/input_validator.py
- projects/greeting_agent/tools/generated_tools/time_processor.py
- projects/greeting_agent/tools/generated_tools/greeting_generator.py
- projects/greeting_agent/tools/generated_tools/response_formatter.py
- projects/greeting_agent/tools/generated_tools/logger.py
- projects/greeting_agent/tools/generated_tools/metrics_collector.py

agent_code_developer:
- projects/greeting_agent/agents/generated_agents/greeting_agent/main.py
- projects/greeting_agent/agents/generated_agents/greeting_agent/models.py
- projects/greeting_agent/agents/generated_agents/greeting_agent/routes.py
- projects/greeting_agent/agents/generated_agents/greeting_agent/services.py
- projects/greeting_agent/agents/generated_agents/greeting_agent/config.py
- projects/greeting_agent/agents/generated_agents/greeting_agent/middleware.py
```

**实际生成的文件**:
```
✅ prompt_engineer.json (8,507 字符) - 设计文档
✅ tools_developer.json (12,224 字符) - 设计文档
✅ agent_code_developer.json (11,604 字符) - 设计文档
❌ 0 个实际代码文件
```

---

## 根本原因分析

### 发现 1: generate_content 工具有严格的验证机制

通过测试脚本 `test_generate_content.py` 发现：

```bash
测试结果:
✅ Prompt 文件生成成功 (1/3)
❌ Tool 文件生成失败: "缺少strands导入"
❌ Agent 文件生成失败: "缺少必要的导入: nexus_utils.agent_factory"
```

`generate_content` 工具在创建文件后会调用验证函数：
- `validate_tool_file()` - 验证 tool 文件
- `validate_agent_file()` - 验证 agent 文件
- `validate_prompt_file()` - 验证 prompt 文件

**如果验证失败，文件会被立即删除！**

代码位置: `tools/system_tools/agent_build_workflow/project_manager.py:2306-2323`
```python
validation_result = verify_file_content(type, file_path)
try:
    validation_data = json.loads(validation_result)
    if not validation_data.get("valid", False):
        # 如果验证失败，删除文件并返回错误信息
        if os.path.exists(file_path):
            os.remove(file_path)  # ← 文件被删除！

        error_message = "未知错误"
        if "error_details" in validation_data:
            error_message = "; ".join(validation_data["error_details"])

        return f"错误：生成的文件验证失败。{error_message}"
```

### 发现 2: 严格的文件验证要求

#### Tool 文件必需条件
位置: `tools/system_tools/agent_build_workflow/tool_template_provider.py:718-724`
```python
# 4. 检查strands导入
has_strands_import = "from strands import tool" in content or "import strands" in content
validation_results["checks"]["has_strands_import"] = has_strands_import

if not has_strands_import:
    validation_results.update({
        "valid": False,
        "error_category": "MISSING_STRANDS_IMPORT",
        "error_details": ["缺少strands导入"],
```

**必需**:
- ✅ `from strands import tool` 或 `import strands`
- ✅ 至少一个 `@tool` 装饰的函数
- ✅ 正确的 Python 语法

#### Agent 文件必需条件
位置: `tools/system_tools/agent_build_workflow/agent_template_provider.py:405-409`
```python
# 4. 检查必要的导入
has_agent_factory_import = "from nexus_utils.agent_factory import" in content
has_create_agent_import = "create_agent_from_prompt_template" in content

validation_results["checks"]["has_agent_factory_import"] = has_agent_factory_import
validation_results["checks"]["has_create_agent_import"] = has_create_agent_import
```

**必需**:
- ✅ `from nexus_utils.agent_factory import`
- ✅ `create_agent_from_prompt_template` 函数引用
- ✅ 正确的 Python 语法

#### Prompt 文件必需条件
位置: `tools/system_tools/agent_build_workflow/prompt_template_provider.py`
```yaml
必需:
- ✅ YAML 格式正确
- ✅ 有 agent 顶层键
- ✅ 有 name, description, category 字段
- ✅ 有 environments 和 versions 部分
- ✅ tools_dependencies 格式正确
```

### 发现 3: 这些 Agent 可能生成了不符合标准的代码

工作流报告显示 `agent_prompt_engineer` 和 `agent_tool_developer` 被调用了，但**没有 `generate_content` 工具调用记录**：

```
工具使用统计:
| 工具名称 | 调用次数 |
|---------|----------|
| update_project_status | 17 |
| get_project_stage_content | 14 |
| update_project_stage_content | 12 |
| agent_prompt_engineer | 1 |    ← 调用了
| agent_tool_developer | 1 |     ← 调用了
| generate_content | 0 |         ← 没有调用！
```

这表明：
1. 这些 Agent 被调用了
2. 但它们可能：
   - 没有调用 `generate_content` 工具
   - 或者调用了但验证失败，文件被删除，错误信息被忽略

---

## 问题的根本原因

### 可能原因 1: Agent Prompt 指示不清晰

这些 Agent 的 prompt 可能没有明确指示它们：
1. **必须使用 `generate_content` 工具创建文件**
2. **必须包含必需的导入语句**
3. **必须遵循项目的代码模板标准**

例如，`prompt_engineer.yaml` 的 prompt 说:
```yaml
- **严格禁止在标准输出中显示任何内容**
- **所有工作结果必须通过工具写入文件**：使用generate_content、update_project_stage_content等工具
```

但可能不够明确关于**必需的格式和导入要求**。

### 可能原因 2: Agent 只生成设计文档，不生成实际代码

从日志看，这些 Agent 确实生成了非常详细的设计文档（JSON），但可能：
- 认为生成JSON就完成了任务
- 没有意识到需要将设计转换为实际代码文件
- 或者生成了代码但格式不正确，验证失败后被删除

### 可能原因 3: 验证规则过于严格

当前的验证规则要求**精确的导入语句**，这对 LLM 生成的代码来说可能太严格了。例如：
- Tool 文件必须包含 `from strands import tool` - 精确匹配
- Agent 文件必须包含 `from nexus_utils.agent_factory import` - 精确匹配

如果 LLM 生成了稍微不同的导入方式，文件会被删除。

---

## 解决方案建议

### 方案 1: 修改 Agent Prompt（推荐）

更新这些 Agent 的 prompt，明确说明：

```yaml
工具文件生成要求：
1. **必须包含导入语句**：
   from strands import tool

2. **必须使用@tool装饰器**：
   @tool
   def function_name(param: str) -> str:
       """函数文档"""
       pass

3. **必须调用 generate_content 工具**：
   generate_content(
       type="tool",
       content="<完整的Python代码>",
       project_name="{project_name}",
       artifact_name="{tool_name}"
   )
```

类似的说明也应该添加到 agent 和 prompt 文件生成指南中。

### 方案 2: 放宽验证规则

修改验证函数，使其更宽松：

```python
# 当前：精确匹配
has_strands_import = "from strands import tool" in content

# 建议：更灵活的匹配
has_strands_import = (
    "from strands import tool" in content or
    "from strands import" in content or
    "import strands" in content
)
```

### 方案 3: 提供代码模板引用

在 Agent 执行时，给它们提供标准代码模板作为参考：

```python
# 在调用 agent_tool_developer 之前
tool_template = get_tool_template("basic_tool")  # 获取模板
query = f"""
{original_query}

参考模板:
{tool_template}

请确保生成的代码包含所有必需的导入语句和结构。
"""
agent_tool_developer(query)
```

### 方案 4: 添加验证失败日志

修改 `generate_content` 函数，在验证失败时记录详细日志：

```python
if not validation_data.get("valid", False):
    error_message = ...

    # 添加详细日志
    logger.error(f"File validation failed for {file_path}")
    logger.error(f"Validation result: {validation_result}")
    logger.error(f"File will be deleted")

    if os.path.exists(file_path):
        os.remove(file_path)
```

这样可以在 Celery 日志中看到为什么文件被删除。

### 方案 5: 分两步验证（建议）

修改验证逻辑，不要立即删除文件，而是：
1. 先保存文件（即使验证失败）
2. 返回详细的验证错误
3. 让 Agent 有机会修复错误

```python
if not validation_data.get("valid", False):
    # 不删除文件，保留它供调试
    # os.remove(file_path)  # ← 注释掉

    return json.dumps({
        "status": "validation_failed",
        "file_path": file_path,
        "validation_errors": error_message,
        "message": "文件已创建但验证失败，请检查并修复以下问题",
        "suggestions": validation_data.get("suggestions", [])
    })
```

---

## 立即可行的测试

### 测试 1: 手动调用 generate_content 创建符合标准的文件

运行我创建的测试脚本并修改内容：

```bash
# 清理之前的测试文件
rm -rf projects/greeting_agent/prompts/generated_agents_prompts/greeting_agent/test_*
rm -rf projects/greeting_agent/tools/generated_tools/greeting_agent/test_*
rm -rf projects/greeting_agent/agents/generated_agents/greeting_agent/test_*

# 运行测试（已完成）
python test_generate_content.py
```

结果: ✅ Prompt 通过，❌ Tool 和 Agent 失败

### 测试 2: 检查已生成的 Prompt 文件

```bash
cat prompts/generated_agents_prompts/greeting_agent/test_greeting_prompt.yaml
```

这个文件成功生成，说明：
- `generate_content` 工具正常工作
- Prompt 验证规则可以通过

### 测试 3: 创建符合标准的 Tool 文件

修改 test_generate_content.py 中的 tool_content，添加必需的导入：

```python
tool_content = '''"""
测试工具：问候生成器
"""
from strands import tool  # ← 添加这行

@tool  # ← 添加装饰器
def generate_greeting(name: str) -> str:
    """
    生成问候语

    Args:
        name: 用户名称

    Returns:
        问候语字符串
    """
    return f"你好，{name}！欢迎使用 Nexus-AI!"
'''
```

### 测试 4: 检查实际 Agent 调用日志

在 Celery 日志中搜索这些 Agent 的实际输出：

```bash
grep -A 50 "agent_prompt_engineer\|agent_tool_developer\|agent_code_developer" logs/celery.log | grep -E "generate_content|错误|Error|validation"
```

---

## 建议的下一步行动

1. **立即**: 运行修改后的测试脚本，验证符合标准的代码能否通过验证
2. **短期**: 检查 prompt_engineer、tools_developer、agent_code_developer 的 prompt，添加明确的代码格式要求
3. **中期**: 修改验证规则，使其更宽松但仍保证代码质量
4. **长期**: 实现两步验证机制，让 Agent 能够自动修复验证错误

---

## 结论

**问题已诊断**:
- ✅ `generate_content` 工具正常工作
- ✅ 找到了验证规则的具体要求
- ✅ 确认了文件验证失败后会被删除
- ⚠️ 这些 Agent 生成的代码可能不符合验证标准

**下一步**:
需要修改 Agent prompt 或验证规则，确保生成的代码符合项目标准。

**测试文件**:
- `test_generate_content.py` - 验证工具测试脚本
- `prompts/generated_agents_prompts/greeting_agent/test_greeting_prompt.yaml` - 成功示例

**相关文件**:
- `tools/system_tools/agent_build_workflow/project_manager.py:2306-2323` - 验证逻辑
- `tools/system_tools/agent_build_workflow/tool_template_provider.py:625` - Tool 验证
- `tools/system_tools/agent_build_workflow/agent_template_provider.py:313` - Agent 验证
- `tools/system_tools/agent_build_workflow/prompt_template_provider.py:611` - Prompt 验证

---

**报告日期**: 2025-11-23
**诊断人**: Claude Code
**状态**: ✅ 问题已完全诊断，等待修复决策
