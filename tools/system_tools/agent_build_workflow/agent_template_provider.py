#!/usr/bin/env python3
# agent_template_provider/get_all_templates - 获取所有可用的Agent模板信息，包含名称、描述、依赖、路径和标签
# agent_template_provider/search_templates_by_tags - 根据标签搜索模板，支持多标签匹配查询
# agent_template_provider/search_templates_by_description - 根据描述关键词搜索模板，支持名称和描述内容匹配
# agent_template_provider/get_template_by_id - 根据模板ID获取特定模板信息，返回完整的模板配置
# agent_template_provider/get_template_content - 获取模板文件的完整内容，用于Agent代码生成
# agent_template_provider/get_available_tags - 获取所有可用的标签列表，用于模板分类和筛选
"""
Agent模板管理工具

提供Agent模板的查询、筛选和管理功能
"""

import sys
import os
import yaml
import ast
import json
from typing import Dict, List, Any, Optional, Union
from strands import tool


def _get_prompt_templates(template_info: Dict[str, Any]) -> Union[str, List[str]]:
    """
    获取模板的prompt模板信息，支持单Agent和多Agent两种情况
    
    Args:
        template_info: 模板信息字典
        
    Returns:
        如果是单Agent，返回字符串；如果是多Agent，返回列表
    """
    # 优先检查prompt_templates（多Agent）
    if "prompt_templates" in template_info:
        return template_info["prompt_templates"]
    # 兼容prompt_template（单Agent）
    elif "prompt_template" in template_info:
        return template_info["prompt_template"]
    else:
        return ""

@tool
def get_all_templates() -> str:
    """
    获取所有可用的Agent模板信息
    
    Returns:
        str: JSON格式的所有模板信息
    """
    try:
        config_path = os.path.join("agents/template_agents", "agent_templates_config.yaml")
        
        if not os.path.exists(config_path):
            return "错误：模板配置文件不存在"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        templates = config.get('templates', {})
        
        # 格式化输出
        result = []
        for template_id, template_info in templates.items():
            prompt_templates = _get_prompt_templates(template_info)
            # 判断是单Agent还是多Agent
            is_multi_agent = isinstance(prompt_templates, list)
            
            result.append({
                "id": template_id,
                "name": template_info.get("name", ""),
                "description": template_info.get("description", ""),
                "agent_dependencies": template_info.get("agent_dependencies", []),
                "tools_dependencies": template_info.get("tools_dependencies", []),
                "path": template_info.get("path", ""),
                "prompt_template": prompt_templates if not is_multi_agent else None,  # 单Agent使用prompt_template
                "prompt_templates": prompt_templates if is_multi_agent else None,  # 多Agent使用prompt_templates
                "is_multi_agent": is_multi_agent,
                "tags": template_info.get("tags", [])
            })
        
        import json
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"获取模板信息时出现错误: {str(e)}"


