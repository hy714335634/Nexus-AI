# 文件验证错误分类系统

## 概述

新的文件验证系统提供了详细的错误分类和具体原因，帮助用户快速定位和解决问题。系统支持三种文件类型的验证：提示词文件(prompt)、代理文件(agent)和工具文件(tool)。

## 错误分类

### 1. 文件相关错误

#### FILE_NOT_FOUND
- **原因**: 指定的文件路径不存在
- **详情**: 文件不存在: {file_path}
- **建议**: 
  - 检查文件路径是否正确
  - 确认文件是否已被删除或移动
  - 参考示例文件: prompts/template_prompts/default.yaml

#### FILE_PERMISSION_ERROR
- **原因**: 文件权限不足，无法读取
- **详情**: 文件权限不足，无法读取: {file_path}
- **建议**: 检查文件权限，确保有读取权限

#### FILE_ENCODING_ERROR
- **原因**: 文件编码错误
- **详情**: 文件编码错误: {error_message}
- **建议**: 确保文件使用UTF-8编码

#### FILE_READ_ERROR
- **原因**: 读取文件时发生错误
- **详情**: 读取文件时发生错误: {error_message}
- **建议**: 检查文件是否被其他程序占用

### 2. YAML语法错误

#### YAML_SYNTAX_ERROR
- **原因**: YAML语法错误
- **详情**: YAML语法错误: {error_message}
- **建议**:
  - 检查YAML缩进是否正确（使用空格，不要使用Tab）
  - 检查是否有未闭合的引号或括号
  - 检查是否有特殊字符需要转义
  - 使用在线YAML验证工具检查语法

#### EMPTY_YAML
- **原因**: YAML文件为空或只包含注释
- **详情**: YAML文件为空或只包含注释
- **建议**: 添加agent配置部分

### 3. 结构错误

#### MISSING_AGENT_SECTION
- **原因**: 缺少agent配置部分
- **详情**: 缺少agent配置部分
- **建议**:
  - 在YAML文件根级别添加agent配置
  - 参考示例文件: prompts/template_prompts/default.yaml

#### MISSING_REQUIRED_FIELDS
- **原因**: 缺少必要字段或字段值无效
- **详情**: 
  - 缺少必要字段: {missing_fields}
  - 字段值无效: {invalid_fields}
- **建议**:
  - 添加缺少的字段: {missing_fields}
  - 为无效字段提供有效值: {invalid_fields}
  - 参考示例文件了解字段格式

#### INVALID_ENVIRONMENTS_FORMAT
- **原因**: environments字段格式错误
- **详情**: environments字段必须是包含环境配置的字典
- **建议**:
  - environments应该包含development、production、testing等环境
  - 每个环境应包含max_tokens、temperature、top_p、streaming等配置

#### INVALID_VERSIONS_FORMAT
- **原因**: versions字段格式错误
- **详情**: versions字段必须是包含版本信息的列表
- **建议**:
  - versions应该是一个列表，包含至少一个版本配置
  - 每个版本应包含version、status、created_date、author、description等字段

### 4. 工具依赖错误

#### INVALID_TOOLS_DEPENDENCIES_FORMAT
- **原因**: tools_dependencies格式错误
- **详情**: 具体的格式错误信息
- **建议**:
  - 检查tools_dependencies格式
  - generated_tools格式: generated_tools/<project_name>/<script_name>/<tool_name>
  - system_tools格式: system_tools/<module_name>/<tool_name>
  - strands_tools格式: strands_tools/<tool_name>

### 5. Python语法错误

#### PYTHON_SYNTAX_ERROR
- **原因**: Python语法错误
- **详情**: Python语法错误: {error_message}
- **建议**:
  - 检查Python语法是否正确
  - 检查缩进是否正确
  - 检查是否有未闭合的括号或引号
  - 使用IDE的语法检查功能

### 6. 导入错误

#### MISSING_REQUIRED_IMPORTS
- **原因**: 缺少必要的导入
- **详情**: 缺少必要的导入: {missing_imports}
- **建议**:
  - 添加必要的导入语句
  - 确保使用正确的导入格式
  - 参考示例文件了解正确的导入格式

#### MISSING_STRANDS_IMPORT
- **原因**: 缺少strands导入
- **详情**: 缺少strands导入
- **建议**:
  - 添加 'from strands import tool' 导入语句
  - 确保使用 @tool 装饰器定义工具函数

