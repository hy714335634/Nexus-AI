#!/usr/bin/env python3
"""
项目验证工具

用于检查和生成最后的项目配置参数，包括：
- 关键脚本位置、脚本语法验证、脚本依赖包、执行参数
- 提示词文件位置、依赖工具列表、工具数量
- 生成的工具脚本列表、语法验证、工具总数
"""

import os
import json
import yaml
import ast
import importlib.util
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from strands import Agent, tool

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ScriptInfo:
    """脚本信息数据结构"""
    def __init__(self):
        self.script_path: str = ""
        self.syntax_valid: bool = False
        self.dependencies: List[str] = []
        self.execution_params: List[Dict[str, str]] = []
        self.argparse_params: List[Dict[str, str]] = []
        self.error_message: str = ""


class PromptInfo:
    """提示词信息数据结构"""
    def __init__(self):
        self.prompt_path: str = ""
        self.tool_dependencies: List[str] = []
        self.tool_count: int = 0
        self.valid: bool = False
        self.error_message: str = ""
        self.metadata: Dict[str, Any] = {}
        self.agent_info: Dict[str, Any] = {}


class ToolInfo:
    """工具信息数据结构"""
    def __init__(self):
        self.tool_path: str = ""
        self.syntax_valid: bool = False
        self.error_message: str = ""


class ProjectConfig:
    """项目配置数据结构"""
    def __init__(self):
        self.project_name: str = ""
        self.agent_scripts: List[ScriptInfo] = []
        self.prompt_files: List[PromptInfo] = []
        self.generated_tools: List[ToolInfo] = []
        self.total_tools: int = 0
        self.validation_timestamp: str = ""
        self.overall_status: str = ""


