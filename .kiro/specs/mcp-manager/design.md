# 设计文档

## 概述

MCP管理器是一个用于管理和访问MCP（模型上下文协议）服务器配置的工具类。它遵循现有prompts_manager.py的设计模式，提供配置加载、解析、访问和客户端创建功能。该管理器将与Strands SDK集成，为配置的MCP服务器创建客户端实例。

## 架构

### 核心组件

1. **MCPServerConfig** - 数据类，表示单个MCP服务器配置
2. **MCPManager** - 主管理器类，负责加载和管理所有MCP配置
3. **MCPClientFactory** - 工厂类，负责创建MCP客户端实例
4. **MCPManagerRegistry** - 注册表类，管理多个MCPManager实例

### 设计模式

- **单例模式**: MCPManager使用单例模式确保配置的一致性
- **工厂模式**: MCPClientFactory负责根据配置创建不同类型的MCP客户端
- **注册表模式**: MCPManagerRegistry管理多个配置路径的实例

## 组件和接口

### MCPServerConfig 数据类

```python
@dataclass
class MCPServerConfig:
    name: str
    command: str
    args: List[str]
    env: Dict[str, str]
    auto_approve: List[str]
    disabled: bool
    
    def is_enabled(self) -> bool:
        return not self.disabled
```

### MCPManager 类

```python
class MCPManager:
    def __init__(self, config_path: str = default_mcp_path)
    def load_configs(self) -> None
    def get_server_config(self, server_name: str) -> Optional[MCPServerConfig]
    def get_all_servers(self) -> Dict[str, MCPServerConfig]
    def get_enabled_servers(self) -> Dict[str, MCPServerConfig]
    def create_client(self, server_name: str) -> Optional[ClientSession]
```

### MCPClientFactory 类

```python
class MCPClientFactory:
    @staticmethod
    async def create_client(config: MCPServerConfig) -> ClientSession
    @staticmethod
    def _validate_config(config: MCPServerConfig) -> bool
```

## 数据模型

### MCP配置文件结构

```json
{
    "mcpServers": {
        "server-name": {
            "command": "uvx",
            "args": ["package@latest"],
            "env": {
                "ENV_VAR": "value"
            },
            "autoApprove": [],
            "disabled": false
        }
    }
}
```

### 内部数据结构

- **配置字典**: `Dict[str, MCPServerConfig]` - 存储所有加载的服务器配置
- **客户端缓存**: `Dict[str, ClientSession]` - 缓存已创建的客户端实例（可选）

## 错误处理

### 配置加载错误

1. **文件不存在**: 记录警告，继续处理其他文件
2. **JSON格式错误**: 记录错误，跳过该文件
3. **配置结构无效**: 记录错误，跳过无效配置项

### 客户端创建错误

1. **服务器已禁用**: 返回None，记录信息
2. **配置无效**: 抛出ConfigurationError异常
3. **连接失败**: 抛出ConnectionError异常
4. **认证失败**: 抛出AuthenticationError异常

### 异常类型

```python
class MCPManagerError(Exception):
    """MCP管理器基础异常"""
    pass

class ConfigurationError(MCPManagerError):
    """配置错误异常"""
    pass

class ConnectionError(MCPManagerError):
    """连接错误异常"""
    pass
```

## 测试策略

### 单元测试

1. **配置加载测试**
   - 测试正确的JSON文件加载
   - 测试无效JSON文件处理
   - 测试空配置文件处理

2. **配置访问测试**
   - 测试获取存在的服务器配置
   - 测试获取不存在的服务器配置
   - 测试获取已禁用的服务器配置

3. **客户端创建测试**
   - 测试有效配置的客户端创建
   - 测试无效配置的错误处理
   - 测试禁用服务器的处理

### 集成测试

1. **端到端测试**
   - 使用真实的MCP服务器配置
   - 测试完整的加载-创建-交互流程
   - 验证与现有system_mcp_server.json的兼容性

2. **错误场景测试**
   - 测试网络连接失败
   - 测试服务器不可用
   - 测试认证失败

### 测试数据

创建测试用的MCP配置文件，包含：
- 有效的服务器配置
- 禁用的服务器配置
- 无效的配置格式
- 空配置文件

## 实现细节

### 文件加载策略

1. 扫描指定目录下的所有.json文件
2. 按文件名排序确保加载顺序的一致性
3. 支持配置覆盖（后加载的同名配置覆盖先加载的）

### 客户端生命周期管理

1. 客户端按需创建，不预先创建
2. 支持客户端缓存以提高性能（可选功能）
3. 提供客户端关闭和清理方法

### 配置热重载

1. 提供reload_configs()方法支持配置热重载
2. 重载时清理现有客户端缓存
3. 通知机制（可选）用于配置变更通知