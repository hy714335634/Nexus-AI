#!/usr/bin/env python3
# tool_template_provider/list_all_tools - 列出所有可用的工具，包括模板工具、生成工具和内置工具，按类型分类
# tool_template_provider/get_builtin_tools - 获取所有内置工具信息，按分类组织，包含安装说明
# tool_template_provider/get_template_tools - 获取所有模板工具信息，解析Python文件中的@tool装饰器函数
# tool_template_provider/get_generated_tools - 获取所有生成工具信息，扫描generated_tools目录
# tool_template_provider/search_tools_by_name - 根据工具名称搜索工具，支持部分匹配和跨类型搜索
# tool_template_provider/search_tools_by_category - 根据分类搜索工具，主要针对内置工具的分类系统
# tool_template_provider/get_tool_details - 获取特定工具的详细信息，支持指定工具类型或全局搜索
# tool_template_provider/get_tool_content - 获取工具的源代码内容，支持自动查找或指定文件路径
# tool_template_provider/validate_tool_file - 验证工具文件的格式和语法，检查Python语法和Strands工具规范
# tool_template_provider/get_available_categories - 获取所有可用的工具分类，基于内置工具的分类系统
"""
工具模板提供工具

为Agent提供工具模板管理功能，支持管理template_tools和generated_tools目录下的所有Strands工具，
同时提供系统内置工具的信息查询功能
"""

import sys
import os
import json
import ast
import inspect
from typing import Optional, List, Dict, Any
from pathlib import Path
from strands import tool
from utils.config_loader import get_config


def _get_tool_directories() -> Dict[str, str]:
    """获取工具目录路径"""
    config = get_config()
    strands_config = config.get_strands_config()
    
    return {
        'template_tools': strands_config.get('template', {}).get('tool_template_path', 'tools/template_tools'),
        'generated_tools': strands_config.get('generated', {}).get('tool_generated_path', 'tools/generated_tools'),
        'system_tools': strands_config.get('system', {}).get('tools_path', 'tools/system_tools')
    }


