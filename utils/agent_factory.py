#!/usr/bin/env python3


import sys
import os
import boto3
import importlib
import json
from typing import Dict, Any, Optional, Type, Union, List
from utils.config_loader import get_config
from strands.models import BedrockModel
from botocore.config import Config as BotocoreConfig
from utils import prompts_manager
from strands import Agent, tool
os.environ["BYPASS_TOOL_CONSENT"] = "true"


config = get_config()

boto_config = BotocoreConfig(
    retries={"max_attempts": 3, "mode": "standard"},
    connect_timeout=10,
    read_timeout=300
)

# Create a custom boto3 session
session = boto3.Session(
    region_name=config.get_aws_config().get("bedrock_region_name")
)


def get_bedrock_model(model_id="model_id",agent_name="template",env="production"):
    bedrock_model = BedrockModel(
        model_id=config.get_bedrock_config().get(model_id),
        max_tokens=prompts_manager.get_agent(agent_name).get_environment_config(env).max_tokens,
        boto_session=session,
        boto_client_config=boto_config
    )
    return bedrock_model

def import_module_by_string(module_name: str):
    """根据字符串导入模块"""
    try:
        module = importlib.import_module(module_name)
        return module
    except ImportError as e:
        print(f"Failed to import {module_name}: {e}")
        return None


def import_class_by_string(module_name: str, class_name: str):
    """根据字符串导入特定的类"""
    try:
        module = importlib.import_module(module_name)
        cls = getattr(module, class_name)
        return cls
    except (ImportError, AttributeError) as e:
        print(f"Failed to import {class_name} from {module_name}: {e}")
        return None


