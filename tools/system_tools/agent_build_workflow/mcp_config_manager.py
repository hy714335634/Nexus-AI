#!/usr/bin/env python3
# mcp_config_manager/get_all_mcp_servers - 获取所有MCP服务器配置信息，包含命令、参数、环境变量和启用状态
# mcp_config_manager/get_enabled_mcp_servers - 获取所有启用的MCP服务器配置信息
# mcp_config_manager/get_mcp_server_by_name - 根据服务器名称获取特定MCP服务器配置信息
# mcp_config_manager/search_mcp_servers_by_command - 根据命令搜索MCP服务器，支持模糊匹配
# mcp_config_manager/search_mcp_servers_by_args - 根据参数关键词搜索MCP服务器
# mcp_config_manager/get_mcp_servers_with_auto_approve - 获取配置了自动批准工具的MCP服务器
# mcp_config_manager/get_mcp_servers_with_env_vars - 获取配置了环境变量的MCP服务器
# mcp_config_manager/get_mcp_server_statistics - 获取MCP服务器配置统计信息，包含总数、启用数、命令分布等
# mcp_config_manager/reload_mcp_configs - 重新加载MCP配置文件
# mcp_config_manager/validate_mcp_server_config - 验证指定MCP服务器的配置是否有效
"""
MCP配置管理工具

提供MCP服务器配置的查询、筛选和管理功能
"""

import sys
import os
import json
from typing import Dict, List, Any, Optional

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from strands import tool
from utils.mcp_manager import get_default_mcp_manager, MCPManagerError


@tool
def get_all_mcp_servers() -> str:
    """
    获取所有MCP服务器配置信息
    
    Returns:
        str: JSON格式的所有MCP服务器配置信息
    """
    try:
        manager = get_default_mcp_manager()
        servers = manager.get_all_servers()
        
        # 格式化输出
        result = []
        for server_name, config in servers.items():
            result.append({
                "name": server_name,
                "command": config.command,
                "args": config.args,
                "env": config.env,
                "auto_approve": config.auto_approve,
                "disabled": config.disabled,
                "enabled": config.is_enabled()
            })
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"获取MCP服务器配置时出现错误: {str(e)}"


@tool
def get_enabled_mcp_servers() -> str:
    """
    获取所有启用的MCP服务器配置信息
    
    Returns:
        str: JSON格式的启用的MCP服务器配置信息
    """
    try:
        manager = get_default_mcp_manager()
        servers = manager.get_enabled_servers()
        
        # 格式化输出
        result = []
        for server_name, config in servers.items():
            result.append({
                "name": server_name,
                "command": config.command,
                "args": config.args,
                "env": config.env,
                "auto_approve": config.auto_approve,
                "disabled": config.disabled,
                "enabled": config.is_enabled()
            })
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"获取启用的MCP服务器配置时出现错误: {str(e)}"