def _get_builtin_tools_info() -> Dict[str, Dict[str, Any]]:
    """获取系统内置工具信息"""
    builtin_tools = {
        # RAG & Memory
        'retrieve': {
            'category': 'RAG & Memory',
            'description': 'Semantically retrieve data from Amazon Bedrock Knowledge Bases for RAG, memory, and other purposes',
            'package': 'strands-agents-tools'
        },
        'memory': {
            'category': 'RAG & Memory', 
            'description': 'Agent memory persistence in Amazon Bedrock Knowledge Bases',
            'package': 'strands-agents-tools'
        },
        'mem0_memory': {
            'category': 'RAG & Memory',
            'description': 'Agent memory and personalization built on top of Mem0',
            'package': 'strands-agents-tools[mem0_memory]'
        },
        
        # File Operations
        'editor': {
            'category': 'File Operations',
            'description': 'File editing operations like line edits, search, and undo',
            'package': 'strands-agents-tools'
        },
        'file_read': {
            'category': 'File Operations',
            'description': 'Read and parse files',
            'package': 'strands-agents-tools'
        },
        'file_write': {
            'category': 'File Operations',
            'description': 'Create and modify files',
            'package': 'strands-agents-tools'
        },
        
        # Shell & System
        'environment': {
            'category': 'Shell & System',
            'description': 'Manage environment variables',
            'package': 'strands-agents-tools'
        },
        'shell': {
            'category': 'Shell & System',
            'description': 'Execute shell commands',
            'package': 'strands-agents-tools'
        },
        'cron': {
            'category': 'Shell & System',
            'description': 'Task scheduling with cron jobs',
            'package': 'strands-agents-tools'
        },
        
        # Code Interpretation
        'python_repl': {
            'category': 'Code Interpretation',
            'description': 'Run Python code',
            'package': 'strands-agents-tools'
        },
        
        # Web & Network
        'http_request': {
            'category': 'Web & Network',
            'description': 'Make API calls, fetch web data, and call local HTTP servers',
            'package': 'strands-agents-tools'
        },
        'slack': {
            'category': 'Web & Network',
            'description': 'Slack integration with real-time events, API access, and message sending',
            'package': 'strands-agents-tools'
        },
        
        # Multi-modal
        'image_reader': {
            'category': 'Multi-modal',
            'description': 'Process and analyze images',
            'package': 'strands-agents-tools'
        },
        'generate_image': {
            'category': 'Multi-modal',
            'description': 'Create AI generated images with Amazon Bedrock',
            'package': 'strands-agents-tools'
        },
        'nova_reels': {
            'category': 'Multi-modal',
            'description': 'Create AI generated videos with Nova Reels on Amazon Bedrock',
            'package': 'strands-agents-tools'
        },
        'speak': {
            'category': 'Multi-modal',
            'description': 'Generate speech from text using macOS say command or Amazon Polly',
            'package': 'strands-agents-tools'
        },
        
        # AWS Services
        'use_aws': {
            'category': 'AWS Services',
            'description': 'Interact with AWS services',
            'package': 'strands-agents-tools'
        },
        
        # Utilities
        'calculator': {
            'category': 'Utilities',
            'description': 'Perform mathematical operations',
            'package': 'strands-agents-tools'
        },
        'current_time': {
            'category': 'Utilities',
            'description': 'Get the current date and time',
            'package': 'strands-agents-tools'
        },
        'load_tool': {
            'category': 'Utilities',
            'description': 'Dynamically load more tools at runtime',
            'package': 'strands-agents-tools'
        },
        
        # Agents & Workflows
        'agent_graph': {
            'category': 'Agents & Workflows',
            'description': 'Create and manage graphs of agents',
            'package': 'strands-agents-tools'
        },
        'journal': {
            'category': 'Agents & Workflows',
            'description': 'Create structured tasks and logs for agents to manage and work from',
            'package': 'strands-agents-tools'
        },
        'swarm': {
            'category': 'Agents & Workflows',
            'description': 'Coordinate multiple AI agents in a swarm / network of agents',
            'package': 'strands-agents-tools'
        },
        'stop': {
            'category': 'Agents & Workflows',
            'description': 'Force stop the agent event loop',
            'package': 'strands-agents-tools'
        },
        'think': {
            'category': 'Agents & Workflows',
            'description': 'Perform deep thinking by creating parallel branches of agentic reasoning',
            'package': 'strands-agents-tools'
        },
        'use_llm': {
            'category': 'Agents & Workflows',
            'description': 'Run a new AI event loop with custom prompts',
            'package': 'strands-agents-tools'
        },
        'workflow': {
            'category': 'Agents & Workflows',
            'description': 'Orchestrate sequenced workflows',
            'package': 'strands-agents-tools'
        }
    }
    
    return builtin_tools


def _parse_tool_file(file_path: Path) -> List[Dict[str, Any]]:
    """解析Python文件中的工具函数"""
    tools = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析AST
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # 检查是否有@tool装饰器
                has_tool_decorator = False
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name) and decorator.id == 'tool':
                        has_tool_decorator = True
                        break
                    elif isinstance(decorator, ast.Attribute) and decorator.attr == 'tool':
                        has_tool_decorator = True
                        break
                
                if has_tool_decorator:
                    # 提取函数信息
                    tool_info = {
                        'name': node.name,
                        'file': file_path.name,
                        'file_path': str(file_path),
                        'line_number': node.lineno,
                        'docstring': ast.get_docstring(node) or "无描述",
                        'parameters': []
                    }
                    
                    # 提取参数信息
                    for arg in node.args.args:
                        param_info = {'name': arg.arg, 'type': 'Any'}
                        
                        # 尝试获取类型注解
                        if arg.annotation:
                            if isinstance(arg.annotation, ast.Name):
                                param_info['type'] = arg.annotation.id
                            elif isinstance(arg.annotation, ast.Constant):
                                param_info['type'] = str(arg.annotation.value)
                        
                        tool_info['parameters'].append(param_info)
                    
                    tools.append(tool_info)
    
    except Exception as e:
        # 如果解析失败，返回基本信息
        tools.append({
            'name': file_path.stem,
            'file': file_path.name,
            'file_path': str(file_path),
            'error': f"解析错误: {str(e)}",
            'docstring': "文件解析失败",
            'parameters': []
        })
    
    return tools