def import_from_path(full_path: str):
    """
    从完整路径导入，格式: 'module.submodule.ClassName'
    """
    try:
        module_path, class_name = full_path.rsplit('.', 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except (ImportError, AttributeError, ValueError) as e:
        print(f"Failed to import from {full_path}: {e}")
        return None


def get_builtin_tools_mapping():
    """通过工具模板提供器获取内置工具映射"""
    try:
        from tools.system_tools.tool_template_provider import get_builtin_tools
        
        builtin_result = get_builtin_tools()
        builtin_data = json.loads(builtin_result)
        
        mapping = {}
        if "tools_by_category" in builtin_data:
            for category, tools in builtin_data["tools_by_category"].items():
                for tool in tools:
                    tool_name = tool["name"]
                    mapping[tool_name] = f"strands_tools.{tool_name}"
        
        return mapping
    except Exception as e:
        print(f"Error getting builtin tools mapping: {e}")
        return {}


def get_system_tools_mapping():
    """通过工具模板提供器获取系统工具映射"""
    try:
        from tools.system_tools.tool_template_provider import list_all_tools
        
        all_tools_result = list_all_tools()
        all_tools_data = json.loads(all_tools_result)
        
        mapping = {}
        
        # 处理系统工具
        if "system_tools" in all_tools_data:
            for tool_info in all_tools_data["system_tools"]:
                tool_name = tool_info["name"]
                file_path = tool_info.get("file_path", "")
                if file_path:
                    # 将文件路径转换为模块路径
                    module_path = file_path.replace("/", ".").replace(".py", "")
                    mapping[tool_name] = f"{module_path}.{tool_name}"
        
        # 处理模板工具
        if "template_tools" in all_tools_data:
            for tool_info in all_tools_data["template_tools"]:
                tool_name = tool_info["name"]
                file_path = tool_info.get("file_path", "")
                if file_path:
                    module_path = file_path.replace("/", ".").replace(".py", "")
                    mapping[tool_name] = f"{module_path}.{tool_name}"
        
        # 处理生成的工具
        if "generated_tools" in all_tools_data:
            for tool_info in all_tools_data["generated_tools"]:
                tool_name = tool_info["name"]
                file_path = tool_info.get("file_path", "")
                if file_path:
                    module_path = file_path.replace("/", ".").replace(".py", "")
                    mapping[tool_name] = f"{module_path}.{tool_name}"
        
        return mapping
    except Exception as e:
        print(f"Error getting system tools mapping: {e}")
        return {}


def get_tool_by_name(tool_name: str):
    """通过工具模板提供器动态获取工具"""
    try:
        # 获取内置工具映射
        builtin_mapping = get_builtin_tools_mapping()
        
        # 首先尝试从内置工具导入
        if tool_name in builtin_mapping:
            try:
                # 使用正确的导入方式: from strands_tools import tool_name
                # 这会导入一个模块，我们需要从模块中获取实际的工具函数
                tool_module = importlib.import_module(f'strands_tools.{tool_name}')
                
                # 尝试获取与工具名称相同的函数
                if hasattr(tool_module, tool_name):
                    return getattr(tool_module, tool_name)
                
                # 如果没有同名函数，查找被 @tool 装饰的函数
                for attr_name in dir(tool_module):
                    attr = getattr(tool_module, attr_name)
                    if hasattr(attr, '__name__') and not attr_name.startswith('_'):
                        # 检查是否是工具函数
                        if hasattr(attr, '__wrapped__') or str(type(attr)).find('Tool') != -1:
                            return attr
                
                # 如果都没找到，返回模块本身
                return tool_module
                
            except (ImportError, AttributeError) as e:
                print(f"Failed to import builtin tool {tool_name}: {e}")
        
        # 获取系统工具映射
        system_mapping = get_system_tools_mapping()
        
        # 然后尝试从系统工具导入
        if tool_name in system_mapping:
            try:
                return import_from_path(system_mapping[tool_name])
            except Exception as e:
                print(f"Failed to import system tool {tool_name}: {e}")
        
        # 最后尝试通过工具模板提供器搜索
        from tools.system_tools.tool_template_provider import search_tools_by_name
        
        search_result = search_tools_by_name(tool_name)
        search_data = json.loads(search_result)
        
        if search_data.get("total_matches", 0) > 0:
            matching_tools = search_data["matching_tools"]
            
            for tool_info in matching_tools:
                if tool_info["name"] == tool_name:
                    if tool_info["type"] == "builtin":
                        try:
                            # 使用正确的导入方式
                            tool_module = importlib.import_module(f'strands_tools.{tool_name}')
                            
                            # 尝试获取与工具名称相同的函数
                            if hasattr(tool_module, tool_name):
                                return getattr(tool_module, tool_name)
                            
                            # 查找被装饰的工具函数
                            for attr_name in dir(tool_module):
                                attr = getattr(tool_module, attr_name)
                                if hasattr(attr, '__name__') and not attr_name.startswith('_'):
                                    if hasattr(attr, '__wrapped__') or str(type(attr)).find('Tool') != -1:
                                        return attr
                            
                            return tool_module
                            
                        except (ImportError, AttributeError):
                            pass
                    else:
                        file_path = tool_info.get("file_path", "")
                        if file_path:
                            module_path = file_path.replace("/", ".").replace(".py", "")
                            try:
                                return import_from_path(f"{module_path}.{tool_name}")
                            except:
                                pass
        
        print(f"Warning: Tool '{tool_name}' not found")
        return None
        
    except Exception as e:
        print(f"Error getting tool '{tool_name}': {e}")
        return None


def import_tools_by_strings(tool_paths: list) -> list:
    """根据字符串列表动态导入多个工具"""
    tools = []
    
    for tool_path in tool_paths:
        if isinstance(tool_path, str):
            # 尝试通过工具模板提供器获取工具
            tool_obj = get_tool_by_name(tool_path)
            
            if tool_obj:
                tools.append(tool_obj)
            else:
                # 如果通过工具提供器找不到，尝试直接导入
                tool_obj = import_from_path(tool_path)
                if tool_obj:
                    tools.append(tool_obj)
                else:
                    print(f"Warning: Failed to import tool {tool_path}")
        else:
            # 如果已经是对象，直接添加
            tools.append(tool_path)
    
    return tools





def get_agent_class_by_type(agent_type: str) -> Optional[Type]:
    """根据 agent 类型字符串获取对应的 Agent 类"""
    agent_type_mapping = {
        "system": "agents.system_agents",
        "template": "agents.template_agents", 
        "generated": "agents.generated_agents"
    }
    
    if agent_type in agent_type_mapping:
        module_path = agent_type_mapping[agent_type]
        try:
            module = importlib.import_module(module_path)
            # 这里可以根据具体需求返回特定的类
            return module
        except ImportError as e:
            print(f"Failed to import agent type {agent_type}: {e}")
            return None
    return None


def create_agent_from_config(agent_config: Dict[str, Any]) -> Optional[Agent]:
    """根据配置字典创建 agent，支持动态导入"""
    agent_type = agent_config.get("type", "template")
    agent_name = agent_config.get("name", "template")
    model_id = agent_config.get("model_id", "default")
    env = agent_config.get("environment", "production")
    version = agent_config.get("version", "latest")
    
    # 如果配置中指定了自定义的 agent 类
    custom_agent_class = agent_config.get("agent_class")
    if custom_agent_class:
        AgentClass = import_from_path(custom_agent_class)
        if AgentClass:
            # 使用自定义的 Agent 类
            return AgentClass(**agent_config.get("init_params", {}))
    
    # 否则使用默认的 bedrock agent
    return get_bedrock_agent(model_id, agent_name, env, version)


def create_agent_from_prompt_template(agent_name: str, env="production", version="latest", model_id="default") -> Optional[Agent]:
    """
    直接从提示词模板创建 agent，无需手动编写 agent 文件
    
    Args:
        agent_name: agent 名称，对应 prompts/system_agents_prompts/{agent_name}.yaml
        env: 环境配置 (development/production/testing)
        version: 版本号
        model_id: 模型ID
    
    Returns:
        Agent 实例或 None
    """
    try:
        print(f"Creating agent '{agent_name}' from prompt template...")
        
        # 获取提示词模板
        agent_template = prompts_manager.get_agent(agent_name)
        latest_version = agent_template.get_version(version)
        
        print(f"Loaded prompt template for '{agent_name}', version: {version}")
        
        # 不再处理 lib_dependencies
        
        # 动态导入工具依赖
        tools_dependencies = []
        if hasattr(latest_version.metadata, 'tools_dependencies') and latest_version.metadata.tools_dependencies:
            print(f"Importing tools dependencies: {latest_version.metadata.tools_dependencies}")
            tools_dependencies = import_tools_by_strings(latest_version.metadata.tools_dependencies)
        
        print(f"Successfully imported {len(tools_dependencies)} tools")
        
        # 获取模型配置 - 默认选择 supported_models 中的第一个
        if model_id == "default":
            if hasattr(latest_version.metadata, 'supported_models') and latest_version.metadata.supported_models:
                # 从 supported_models 中选择第一个模型
                supported_model = latest_version.metadata.supported_models[0]
                print(f"Using supported model: {supported_model}")
                # 创建模型时使用支持的模型ID
                model = BedrockModel(
                    model_id=supported_model,
                    max_tokens=prompts_manager.get_agent(agent_name).get_environment_config(env).max_tokens,
                    boto_session=session,
                    boto_client_config=boto_config
                )
            else:
                # 如果 supported_models 为空，使用配置文件中的默认模型
                default_model_id = config.get_bedrock_config().get("model_id")
                print(f"No supported models found, using default config model: {default_model_id}")
                model = BedrockModel(
                    model_id=default_model_id,
                    max_tokens=prompts_manager.get_agent(agent_name).get_environment_config(env).max_tokens,
                    boto_session=session,
                    boto_client_config=boto_config
                )
        else:
            # 使用指定的模型ID
            model = get_bedrock_model(model_id=model_id, agent_name=agent_name, env=env)
        
        # 创建 Agent
        agent = Agent(
            name=agent_name,
            model=model,
            system_prompt=latest_version.system_prompt,
            tools=tools_dependencies
        )
        
        print(f"Successfully created agent '{agent_name}' from prompt template")
        print(f"Agent has {len(tools_dependencies)} tools available")
        
        return agent
        
    except Exception as e:
        print(f"Failed to create agent '{agent_name}' from prompt template: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_bedrock_agent(model_id="default",agent_name="template",env="production",version="latest"):
    """保持向后兼容的原有方法"""
    return create_agent_from_prompt_template(agent_name, env, version, model_id)


def create_system_agent(agent_name: str, **kwargs) -> Optional[Agent]:
    """
    创建系统 agent 的便捷方法
    
    Args:
        agent_name: 系统 agent 名称 (如 'system_architect', 'orchestrator', 等)
        **kwargs: 其他参数 (env, version, model_id)
    
    Returns:
        Agent 实例或 None
    """
    return create_agent_from_prompt_template(agent_name, **kwargs)


def list_available_agents() -> Dict[str, list]:
    """
    列出所有可用的 agent 模板
    
    Returns:
        按类型分组的 agent 列表
    """
    import os
    import glob
    
    agents = {
        "system_agents": [],
        "template_agents": [],
        "generated_agents": []
    }
    
    # 扫描系统 agent 提示词
    system_prompts_dir = "prompts/system_agents_prompts"
    if os.path.exists(system_prompts_dir):
        for yaml_file in glob.glob(f"{system_prompts_dir}/*.yaml"):
            agent_name = os.path.basename(yaml_file).replace('.yaml', '')
            agents["system_agents"].append(agent_name)
    
    # 扫描模板 agent 提示词
    template_prompts_dir = "prompts/template_prompts"
    if os.path.exists(template_prompts_dir):
        for yaml_file in glob.glob(f"{template_prompts_dir}/*.yaml"):
            agent_name = os.path.basename(yaml_file).replace('.yaml', '')
            agents["template_agents"].append(agent_name)
    
    # 扫描生成的 agent 提示词
    generated_prompts_dir = "prompts/generated_agents_prompts"
    if os.path.exists(generated_prompts_dir):
        for yaml_file in glob.glob(f"{generated_prompts_dir}/*.yaml"):
            agent_name = os.path.basename(yaml_file).replace('.yaml', '')
            agents["generated_agents"].append(agent_name)
    
    return agents