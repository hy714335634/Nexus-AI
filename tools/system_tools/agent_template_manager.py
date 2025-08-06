#!/usr/bin/env python3
"""
Agent模板管理工具

提供Agent模板的查询、筛选和管理功能
"""

import sys
import os
import yaml
from typing import Dict, List, Any, Optional

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from strands import tool


@tool
def get_all_templates() -> str:
    """
    获取所有可用的Agent模板信息
    
    Returns:
        str: JSON格式的所有模板信息
    """
    try:
        config_path = os.path.join(project_root, "config", "agent_templates_config.yaml")
        
        if not os.path.exists(config_path):
            return "错误：模板配置文件不存在"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        templates = config.get('templates', {})
        
        # 格式化输出
        result = []
        for template_id, template_info in templates.items():
            result.append({
                "id": template_id,
                "name": template_info.get("name", ""),
                "description": template_info.get("description", ""),
                "dependencies": template_info.get("dependencies", []),
                "path": template_info.get("path", ""),
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
        config_path = os.path.join(project_root, "config", "agent_templates_config.yaml")
        
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
                matched_templates.append({
                    "id": template_id,
                    "name": template_info.get("name", ""),
                    "description": template_info.get("description", ""),
                    "dependencies": template_info.get("dependencies", []),
                    "path": template_info.get("path", ""),
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
        config_path = os.path.join(project_root, "config", "agent_templates_config.yaml")
        
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
                matched_templates.append({
                    "id": template_id,
                    "name": template_info.get("name", ""),
                    "description": template_info.get("description", ""),
                    "dependencies": template_info.get("dependencies", []),
                    "path": template_info.get("path", ""),
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
        config_path = os.path.join(project_root, "config", "agent_templates_config.yaml")
        
        if not os.path.exists(config_path):
            return "错误：模板配置文件不存在"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        templates = config.get('templates', {})
        
        if template_id not in templates:
            return f"错误：未找到ID为 '{template_id}' 的模板"
        
        template_info = templates[template_id]
        result = {
            "id": template_id,
            "name": template_info.get("name", ""),
            "description": template_info.get("description", ""),
            "dependencies": template_info.get("dependencies", []),
            "path": template_info.get("path", ""),
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
        config_path = os.path.join(project_root, "config", "agent_templates_config.yaml")
        
        if not os.path.exists(config_path):
            return "错误：模板配置文件不存在"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        templates = config.get('templates', {})
        
        if template_id not in templates:
            return f"错误：未找到ID为 '{template_id}' 的模板"
        
        template_path = templates[template_id].get("path", "")
        full_path = os.path.join(project_root, template_path)
        
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
        config_path = os.path.join(project_root, "config", "agent_templates_config.yaml")
        
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

if __name__ == "__main__":
    main() 