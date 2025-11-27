#!/usr/bin/env python3
# prompt_template_provider/list_prompt_templates - 列出所有可用的提示词模板，包含基本信息、版本数和环境配置
# prompt_template_provider/get_prompt_template - 获取指定提示词模板的完整内容，默认返回template.yaml
# prompt_template_provider/get_template_metadata - 获取指定模板的元数据信息，包含文件信息和YAML结构
# prompt_template_provider/get_prompt_template_info - 获取提示词模板的基本信息，包含路径、大小、行数等
# prompt_template_provider/validate_prompt_template - 验证提示词模板文件的格式是否正确，检查YAML结构和必要字段
# prompt_template_provider/validate_all_templates - 验证所有提示词模板文件的格式，返回验证摘要
# prompt_template_provider/get_template_structure - 获取提示词模板的结构概览，显示YAML层次结构
# prompt_template_provider/search_templates_by_category - 根据分类搜索模板，支持分类名称匹配
"""
提示词模板提供工具

为Agent提供标准的提示词模板内容，支持管理template_prompts目录下的所有模板
"""

import sys
import os
import yaml
import json
import re
from typing import Optional, List, Dict
from pathlib import Path
from strands import tool
from nexus_utils.config_loader import get_config


def _get_template_directory() -> str:
    """获取模板目录路径"""
    config = get_config()
    strands_config = config.get_strands_config()
    prompt_template_path = strands_config.get('prompt_template_path', 'prompts/template_prompts')
    return os.path.join(prompt_template_path)

def _get_system_directory() -> str:
    """获取模板目录路径"""
    config = get_config()
    strands_config = config.get_strands_config()
    prompt_template_path = strands_config.get('prompt_template_path', 'prompts/system_agents_prompts')
    return os.path.join(prompt_template_path)

def _get_generated_directory() -> str:
    """获取模板目录路径"""
    config = get_config()
    strands_config = config.get_strands_config()
    prompt_template_path = strands_config.get('prompt_template_path', 'prompts/generated_agents_prompts')
    return os.path.join(prompt_template_path)


