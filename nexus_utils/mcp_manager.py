"""
MCP管理器模块

此模块提供了一个完整的MCP（模型上下文协议）服务器配置管理和客户端创建系统。
它遵循现有prompts_manager.py的设计模式，提供配置加载、解析、访问和客户端创建功能。

主要功能：
- 从JSON配置文件加载MCP服务器配置
- 验证和管理服务器配置
- 创建和管理MCP客户端实例
- 提供单例模式的配置管理
- 支持配置热重载

快速开始：
    # 1. 获取管理器实例（推荐方式）
    from nexus_utils.mcp_manager import get_default_mcp_manager
    manager = get_default_mcp_manager()
    
    # 2. 查看可用服务器
    servers = manager.get_enabled_servers()
    print(f"可用服务器: {list(servers.keys())}")
    
    # 3. 创建客户端（同步方式）
    client = manager.create_client_sync("server-name")
    
    # 4. 创建客户端（异步方式）
    client = await manager.create_client("server-name")

常用API：
    - get_default_mcp_manager(): 获取默认管理器实例
    - manager.get_all_servers(): 获取所有服务器配置
    - manager.get_enabled_servers(): 获取启用的服务器配置
    - manager.get_server_config(name): 获取指定服务器配置
    - manager.create_client(name): 异步创建客户端
    - manager.create_client_sync(name): 同步创建客户端
    - manager.reload_configs(): 重新加载配置文件

配置文件格式：
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

作者: Nexus-AI Team
版本: 1.0.0
"""

from typing import Dict, Optional, List, Any
from dataclasses import dataclass
import json
import glob
import os
from pathlib import Path
import asyncio
from strands.tools.mcp.mcp_client import MCPClient

# Default MCP configuration path
default_mcp_path = './mcp/*.json'

# Exception classes
class MCPManagerError(Exception):
    """
    MCP管理器基础异常类
    
    所有MCP管理器相关异常的基类。
    """
    pass


class ConfigurationError(MCPManagerError):
    """
    配置错误异常
    
    当MCP服务器配置无效或缺失时抛出此异常。
    
    常见情况：
    - 配置文件格式错误
    - 必需字段缺失
    - 字段类型不正确
    - 服务器已被禁用
    """
    pass


class ConnectionError(MCPManagerError):
    """
    连接错误异常
    
    当无法连接到MCP服务器或创建客户端失败时抛出此异常。
    
    常见情况：
    - 服务器未运行
    - 网络连接问题
    - 认证失败
    - 服务器配置错误
    """
    pass

@dataclass
class MCPServerConfig:
    """
    MCP服务器配置数据类
    
    表示单个MCP服务器的完整配置信息。
    
    属性:
        name (str): 服务器名称，用作唯一标识符
        command (str): 启动服务器的命令（如 "uvx"）
        args (List[str]): 命令参数列表（如 ["package@latest"]）
        env (Dict[str, str]): 环境变量字典
        auto_approve (List[str]): 自动批准的工具列表
        disabled (bool): 是否禁用此服务器
    
    示例:
        config = MCPServerConfig(
            name="my-server",
            command="uvx",
            args=["my-package@latest"],
            env={"API_KEY": "secret"},
            auto_approve=["tool1", "tool2"],
            disabled=False
        )
    """
    name: str
    command: str
    args: List[str]
    env: Dict[str, str]
    auto_approve: List[str]
    disabled: bool
    
    def is_enabled(self) -> bool:
        """
        检查服务器是否启用
        
        Returns:
            bool: 如果服务器启用返回True，否则返回False
        """
        return not self.disabled


