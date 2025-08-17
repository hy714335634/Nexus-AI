#!/usr/bin/env python3
"""
提示词模板提供工具

为Agent提供标准的提示词模板内容
"""

import sys
import os
from typing import Optional

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from strands import tool
from utils.config_loader import get_config


@tool
def get_prompt_template() -> str:
    """
    获取标准提示词模板内容
    
    Returns:
        str: prompts/template_prompts/template.yaml 文件的完整内容
    """
    try:
        # 从配置文件获取路径
        config = get_config()
        strands_config = config.get_strands_config()
        prompt_template_path = strands_config.get('prompt_template_path', 'prompts/template_prompts')
        template_path = os.path.join(project_root, prompt_template_path, "template.yaml")
        
        if not os.path.exists(template_path):
            return "错误：提示词模板文件不存在"
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return content
        
    except Exception as e:
        return f"获取提示词模板时出现错误: {str(e)}"


@tool
def get_prompt_template_info() -> str:
    """
    获取提示词模板的基本信息（不包含完整内容）
    
    Returns:
        str: 模板的基本信息，包括路径、大小等
    """
    try:
        # 从配置文件获取路径
        config = get_config()
        strands_config = config.get_strands_config()
        prompt_template_path = strands_config.get('prompt_template_path', 'prompts/template_prompts')
        template_path = os.path.join(project_root, prompt_template_path, "template.yaml")
        
        if not os.path.exists(template_path):
            return "错误：提示词模板文件不存在"
        
        # 获取文件信息
        file_size = os.path.getsize(template_path)
        file_stat = os.stat(template_path)
        
        import time
        modified_time = time.ctime(file_stat.st_mtime)
        
        # 读取文件行数
        with open(template_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            line_count = len(lines)
        
        info = f"""提示词模板文件信息：
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
def validate_prompt_template() -> str:
    """
    验证提示词模板文件的格式是否正确
    
    Returns:
        str: 验证结果信息
    """
    try:
        # 从配置文件获取路径
        config = get_config()
        strands_config = config.get_strands_config()
        prompt_template_path = strands_config.get('prompt_template_path', 'prompts/template_prompts')
        template_path = os.path.join(project_root, prompt_template_path, "template.yaml")
        
        if not os.path.exists(template_path):
            return "错误：提示词模板文件不存在"
        
        # 尝试解析YAML文件
        import yaml
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = yaml.safe_load(f)
        
        # 基本结构验证
        validation_results = {
            "valid": True,
            "checks": {
                "file_exists": True,
                "yaml_parseable": True,
                "has_agent_section": "agent" in content if content else False,
                "has_name": False,
                "has_description": False,
                "has_versions": False
            }
        }
        
        if content and "agent" in content:
            agent_section = content["agent"]
            validation_results["checks"]["has_name"] = "name" in agent_section
            validation_results["checks"]["has_description"] = "description" in agent_section
            validation_results["checks"]["has_versions"] = "versions" in agent_section
        
        # 检查是否所有基本检查都通过
        all_checks_passed = all(validation_results["checks"].values())
        validation_results["valid"] = all_checks_passed
        
        import json
        return json.dumps(validation_results, ensure_ascii=False, indent=2)
        
    except yaml.YAMLError as e:
        return f"YAML格式错误: {str(e)}"
    except Exception as e:
        return f"验证提示词模板时出现错误: {str(e)}"


@tool
def get_template_structure() -> str:
    """
    获取提示词模板的结构概览
    
    Returns:
        str: 模板结构的简要说明
    """
    try:
        # 从配置文件获取路径
        config = get_config()
        strands_config = config.get_strands_config()
        prompt_template_path = strands_config.get('prompt_template_path', 'prompts/template_prompts')
        template_path = os.path.join(project_root, prompt_template_path, "template.yaml")
        
        if not os.path.exists(template_path):
            return "错误：提示词模板文件不存在"
        
        import yaml
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = yaml.safe_load(f)
        
        if not content:
            return "错误：模板文件内容为空"
        
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
        
        structure_lines = get_structure(content)
        return "\n".join(structure_lines)
        
    except Exception as e:
        return f"获取模板结构时出现错误: {str(e)}"


# 主函数，用于直接调用测试
def main():
    """主函数，用于测试提示词模板提供工具"""
    print("=== 提示词模板提供工具测试 ===")
    
    print("\n1. 获取模板信息:")
    print(get_prompt_template_info())
    
    print("\n2. 验证模板格式:")
    print(validate_prompt_template())
    
    print("\n3. 获取模板结构:")
    print(get_template_structure())
    
    print("\n4. 获取完整模板内容:")
    content = get_prompt_template()
    print(f"内容长度: {len(content)} 字符")
    print("前200个字符:")
    print(content[:200] + "..." if len(content) > 200 else content)


if __name__ == "__main__":
    main()