@tool
def get_mcp_server_by_name(server_name: str) -> str:
    """
    根据服务器名称获取特定MCP服务器配置信息
    
    Args:
        server_name (str): MCP服务器名称
        
    Returns:
        str: JSON格式的MCP服务器配置信息
    """
    try:
        manager = get_default_mcp_manager()
        config = manager.get_server_config(server_name)
        
        if not config:
            return f"错误：未找到名为 '{server_name}' 的MCP服务器"
        
        result = {
            "name": server_name,
            "command": config.command,
            "args": config.args,
            "env": config.env,
            "auto_approve": config.auto_approve,
            "disabled": config.disabled,
            "enabled": config.is_enabled()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"获取MCP服务器配置时出现错误: {str(e)}"


@tool
def search_mcp_servers_by_command(command: str) -> str:
    """
    根据命令搜索MCP服务器
    
    Args:
        command (str): 要搜索的命令
        
    Returns:
        str: JSON格式的匹配的MCP服务器配置信息
    """
    try:
        manager = get_default_mcp_manager()
        servers = manager.get_all_servers()
        
        # 搜索匹配的服务器
        matched_servers = []
        for server_name, config in servers.items():
            if command.lower() in config.command.lower():
                matched_servers.append({
                    "name": server_name,
                    "command": config.command,
                    "args": config.args,
                    "env": config.env,
                    "auto_approve": config.auto_approve,
                    "disabled": config.disabled,
                    "enabled": config.is_enabled()
                })
        
        return json.dumps(matched_servers, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"搜索MCP服务器时出现错误: {str(e)}"


@tool
def search_mcp_servers_by_args(keyword: str) -> str:
    """
    根据参数关键词搜索MCP服务器
    
    Args:
        keyword (str): 要搜索的参数关键词
        
    Returns:
        str: JSON格式的匹配的MCP服务器配置信息
    """
    try:
        manager = get_default_mcp_manager()
        servers = manager.get_all_servers()
        
        # 搜索匹配的服务器
        matched_servers = []
        for server_name, config in servers.items():
            # 检查参数列表中是否包含关键词
            args_str = " ".join(config.args).lower()
            if keyword.lower() in args_str:
                matched_servers.append({
                    "name": server_name,
                    "command": config.command,
                    "args": config.args,
                    "env": config.env,
                    "auto_approve": config.auto_approve,
                    "disabled": config.disabled,
                    "enabled": config.is_enabled()
                })
        
        return json.dumps(matched_servers, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"搜索MCP服务器时出现错误: {str(e)}"


@tool
def get_mcp_servers_with_auto_approve() -> str:
    """
    获取配置了自动批准工具的MCP服务器
    
    Returns:
        str: JSON格式的配置了自动批准的MCP服务器信息
    """
    try:
        manager = get_default_mcp_manager()
        servers = manager.get_all_servers()
        
        # 筛选有自动批准配置的服务器
        servers_with_auto_approve = []
        for server_name, config in servers.items():
            if config.auto_approve:  # 如果auto_approve列表不为空
                servers_with_auto_approve.append({
                    "name": server_name,
                    "command": config.command,
                    "args": config.args,
                    "env": config.env,
                    "auto_approve": config.auto_approve,
                    "disabled": config.disabled,
                    "enabled": config.is_enabled()
                })
        
        return json.dumps(servers_with_auto_approve, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"获取自动批准配置时出现错误: {str(e)}"


@tool
def get_mcp_servers_with_env_vars() -> str:
    """
    获取配置了环境变量的MCP服务器
    
    Returns:
        str: JSON格式的配置了环境变量的MCP服务器信息
    """
    try:
        manager = get_default_mcp_manager()
        servers = manager.get_all_servers()
        
        # 筛选有环境变量配置的服务器
        servers_with_env = []
        for server_name, config in servers.items():
            if config.env:  # 如果env字典不为空
                servers_with_env.append({
                    "name": server_name,
                    "command": config.command,
                    "args": config.args,
                    "env": config.env,
                    "auto_approve": config.auto_approve,
                    "disabled": config.disabled,
                    "enabled": config.is_enabled()
                })
        
        return json.dumps(servers_with_env, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"获取环境变量配置时出现错误: {str(e)}"


@tool
def get_mcp_server_statistics() -> str:
    """
    获取MCP服务器配置统计信息
    
    Returns:
        str: JSON格式的MCP服务器统计信息
    """
    try:
        manager = get_default_mcp_manager()
        all_servers = manager.get_all_servers()
        enabled_servers = manager.get_enabled_servers()
        
        # 统计信息
        total_count = len(all_servers)
        enabled_count = len(enabled_servers)
        disabled_count = total_count - enabled_count
        
        # 统计命令类型
        command_stats = {}
        for config in all_servers.values():
            command = config.command
            command_stats[command] = command_stats.get(command, 0) + 1
        
        # 统计有环境变量的服务器
        env_count = sum(1 for config in all_servers.values() if config.env)
        
        # 统计有自动批准的服务器
        auto_approve_count = sum(1 for config in all_servers.values() if config.auto_approve)
        
        result = {
            "total_servers": total_count,
            "enabled_servers": enabled_count,
            "disabled_servers": disabled_count,
            "servers_with_env_vars": env_count,
            "servers_with_auto_approve": auto_approve_count,
            "command_distribution": command_stats,
            "server_names": list(all_servers.keys()),
            "enabled_server_names": list(enabled_servers.keys())
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"获取MCP服务器统计信息时出现错误: {str(e)}"


@tool
def reload_mcp_configs() -> str:
    """
    重新加载MCP配置文件
    
    Returns:
        str: 重新加载结果信息
    """
    try:
        manager = get_default_mcp_manager()
        old_count = len(manager.get_all_servers())
        
        manager.reload_configs()
        
        new_count = len(manager.get_all_servers())
        
        result = {
            "status": "success",
            "message": "MCP配置已重新加载",
            "old_server_count": old_count,
            "new_server_count": new_count
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"重新加载MCP配置时出现错误: {str(e)}"


@tool
def validate_mcp_server_config(server_name: str) -> str:
    """
    验证指定MCP服务器的配置是否有效
    
    Args:
        server_name (str): MCP服务器名称
        
    Returns:
        str: JSON格式的验证结果
    """
    try:
        manager = get_default_mcp_manager()
        config = manager.get_server_config(server_name)
        
        if not config:
            return json.dumps({
                "valid": False,
                "error": f"服务器 '{server_name}' 不存在"
            }, ensure_ascii=False, indent=2)
        
        # 基本验证
        validation_results = {
            "valid": True,
            "server_name": server_name,
            "checks": {
                "has_command": bool(config.command),
                "has_args": isinstance(config.args, list),
                "has_env": isinstance(config.env, dict),
                "has_auto_approve": isinstance(config.auto_approve, list),
                "is_enabled": config.is_enabled()
            }
        }
        
        # 检查是否所有基本检查都通过
        all_checks_passed = all(validation_results["checks"].values())
        validation_results["valid"] = all_checks_passed
        
        if not all_checks_passed:
            validation_results["error"] = "配置验证失败，请检查配置格式"
        
        return json.dumps(validation_results, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"验证MCP服务器配置时出现错误: {str(e)}"


# 主函数，用于直接调用测试
def main():
    """主函数，用于测试MCP配置管理工具"""
    print("=== MCP配置管理工具测试 ===")
    
    print("\n1. 获取所有MCP服务器:")
    print(get_all_mcp_servers())
    
    print("\n2. 获取启用的MCP服务器:")
    print(get_enabled_mcp_servers())
    
    print("\n3. 获取MCP服务器统计信息:")
    print(get_mcp_server_statistics())
    
    print("\n4. 根据命令搜索MCP服务器 (uvx):")
    print(search_mcp_servers_by_command("uvx"))
    
    print("\n5. 获取配置了自动批准的服务器:")
    print(get_mcp_servers_with_auto_approve())
    
    print("\n6. 获取配置了环境变量的服务器:")
    print(get_mcp_servers_with_env_vars())


if __name__ == "__main__":
    main()