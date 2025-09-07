#!/usr/bin/env python3


import sys
import os
import boto3
import importlib
import json
import time
from typing import Dict, Any, Optional, Type, Union, List
from utils.config_loader import get_config
from strands.models import BedrockModel
from botocore.config import Config as BotocoreConfig
from utils import prompts_manager
from strands import Agent, tool
os.environ["BYPASS_TOOL_CONSENT"] = "true"


config = get_config()

boto_config = BotocoreConfig(
    retries={"max_attempts": config.get_bedrock_config().get("connect_config").get("retries").get("max_attempts"), "mode": "standard"},
    connect_timeout=config.get_bedrock_config().get("connect_config").get("connect_timeout"),
    read_timeout=config.get_bedrock_config().get("connect_config").get("read_timeout")
)

# Create a custom boto3 session
session = boto3.Session(
    region_name=config.get_aws_config().get("bedrock_region_name")
)


def get_bedrock_model(model_id="model_id",agent_name="template",env="production"):
    bedrock_model = BedrockModel(
        model_id=config.get_bedrock_config().get(model_id),
        max_tokens=prompts_manager.get_agent(agent_name).get_environment_config(env).max_tokens,
        temperature=prompts_manager.get_agent(agent_name).get_environment_config(env).temperature,
        top_p=prompts_manager.get_agent(agent_name).get_environment_config(env).top_p,
        streaming=prompts_manager.get_agent(agent_name).get_environment_config(env).streaming,
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
        from tools.system_tools.agent_build_workflow.tool_template_provider import get_builtin_tools
        
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
        from tools.system_tools.agent_build_workflow.tool_template_provider import list_all_tools
        
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


def get_tool_by_path(tool_path: str):
    """
    通过路径导入工具，支持以下格式：
    - template_tools/common/demo/weather_forecast
    - system_tools/project_manager/project_init
    - generated_tools/aws/security/aws_compliance_checker/check_aws_compliance
    - strands_tools/calculator
    """
    try:
        # 处理 strands_tools 路径
        if tool_path.startswith('strands_tools/'):
            tool_name = tool_path.split('/')[-1]
            try:
                tool_module = importlib.import_module(f'strands_tools.{tool_name}')
                # 对于strands_tools，直接返回模块本身
                # 因为strands_tools中的工具通常是以模块形式提供的
                return tool_module
            except ImportError as e:
                print(f"Failed to import strands_tools tool {tool_path}: {e}")
                return None
        
        # 处理 system_tools 路径
        if tool_path.startswith('system_tools/'):
            try:
                # 分离模块路径和函数名
                parts = tool_path.split('/')
                if len(parts) >= 3:
                    # 例如: system_tools/agent_build_workflow/project_manager/get_project_status
                    # 模块路径: tools.system_tools.agent_build_workflow.project_manager
                    # 函数名: get_project_status
                    module_path = f"tools.{'.'.join(parts[:-1])}"
                    function_name = parts[-1]
                    
                    # print(f"尝试导入system_tools模块: {module_path}, 函数: {function_name}")
                    
                    # 导入模块
                    module = importlib.import_module(module_path)
                    
                    # 获取函数
                    if hasattr(module, function_name):
                        return getattr(module, function_name)
                    else:
                        print(f"模块 {module_path} 中没有找到函数 {function_name}")
                        return None
                else:
                    print(f"system_tools路径格式不正确: {tool_path}")
                    return None
                    
            except Exception as e:
                print(f"Failed to import system_tools tool {tool_path}: {e}")
                return None
        if tool_path.startswith('generated_tools/'):
            try:
                # 分离模块路径和函数名
                parts = tool_path.split('/')
                if len(parts) >= 3:
                    # 例如: generated_tools/aws/security/aws_compliance_checker/check_aws_compliance
                    # 模块路径: tools.generated_tools.aws.security.aws_compliance_checker
                    # 函数名: get_project_status
                    module_path = f"tools.{'.'.join(parts[:-1])}"
                    function_name = parts[-1]
                    
                    # print(f"尝试导入generated_tools模块: {module_path}, 函数: {function_name}")
                    
                    # 导入模块
                    module = importlib.import_module(module_path)
                    
                    # 获取函数
                    if hasattr(module, function_name):
                        return getattr(module, function_name)
                    else:
                        print(f"模块 {module_path} 中没有找到函数 {function_name}")
                        return None
                else:
                    print(f"generated_tools路径格式不正确: {tool_path}")
                    return None
                    
            except Exception as e:
                print(f"Failed to import system_tools tool {tool_path}: {e}")
                return None
        
        # 处理 template_tools 路径
        if tool_path.startswith('template_tools/'):
            try:
                # 分离模块路径和函数名
                parts = tool_path.split('/')
                if len(parts) >= 3:
                    # 例如: template_tools/common/demo/weather_forecast
                    # 模块路径: tools.template_tools.common.demo
                    # 函数名: weather_forecast
                    module_path = f"tools.{'.'.join(parts[:-1])}"
                    function_name = parts[-1]
                    
                    print(f"尝试导入template_tools模块: {module_path}, 函数: {function_name}")
                    
                    # 导入模块
                    module = importlib.import_module(module_path)
                    
                    # 获取函数
                    if hasattr(module, function_name):
                        return getattr(module, function_name)
                    else:
                        print(f"模块 {module_path} 中没有找到函数 {function_name}")
                        return None
                else:
                    print(f"template_tools路径格式不正确: {tool_path}")
                    return None
                    
            except Exception as e:
                print(f"Failed to import template_tools tool {tool_path}: {e}")
                return None
        
        # 如果不是路径格式，返回None，让get_tool_by_name处理
        return None
        
    except Exception as e:
        print(f"Error getting tool by path '{tool_path}': {e}")
        return None


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
        from tools.system_tools.agent_build_workflow.tool_template_provider import search_tools_by_name
        
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
            # 首先尝试通过路径导入工具
            tool_obj = get_tool_by_path(tool_path)
            
            if tool_obj:
                tools.append(tool_obj)
                # print(f"✅ 成功通过路径导入工具: {tool_path}")
                continue
            
            # 如果路径导入失败，尝试通过工具名称导入
            tool_obj = get_tool_by_name(tool_path)
            
            if tool_obj:
                tools.append(tool_obj)
                # print(f"✅ 成功通过名称导入工具: {tool_path}")
            else:
                print(f"❌ 无法导入工具: {tool_path}")
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


def create_agent_from_prompt_template(agent_name: str, env="production", version="latest", model_id="default", enable_logging=False, state=None, session_manager=None, **agent_params) -> Optional[Agent]:
    """
    直接从提示词模板创建 agent，支持多级相对路径
    
    Args:
        agent_name: agent 名称或相对路径，支持以下格式：
                   - "requirements_analyzer" (agent名称)
                   - "system_agents_prompts/requirements_analyzer" (相对路径)
                   - "system_agents_prompts/agent_build_workflow/requirements_analyzer" (多级路径)
                   - "template_prompts/template" (模板路径)
                   - "generated_agents_prompts/price_agent/price_matcher" (生成的agent路径)
                   - "generated_agents_prompts/price_agent/price_matcher.yaml" (agent路径中.yaml默认会被移除)
        env: 环境配置 (development/production/testing)
        version: 版本号
        model_id: 模型ID
        enable_logging: 是否启用日志跟踪
        state: 状态数据,json类型，默认None
        **agent_params: 额外的agent参数
    
    Returns:
        Agent 实例或 None
    """
    import re
    if agent_name.endswith(".yaml"):
        agent_name = agent_name.replace(".yaml", "")
    if agent_name.startswith("prompts/"):
        agent_name = re.sub(r'^prompts/', '', agent_name)
    try:
        print(f"Creating agent '{agent_name}' from prompt template...")
        
        # 获取默认的prompt manager实例
        from utils.prompts_manager import get_default_prompt_manager
        manager = get_default_prompt_manager()
        
        # 尝试通过agent名称或相对路径获取agent模板
        agent_template = manager.get_agent(agent_name)
        
        if not agent_template:
            print(f"Agent template '{agent_name}' not found")
            return None
            
        latest_version = agent_template.get_version(version)
        
        if not latest_version:
            print(f"Version '{version}' not found for agent '{agent_name}'")
            return None
        
        print(f"Loaded prompt template for '{agent_name}', version: {version}")
        
        # 动态导入工具依赖
        tools_dependencies = []
        if hasattr(latest_version.metadata, 'tools_dependencies') and latest_version.metadata.tools_dependencies:
            # print(f"Importing tools dependencies: {latest_version.metadata.tools_dependencies}")
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
                    max_tokens=agent_template.get_environment_config(env).max_tokens,
                    temperature=agent_template.get_environment_config(env).temperature,
                    top_p=agent_template.get_environment_config(env).top_p,
                    streaming=agent_template.get_environment_config(env).streaming,
                    boto_session=session,
                    boto_client_config=boto_config
                )
            else:
                # 如果 supported_models 为空，使用配置文件中的默认模型
                default_model_id = config.get_bedrock_config().get("model_id")
                print(f"No supported models found, using default config model: {default_model_id}")
                model = BedrockModel(
                    model_id=default_model_id,
                    max_tokens=agent_template.get_environment_config(env).max_tokens,
                    temperature=agent_template.get_environment_config(env).temperature,
                    top_p=agent_template.get_environment_config(env).top_p,
                    streaming=agent_template.get_environment_config(env).streaming,
                    boto_session=session,
                    boto_client_config=boto_config
                )
        else:
            # 使用指定的模型ID
            model_config_key = model_id if model_id in config.get_bedrock_config() else "model_id"
            model = BedrockModel(
                model_id=config.get_bedrock_config().get(model_config_key),
                max_tokens=agent_template.get_environment_config(env).max_tokens,
                temperature=agent_template.get_environment_config(env).temperature,
                top_p=agent_template.get_environment_config(env).top_p,
                streaming=agent_template.get_environment_config(env).streaming,
                boto_session=session,
                boto_client_config=boto_config
            )
        
        # 创建 Agent，合并额外参数
        agent_kwargs = {
            'name': latest_version.agent_name,
            'model': model,
            'system_prompt': latest_version.system_prompt,
            'tools': tools_dependencies
        }
        
        # 合并用户提供的额外参数
        agent_kwargs.update(agent_params)
        
        # 如果启用日志跟踪，为Agent添加Strands官方Hooks
        if enable_logging:
            # 从agent_name中提取实际的Agent名称
            actual_agent_name = agent_name.split('/')[-1] if '/' in agent_name else agent_name
            
            # 创建Agent日志Hook
            from utils.strands_agent_logging_hook import create_agent_logging_hook
            logging_hook = create_agent_logging_hook(actual_agent_name)
            
            # 将Hook添加到Agent的hooks参数中
            if 'hooks' not in agent_kwargs:
                agent_kwargs['hooks'] = []
            agent_kwargs['hooks'].append(logging_hook)
        
        if session_manager:
            agent_kwargs['session_manager'] = session_manager

        # 创建Agent
        agent = Agent(**agent_kwargs)
        if state:
            for key, value in state.items():
                agent.state.set(key, value)
        
        print(f"✅Successfully created agent '{agent_name}' from prompt template")
        print(f"Agent has {len(tools_dependencies)} tools available")
        print("-"*100)
        
        return agent
        
    except Exception as e:
        print(f"Failed to create agent '{agent_name}' from prompt template: {e}")
        import traceback
        traceback.print_exc()
        return None


