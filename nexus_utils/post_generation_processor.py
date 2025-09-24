#!/usr/bin/env python3
"""
Agent生成后处理器

在Agent Build Workflow生成Agent后，自动进行验证和修复
"""

import os
import json
import logging
import shutil
from typing import Dict, List, Any, Optional
from nexus_utils.agent_validation import validate_agent_dependencies, fix_agent_dependencies
from nexus_utils.safe_agent_factory import create_validated_agent

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def process_generated_agent(
    agent_project_path: str,
    auto_fix: bool = True,
    create_backup: bool = True
) -> Dict[str, Any]:
    """
    处理生成的Agent项目
    
    Args:
        agent_project_path: Agent项目路径
        auto_fix: 是否自动修复问题
        create_backup: 是否创建备份
        
    Returns:
        Dict[str, Any]: 处理结果
    """
    try:
        logger.info(f"开始处理Agent项目: {agent_project_path}")
        
        # 检查项目路径是否存在
        if not os.path.exists(agent_project_path):
            return {
                "success": False,
                "error": f"Agent项目路径不存在: {agent_project_path}"
            }
        
        # 查找Agent相关文件
        agent_files = find_agent_files(agent_project_path)
        
        if not agent_files:
            return {
                "success": False,
                "error": f"在项目路径中未找到Agent文件: {agent_project_path}"
            }
        
        results = {
            "success": True,
            "project_path": agent_project_path,
            "processed_files": [],
            "issues_found": [],
            "fixes_applied": []
        }
        
        # 处理每个Agent文件
        for agent_file in agent_files:
            logger.info(f"处理Agent文件: {agent_file}")
            
            # 创建备份
            if create_backup:
                backup_path = agent_file + ".backup"
                shutil.copy2(agent_file, backup_path)
                logger.info(f"创建备份: {backup_path}")
            
            # 分析和修复Agent文件
            file_result = process_agent_file(agent_file, auto_fix)
            
            results["processed_files"].append({
                "file_path": agent_file,
                "result": file_result
            })
            
            if not file_result["success"]:
                results["success"] = False
                results["issues_found"].extend(file_result.get("issues", []))
            
            if file_result.get("fixes_applied"):
                results["fixes_applied"].extend(file_result["fixes_applied"])
        
        # 验证对应的prompt文件
        prompt_validation_result = validate_prompt_files(agent_project_path)
        results["prompt_validation"] = prompt_validation_result
        
        return results
        
    except Exception as e:
        logger.error(f"处理Agent项目时出错: {str(e)}")
        return {
            "success": False,
            "error": f"处理Agent项目时出错: {str(e)}"
        }


def find_agent_files(project_path: str) -> List[str]:
    """
    在项目路径中查找Agent文件
    
    Args:
        project_path: 项目路径
        
    Returns:
        List[str]: Agent文件路径列表
    """
    agent_files = []
    
    for root, dirs, files in os.walk(project_path):
        for file in files:
            if file.endswith('.py') and 'agent' in file.lower():
                file_path = os.path.join(root, file)
                
                # 检查文件内容是否包含Agent相关代码
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'create_agent_from_prompt_template' in content or 'Agent' in content:
                            agent_files.append(file_path)
                except Exception as e:
                    logger.warning(f"读取文件时出错 {file_path}: {str(e)}")
    
    return agent_files