@tool
def search_templates_by_tags(tags: List[str]) -> str:
    """
    根据标签搜索模板
    
    Args:
        tags (List[str]): 要搜索的标签列表
        
    Returns:
        str: JSON格式的匹配模板信息
    """
    try:
        config_path = os.path.join("agents/template_agents", "agent_templates_config.yaml")
        
        if not os.path.exists(config_path):
            return "错误：模板配置文件不存在"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        templates = config.get('templates', {})
        
        # 搜索匹配的模板
        matched_templates = []
        for template_id, template_info in templates.items():
            template_tags = template_info.get("tags", [])
            
            # 检查是否有任何标签匹配
            if any(tag in template_tags for tag in tags):
                prompt_templates = _get_prompt_templates(template_info)
                is_multi_agent = isinstance(prompt_templates, list)
                
                matched_templates.append({
                    "id": template_id,
                    "name": template_info.get("name", ""),
                    "description": template_info.get("description", ""),
                    "agent_dependencies": template_info.get("agent_dependencies", []),
                    "tools_dependencies": template_info.get("tools_dependencies", []),
                    "path": template_info.get("path", ""),
                    "prompt_template": prompt_templates if not is_multi_agent else None,
                    "prompt_templates": prompt_templates if is_multi_agent else None,
                    "is_multi_agent": is_multi_agent,
                    "tags": template_info.get("tags", [])
                })
        
        import json
        return json.dumps(matched_templates, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"搜索模板时出现错误: {str(e)}"


@tool
def search_templates_by_description(keywords: List[str]) -> str:
    """
    根据描述关键词搜索模板
    
    Args:
        keywords (List[str]): 要搜索的关键词列表
        
    Returns:
        str: JSON格式的匹配模板信息
    """
    try:
        config_path = os.path.join("agents/template_agents", "agent_templates_config.yaml")
        
        if not os.path.exists(config_path):
            return "错误：模板配置文件不存在"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        templates = config.get('templates', {})
        
        # 搜索匹配的模板
        matched_templates = []
        for template_id, template_info in templates.items():
            description = template_info.get("description", "").lower()
            name = template_info.get("name", "").lower()
            
            # 检查描述或名称中是否包含任何关键词
            if any(keyword.lower() in description or keyword.lower() in name for keyword in keywords):
                prompt_templates = _get_prompt_templates(template_info)
                is_multi_agent = isinstance(prompt_templates, list)
                
                matched_templates.append({
                    "id": template_id,
                    "name": template_info.get("name", ""),
                    "description": template_info.get("description", ""),
                    "agent_dependencies": template_info.get("agent_dependencies", []),
                    "tools_dependencies": template_info.get("tools_dependencies", []),
                    "path": template_info.get("path", ""),
                    "prompt_template": prompt_templates if not is_multi_agent else None,
                    "prompt_templates": prompt_templates if is_multi_agent else None,
                    "is_multi_agent": is_multi_agent,
                    "tags": template_info.get("tags", [])
                })
        
        import json
        return json.dumps(matched_templates, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"搜索模板时出现错误: {str(e)}"


@tool
def get_template_by_id(template_id: str) -> str:
    """
    根据模板ID获取特定模板信息
    
    Args:
        template_id (str): 模板ID
        
    Returns:
        str: JSON格式的模板信息
    """
    try:
        config_path = os.path.join("agents/template_agents", "agent_templates_config.yaml")
        
        if not os.path.exists(config_path):
            return "错误：模板配置文件不存在"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        templates = config.get('templates', {})
        
        if template_id not in templates:
            return f"错误：未找到ID为 '{template_id}' 的模板"
        
        template_info = templates[template_id]
        prompt_templates = _get_prompt_templates(template_info)
        is_multi_agent = isinstance(prompt_templates, list)
        
        result = {
            "id": template_id,
            "name": template_info.get("name", ""),
            "description": template_info.get("description", ""),
            "agent_dependencies": template_info.get("agent_dependencies", []),
            "tools_dependencies": template_info.get("tools_dependencies", []),
            "path": template_info.get("path", ""),
            "prompt_template": prompt_templates if not is_multi_agent else None,
            "prompt_templates": prompt_templates if is_multi_agent else None,
            "is_multi_agent": is_multi_agent,
            "tags": template_info.get("tags", [])
        }
        
        import json
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"获取模板信息时出现错误: {str(e)}"


@tool
def get_template_content(template_id: str) -> str:
    """
    获取模板文件的内容
    
    Args:
        template_id (str): 模板ID
        
    Returns:
        str: 模板文件的内容
    """
    try:
        config_path = os.path.join("agents/template_agents", "agent_templates_config.yaml")
        
        if not os.path.exists(config_path):
            return "错误：模板配置文件不存在"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        templates = config.get('templates', {})
        
        if template_id not in templates:
            return f"错误：未找到ID为 '{template_id}' 的模板"
        
        template_path = templates[template_id].get("path", "")
        full_path = os.path.join(template_path)
        
        if not os.path.exists(full_path):
            return f"错误：模板文件不存在: {full_path}"
        
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return content
        
    except Exception as e:
        return f"获取模板内容时出现错误: {str(e)}"


@tool
def get_available_tags() -> str:
    """
    获取所有可用的标签
    
    Returns:
        str: JSON格式的标签列表
    """
    try:
        config_path = os.path.join("agents/template_agents", "agent_templates_config.yaml")
        
        if not os.path.exists(config_path):
            return "错误：模板配置文件不存在"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        templates = config.get('templates', {})
        
        # 收集所有标签
        all_tags = set()
        for template_info in templates.values():
            tags = template_info.get("tags", [])
            all_tags.update(tags)
        
        import json
        return json.dumps(list(all_tags), ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"获取标签时出现错误: {str(e)}"

def validate_agent_file(file_path: str) -> str:
    """
    验证Agent文件的格式和语法，提供详细的错误分类和具体原因
    
    Args:
        file_path: Agent文件路径
    
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
                "has_agent_factory_import": False,
                "has_create_agent_import": False
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
                    "参考示例文件: agents/template_agents/single_agent/default_agent.py"
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
        
        # 4. 检查必要的导入
        has_agent_factory_import = "from nexus_utils.agent_factory import" in content
        has_create_agent_import = "create_agent_from_prompt_template" in content
        
        validation_results["checks"]["has_agent_factory_import"] = has_agent_factory_import
        validation_results["checks"]["has_create_agent_import"] = has_create_agent_import
        
        # 检查是否所有检查都通过
        missing_imports = []
        if not has_agent_factory_import:
            missing_imports.append("nexus_utils.agent_factory")
        if not has_create_agent_import:
            missing_imports.append("create_agent_from_prompt_template")
        
        if missing_imports:
            validation_results.update({
                "valid": False,
                "error_category": "MISSING_REQUIRED_IMPORTS",
                "error_details": [f"缺少必要的导入: {', '.join(missing_imports)}"],
                "suggestions": [
                    "添加 'from nexus_utils.agent_factory import create_agent_from_prompt_template' 导入语句",
                    "确保使用 create_agent_from_prompt_template 函数创建代理",
                    "参考示例文件了解正确的导入格式"
                ]
            })
            return json.dumps(validation_results, ensure_ascii=False, indent=2)
        
        # 5. 添加建议
        validation_results["suggestions"] = [
            "Agent文件验证通过",
            "建议定期检查代理函数的有效性",
            "建议使用类型注解提高代码质量",
            "建议添加适当的错误处理"
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
    """主函数，用于测试模板管理工具"""
    print("=== Agent模板管理工具测试 ===")
    
    print("\n1. 获取所有模板:")
    print(get_all_templates())
    
    print("\n2. 根据标签搜索模板 (single_agent):")
    print(search_templates_by_tags(["single_agent"]))
    
    print("\n3. 根据关键词搜索模板 (MCP):")
    print(search_templates_by_description(["MCP"]))
    
    print("\n4. 获取特定模板信息:")
    print(get_template_by_id("single_agent_with_local_tool"))
    
    print("\n5. 获取可用标签:")
    print(get_available_tags())

    print("\n6. 验证Agent文件:")
    print(validate_agent_file("agents/template_agents/single_agent/default_agent.py"))

if __name__ == "__main__":
    main() 