### 7. 工具函数错误

#### NO_TOOL_FUNCTIONS
- **原因**: 文件中没有找到工具函数
- **详情**: 文件中没有找到工具函数
- **建议**:
  - 使用 @tool 装饰器定义至少一个工具函数
  - 确保函数有正确的类型注解
  - 参考示例文件了解工具函数格式

#### TOOL_PARSING_ERROR
- **原因**: 解析工具函数时发生错误
- **详情**: 解析工具函数时发生错误: {error_message}
- **建议**:
  - 检查工具函数的定义格式
  - 确保使用正确的 @tool 装饰器
  - 检查函数参数的类型注解

### 8. 系统错误

#### UNEXPECTED_ERROR
- **原因**: 验证过程中发生意外错误
- **详情**: 验证过程中发生意外错误: {error_message}
- **建议**:
  - 检查文件是否损坏
  - 尝试重新创建文件
  - 联系技术支持

## 验证结果结构

```json
{
  "valid": true/false,
  "file_path": "文件路径",
  "error_category": "错误分类",
  "error_details": ["错误详情列表"],
  "checks": {
    "file_exists": true/false,
    "file_readable": true/false,
    "yaml_syntax": true/false,
    "has_agent_section": true/false,
    "has_required_fields": true/false,
    "required_fields_details": {
      "missing_fields": ["缺少的字段"],
      "invalid_fields": ["无效字段"]
    },
    "environments_format": true/false,
    "versions_format": true/false,
    "tools_dependencies_format": true/false,
    "tools_dependencies_details": {
      "errors": ["错误列表"],
      "warnings": ["警告列表"]
    }
  },
  "suggestions": ["建议列表"],
  "warnings": ["警告信息列表"]
}
```

## 使用示例

### 验证提示词文件
```python
from tools.system_tools.agent_build_workflow.prompt_template_provider import validate_prompt_file

# 验证提示词文件
result = validate_prompt_file("prompts/template_prompts/default.yaml")
data = json.loads(result)

if data["valid"]:
    print("验证通过")
    if "warnings" in data:
        print(f"警告: {data['warnings']}")
else:
    print(f"错误分类: {data['error_category']}")
    print(f"错误详情: {data['error_details']}")
    print(f"建议: {data['suggestions']}")
```

### 验证代理文件
```python
from tools.system_tools.agent_build_workflow.agent_template_provider import validate_agent_file

# 验证代理文件
result = validate_agent_file("agents/generated_agents/test_project/test_agent.py")
data = json.loads(result)

if data["valid"]:
    print("验证通过")
else:
    print(f"错误分类: {data['error_category']}")
    print(f"错误详情: {data['error_details']}")
    print(f"建议: {data['suggestions']}")
```

### 验证工具文件
```python
from tools.system_tools.agent_build_workflow.tool_template_provider import validate_tool_file

# 验证工具文件
result = validate_tool_file("tools/generated_tools/test_project/test_tool.py")
data = json.loads(result)

if data["valid"]:
    print("验证通过")
else:
    print(f"错误分类: {data['error_category']}")
    print(f"错误详情: {data['error_details']}")
    print(f"建议: {data['suggestions']}")
```

### 使用generate_content函数
```python
from tools.system_tools.agent_build_workflow.project_manager import generate_content

# 生成内容文件（会自动验证）
result = generate_content("prompt", content, "project_name", "artifact_name")
print(result)
```

## 工具依赖格式规范

### generated_tools
格式: `generated_tools/<project_name>/<script_name>/<tool_name>`
示例: `generated_tools/aws_pricing_agent/aws_pricing_functions/get_pricing`

### system_tools
格式: `system_tools/<module_name>/<tool_name>`
示例: `system_tools/agent_build_workflow/tool_template_provider/list_all_tools`

### strands_tools
格式: `strands_tools/<tool_name>`
示例: `strands_tools/shell`

## 最佳实践

1. **定期验证**: 建议在修改提示词文件后立即进行验证
2. **版本控制**: 使用版本控制管理提示词文件
3. **格式检查**: 使用IDE的YAML语法检查功能
4. **工具依赖**: 确保工具依赖路径的正确性
5. **测试验证**: 在部署前进行完整的验证测试
