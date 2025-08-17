# MCP配置管理工具

这个工具提供了一套完整的MCP（模型上下文协议）服务器配置管理功能，基于 `utils/mcp_manager.py` 构建，为Agent提供便捷的MCP配置查询和管理接口。

## 功能特性

### 基础查询功能
- `get_all_mcp_servers()` - 获取所有MCP服务器配置
- `get_enabled_mcp_servers()` - 获取所有启用的MCP服务器配置
- `get_mcp_server_by_name(server_name)` - 根据名称获取特定服务器配置

### 搜索和筛选功能
- `search_mcp_servers_by_command(command)` - 根据命令搜索服务器
- `search_mcp_servers_by_args(keyword)` - 根据参数关键词搜索服务器
- `get_mcp_servers_with_auto_approve()` - 获取配置了自动批准的服务器
- `get_mcp_servers_with_env_vars()` - 获取配置了环境变量的服务器

### 统计和管理功能
- `get_mcp_server_statistics()` - 获取服务器配置统计信息
- `validate_mcp_server_config(server_name)` - 验证服务器配置有效性
- `reload_mcp_configs()` - 重新加载配置文件

## 使用示例

### 在Agent中使用

```python
from tools.system_tools.mcp_config_manager import (
    get_all_mcp_servers,
    get_enabled_mcp_servers,
    get_mcp_server_statistics
)

# 获取所有服务器配置
all_servers = get_all_mcp_servers()
print(all_servers)

# 获取启用的服务器
enabled_servers = get_enabled_mcp_servers()
print(enabled_servers)

# 获取统计信息
stats = get_mcp_server_statistics()
print(stats)
```

### 直接测试

```bash
python tools/system_tools/mcp_config_manager.py
```

## 返回数据格式

所有函数都返回JSON格式的字符串，包含以下字段：

```json
{
  "name": "服务器名称",
  "command": "启动命令",
  "args": ["参数列表"],
  "env": {"环境变量": "值"},
  "auto_approve": ["自动批准的工具列表"],
  "disabled": false,
  "enabled": true
}
```

## 配置文件位置

工具会自动扫描以下位置的MCP配置文件：
- `./mcp/*.json`

配置文件格式：
```json
{
  "mcpServers": {
    "server-name": {
      "command": "uvx",
      "args": ["package@latest"],
      "env": {"VAR": "value"},
      "autoApprove": ["tool1"],
      "disabled": false
    }
  }
}
```

## 错误处理

所有函数都包含完善的错误处理机制，当出现错误时会返回包含错误信息的字符串。

## 依赖关系

- `utils.mcp_manager` - 核心MCP管理功能
- `strands` - 工具装饰器支持
- Python标准库：`json`, `sys`, `os`

## 注意事项

1. 确保MCP配置文件格式正确
2. 工具会自动处理配置文件的加载和解析
3. 支持配置热重载，无需重启应用
4. 所有返回值都是JSON格式的字符串，便于Agent处理