def list_available_agents() -> Dict[str, list]:
    """
    列出所有可用的 agent 模板，支持多级目录结构
    
    Returns:
        按类型分组的 agent 列表，包含相对路径
    """
    agents = {
        "system_agents": [],
        "template_agents": [],
        "generated_agents": []
    }
    
    # 获取prompt manager实例
    from utils.prompts_manager import get_default_prompt_manager
    manager = get_default_prompt_manager()
    
    # 获取所有agent路径映射
    path_mapping = manager.list_all_agent_paths()
    
    for agent_name, relative_path in path_mapping.items():
        # 跳过相对路径作为key的重复项
        if agent_name == relative_path:
            continue
            
        if relative_path.startswith("system_agents_prompts/"):
            agents["system_agents"].append({
                "name": agent_name,
                "path": relative_path
            })
        elif relative_path.startswith("template_prompts/"):
            agents["template_agents"].append({
                "name": agent_name,
                "path": relative_path
            })
        elif relative_path.startswith("generated_agents_prompts/"):
            agents["generated_agents"].append({
                "name": agent_name,
                "path": relative_path
            })
    
    return agents

def add_logging_hook_to_agent(agent: Agent, agent_name: str) -> Agent:
    """
    为Agent添加日志跟踪hook
    
    Args:
        agent: 原始Agent实例
        agent_name: Agent名称
    
    Returns:
        带有日志hook的Agent实例
    """
    try:
        from utils.enhanced_logging import get_enhanced_logger
        logger = get_enhanced_logger()
        
        # 保存原始的__call__方法
        original_call = agent.__call__
        
        def logged_call(*args, **kwargs):
            """带日志的Agent调用方法"""
            # 添加调试信息
            print(f"🔍 DEBUG: Hook被调用 - Agent: {agent_name}")
            
            # 获取输入数据
            input_data = None
            if args:
                input_data = str(args[0])
            elif kwargs:
                input_data = str(kwargs)
            
            # 记录Agent开始
            print(f"🚀 开始执行Agent: {agent_name}")
            logger.agent_start(agent_name, input_data)
            
            start_time = time.time()
            try:
                # 执行原始Agent
                result = original_call(*args, **kwargs)
                
                # 记录Agent结束
                result_str = str(result) if result else None
                duration = time.time() - start_time
                print(f"🎉 Agent执行完成: {agent_name}, 耗时: {duration:.2f}秒")
                logger.agent_end(agent_name, result_str, duration)
                
                return result
                
            except Exception as e:
                print(f"❌ Agent执行失败: {agent_name}, 错误: {e}")
                logger.error(agent_name, f"Agent执行失败: {e}")
                raise
        
        # 替换Agent的__call__方法
        agent.__call__ = logged_call
        
        return agent
        
    except Exception as e:
        print(f"Warning: Failed to add logging hook to agent '{agent_name}': {e}")
        return agent


def list_available_agent_paths() -> List[str]:
    """
    列出所有可用的 agent 相对路径
    
    Returns:
        所有agent的相对路径列表
    """
    from utils.prompts_manager import get_default_prompt_manager
    manager = get_default_prompt_manager()
    path_mapping = manager.list_all_agent_paths()
    
    # 返回所有相对路径（去重）
    paths = set()
    for agent_name, relative_path in path_mapping.items():
        paths.add(relative_path)
    
    return sorted(list(paths))