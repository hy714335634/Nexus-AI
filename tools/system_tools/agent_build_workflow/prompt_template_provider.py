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
from utils.config_loader import get_config


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
    验证提示词文件的格式和语法
    
    Args:
        file_path: 提示词文件路径
    
    Returns:
        str: JSON格式的验证结果
    """
    try:
        if not os.path.exists(file_path):
            return json.dumps({
                "valid": False,
                "file_path": file_path,
                "error": "文件不存在",
                "checks": {}
            }, ensure_ascii=False, indent=2)
        
        validation_results = {
            "valid": True,
            "file_path": file_path,
            "checks": {
                "file_exists": True,
                "yaml_syntax": False,
                "has_agent_section": False,
                "has_required_fields": False,
                "tools_dependencies_format": False
            }
        }
        
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查YAML语法
        try:
            yaml_data = yaml.safe_load(content)
            validation_results["checks"]["yaml_syntax"] = True
        except yaml.YAMLError as e:
            validation_results["valid"] = False
            validation_results["error"] = f"YAML语法错误: {str(e)}"
            return json.dumps(validation_results, ensure_ascii=False, indent=2)
        
        # 检查是否有agent部分
        if yaml_data and "agent" in yaml_data:
            validation_results["checks"]["has_agent_section"] = True
            
            agent_data = yaml_data["agent"]
            
            # 检查必要字段
            required_fields = ["name", "description", "category", "environments", "versions"]
            has_required_fields = all(field in agent_data for field in required_fields)
            validation_results["checks"]["has_required_fields"] = has_required_fields
            
            # 检查tools_dependencies格式
            if "versions" in agent_data and agent_data["versions"]:
                for version in agent_data["versions"]:
                    if "metadata" in version and "tools_dependencies" in version["metadata"]:
                        tools_deps = version["metadata"]["tools_dependencies"]
                        if isinstance(tools_deps, list):
                            # 检查generated_tools格式
                            generated_tools_format_valid = True
                            for tool_dep in tools_deps:
                                if tool_dep.startswith("generated_tools/"):
                                    # 检查格式: generated_tools/<project_name>/<script_name>/<tool_name>
                                    pattern = r'^generated_tools/[^/]+/[^/]+/[^/]+$'
                                    if not re.match(pattern, tool_dep):
                                        generated_tools_format_valid = False
                                        break
                            
                            validation_results["checks"]["tools_dependencies_format"] = generated_tools_format_valid
                            break
        
        # 检查是否所有检查都通过
        required_checks = ["yaml_syntax", "has_agent_section", "has_required_fields", "tools_dependencies_format"]
        all_checks_passed = all(validation_results["checks"][check] for check in required_checks)
        validation_results["valid"] = all_checks_passed
        
        if not all_checks_passed:
            validation_results["error"] = "提示词文件格式不符合要求"
        
        return json.dumps(validation_results, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "valid": False,
            "file_path": file_path,
            "error": f"验证提示词文件时出现错误: {str(e)}",
            "checks": {},
            "sample_content": "prompts/template_prompts/default.yaml"
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


if __name__ == "__main__":
    main()