@tool
def list_all_tools() -> str:
    """
    列出所有可用的工具，包括模板工具、生成工具和内置工具
    
    Returns:
        str: JSON格式的所有工具信息
    """
    try:
        tool_dirs = _get_tool_directories()
        builtin_tools = _get_builtin_tools_info()
        
        result = {
            'builtin_tools': [],
            'template_tools': [],
            'generated_tools': [],
            'system_tools': [],
            'summary': {}
        }
        
        # 内置工具
        for tool_name, tool_info in builtin_tools.items():
            result['builtin_tools'].append({
                'name': tool_name,
                'category': tool_info['category'],
                'description': tool_info['description'],
                'package': tool_info['package'],
                'type': 'builtin'
            })
        
        # 扫描各个目录
        for tool_type, tool_dir in tool_dirs.items():
            if os.path.exists(tool_dir):
                for file_path in Path(tool_dir).rglob("*.py"):
                    if file_path.name.startswith('__'):
                        continue
                    
                    tools_in_file = _parse_tool_file(file_path)
                    for tool_info in tools_in_file:
                        tool_info['type'] = tool_type
                        # 添加相对路径信息
                        relative_path = file_path.relative_to(Path(tool_dir))
                        tool_info['relative_path'] = str(relative_path)
                        result[tool_type].append(tool_info)
        
        # 生成摘要
        result['summary'] = {
            'total_builtin': len(result['builtin_tools']),
            'total_template': len(result['template_tools']),
            'total_generated': len(result['generated_tools']),
            'total_system': len(result['system_tools']),
            'total_tools': (len(result['builtin_tools']) + 
                          len(result['template_tools']) + 
                          len(result['generated_tools']) + 
                          len(result['system_tools']))
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({"error": f"列出工具时出现错误: {str(e)}"}, ensure_ascii=False, indent=2)


@tool
def get_builtin_tools() -> str:
    """
    获取所有内置工具信息
    
    Returns:
        str: JSON格式的内置工具信息
    """
    try:
        builtin_tools = _get_builtin_tools_info()
        
        # 按分类组织工具
        tools_by_category = {}
        for tool_name, tool_info in builtin_tools.items():
            category = tool_info['category']
            if category not in tools_by_category:
                tools_by_category[category] = []
            
            tools_by_category[category].append({
                'name': tool_name,
                'description': tool_info['description'],
                'package': tool_info['package']
            })
        
        result = {
            'total_tools': len(builtin_tools),
            'categories': list(tools_by_category.keys()),
            'tools_by_category': tools_by_category,
            'installation_note': 'Install with: pip install strands-agents-tools'
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({"error": f"获取内置工具时出现错误: {str(e)}"}, ensure_ascii=False, indent=2)


@tool
def get_template_tools() -> str:
    """
    获取所有模板工具信息
    
    Returns:
        str: JSON格式的模板工具信息
    """
    try:
        tool_dirs = _get_tool_directories()
        template_dir = tool_dirs['template_tools']
        
        if not os.path.exists(template_dir):
            return json.dumps({"error": "模板工具目录不存在", "tools": []}, ensure_ascii=False, indent=2)
        
        tools = []
        
        for file_path in Path(template_dir).rglob("*.py"):
            if file_path.name.startswith('__'):
                continue
            
            tools_in_file = _parse_tool_file(file_path)
            # 为每个工具添加相对路径信息
            for tool_info in tools_in_file:
                relative_path = file_path.relative_to(Path(template_dir))
                tool_info['relative_path'] = str(relative_path)
            tools.extend(tools_in_file)
        
        result = {
            'total_tools': len(tools),
            'template_directory': template_dir,
            'tools': tools
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({"error": f"获取模板工具时出现错误: {str(e)}"}, ensure_ascii=False, indent=2)


@tool
def get_generated_tools() -> str:
    """
    获取所有生成工具信息
    
    Returns:
        str: JSON格式的生成工具信息
    """
    try:
        tool_dirs = _get_tool_directories()
        generated_dir = tool_dirs['generated_tools']
        
        if not os.path.exists(generated_dir):
            return json.dumps({"error": "生成工具目录不存在", "tools": []}, ensure_ascii=False, indent=2)
        
        tools = []
        
        for file_path in Path(generated_dir).rglob("*.py"):
            if file_path.name.startswith('__'):
                continue
            
            tools_in_file = _parse_tool_file(file_path)
            # 为每个工具添加相对路径信息
            for tool_info in tools_in_file:
                relative_path = file_path.relative_to(Path(generated_dir))
                tool_info['relative_path'] = str(relative_path)
            tools.extend(tools_in_file)
        
        result = {
            'total_tools': len(tools),
            'generated_directory': generated_dir,
            'tools': tools
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({"error": f"获取生成工具时出现错误: {str(e)}"}, ensure_ascii=False, indent=2)


@tool
def search_tools_by_name(tool_name: str) -> str:
    """
    根据工具名称搜索工具
    
    Args:
        tool_name: 要搜索的工具名称（支持部分匹配）
    
    Returns:
        str: JSON格式的匹配工具信息
    """
    try:
        # 获取所有工具
        all_tools_result = list_all_tools()
        all_tools_data = json.loads(all_tools_result)
        
        if "error" in all_tools_data:
            return all_tools_result
        
        matching_tools = []
        
        # 搜索内置工具
        for tool in all_tools_data['builtin_tools']:
            if tool_name.lower() in tool['name'].lower():
                matching_tools.append(tool)
        
        # 搜索其他类型工具
        for tool_type in ['template_tools', 'generated_tools', 'system_tools']:
            for tool in all_tools_data[tool_type]:
                if tool_name.lower() in tool['name'].lower():
                    matching_tools.append(tool)
        
        result = {
            'search_term': tool_name,
            'total_matches': len(matching_tools),
            'matching_tools': matching_tools
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({"error": f"搜索工具时出现错误: {str(e)}"}, ensure_ascii=False, indent=2)


@tool
def search_tools_by_category(category: str) -> str:
    """
    根据分类搜索工具
    
    Args:
        category: 工具分类（如：File Operations, Web & Network等）
    
    Returns:
        str: JSON格式的匹配工具信息
    """
    try:
        builtin_tools = _get_builtin_tools_info()
        matching_tools = []
        
        # 搜索内置工具
        for tool_name, tool_info in builtin_tools.items():
            if category.lower() in tool_info['category'].lower():
                matching_tools.append({
                    'name': tool_name,
                    'category': tool_info['category'],
                    'description': tool_info['description'],
                    'package': tool_info['package'],
                    'type': 'builtin'
                })
        
        result = {
            'search_category': category,
            'total_matches': len(matching_tools),
            'matching_tools': matching_tools
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({"error": f"按分类搜索工具时出现错误: {str(e)}"}, ensure_ascii=False, indent=2)


@tool
def get_tool_details(tool_name: str, tool_type: Optional[str] = None) -> str:
    """
    获取特定工具的详细信息
    
    Args:
        tool_name: 工具名称
        tool_type: 工具类型（builtin, template_tools, generated_tools, system_tools），可选
    
    Returns:
        str: JSON格式的工具详细信息
    """
    try:
        # 如果指定了工具类型，直接在该类型中搜索
        if tool_type == 'builtin':
            builtin_tools = _get_builtin_tools_info()
            if tool_name in builtin_tools:
                tool_info = builtin_tools[tool_name]
                result = {
                    'name': tool_name,
                    'type': 'builtin',
                    'category': tool_info['category'],
                    'description': tool_info['description'],
                    'package': tool_info['package']
                }
                return json.dumps(result, ensure_ascii=False, indent=2)
        
        # 搜索所有工具
        all_tools_result = list_all_tools()
        all_tools_data = json.loads(all_tools_result)
        
        if "error" in all_tools_data:
            return all_tools_result
        
        # 在所有工具中搜索
        for tool_type_key in ['builtin_tools', 'template_tools', 'generated_tools', 'system_tools']:
            for tool in all_tools_data[tool_type_key]:
                if tool['name'] == tool_name:
                    return json.dumps(tool, ensure_ascii=False, indent=2)
        
        return json.dumps({"error": f"未找到名为 '{tool_name}' 的工具"}, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({"error": f"获取工具详情时出现错误: {str(e)}"}, ensure_ascii=False, indent=2)


@tool
def get_tool_content(tool_name: str, file_path: Optional[str] = None) -> str:
    """
    获取工具的源代码内容
    
    Args:
        tool_name: 工具名称
        file_path: 工具文件路径（可选，如果不提供则尝试自动查找）
    
    Returns:
        str: 工具的源代码内容
    """
    try:
        target_file = None
        
        if file_path and os.path.exists(file_path):
            target_file = file_path
        else:
            # 自动查找工具文件
            tool_dirs = _get_tool_directories()
            
            for tool_type, tool_dir in tool_dirs.items():
                if os.path.exists(tool_dir):
                    for file_path in Path(tool_dir).rglob("*.py"):
                        if file_path.name.startswith('__'):
                            continue
                        
                        tools_in_file = _parse_tool_file(file_path)
                        for tool_info in tools_in_file:
                            if tool_info['name'] == tool_name:
                                target_file = str(file_path)
                                break
                        
                        if target_file:
                            break
                
                if target_file:
                    break
        
        if not target_file:
            return f"错误：未找到工具 '{tool_name}' 的源文件"
        
        with open(target_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return content
        
    except Exception as e:
        return f"获取工具内容时出现错误: {str(e)}"


@tool
def validate_tool_file(file_path: str) -> str:
    """
    验证工具文件的格式和语法，提供详细的错误分类和具体原因
    
    Args:
        file_path: 工具文件路径
    
    Returns:
        str: JSON格式的验证结果，包含详细的错误分类和具体原因
    """
    try:
        # 初始化验证结果
        validation_results = {
            "valid": True,
            "file_path": file_path,
            "error_category": None,
            "error_details": [],
            "checks": {
                "file_exists": False,
                "file_readable": False,
                "python_syntax": False,
                "has_strands_import": False,
                "has_tool_functions": False,
                "tool_count": 0
            },
            "suggestions": []
        }
        
        # 1. 检查文件是否存在
        if not os.path.exists(file_path):
            validation_results.update({
                "valid": False,
                "error_category": "FILE_NOT_FOUND",
                "error_details": [f"文件不存在: {file_path}"],
                "suggestions": [
                    "检查文件路径是否正确",
                    "确认文件是否已被删除或移动",
                    "参考示例文件: tools/template_tools/common/example_tool.py"
                ]
            })
            return json.dumps(validation_results, ensure_ascii=False, indent=2)
        
        validation_results["checks"]["file_exists"] = True
        
        # 2. 检查文件是否可读
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            validation_results["checks"]["file_readable"] = True
        except PermissionError:
            validation_results.update({
                "valid": False,
                "error_category": "FILE_PERMISSION_ERROR",
                "error_details": [f"文件权限不足，无法读取: {file_path}"],
                "suggestions": ["检查文件权限，确保有读取权限"]
            })
            return json.dumps(validation_results, ensure_ascii=False, indent=2)
        except UnicodeDecodeError as e:
            validation_results.update({
                "valid": False,
                "error_category": "FILE_ENCODING_ERROR",
                "error_details": [f"文件编码错误: {str(e)}"],
                "suggestions": ["确保文件使用UTF-8编码"]
            })
            return json.dumps(validation_results, ensure_ascii=False, indent=2)
        except Exception as e:
            validation_results.update({
                "valid": False,
                "error_category": "FILE_READ_ERROR",
                "error_details": [f"读取文件时发生错误: {str(e)}"],
                "suggestions": ["检查文件是否被其他程序占用"]
            })
            return json.dumps(validation_results, ensure_ascii=False, indent=2)
        
        # 3. 检查Python语法
        try:
            tree = ast.parse(content)
            validation_results["checks"]["python_syntax"] = True
        except SyntaxError as e:
            validation_results.update({
                "valid": False,
                "error_category": "PYTHON_SYNTAX_ERROR",
                "error_details": [f"Python语法错误: {str(e)}"],
                "suggestions": [
                    "检查Python语法是否正确",
                    "检查缩进是否正确",
                    "检查是否有未闭合的括号或引号",
                    "使用IDE的语法检查功能"
                ]
            })
            return json.dumps(validation_results, ensure_ascii=False, indent=2)
        
        # 4. 检查strands导入
        has_strands_import = "from strands import tool" in content or "import strands" in content
        validation_results["checks"]["has_strands_import"] = has_strands_import
        
        if not has_strands_import:
            validation_results.update({
                "valid": False,
                "error_category": "MISSING_STRANDS_IMPORT",
                "error_details": ["缺少strands导入"],
                "suggestions": [
                    "添加 'from strands import tool' 导入语句",
                    "确保使用 @tool 装饰器定义工具函数"
                ]
            })
            return json.dumps(validation_results, ensure_ascii=False, indent=2)
        
        # 5. 检查工具函数
        try:
            tools_in_file = _parse_tool_file(Path(file_path))
            validation_results["checks"]["has_tool_functions"] = len(tools_in_file) > 0
            validation_results["checks"]["tool_count"] = len(tools_in_file)
            
            if len(tools_in_file) == 0:
                validation_results.update({
                    "valid": False,
                    "error_category": "NO_TOOL_FUNCTIONS",
                    "error_details": ["文件中没有找到工具函数"],
                    "suggestions": [
                        "使用 @tool 装饰器定义至少一个工具函数",
                        "确保函数有正确的类型注解",
                        "参考示例文件了解工具函数格式"
                    ]
                })
                return json.dumps(validation_results, ensure_ascii=False, indent=2)
                
        except Exception as e:
            validation_results.update({
                "valid": False,
                "error_category": "TOOL_PARSING_ERROR",
                "error_details": [f"解析工具函数时发生错误: {str(e)}"],
                "suggestions": [
                    "检查工具函数的定义格式",
                    "确保使用正确的 @tool 装饰器",
                    "检查函数参数的类型注解"
                ]
            })
            return json.dumps(validation_results, ensure_ascii=False, indent=2)
        
        # 6. 添加建议
        validation_results["suggestions"] = [
            "工具文件验证通过",
            f"找到 {len(tools_in_file)} 个工具函数",
            "建议定期检查工具函数的有效性",
            "建议使用类型注解提高代码质量"
        ]
        
        return json.dumps(validation_results, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "valid": False,
            "file_path": file_path,
            "error_category": "UNEXPECTED_ERROR",
            "error_details": [f"验证过程中发生意外错误: {str(e)}"],
            "checks": {},
            "suggestions": [
                "检查文件是否损坏",
                "尝试重新创建文件",
                "联系技术支持"
            ]
        }, ensure_ascii=False, indent=2)


@tool
def get_available_categories() -> str:
    """
    获取所有可用的工具分类
    
    Returns:
        str: JSON格式的分类列表
    """
    try:
        builtin_tools = _get_builtin_tools_info()
        categories = set()
        
        for tool_info in builtin_tools.values():
            categories.add(tool_info['category'])
        
        result = {
            'total_categories': len(categories),
            'categories': sorted(list(categories))
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({"error": f"获取分类时出现错误: {str(e)}"}, ensure_ascii=False, indent=2)


# 主函数，用于直接调用测试
def main():
    """主函数，用于测试工具模板提供工具"""
    print("=== 工具模板提供工具测试 ===")
    
    print("\n1. 获取所有内置工具:")
    builtin_result = get_builtin_tools()
    print(builtin_result[:500] + "..." if len(builtin_result) > 500 else builtin_result)
    
    print("\n2. 获取模板工具:")
    template_result = get_template_tools()
    print(template_result)
    
    print("\n3. 搜索计算器工具:")
    search_result = search_tools_by_name("calculator")
    print(search_result)
    
    print("\n4. 按分类搜索工具:")
    category_result = search_tools_by_category("File Operations")
    print(category_result)
    
    print("\n5. 获取可用分类:")
    categories_result = get_available_categories()
    print(categories_result)
    
    print("\n6. 列出所有工具概览:")
    all_tools_result = list_all_tools()
    all_tools_data = json.loads(all_tools_result)
    print(all_tools_data)
    print(f"总计: {all_tools_data.get('summary', {}).get('total_tools', 0)} 个工具")


if __name__ == "__main__":
    main()