class MCPClientFactory:
    """
    MCP客户端工厂类
    
    负责创建和验证MCP客户端实例。使用工厂模式来封装客户端创建的复杂性。
    
    主要功能：
    - 验证MCP服务器配置
    - 创建MCP客户端实例
    - 处理客户端创建过程中的错误
    
    使用示例:
        config = MCPServerConfig(...)
        client = await MCPClientFactory.create_client(config)
    """
    
    @staticmethod
    def _validate_config(config: MCPServerConfig) -> bool:
        """验证MCP服务器配置
        
        Args:
            config: MCP服务器配置对象
            
        Returns:
            bool: 配置是否有效
            
        Raises:
            ConfigurationError: 配置无效时抛出异常
        """
        if not config:
            raise ConfigurationError("配置对象不能为空")
        
        if not config.name:
            raise ConfigurationError("服务器名称不能为空")
        
        if not config.command:
            raise ConfigurationError("服务器命令不能为空")
        
        if not isinstance(config.args, list):
            raise ConfigurationError("服务器参数必须是列表类型")
        
        if not isinstance(config.env, dict):
            raise ConfigurationError("环境变量必须是字典类型")
        
        if not isinstance(config.auto_approve, list):
            raise ConfigurationError("自动批准列表必须是列表类型")
        
        if not isinstance(config.disabled, bool):
            raise ConfigurationError("禁用状态必须是布尔类型")
        
        return True
    
    @staticmethod
    async def create_client(config: MCPServerConfig) -> MCPClient:
        """创建MCP客户端实例
        
        Args:
            config: MCP服务器配置对象
            
        Returns:
            MCPClient: 创建的MCP客户端实例
            
        Raises:
            ConfigurationError: 配置无效时抛出异常
            ConnectionError: 连接失败时抛出异常
        """
        # 验证配置
        MCPClientFactory._validate_config(config)
        
        # 检查服务器是否启用
        if not config.is_enabled():
            raise ConfigurationError(f"MCP服务器 '{config.name}' 已被禁用")
        
        try:
            # 导入必要的模块
            from mcp import stdio_client, StdioServerParameters
            
            # 设置环境变量（如果需要）
            if config.env:
                for key, value in config.env.items():
                    os.environ[key] = value
            
            # 创建stdio客户端连接函数
            def create_connection():
                return stdio_client(
                    StdioServerParameters(
                        command=config.command,
                        args=config.args,
                        env=config.env
                    )
                )
            
            # 创建MCPClient实例
            client = MCPClient(create_connection)
            
            return client
            
        except Exception as e:
            raise ConnectionError(f"创建MCP客户端失败: {str(e)}")
    
    @staticmethod
    def create_client_sync(config: MCPServerConfig) -> MCPClient:
        """同步方式创建MCP客户端实例
        
        Args:
            config: MCP服务器配置对象
            
        Returns:
            MCPClient: 创建的MCP客户端实例
        """
        # 验证配置
        MCPClientFactory._validate_config(config)
        
        # 检查服务器是否启用
        if not config.is_enabled():
            raise ConfigurationError(f"MCP服务器 '{config.name}' 已被禁用")
        
        try:
            # 导入必要的模块
            from mcp import stdio_client, StdioServerParameters
            
            # 设置环境变量（如果需要）
            if config.env:
                for key, value in config.env.items():
                    os.environ[key] = value
            
            # 创建stdio客户端连接函数
            def create_connection():
                return stdio_client(
                    StdioServerParameters(
                        command=config.command,
                        args=config.args,
                        env=config.env
                    )
                )
            
            # 创建MCPClient实例
            client = MCPClient(create_connection)
            
            return client
            
        except Exception as e:
            raise ConnectionError(f"创建MCP客户端失败: {str(e)}")


