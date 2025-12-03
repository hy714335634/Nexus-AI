# 修复 update_project_readme 工具类型错误

## 问题描述

在执行 `update_project_readme` 工具时，出现以下错误：

```
更新项目README时出现错误: 'str' object has no attribute 'get'
```

## 错误原因

1. **YAML解析返回值类型不确定**：`yaml.safe_load()` 可能返回字典、字符串、列表或其他类型，取决于YAML文件的内容和格式。

2. **缺少类型检查**：代码直接对 `yaml.safe_load()` 的返回值调用 `.get()` 方法，如果返回值是字符串类型，就会导致 `'str' object has no attribute 'get'` 错误。

3. **问题位置**：
   - 第482行：`config.get("project", {})` - 当 `config` 是字符串时会报错
   - 第498行和第503行：`project.get("name")` 和 `status.get("project", [])` - 当对象不是字典时会报错

## 修复方案

### 1. 配置文件读取部分（第475-485行）

**修复前**：
```python
config = yaml.safe_load(f) or {}
project_description = config.get("project", {}).get("description", project_description)
```

**修复后**：
```python
config_raw = yaml.safe_load(f)
# 确保config是字典类型，如果不是则使用空字典
if not isinstance(config_raw, dict):
    config = {}
else:
    config = config_raw

# 安全获取项目描述
project_section = config.get("project", {})
if isinstance(project_section, dict):
    project_description = project_section.get("description", project_description)
```

### 2. 状态文件读取部分（第487-515行）

**修复前**：
```python
status = yaml.safe_load(f) or {}
if "project_info" in status and isinstance(status["project_info"], list):
    for project in status["project_info"]:
        if project.get("name") == project_name:
            agents_status = project.get("agents", [])
            break
else:
    agents_status = status.get("project", [])
```

**修复后**：
```python
status_raw = yaml.safe_load(f)
# 确保status是字典类型，如果不是则使用空字典
if not isinstance(status_raw, dict):
    status = {}
else:
    status = status_raw

# 兼容新格式
if "project_info" in status and isinstance(status.get("project_info"), list):
    for project in status["project_info"]:
        # 确保project是字典类型
        if isinstance(project, dict) and project.get("name") == project_name:
            agents_status = project.get("agents", [])
            if not isinstance(agents_status, list):
                agents_status = []
            break
else:
    # 兼容旧格式
    project_data = status.get("project", [])
    if isinstance(project_data, list):
        agents_status = project_data
```

### 3. 异常处理增强

添加了更全面的异常处理，捕获 `TypeError` 和 `AttributeError`：

```python
except (yaml.YAMLError, TypeError, AttributeError) as e:
    logger.warning(f"读取status.yaml时出现错误: {str(e)}")
    agents_status = []
```

## 修复效果

1. ✅ **类型安全**：确保所有字典操作都在字典类型对象上进行
2. ✅ **容错性增强**：即使YAML文件格式异常，也不会导致工具失败
3. ✅ **日志记录**：添加了警告日志，便于排查问题
4. ✅ **向后兼容**：保持了对新格式和旧格式状态文件的兼容

## 测试建议

### 测试场景1：正常YAML文件
- 配置文件包含正确的字典结构
- 状态文件包含正确的字典结构
- 预期：正常解析并生成README

### 测试场景2：格式异常的YAML文件
- 配置文件内容是纯字符串
- 状态文件内容是列表而不是字典
- 预期：使用默认值，不报错

### 测试场景3：空的YAML文件
- 配置文件为空
- 状态文件为空
- 预期：使用默认值，不报错

### 测试场景4：格式错误的YAML文件
- YAML语法错误
- 预期：捕获异常，使用默认值

## 相关文件

- 修复文件：`tools/system_tools/agent_build_workflow/project_manager.py`
- 函数：`update_project_readme()` (第452-600行)

## 修复日期

2025-01-XX

## 影响范围

- 仅影响 `update_project_readme` 工具
- 不影响其他工具功能
- 向后兼容，不破坏现有功能