def validate_python_syntax(file_path: str) -> Tuple[bool, str]:
    """验证Python文件语法"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
        return True, ""
    except SyntaxError as e:
        return False, f"语法错误: {e}"
    except Exception as e:
        return False, f"文件读取错误: {e}"


def extract_dependencies(file_path: str) -> List[str]:
    """提取Python文件的依赖包"""
    dependencies = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    dependencies.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    dependencies.append(node.module)
    except Exception as e:
        logger.warning(f"提取依赖失败 {file_path}: {e}")
    
    return dependencies


def extract_execution_params(file_path: str) -> List[Dict[str, str]]:
    """提取脚本的执行参数"""
    params = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # 查找@tool装饰的函数
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name) and decorator.id == 'tool':
                        # 提取函数参数
                        for arg in node.args.args:
                            if arg.arg != 'self':
                                param_info = {
                                    "name": arg.arg,
                                    "type": "str",  # 默认类型
                                    "description": "参数描述"
                                }
                                # 尝试获取类型注解
                                if arg.annotation:
                                    if isinstance(arg.annotation, ast.Name):
                                        param_info["type"] = arg.annotation.id
                                params.append(param_info)
    except Exception as e:
        logger.warning(f"提取执行参数失败 {file_path}: {e}")
    
    return params


def extract_argparse_params(file_path: str) -> List[Dict[str, str]]:
    """提取argparse.ArgumentParser参数"""
    params = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # 查找parser.add_argument()调用
                if (isinstance(node.func, ast.Attribute) and 
                    node.func.attr == 'add_argument'):
                    
                    # 提取参数信息
                    param_info = {
                        "name": "",
                        "type": "str",
                        "description": "",
                        "required": False,
                        "default": None,
                        "action": None
                    }
                    
                    # 提取位置参数（通常是参数名）
                    for i, arg in enumerate(node.args):
                        if i == 0 and isinstance(arg, ast.Constant):
                            param_info["name"] = arg.value
                        elif i == 1 and isinstance(arg, ast.Constant):
                            param_info["description"] = arg.value
                    
                    # 提取关键字参数
                    for keyword in node.keywords:
                        if keyword.arg == "help" and isinstance(keyword.value, ast.Constant):
                            param_info["description"] = keyword.value.value
                        elif keyword.arg == "type" and isinstance(keyword.value, ast.Name):
                            param_info["type"] = keyword.value.id
                        elif keyword.arg == "required" and isinstance(keyword.value, ast.Constant):
                            param_info["required"] = keyword.value.value
                        elif keyword.arg == "default" and isinstance(keyword.value, ast.Constant):
                            param_info["default"] = keyword.value.value
                        elif keyword.arg == "action" and isinstance(keyword.value, ast.Constant):
                            param_info["action"] = keyword.value.value
                    
                    if param_info["name"]:  # 只有当有参数名时才添加
                        params.append(param_info)
    except Exception as e:
        logger.warning(f"提取argparse参数失败 {file_path}: {e}")
    
    return params


def analyze_prompt_file(prompt_path: str) -> PromptInfo:
    """分析提示词文件"""
    prompt_info = PromptInfo()
    prompt_info.prompt_path = prompt_path
    
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析YAML内容
        data = yaml.safe_load(content)
        
        if isinstance(data, dict) and 'agent' in data:
            agent_data = data['agent']
            # 过滤掉system_prompt、versions和environments字段
            filtered_agent_data = {}
            for key, value in agent_data.items():
                if key in ['versions', 'environments']:
                    # 跳过versions和environments字段
                    continue
                elif key == 'system_prompt':
                    # 跳过system_prompt字段
                    continue
                else:
                    filtered_agent_data[key] = value
            prompt_info.agent_info = filtered_agent_data
            
            # 提取工具依赖 - 从versions/latest/metadata/tools_dependencies中获取
            if 'versions' in agent_data:
                versions = agent_data['versions']
                if isinstance(versions, list):
                    # 查找latest版本
                    latest_version = None
                    for version in versions:
                        if isinstance(version, dict) and version.get('version') == 'latest':
                            latest_version = version
                            break
                    
                    if latest_version and 'metadata' in latest_version:
                        metadata = latest_version['metadata']
                        if 'tools_dependencies' in metadata:
                            tools_deps = metadata['tools_dependencies']
                            if isinstance(tools_deps, list):
                                prompt_info.tool_dependencies = tools_deps
                                prompt_info.tool_count = len(tools_deps)
                            elif isinstance(tools_deps, str):
                                prompt_info.tool_dependencies = [tools_deps]
                                prompt_info.tool_count = 1
                        
                        # 保存完整的metadata信息
                        prompt_info.metadata = metadata
            
            # 兼容性：如果versions中没有找到，尝试从agent根级别查找
            if not prompt_info.tool_dependencies:
                if 'tools' in agent_data:
                    tools = agent_data['tools']
                    if isinstance(tools, list):
                        prompt_info.tool_dependencies = tools
                        prompt_info.tool_count = len(tools)
                    elif isinstance(tools, str):
                        prompt_info.tool_dependencies = [tools]
                        prompt_info.tool_count = 1
        
        prompt_info.valid = True
    except Exception as e:
        prompt_info.valid = False
        prompt_info.error_message = f"解析提示词文件失败: {e}"
        logger.error(f"分析提示词文件失败 {prompt_path}: {e}")
    
    return prompt_info


def analyze_tool_file(tool_path: str) -> ToolInfo:
    """分析工具文件"""
    tool_info = ToolInfo()
    tool_info.tool_path = tool_path
    
    try:
        # 验证语法
        syntax_valid, error_msg = validate_python_syntax(tool_path)
        tool_info.syntax_valid = syntax_valid
        if not syntax_valid:
            tool_info.error_message = error_msg
        
    except Exception as e:
        tool_info.syntax_valid = False
        tool_info.error_message = f"分析工具文件失败: {e}"
        logger.error(f"分析工具文件失败 {tool_path}: {e}")
    
    return tool_info


@tool
def project_verify(project_name: str) -> str:
    """
    验证项目配置并生成配置参数
    
    Args:
        project_name: 项目名称
        
    Returns:
        str: JSON格式的项目配置信息
    """
    try:
        config = ProjectConfig()
        config.project_name = project_name
        config.validation_timestamp = datetime.now(timezone.utc).isoformat()
        
        # 项目根目录
        project_root = Path("/Users/qangz/Downloads/99.Project/Nexus-AI")
        project_dir = project_root / "projects" / project_name
        
        if not project_dir.exists():
            return json.dumps({
                "error": f"项目目录不存在: {project_dir}",
                "project_name": project_name
            }, ensure_ascii=False, indent=2)
        
        # 1. 分析Agent脚本
        # 首先检查项目对应的generated_agents目录
        generated_agents_dir = project_root / "agents" / "generated_agents" / project_name
        if generated_agents_dir.exists():
            for py_file in generated_agents_dir.glob("*.py"):
                if py_file.name != "__init__.py":
                                script_info = ScriptInfo()
                                script_info.script_path = str(py_file.relative_to(project_root))
                                
                                # 验证语法
                                syntax_valid, error_msg = validate_python_syntax(str(py_file))
                                script_info.syntax_valid = syntax_valid
                                if not syntax_valid:
                                    script_info.error_message = error_msg
                                
                                # 提取依赖
                                script_info.dependencies = extract_dependencies(str(py_file))
                                
                                # 提取执行参数
                                script_info.execution_params = extract_execution_params(str(py_file))
                                
                                # 提取argparse参数
                                script_info.argparse_params = extract_argparse_params(str(py_file))
                                
                                config.agent_scripts.append(script_info)
        
        # 也检查agents目录下的子目录（兼容性）
        agents_dir = project_dir / "agents"
        if agents_dir.exists():
            for agent_subdir in agents_dir.iterdir():
                if agent_subdir.is_dir():
                    # 查找生成的Agent Python文件
                    generated_agents_dir = project_root / "agents" / "generated_agents" / agent_subdir.name
                    if generated_agents_dir.exists():
                        for py_file in generated_agents_dir.glob("*.py"):
                            if py_file.name != "__init__.py":
                                # 避免重复添加
                                script_path = str(py_file.relative_to(project_root))
                                if not any(script.script_path == script_path for script in config.agent_scripts):
                                    script_info = ScriptInfo()
                                    script_info.script_path = script_path
                                    
                                    # 验证语法
                                    syntax_valid, error_msg = validate_python_syntax(str(py_file))
                                    script_info.syntax_valid = syntax_valid
                                    if not syntax_valid:
                                        script_info.error_message = error_msg
                                    
                                    # 提取依赖
                                    script_info.dependencies = extract_dependencies(str(py_file))
                                    
                                    # 提取执行参数
                                    script_info.execution_params = extract_execution_params(str(py_file))
                                    
                                    # 提取argparse参数
                                    script_info.argparse_params = extract_argparse_params(str(py_file))
                                    
                                    config.agent_scripts.append(script_info)
        
        # 2. 分析提示词文件
        prompts_dir = project_root / "prompts" / "generated_agents_prompts" / project_name
        if prompts_dir.exists():
            for yaml_file in prompts_dir.glob("*.yaml"):
                prompt_info = analyze_prompt_file(str(yaml_file))
                # 设置从prompts/开始的相对路径
                prompt_info.prompt_path = str(yaml_file.relative_to(project_root / "prompts"))
                config.prompt_files.append(prompt_info)
        
        # 3. 分析生成的工具
        tools_dir = project_root / "tools" / "generated_tools" / project_name
        if tools_dir.exists():
            for py_file in tools_dir.glob("*.py"):
                if py_file.name != "__init__.py":
                    tool_info = analyze_tool_file(str(py_file))
                    # 设置从tools/开始的相对路径
                    tool_info.tool_path = str(py_file.relative_to(project_root / "tools"))
                    config.generated_tools.append(tool_info)
        
        # total_tools应该是所有prompt_files中tools_dependencies的总数
        total_tools_count = 0
        for prompt in config.prompt_files:
            total_tools_count += prompt.tool_count
        config.total_tools = total_tools_count
        
        # 4. 计算整体状态
        all_scripts_valid = all(script.syntax_valid for script in config.agent_scripts)
        all_tools_valid = all(tool.syntax_valid for tool in config.generated_tools)
        all_prompts_valid = all(prompt.valid for prompt in config.prompt_files)
        
        if all_scripts_valid and all_tools_valid and all_prompts_valid:
            config.overall_status = "success"
        else:
            config.overall_status = "warning"
        
        # 5. 输出配置到项目文件夹
        output_config = {
            "project_name": config.project_name,
            "validation_timestamp": config.validation_timestamp,
            "overall_status": config.overall_status,
            "agent_scripts": [
                {
                    "script_path": script.script_path,
                    "syntax_valid": script.syntax_valid,
                    "dependencies": script.dependencies,
                    "execution_params": script.execution_params,
                    "argparse_params": script.argparse_params,
                    "error_message": script.error_message
                }
                for script in config.agent_scripts
            ],
            "prompt_files": [
                {
                    "prompt_path": prompt.prompt_path,
                    "tool_count": prompt.tool_count,
                    "valid": prompt.valid,
                    "error_message": prompt.error_message,
                    "metadata": prompt.metadata,
                    "agent_info": prompt.agent_info
                }
                for prompt in config.prompt_files
            ],
            "generated_tools": [
                {
                    "tool_path": tool.tool_path,
                    "syntax_valid": tool.syntax_valid,
                    "error_message": tool.error_message
                }
                for tool in config.generated_tools
            ],
            "total_tools": config.total_tools,
            "summary": {
                "agent_scripts_count": len(config.agent_scripts),
                "prompt_files_count": len(config.prompt_files),
                "generated_tool_files_count": len(config.generated_tools),
                "all_scripts_valid": all_scripts_valid,
                "all_tools_valid": all_tools_valid,
                "all_prompts_valid": all_prompts_valid
            }
        }
        
        # 保存配置到项目文件夹
        config_file = project_dir / "project_config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(output_config, f, ensure_ascii=False, indent=2)
        
        logger.info(f"项目验证完成，配置已保存到: {config_file}")
        
        return json.dumps(output_config, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "error": f"项目验证失败: {str(e)}",
            "project_name": project_name
        }
        logger.error(f"项目验证失败: {e}")
        return json.dumps(error_result, ensure_ascii=False, indent=2)