def process_agent_file(agent_file_path: str, auto_fix: bool = True) -> Dict[str, Any]:
    """
    处理单个Agent文件
    
    Args:
        agent_file_path: Agent文件路径
        auto_fix: 是否自动修复
        
    Returns:
        Dict[str, Any]: 处理结果
    """
    try:
        logger.info(f"分析Agent文件: {agent_file_path}")
        
        # 读取文件内容
        with open(agent_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        issues = []
        fixes_applied = []
        
        # 检查常见问题
        
        # 1. 检查是否使用了不存在的参数
        if 'prompt_template_path=' in content:
            issues.append({
                "type": "invalid_parameter",
                "description": "使用了不存在的参数 'prompt_template_path'",
                "line": find_line_number(content, 'prompt_template_path=')
            })
            
            if auto_fix:
                # 移除prompt_template_path参数
                fixed_content = fix_prompt_template_path_parameter(content)
                if fixed_content != content:
                    content = fixed_content
                    fixes_applied.append("移除了无效的prompt_template_path参数")
        
        # 2. 检查Agent名称是否正确
        agent_name_issues = check_agent_name_format(content)
        if agent_name_issues:
            issues.extend(agent_name_issues)
            
            if auto_fix:
                fixed_content = fix_agent_name_format(content)
                if fixed_content != content:
                    content = fixed_content
                    fixes_applied.append("修复了Agent名称格式")
        
        # 3. 检查模型配置
        model_issues = check_model_configuration(content)
        if model_issues:
            issues.extend(model_issues)
            
            if auto_fix:
                fixed_content = fix_model_configuration(content)
                if fixed_content != content:
                    content = fixed_content
                    fixes_applied.append("修复了模型配置")
        
        # 如果有修复，写回文件
        if fixes_applied:
            with open(agent_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"已应用修复到文件: {agent_file_path}")
        
        return {
            "success": len(issues) == 0 or len(fixes_applied) > 0,
            "issues": issues,
            "fixes_applied": fixes_applied
        }
        
    except Exception as e:
        logger.error(f"处理Agent文件时出错: {str(e)}")
        return {
            "success": False,
            "error": f"处理Agent文件时出错: {str(e)}"
        }


def validate_prompt_files(project_path: str) -> Dict[str, Any]:
    """
    验证对应的prompt文件是否存在
    
    Args:
        project_path: 项目路径
        
    Returns:
        Dict[str, Any]: 验证结果
    """
    try:
        # 从项目路径推断prompt文件路径
        project_name = os.path.basename(project_path)
        
        # 检查generated_agents_prompts目录
        prompt_path = f"prompts/generated_agents_prompts/{project_name}"
        
        if os.path.exists(prompt_path):
            # 查找YAML文件
            yaml_files = []
            for file in os.listdir(prompt_path):
                if file.endswith('.yaml') or file.endswith('.yml'):
                    yaml_files.append(os.path.join(prompt_path, file))
            
            if yaml_files:
                # 验证每个YAML文件
                validation_results = []
                for yaml_file in yaml_files:
                    agent_name = f"generated_agents_prompts/{project_name}/{os.path.splitext(os.path.basename(yaml_file))[0]}"
                    validation_result = validate_agent_dependencies(agent_name)
                    validation_results.append({
                        "yaml_file": yaml_file,
                        "agent_name": agent_name,
                        "validation": validation_result
                    })
                
                return {
                    "prompt_files_exist": True,
                    "yaml_files": yaml_files,
                    "validations": validation_results
                }
            else:
                return {
                    "prompt_files_exist": False,
                    "error": f"在 {prompt_path} 中未找到YAML文件"
                }
        else:
            return {
                "prompt_files_exist": False,
                "error": f"Prompt目录不存在: {prompt_path}"
            }
        
    except Exception as e:
        logger.error(f"验证prompt文件时出错: {str(e)}")
        return {
            "prompt_files_exist": False,
            "error": f"验证prompt文件时出错: {str(e)}"
        }


# 辅助函数
def find_line_number(content: str, search_text: str) -> int:
    """查找文本在内容中的行号"""
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if search_text in line:
            return i + 1
    return -1


def fix_prompt_template_path_parameter(content: str) -> str:
    """修复prompt_template_path参数"""
    import re
    
    # 移除prompt_template_path参数
    pattern = r',?\s*prompt_template_path\s*=\s*["\'][^"\']*["\']'
    fixed_content = re.sub(pattern, '', content)
    
    return fixed_content


def check_agent_name_format(content: str) -> List[Dict[str, Any]]:
    """检查Agent名称格式"""
    issues = []
    
    # 检查是否使用了正确的路径格式
    import re
    
    # 查找agent_name参数
    pattern = r'agent_name\s*=\s*["\']([^"\']*)["\']'
    matches = re.findall(pattern, content)
    
    for agent_name in matches:
        if not agent_name.startswith(('system_agents_prompts/', 'template_prompts/', 'generated_agents_prompts/')):
            issues.append({
                "type": "invalid_agent_name",
                "description": f"Agent名称格式不正确: {agent_name}",
                "suggestion": f"应该使用相对路径格式，如 'generated_agents_prompts/project_name/agent_name'"
            })
    
    return issues


def fix_agent_name_format(content: str) -> str:
    """修复Agent名称格式"""
    # 这里可以实现自动修复逻辑
    # 目前只返回原内容，具体修复逻辑需要根据实际情况实现
    return content


def check_model_configuration(content: str) -> List[Dict[str, Any]]:
    """检查模型配置"""
    issues = []
    
    # 检查是否使用了硬编码的模型ID
    import re
    
    pattern = r'model_id\s*[:\s]*["\']([^"\']*)["\']'
    matches = re.findall(pattern, content)
    
    for model_id in matches:
        if model_id.startswith('anthropic.') or model_id.startswith('us.anthropic.'):
            issues.append({
                "type": "hardcoded_model_id",
                "description": f"使用了硬编码的模型ID: {model_id}",
                "suggestion": "建议使用 'default' 或配置文件中的模型ID"
            })
    
    return issues


def fix_model_configuration(content: str) -> str:
    """修复模型配置"""
    import re
    
    # 将硬编码的模型ID替换为"default"
    pattern = r'(model_id\s*[:\s]*)["\'][^"\']*anthropic[^"\']*["\']'
    fixed_content = re.sub(pattern, r'\1"default"', content)
    
    return fixed_content


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Agent生成后处理器')
    parser.add_argument('-p', '--project', type=str, required=True, help='Agent项目路径')
    parser.add_argument('--no-auto-fix', action='store_true', help='禁用自动修复')
    parser.add_argument('--no-backup', action='store_true', help='不创建备份')
    
    args = parser.parse_args()
    
    print(f"处理Agent项目: {args.project}")
    
    result = process_generated_agent(
        agent_project_path=args.project,
        auto_fix=not args.no_auto_fix,
        create_backup=not args.no_backup
    )
    
    print(json.dumps(result, ensure_ascii=False, indent=2))