@tool
def list_prompt_templates(type="template") -> str:
    """
    列出所有可用的提示词模板
    
    Returns:
        str: JSON格式的模板列表，包含每个模板的基本信息
    """
    try:
        if type == "template":
            template_dir = _get_template_directory()
        elif type == "system":
            template_dir = _get_system_directory()
        elif type == "generated":
            template_dir = _get_generated_directory()
        else:
            return json.dumps({"error": "无效的类型", "templates": []}, ensure_ascii=False, indent=2)
        
        if not os.path.exists(template_dir):
            return json.dumps({"error": "模板目录不存在", "templates": []}, ensure_ascii=False, indent=2)
        
        templates = []
        
        # 递归遍历目录中的所有YAML文件（包括子目录）
        for file_path in Path(template_dir).rglob("*.yaml"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = yaml.safe_load(f)
                
                if content and "agent" in content:
                    agent_info = content["agent"]
                    # 计算相对路径 - 相对于 prompts 目录
                    template_info = {
                        "filename": file_path.name,
                        "relative_path": str(file_path),
                        "name": agent_info.get("name", file_path.stem),
                        "description": agent_info.get("description", "无描述"),
                        "category": agent_info.get("category", "未分类"),
                        "versions": len(agent_info.get("versions", [])),
                        "environments": list(agent_info.get("environments", {}).keys()),
                        "file_size": file_path.stat().st_size,
                        "modified_time": file_path.stat().st_mtime
                    }
                    templates.append(template_info)
                    
            except Exception as e:
                # 如果单个文件解析失败，记录错误但继续处理其他文件
                templates.append({
                    "filename": file_path.name,
                    "name": file_path.stem,
                    "description": f"解析错误: {str(e)}",
                    "category": "错误",
                    "versions": 0,
                    "environments": [],
                    "file_size": file_path.stat().st_size,
                    "modified_time": file_path.stat().st_mtime
                })
        
        result = {
            "total_templates": len(templates),
            "template_directory": template_dir,
            "templates": templates
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({"error": f"列出模板时出现错误: {str(e)}", "templates": []}, ensure_ascii=False, indent=2)


@tool
def get_prompt_template(template_name: Optional[str] = None) -> str:
    """
    获取指定提示词模板的完整内容
    
    Args:
        template_name: 模板名称或相对路径（若无.yaml扩展名，则自动添加），如果为空则返回template.yaml
                      支持格式：
                      - "template" (直接文件名)
                      - "api_integration_agent" (相对文件名)
                      - "prompts/template_prompts/api_integration_agent" (完整相对路径)
                      - "prompts/system_agents_prompts/multimodal_analysis/multimodal_analyzer_agent.yaml" (完整相对路径)
    
    Returns:
        str: 指定模板文件的完整内容
    """
    try:
        # 如果没有指定模板名称，默认使用template.yaml
        if not template_name:
            template_name = "template"
        
        # 确保文件名以.yaml结尾
        if not template_name.endswith('.yaml'):
            template_name += '.yaml'
        
        # 检查是否包含完整路径
        if template_name.startswith('prompts/'):
            # 如果是完整相对路径，直接使用（相对于项目根目录）
            template_path = template_name
        else:
            # 如果是相对文件名，使用默认模板目录
            template_dir = _get_template_directory()
            template_path = os.path.join(template_dir, template_name)
        
        if not os.path.exists(template_path):
            return f"错误：提示词模板文件 '{template_name}' 不存在，尝试的路径: {template_path}"
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return content
        
    except Exception as e:
        return f"获取提示词模板时出现错误: {str(e)}"


@tool
def get_template_metadata(template_name: str) -> str:
    """
    获取指定模板的元数据信息（不包含完整内容）
    
    Args:
        template_name: 模板名称或相对路径（不含.yaml扩展名）
                      支持格式：
                      - "template" (直接文件名)
                      - "test/template_requirements_analyzer" (相对路径)
    
    Returns:
        str: JSON格式的模板元数据
    """
    try:
        template_dir = _get_template_directory()
        
        # 确保文件名以.yaml结尾
        if not template_name.endswith('.yaml'):
            template_name += '.yaml'
        
        # 支持相对路径
        template_path = os.path.join(template_dir, template_name)
        
        if not os.path.exists(template_path):
            return json.dumps({"error": f"模板文件 '{template_name}' 不存在"}, ensure_ascii=False, indent=2)
        
        # 获取文件信息
        file_stat = os.stat(template_path)
        file_size = file_stat.st_size
        
        # 解析YAML内容获取元数据
        with open(template_path, 'r', encoding='utf-8') as f:
            content = yaml.safe_load(f)
        
        # 重新打开文件计算行数
        with open(template_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 计算相对路径
        relative_path = os.path.relpath(template_path, template_dir)
        
        metadata = {
            "filename": os.path.basename(template_name),
            "relative_path": relative_path,
            "file_path": template_path,
            "file_size": file_size,
            "line_count": len(lines),
            "modified_time": file_stat.st_mtime,
            "encoding": "UTF-8",
            "format": "YAML"
        }
        
        if content and "agent" in content:
            agent_info = content["agent"]
            metadata.update({
                "name": agent_info.get("name", "未命名"),
                "description": agent_info.get("description", "无描述"),
                "category": agent_info.get("category", "未分类"),
                "environments": list(agent_info.get("environments", {}).keys()),
                "versions": [v.get("version", "unknown") for v in agent_info.get("versions", [])],
                "latest_version": agent_info.get("versions", [{}])[-1] if agent_info.get("versions") else {}
            })
        
        return json.dumps(metadata, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({"error": f"获取模板元数据时出现错误: {str(e)}"}, ensure_ascii=False, indent=2)


@tool
def get_prompt_template_info(template_name: Optional[str] = None) -> str:
    """
    获取提示词模板的基本信息（不包含完整内容）
    
    Args:
        template_name: 模板名称或相对路径（若无.yaml扩展名，则自动添加），如果为空则返回template.yaml的信息
                      支持格式：
                      - "template" (直接文件名)
                      - "api_integration_agent" (相对文件名)
                      - "prompts/template_prompts/api_integration_agent" (完整相对路径)
                      - "prompts/system_agents_prompts/multimodal_analysis/multimodal_analyzer_agent.yaml" (完整相对路径)
    
    Returns:
        str: 模板的基本信息，包括路径、大小等
    """
    try:
        # 如果没有指定模板名称，默认使用template.yaml
        if not template_name:
            template_name = "template"
        
        # 确保文件名以.yaml结尾
        if not template_name.endswith('.yaml'):
            template_name += '.yaml'
        
        # 检查是否包含完整路径
        if template_name.startswith('prompts/'):
            # 如果是完整相对路径，直接使用（相对于项目根目录）
            template_path = template_name
            template_dir = _get_template_directory()  # 用于计算相对路径
        else:
            # 如果是相对文件名，使用默认模板目录
            template_dir = _get_template_directory()
            template_path = os.path.join(template_dir, template_name)
        
        if not os.path.exists(template_path):
            return f"错误：提示词模板文件 '{template_name}' 不存在，尝试的路径: {template_path}"
        
        # 获取文件信息
        file_size = os.path.getsize(template_path)
        file_stat = os.stat(template_path)
        
        import time
        modified_time = time.ctime(file_stat.st_mtime)
        
        # 读取文件行数
        with open(template_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            line_count = len(lines)
        
        # 计算相对路径
        relative_path = os.path.relpath(template_path, template_dir)
        
        info = f"""提示词模板文件信息：
文件名: {os.path.basename(template_name)}
相对路径: {relative_path}
文件路径: {template_path}
文件大小: {file_size} 字节
行数: {line_count}
最后修改时间: {modified_time}
编码: UTF-8
格式: YAML"""
        
        return info
        
    except Exception as e:
        return f"获取提示词模板信息时出现错误: {str(e)}"


@tool
def validate_prompt_template(template_name: Optional[str] = None) -> str:
    """
    验证提示词模板文件的格式是否正确
    
    Args:
        template_name: 模板名称或相对路径（不含.yaml扩展名），如果为空则验证template.yaml
                      支持格式：
                      - "template" (直接文件名)
                      - "api_integration_agent" (相对文件名)
                      - "prompts/template_prompts/api_integration_agent" (完整相对路径)
                      - "prompts/system_agents_prompts/multimodal_analysis/multimodal_analyzer_agent.yaml" (完整相对路径)
    
    Returns:
        str: JSON格式的验证结果信息
    """
    try:
        # 如果没有指定模板名称，默认使用template.yaml
        if not template_name:
            template_name = "template"
        
        # 确保文件名以.yaml结尾
        if not template_name.endswith('.yaml'):
            template_name += '.yaml'
        
        # 检查是否包含完整路径
        if template_name.startswith('prompts/'):
            # 如果是完整相对路径，直接使用（相对于项目根目录）
            template_path = template_name
            template_dir = _get_template_directory()  # 用于计算相对路径
        else:
            # 如果是相对文件名，使用默认模板目录
            template_dir = _get_template_directory()
            template_path = os.path.join(template_dir, template_name)
        
        if not os.path.exists(template_path):
            return json.dumps({
                "valid": False,
                "template_name": template_name,
                "relative_path": template_name,  # 使用原始输入作为相对路径
                "error": "模板文件不存在",
                "checks": {}
            }, ensure_ascii=False, indent=2)
        
        # 尝试解析YAML文件
        with open(template_path, 'r', encoding='utf-8') as f:
            content = yaml.safe_load(f)
        
        # 基本结构验证
        validation_results = {
            "valid": True,
            "template_name": template_name,
            "relative_path": template_name,  # 默认使用template_name
            "checks": {
                "file_exists": True,
                "yaml_parseable": True,
                "has_agent_section": "agent" in content if content else False,
                "has_name": False,
                "has_description": False,
                "has_versions": False,
                "has_environments": False
            }
        }
        
        # 如果template_name是简单文件名，计算完整的相对路径
        if not template_name.startswith('prompts/'):
            try:
                # 计算相对于项目根目录的完整相对路径
                project_root = Path.cwd()
                # 使用绝对路径来计算相对路径
                absolute_path = Path(template_path).resolve()
                full_relative_path = absolute_path.relative_to(project_root)
                validation_results["relative_path"] = str(full_relative_path)
            except ValueError:
                # 如果计算失败，保持原样
                pass
        
        if content and "agent" in content:
            agent_section = content["agent"]
            validation_results["checks"]["has_name"] = "name" in agent_section
            validation_results["checks"]["has_description"] = "description" in agent_section
            validation_results["checks"]["has_versions"] = "versions" in agent_section
            validation_results["checks"]["has_environments"] = "environments" in agent_section
        
        # 检查是否所有基本检查都通过
        all_checks_passed = all(validation_results["checks"].values())
        validation_results["valid"] = all_checks_passed
        
        return json.dumps(validation_results, ensure_ascii=False, indent=2)
        
    except yaml.YAMLError as e:
        return json.dumps({
            "valid": False,
            "template_name": template_name,
            "relative_path": template_name,  # 使用原始输入作为相对路径
            "error": f"YAML格式错误: {str(e)}",
            "checks": {"yaml_parseable": False}
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "valid": False,
            "template_name": template_name,
            "relative_path": template_name,  # 使用原始输入作为相对路径
            "error": f"验证模板时出现错误: {str(e)}",
            "checks": {}
        }, ensure_ascii=False, indent=2)


@tool
def validate_all_templates() -> str:
    """
    验证所有提示词模板文件的格式
    
    Returns:
        str: JSON格式的所有模板验证结果
    """
    try:
        template_dir = _get_template_directory()
        
        if not os.path.exists(template_dir):
            return json.dumps({
                "error": "模板目录不存在",
                "results": []
            }, ensure_ascii=False, indent=2)
        
        results = []
        
        # 递归遍历目录中的所有YAML文件（包括子目录）
        for file_path in Path(template_dir).rglob("*.yaml"):
            # 计算相对于项目根目录的完整相对路径
            project_root = Path.cwd()
            try:
                full_relative_path = file_path.relative_to(project_root)
                relative_path = str(full_relative_path)
            except ValueError:
                # 如果文件不在项目根目录的子路径中，使用相对于模板目录的路径
                relative_to_template = file_path.relative_to(Path(template_dir))
                relative_path = f"prompts/template_prompts/{relative_to_template}"
            
            # template_name 保持为文件名
            template_name = file_path.name
            
            validation_result = validate_prompt_template(template_name)
            
            # 解析验证结果并添加到结果列表
            try:
                result_data = json.loads(validation_result)
                results.append(result_data)
            except json.JSONDecodeError:
                results.append({
                    "valid": False,
                    "template_name": template_name,
                    "relative_path": template_name,
                    "error": "验证结果解析失败",
                    "checks": {}
                })
        
        summary = {
            "total_templates": len(results),
            "valid_templates": len([r for r in results if r.get("valid", False)]),
            "invalid_templates": len([r for r in results if not r.get("valid", False)]),
            "results": results
        }
        
        return json.dumps(summary, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": f"验证所有模板时出现错误: {str(e)}",
            "results": []
        }, ensure_ascii=False, indent=2)


@tool
def get_template_structure(template_name: Optional[str] = None) -> str:
    """
    获取提示词模板的结构概览
    
    Args:
        template_name: 模板名称或相对路径（若无.yaml扩展名，则自动添加），如果为空则获取template.yaml的结构
                      支持格式：
                      - "template" (直接文件名)
                      - "api_integration_agent" (相对文件名)
                      - "prompts/template_prompts/api_integration_agent" (完整相对路径)
                      - "prompts/system_agents_prompts/multimodal_analysis/multimodal_analyzer_agent.yaml" (完整相对路径)
    
    Returns:
        str: 模板结构的简要说明
    """
    try:
        # 如果没有指定模板名称，默认使用template.yaml
        if not template_name:
            template_name = "template"
        
        # 确保文件名以.yaml结尾
        if not template_name.endswith('.yaml'):
            template_name += '.yaml'
        
        # 检查是否包含完整路径
        if template_name.startswith('prompts/'):
            # 如果是完整相对路径，直接使用
            template_path = template_name
            template_dir = _get_template_directory()  # 用于计算相对路径
        else:
            # 如果是相对文件名，使用默认模板目录
            template_dir = _get_template_directory()
            template_path = os.path.join(template_dir, template_name)
        
        if not os.path.exists(template_path):
            return f"错误：提示词模板文件 '{template_name}' 不存在"
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = yaml.safe_load(f)
        
        if not content:
            return f"错误：模板文件 '{template_name}' 内容为空"
        
        def get_structure(obj, indent=0):
            """递归获取结构"""
            result = []
            prefix = "  " * indent
            
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, (dict, list)):
                        result.append(f"{prefix}{key}:")
                        result.extend(get_structure(value, indent + 1))
                    else:
                        value_type = type(value).__name__
                        if isinstance(value, str) and len(value) > 50:
                            result.append(f"{prefix}{key}: ({value_type}, {len(value)} chars)")
                        else:
                            result.append(f"{prefix}{key}: ({value_type})")
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    result.append(f"{prefix}[{i}]:")
                    result.extend(get_structure(item, indent + 1))
            
            return result
        
        # 计算相对路径用于显示
        relative_path = os.path.relpath(template_path, template_dir)
        structure_lines = [f"模板文件: {relative_path}"] + get_structure(content)
        return "\n".join(structure_lines)
        
    except Exception as e:
        return f"获取模板结构时出现错误: {str(e)}"


@tool
def search_templates_by_category(category: str) -> str:
    """
    根据分类搜索模板
    
    Args:
        category: 模板分类（如：assistant, analysis, generator等）
    
    Returns:
        str: JSON格式的匹配模板列表
    """
    try:
        template_dir = _get_template_directory()
        
        if not os.path.exists(template_dir):
            return json.dumps({"error": "模板目录不存在", "templates": []}, ensure_ascii=False, indent=2)
        
        matching_templates = []
        
        # 递归遍历目录中的所有YAML文件（包括子目录）
        for file_path in Path(template_dir).rglob("*.yaml"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = yaml.safe_load(f)
                
                if content and "agent" in content:
                    agent_info = content["agent"]
                    template_category = agent_info.get("category", "").lower()
                    
                    if category.lower() in template_category or template_category in category.lower():
                        # 计算相对路径
                        relative_path = file_path.relative_to(Path(template_dir))
                        template_info = {
                            "filename": file_path.name,
                            "relative_path": str(relative_path),
                            "name": agent_info.get("name", file_path.stem),
                            "description": agent_info.get("description", "无描述"),
                            "category": agent_info.get("category", "未分类"),
                            "versions": len(agent_info.get("versions", [])),
                            "environments": list(agent_info.get("environments", {}).keys())
                        }
                        matching_templates.append(template_info)
                        
            except Exception as e:
                continue  # 跳过解析失败的文件
        
        result = {
            "search_category": category,
            "total_matches": len(matching_templates),
            "templates": matching_templates
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({"error": f"搜索模板时出现错误: {str(e)}", "templates": []}, ensure_ascii=False, indent=2)


def validate_prompt_file(file_path: str) -> str:
    """
    验证提示词文件的格式和语法，提供详细的错误分类和具体原因
    
    Args:
        file_path: 提示词文件路径
    
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
                "yaml_syntax": False,
                "has_agent_section": False,
                "has_required_fields": False,
                "required_fields_details": {},
                "environments_format": False,
                "versions_format": False,
                "tools_dependencies_format": False,
                "tools_dependencies_details": []
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
                    "参考示例文件: prompts/template_prompts/default.yaml"
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
        
        # 3. 检查YAML语法
        try:
            yaml_data = yaml.safe_load(content)
            validation_results["checks"]["yaml_syntax"] = True
        except yaml.YAMLError as e:
            validation_results.update({
                "valid": False,
                "error_category": "YAML_SYNTAX_ERROR",
                "error_details": [f"YAML语法错误: {str(e)}"],
                "suggestions": [
                    "检查YAML缩进是否正确（使用空格，不要使用Tab）",
                    "检查是否有未闭合的引号或括号",
                    "检查是否有特殊字符需要转义",
                    "使用在线YAML验证工具检查语法"
                ]
            })
            return json.dumps(validation_results, ensure_ascii=False, indent=2)
        
        # 4. 检查是否有agent部分
        if not yaml_data:
            validation_results.update({
                "valid": False,
                "error_category": "EMPTY_YAML",
                "error_details": ["YAML文件为空或只包含注释"],
                "suggestions": ["添加agent配置部分"]
            })
            return json.dumps(validation_results, ensure_ascii=False, indent=2)
        
        if "agent" not in yaml_data:
            validation_results.update({
                "valid": False,
                "error_category": "MISSING_AGENT_SECTION",
                "error_details": ["缺少agent配置部分"],
                "suggestions": [
                    "在YAML文件根级别添加agent配置",
                    "参考示例文件: prompts/template_prompts/default.yaml"
                ]
            })
            return json.dumps(validation_results, ensure_ascii=False, indent=2)
        
        validation_results["checks"]["has_agent_section"] = True
        agent_data = yaml_data["agent"]
        
        # 5. 检查必要字段
        required_fields = ["name", "description", "category", "environments", "versions"]
        missing_fields = []
        invalid_fields = []
        
        for field in required_fields:
            if field not in agent_data:
                missing_fields.append(field)
            elif agent_data[field] is None or agent_data[field] == "":
                invalid_fields.append(f"{field}字段为空")
        
        validation_results["checks"]["required_fields_details"] = {
            "missing_fields": missing_fields,
            "invalid_fields": invalid_fields
        }
        
        if missing_fields or invalid_fields:
            validation_results.update({
                "valid": False,
                "error_category": "MISSING_REQUIRED_FIELDS",
                "error_details": [
                    f"缺少必要字段: {', '.join(missing_fields)}" if missing_fields else "",
                    f"字段值无效: {', '.join(invalid_fields)}" if invalid_fields else ""
                ],
                "suggestions": [
                    f"添加缺少的字段: {', '.join(missing_fields)}" if missing_fields else "",
                    f"为无效字段提供有效值: {', '.join(invalid_fields)}" if invalid_fields else "",
                    "参考示例文件了解字段格式"
                ]
            })
            return json.dumps(validation_results, ensure_ascii=False, indent=2)
        
        validation_results["checks"]["has_required_fields"] = True
        
        # 6. 检查environments格式
        environments = agent_data.get("environments", {})
        if not isinstance(environments, dict) or not environments:
            validation_results.update({
                "valid": False,
                "error_category": "INVALID_ENVIRONMENTS_FORMAT",
                "error_details": ["environments字段必须是包含环境配置的字典"],
                "suggestions": [
                    "environments应该包含development、production、testing等环境",
                    "每个环境应包含max_tokens、temperature、streaming等配置"
                ]
            })
            return json.dumps(validation_results, ensure_ascii=False, indent=2)
        
        validation_results["checks"]["environments_format"] = True
        
        # 7. 检查versions格式
        versions = agent_data.get("versions", [])
        if not isinstance(versions, list) or not versions:
            validation_results.update({
                "valid": False,
                "error_category": "INVALID_VERSIONS_FORMAT",
                "error_details": ["versions字段必须是包含版本信息的列表"],
                "suggestions": [
                    "versions应该是一个列表，包含至少一个版本配置",
                    "每个版本应包含version、status、created_date、author、description等字段"
                ]
            })
            return json.dumps(validation_results, ensure_ascii=False, indent=2)
        
        validation_results["checks"]["versions_format"] = True
        
        # 8. 检查tools_dependencies格式
        tools_dependencies_errors = []
        tools_dependencies_warnings = []
        
        for i, version in enumerate(versions):
            if not isinstance(version, dict):
                tools_dependencies_errors.append(f"版本{i+1}不是字典格式")
                continue
                
            if "metadata" not in version:
                tools_dependencies_warnings.append(f"版本{i+1}缺少metadata字段")
                continue
                
            metadata = version["metadata"]
            if "tools_dependencies" not in metadata:
                tools_dependencies_warnings.append(f"版本{i+1}的metadata中缺少tools_dependencies字段")
                continue
            
            tools_deps = metadata["tools_dependencies"]
            if not isinstance(tools_deps, list):
                tools_dependencies_errors.append(f"版本{i+1}的tools_dependencies不是列表格式")
                continue
            
            for j, tool_dep in enumerate(tools_deps):
                if not isinstance(tool_dep, str):
                    tools_dependencies_errors.append(f"版本{i+1}的工具依赖{j+1}不是字符串格式")
                    continue
                
                # 检查generated_tools格式
                if tool_dep.startswith("generated_tools/"):
                    pattern = r'^generated_tools/[^/]+/[^/]+/[^/]+$'
                    if not re.match(pattern, tool_dep):
                        tools_dependencies_errors.append(
                            f"版本{i+1}的工具依赖{j+1}格式错误: {tool_dep}，"
                            f"应为 generated_tools/<project_name>/<script_name>/<tool_name>"
                        )
                
                # 检查system_tools格式
                elif tool_dep.startswith("system_tools/"):
                    pattern = r'^system_tools/[^/]+/[^/]+/[^/]+$'
                    if not re.match(pattern, tool_dep):
                        tools_dependencies_errors.append(
                            f"版本{i+1}的工具依赖{j+1}格式错误: {tool_dep}，"
                            f"应为 system_tools/<module_name>/<tool_name>"
                        )
                
                # 检查strands_tools格式
                elif tool_dep.startswith("strands_tools/"):
                    pattern = r'^strands_tools/[^/]+$'
                    if not re.match(pattern, tool_dep):
                        tools_dependencies_errors.append(
                            f"版本{i+1}的工具依赖{j+1}格式错误: {tool_dep}，"
                            f"应为 strands_tools/<tool_name>"
                        )
                
                # 检查其他格式
                elif not any(tool_dep.startswith(prefix) for prefix in ["generated_tools/", "system_tools/", "strands_tools/"]):
                    tools_dependencies_warnings.append(
                        f"版本{i+1}的工具依赖{j+1}使用了未知前缀: {tool_dep}"
                    )
        
        validation_results["checks"]["tools_dependencies_details"] = {
            "errors": tools_dependencies_errors,
            "warnings": tools_dependencies_warnings
        }
        
        if tools_dependencies_errors:
            validation_results.update({
                "valid": False,
                "error_category": "INVALID_TOOLS_DEPENDENCIES_FORMAT",
                "error_details": tools_dependencies_errors,
                "suggestions": [
                    "检查tools_dependencies格式",
                    "generated_tools格式: generated_tools/<project_name>/<script_name>/<tool_name>",
                    "system_tools格式: system_tools/<module_name>/<tool_name>",
                    "strands_tools格式: strands_tools/<tool_name>"
                ]
            })
            return json.dumps(validation_results, ensure_ascii=False, indent=2)
        
        validation_results["checks"]["tools_dependencies_format"] = True
        
        # 9. 添加警告信息
        if tools_dependencies_warnings:
            validation_results["warnings"] = tools_dependencies_warnings
        
        # 10. 添加建议
        validation_results["suggestions"] = [
            "提示词文件验证通过",
            "建议定期检查工具依赖的有效性",
            "建议使用版本控制管理提示词文件"
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

# 主函数，用于直接调用测试
def main():
    """主函数，用于测试提示词模板提供工具"""
    print("=== 提示词模板提供工具测试 ===")
    
    print("\n1. 列出所有模板:")
    print(list_prompt_templates())
    
    print("\n2. 获取default模板信息:")
    print(get_prompt_template_info("default"))
    
    print("\n3. 获取requirements_analyzer模板信息:")
    print(get_prompt_template_info("requirements_analyzer"))
    
    print("\n4. 验证所有模板:")
    print(validate_all_templates())
    
    print("\n5. 获取requirements_analyzer模板结构:")
    print(get_template_structure("prompts/template_prompts/requirements_analyzer.yaml"))
    
    print("\n6. 按分类搜索模板:")
    print(search_templates_by_category("analysis"))
    
    print("\n7. 获取deep_research_agent模板内容:")
    content = get_prompt_template("prompts/template_prompts/api_integration_agent.yaml")
    print(f"内容长度: {len(content)} 字符")
    print("前200个字符:")
    print(content[:200] + "..." if len(content) > 200 else content)

    print("\n8. 验证prompt文件:")
    print(validate_prompt_file("prompts/template_prompts/requirements_analyzer.yaml"))


if __name__ == "__main__":
    main()