class MCPManager:
    """
    MCP管理器类
    
    核心管理类，负责加载、管理和提供对MCP服务器配置的访问。
    
    主要功能：
    - 从JSON文件加载MCP服务器配置
    - 提供配置查询和访问接口
    - 创建MCP客户端实例
    - 支持配置热重载
    
    配置文件格式:
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
    
    使用示例:
        # 创建管理器
        manager = MCPManager("./config/*.json")
        
        # 获取配置
        config = manager.get_server_config("server-name")
        
        # 创建客户端
        client = await manager.create_client("server-name")
    """
    
    def __init__(self, config_path: str = default_mcp_path):
        self.config_path = config_path
        self.servers: Dict[str, MCPServerConfig] = {}
        self.load_configs()
    
    def load_configs(self) -> None:
        """
        加载所有MCP配置文件
        
        扫描指定路径下的所有JSON文件，解析并加载MCP服务器配置。
        文件按名称排序以确保加载顺序的一致性。
        
        异常处理：
        - 文件不存在：记录警告，继续处理其他文件
        - JSON格式错误：记录错误，跳过该文件
        - 配置结构无效：记录错误，跳过无效配置项
        """
        config_files = glob.glob(self.config_path)
        
        if not config_files:
            print(f"警告: 在路径 {self.config_path} 下未找到MCP配置文件")
            return
        
        # 按文件名排序确保加载顺序的一致性
        config_files.sort()
        
        for config_file in config_files:
            try:
                print(f"加载MCP配置文件: {config_file}")
                self._load_single_config(config_file)
            except Exception as e:
                print(f"加载MCP配置文件 {config_file} 时出错: {str(e)}")
    
    def _load_single_config(self, config_file: str) -> None:
        """加载单个配置文件"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            if not config_data:
                print(f"警告: 配置文件 {config_file} 为空")
                return
            
            # 处理配置文件结构
            mcp_servers = config_data.get('mcpServers', {})
            
            # 如果没有mcpServers键，检查是否直接包含服务器配置
            if not mcp_servers and any(key for key in config_data.keys() if key != 'mcpServers'):
                # 处理格式错误的配置文件，将根级别的服务器配置移到mcpServers下
                mcp_servers = {k: v for k, v in config_data.items() if k != 'mcpServers'}
            
            for server_name, server_config in mcp_servers.items():
                try:
                    self._parse_server_config(server_name, server_config)
                except Exception as e:
                    print(f"解析服务器配置 {server_name} 时出错: {str(e)}")
                    continue
                    
        except FileNotFoundError:
            print(f"警告: 配置文件 {config_file} 不存在")
        except json.JSONDecodeError as e:
            print(f"错误: 配置文件 {config_file} JSON格式错误: {str(e)}")
        except Exception as e:
            print(f"错误: 读取配置文件 {config_file} 时发生未知错误: {str(e)}")
    
    def _parse_server_config(self, server_name: str, server_config: Dict[str, Any]) -> None:
        """解析单个服务器配置"""
        if not isinstance(server_config, dict):
            raise ConfigurationError(f"服务器 {server_name} 的配置必须是字典类型")
        
        # 验证必需字段
        required_fields = ['command']
        for field in required_fields:
            if field not in server_config:
                raise ConfigurationError(f"服务器 {server_name} 缺少必需字段: {field}")
        
        # 解析配置字段，提供默认值
        command = server_config.get('command', '')
        args = server_config.get('args', [])
        env = server_config.get('env', {})
        auto_approve = server_config.get('autoApprove', [])
        disabled = server_config.get('disabled', False)
        
        # 验证字段类型
        if not isinstance(args, list):
            raise ConfigurationError(f"服务器 {server_name} 的 args 字段必须是列表类型")
        if not isinstance(env, dict):
            raise ConfigurationError(f"服务器 {server_name} 的 env 字段必须是字典类型")
        if not isinstance(auto_approve, list):
            raise ConfigurationError(f"服务器 {server_name} 的 autoApprove 字段必须是列表类型")
        if not isinstance(disabled, bool):
            raise ConfigurationError(f"服务器 {server_name} 的 disabled 字段必须是布尔类型")
        
        # 创建配置对象
        config = MCPServerConfig(
            name=server_name,
            command=command,
            args=args,
            env=env,
            auto_approve=auto_approve,
            disabled=disabled
        )
        
        self.servers[server_name] = config
        print(f"成功加载服务器配置: {server_name} (启用: {config.is_enabled()})")
    
    def get_server_config(self, server_name: str) -> Optional[MCPServerConfig]:
        """
        根据服务器名称获取配置
        
        Args:
            server_name (str): 服务器名称
            
        Returns:
            Optional[MCPServerConfig]: 服务器配置对象，如果不存在则返回None
        """
        return self.servers.get(server_name)
    
    def get_all_servers(self) -> Dict[str, MCPServerConfig]:
        """
        返回所有服务器配置
        
        Returns:
            Dict[str, MCPServerConfig]: 包含所有服务器配置的字典副本
        """
        return self.servers.copy()
    
    def get_enabled_servers(self) -> Dict[str, MCPServerConfig]:
        """
        返回启用的服务器配置
        
        Returns:
            Dict[str, MCPServerConfig]: 包含所有启用服务器配置的字典
        """
        return {name: config for name, config in self.servers.items() if config.is_enabled()}
    
    def reload_configs(self) -> None:
        """
        重新加载配置文件
        
        清除当前配置并重新从文件加载。这对于配置文件更新后的热重载很有用。
        """
        self.servers.clear()
        self.load_configs()
    
    async def create_client(self, server_name: str) -> Optional[MCPClient]:
        """为指定服务器创建MCP客户端
        
        Args:
            server_name: 服务器名称
            
        Returns:
            Optional[MCPClient]: 创建的客户端实例，如果服务器不存在或被禁用则返回None
            
        Raises:
            ConfigurationError: 配置错误时抛出异常
            ConnectionError: 连接失败时抛出异常
        """
        config = self.get_server_config(server_name)
        if not config:
            print(f"警告: 服务器 '{server_name}' 不存在")
            return None
        
        if not config.is_enabled():
            print(f"警告: 服务器 '{server_name}' 已被禁用")
            return None
        
        try:
            return await MCPClientFactory.create_client(config)
        except Exception as e:
            print(f"创建客户端失败: {str(e)}")
            raise
    
    def create_client_sync(self, server_name: str) -> Optional[MCPClient]:
        """同步方式为指定服务器创建MCP客户端
        
        Args:
            server_name: 服务器名称
            
        Returns:
            Optional[MCPClient]: 创建的客户端实例，如果服务器不存在或被禁用则返回None
        """
        config = self.get_server_config(server_name)
        if not config:
            print(f"警告: 服务器 '{server_name}' 不存在")
            return None
        
        if not config.is_enabled():
            print(f"警告: 服务器 '{server_name}' 已被禁用")
            return None
        
        try:
            return MCPClientFactory.create_client_sync(config)
        except Exception as e:
            print(f"创建客户端失败: {str(e)}")
            raise

# 全局实例管理器
class MCPManagerRegistry:
    """
    MCPManager 注册表类
    
    管理多个MCPManager实例，为不同的配置路径提供单例模式支持。
    这确保了相同配置路径的管理器实例是唯一的，避免重复加载配置。
    
    使用示例:
        # 获取默认实例
        manager = MCPManagerRegistry.get_default_instance()
        
        # 获取特定路径的实例
        manager = MCPManagerRegistry.get_instance("./custom/*.json")
    """
    _instances: Dict[str, MCPManager] = {}
    
    @classmethod
    def get_instance(cls, config_path: str = default_mcp_path) -> MCPManager:
        """
        获取指定路径的 MCPManager 实例
        
        Args:
            config_path (str): 配置文件路径模式，默认为 './mcp/*.json'
            
        Returns:
            MCPManager: 对应路径的管理器实例
        """
        if config_path not in cls._instances:
            cls._instances[config_path] = MCPManager(config_path)
        return cls._instances[config_path]
    
    @classmethod
    def get_default_instance(cls) -> MCPManager:
        """
        获取默认的 MCPManager 实例
        
        Returns:
            MCPManager: 使用默认配置路径的管理器实例
        """
        return cls.get_instance(default_mcp_path)
    
    @classmethod
    def clear_instances(cls) -> None:
        """
        清除所有实例（主要用于测试）
        
        清除注册表中的所有实例，主要用于单元测试中的清理工作。
        """
        cls._instances.clear()


# 便捷函数
def get_mcp_manager(config_path: str = default_mcp_path) -> MCPManager:
    """
    获取 MCPManager 实例的便捷函数
    
    这是获取MCPManager实例的推荐方式，它通过注册表确保单例模式。
    
    Args:
        config_path (str): 配置文件路径模式，默认为 './mcp/*.json'
        
    Returns:
        MCPManager: 管理器实例
        
    示例:
        # 使用默认路径
        manager = get_mcp_manager()
        
        # 使用自定义路径
        manager = get_mcp_manager("./custom_config/*.json")
    """
    return MCPManagerRegistry.get_instance(config_path)


def get_default_mcp_manager() -> MCPManager:
    """
    获取默认 MCPManager 实例的便捷函数
    
    这是最常用的获取管理器实例的方式，使用默认的配置文件路径。
    
    Returns:
        MCPManager: 使用默认配置的管理器实例
        
    示例:
        manager = get_default_mcp_manager()
        servers = manager.get_all_servers()
    """
    return MCPManagerRegistry.get_default_instance()


def demo_basic_usage():
    """
    演示基本使用方法
    """
    print("=" * 60)
    print("MCP管理器基本使用演示")
    print("=" * 60)
    
    # 1. 创建管理器实例（推荐使用便捷函数）
    print("1. 创建MCP管理器实例")
    manager = get_default_mcp_manager()
    print("✓ 管理器创建成功")
    
    # 2. 获取服务器配置信息
    print("\n2. 获取服务器配置信息")
    all_servers = manager.get_all_servers()
    enabled_servers = manager.get_enabled_servers()
    
    print(f"总服务器数量: {len(all_servers)}")
    print(f"启用服务器数量: {len(enabled_servers)}")
    print(f"所有服务器: {list(all_servers.keys())}")
    print(f"启用的服务器: {list(enabled_servers.keys())}")
    
    # 3. 显示服务器详细信息
    print("\n3. 服务器详细信息")
    print("-" * 40)
    for server_name, config in all_servers.items():
        print(f"\n[{server_name}]")
        print(f"  命令: {config.command}")
        print(f"  参数: {config.args}")
        print(f"  环境变量: {config.env}")
        print(f"  自动批准: {config.auto_approve}")
        print(f"  状态: {'启用' if config.is_enabled() else '禁用'}")
    
    return manager, enabled_servers


def demo_client_creation(manager: MCPManager, enabled_servers: Dict[str, MCPServerConfig]):
    """
    演示客户端创建功能
    """
    print("\n" + "=" * 60)
    print("MCP客户端创建演示")
    print("=" * 60)
    
    if not enabled_servers:
        print("没有启用的服务器，跳过客户端创建演示")
        return
    
    print(f"尝试为 {len(enabled_servers)} 个启用的服务器创建客户端...")
    
    for server_name in enabled_servers.keys():
        print(f"\n正在为服务器 '{server_name}' 创建客户端...")
        try:
            # 使用同步方法进行演示（在实际应用中建议使用异步方法）
            client = manager.create_client_sync(server_name)
            if client:
                print(f"✓ 成功创建客户端，类型: {type(client).__name__}")
            else:
                print("✗ 客户端创建失败")
        except Exception as e:
            print(f"⚠ 创建客户端时出错: {str(e)}")
            print("  注意：这可能是因为实际的MCP服务器没有运行")


def demo_error_handling(manager: MCPManager):
    """
    演示错误处理功能
    """
    print("\n" + "=" * 60)
    print("错误处理演示")
    print("=" * 60)
    
    # 1. 测试获取不存在的服务器
    print("1. 测试获取不存在的服务器配置")
    config = manager.get_server_config("non-existent-server")
    if config is None:
        print("✓ 正确返回None表示服务器不存在")
    
    # 2. 测试为不存在的服务器创建客户端
    print("\n2. 测试为不存在的服务器创建客户端")
    try:
        client = manager.create_client_sync("non-existent-server")
        if client is None:
            print("✓ 正确返回None表示无法创建客户端")
    except Exception as e:
        print(f"✓ 正确抛出异常: {str(e)}")
    
    # 3. 测试配置验证
    print("\n3. 测试配置验证")
    try:
        MCPClientFactory._validate_config(None)
        print("✗ 应该抛出异常但没有")
    except ConfigurationError as e:
        print(f"✓ 正确验证无效配置: {str(e)}")


def demo_advanced_features(manager: MCPManager):
    """
    演示高级功能
    """
    print("\n" + "=" * 60)
    print("高级功能演示")
    print("=" * 60)
    
    # 1. 配置重新加载
    print("1. 配置重新加载")
    initial_count = len(manager.get_all_servers())
    print(f"重新加载前的服务器数量: {initial_count}")
    
    manager.reload_configs()
    final_count = len(manager.get_all_servers())
    print(f"重新加载后的服务器数量: {final_count}")
    print("✓ 配置重新加载完成")
    
    # 2. 注册表功能
    print("\n2. 注册表功能演示")
    manager1 = get_mcp_manager("./mcp/*.json")
    manager2 = get_mcp_manager("./mcp/*.json")
    
    if manager1 is manager2:
        print("✓ 相同路径返回相同实例（单例模式）")
    else:
        print("✗ 单例模式失效")
    
    # 3. 不同路径的管理器
    custom_manager = get_mcp_manager("./custom/*.json")
    if custom_manager is not manager1:
        print("✓ 不同路径返回不同实例")
    else:
        print("✗ 不同路径应该返回不同实例")


# 使用示例和演示
if __name__ == "__main__":
    """
    MCP管理器完整使用示例
    
    运行此脚本将演示MCP管理器的所有主要功能：
    - 基本配置加载和访问
    - 客户端创建
    - 错误处理
    - 高级功能
    
    使用方法:
        python nexus_utils/mcp_manager.py
    """
    try:
        # 基本使用演示
        manager, enabled_servers = demo_basic_usage()
        
        # 客户端创建演示
        demo_client_creation(manager, enabled_servers)
        
        # 错误处理演示
        demo_error_handling(manager)
        
        # 高级功能演示
        demo_advanced_features(manager)
        
        print("\n" + "=" * 60)
        print("演示完成！")
        print("=" * 60)
        print("\n使用提示:")
        print("1. 推荐使用 get_default_mcp_manager() 获取管理器实例")
        print("2. 在异步环境中使用 await manager.create_client()")
        print("3. 在同步环境中使用 manager.create_client_sync()")
        print("4. 定期调用 manager.reload_configs() 以获取最新配置")
        print("5. 查看 tests/mcp_manager_test.py 了解更多集成测试示例")
        
    except KeyboardInterrupt:
        print("\n演示被用户中断")
    except Exception as e:
        print(f"\n演示过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()