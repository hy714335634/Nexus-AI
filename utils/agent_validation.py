#!/usr/bin/env python3
"""
Agent验证工具

提供Agent创建前的验证功能，确保所有依赖都存在
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from utils.prompts_manager import get_default_prompt_manager
from utils.agent_factory import get_tool_by_path, get_tool_by_name

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def validate_agent_dependencies(agent_name: str, version: str = "latest") -> Dict[str, Any]:
    """
    验证Agent的所有依赖是否存在
    
    Args:
        agent_name: Agent名称或相对路径
        version: 版本号
        
    Returns:
        Dict[str, Any]: 验证结果
    """
    try:
        # 获取prompt manager实例
        manager = get_default_prompt_manager()
        
        # 获取agent模板
        agent_template = manager.get_agent(agent_name)
        if not agent_template:
            return {
                "valid": False,
                "error": f"Agent模板 '{agent_name}' 不存在"
            }
        
        # 获取指定版本
        agent_version = agent_template.get_version(version)
        if not agent_version:
            return {
                "valid": False,
                "error": f"Agent '{agent_name}' 的版本 '{version}' 不存在"
            }
        
        # 验证工具依赖
        missing_tools = []
        invalid_tools = []
        valid_tools = []
        
        if hasattr(agent_version.metadata, 'tools_dependencies') and agent_version.metadata.tools_dependencies:
            for tool_path in agent_version.metadata.tools_dependencies:
                try:
                    # 尝试通过路径导入工具
                    tool_obj = get_tool_by_path(tool_path)
                    
                    if tool_obj:
                        valid_tools.append(tool_path)
                    else:
                        # 尝试通过名称导入
                        tool_name = tool_path.split('/')[-1]
                        tool_obj = get_tool_by_name(tool_name)
                        
                        if tool_obj:
                            valid_tools.append(tool_path)
                        else:
                            missing_tools.append(tool_path)
                
                except Exception as e:
                    invalid_tools.append({
                        "tool_path": tool_path,
                        "error": str(e)
                    })
        
        # 验证模型支持
        model_issues = []
        if hasattr(agent_version.metadata, 'supported_models') and agent_version.metadata.supported_models:
            # 这里可以添加模型可用性检查
            pass
        
        # 生成验证结果
        is_valid = len(missing_tools) == 0 and len(invalid_tools) == 0
        
        result = {
            "valid": is_valid,
            "agent_name": agent_name,
            "version": version,
            "tools_validation": {
                "total_tools": len(agent_version.metadata.tools_dependencies) if hasattr(agent_version.metadata, 'tools_dependencies') else 0,
                "valid_tools": valid_tools,
                "missing_tools": missing_tools,
                "invalid_tools": invalid_tools
            }
        }
        
        if not is_valid:
            result["recommendations"] = generate_fix_recommendations(missing_tools, invalid_tools)
        
        return result
        
    except Exception as e:
        logger.error(f"验证Agent依赖时出错: {str(e)}")
        return {
            "valid": False,
            "error": f"验证过程中出现错误: {str(e)}"
        }


def generate_fix_recommendations(missing_tools: List[str], invalid_tools: List[Dict[str, Any]]) -> List[str]:
    """
    生成修复建议
    
    Args:
        missing_tools: 缺失的工具列表
        invalid_tools: 无效的工具列表
        
    Returns:
        List[str]: 修复建议列表
    """
    recommendations = []
    
    if missing_tools:
        recommendations.append("缺失的工具:")
        for tool in missing_tools:
            recommendations.append(f"  - {tool}")
            
            # 分析工具路径并提供建议
            if tool.startswith("strands_tools/"):
                recommendations.append(f"    建议: 检查strands-agents-tools包是否正确安装")
            elif tool.startswith("tools/generated_tools/"):
                recommendations.append(f"    建议: 创建工具文件 {tool}")
            elif tool.startswith("tools/system_tools/"):
                recommendations.append(f"    建议: 创建系统工具文件 {tool}")
            elif tool.startswith("tools/template_tools/"):
                recommendations.append(f"    建议: 创建模板工具文件 {tool}")
    
    if invalid_tools:
        recommendations.append("无效的工具:")
        for tool_info in invalid_tools:
            recommendations.append(f"  - {tool_info['tool_path']}: {tool_info['error']}")
    
    return recommendations


def validate_all_agents() -> Dict[str, Any]:
    """
    验证所有Agent的依赖
    
    Returns:
        Dict[str, Any]: 所有Agent的验证结果
    """
    try:
        manager = get_default_prompt_manager()
        path_mapping = manager.list_all_agent_paths()
        
        results = {
            "total_agents": 0,
            "valid_agents": 0,
            "invalid_agents": 0,
            "agent_results": {}
        }
        
        for agent_name, relative_path in path_mapping.items():
            # 跳过相对路径作为key的重复项
            if agent_name == relative_path:
                continue
            
            results["total_agents"] += 1
            validation_result = validate_agent_dependencies(relative_path)
            
            if validation_result["valid"]:
                results["valid_agents"] += 1
            else:
                results["invalid_agents"] += 1
            
            results["agent_results"][relative_path] = validation_result
        
        return results
        
    except Exception as e:
        logger.error(f"验证所有Agent时出错: {str(e)}")
        return {
            "error": f"验证过程中出现错误: {str(e)}"
        }


def fix_agent_dependencies(agent_name: str, version: str = "latest", auto_fix: bool = False) -> Dict[str, Any]:
    """
    修复Agent的依赖问题
    
    Args:
        agent_name: Agent名称或相对路径
        version: 版本号
        auto_fix: 是否自动修复
        
    Returns:
        Dict[str, Any]: 修复结果
    """
    try:
        # 首先验证依赖
        validation_result = validate_agent_dependencies(agent_name, version)
        
        if validation_result["valid"]:
            return {
                "success": True,
                "message": "Agent依赖已经是有效的，无需修复"
            }
        
        if not auto_fix:
            return {
                "success": False,
                "message": "发现依赖问题，但未启用自动修复",
                "validation_result": validation_result
            }
        
        # 自动修复逻辑
        fixed_tools = []
        failed_fixes = []
        
        missing_tools = validation_result["tools_validation"]["missing_tools"]
        
        for tool_path in missing_tools:
            try:
                # 尝试创建缺失的工具文件
                if tool_path.startswith("tools/generated_tools/"):
                    # 创建生成的工具文件
                    success = create_generated_tool_stub(tool_path)
                    if success:
                        fixed_tools.append(tool_path)
                    else:
                        failed_fixes.append(tool_path)
                
                elif tool_path.startswith("tools/system_tools/"):
                    # 创建系统工具文件
                    success = create_system_tool_stub(tool_path)
                    if success:
                        fixed_tools.append(tool_path)
                    else:
                        failed_fixes.append(tool_path)
                
                else:
                    failed_fixes.append(tool_path)
            
            except Exception as e:
                logger.error(f"修复工具 {tool_path} 时出错: {str(e)}")
                failed_fixes.append(tool_path)
        
        return {
            "success": len(failed_fixes) == 0,
            "fixed_tools": fixed_tools,
            "failed_fixes": failed_fixes,
            "message": f"成功修复 {len(fixed_tools)} 个工具，{len(failed_fixes)} 个工具修复失败"
        }
        
    except Exception as e:
        logger.error(f"修复Agent依赖时出错: {str(e)}")
        return {
            "success": False,
            "error": f"修复过程中出现错误: {str(e)}"
        }


def create_generated_tool_stub(tool_path: str) -> bool:
    """
    创建生成工具的存根文件
    
    Args:
        tool_path: 工具路径
        
    Returns:
        bool: 是否成功创建
    """
    try:
        # 解析路径
        parts = tool_path.split('/')
        if len(parts) < 4:
            return False
        
        # 构建文件路径
        file_path = '/'.join(parts[:-1]) + '.py'
        function_name = parts[-1]
        
        # 确保目录存在
        dir_path = os.path.dirname(file_path)
        os.makedirs(dir_path, exist_ok=True)
        
        # 创建存根文件
        stub_content = f'''#!/usr/bin/env python3
"""
自动生成的工具存根文件

这个文件是由Agent验证系统自动生成的存根文件。
请根据实际需求实现具体的工具功能。
"""

from strands import tool


@tool
def {function_name}(*args, **kwargs) -> str:
    """
    工具函数存根
    
    这是一个自动生成的存根函数，请根据实际需求实现具体功能。
    
    Returns:
        str: 工具执行结果
    """
    return "这是一个自动生成的工具存根，请实现具体功能"
'''
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(stub_content)
        
        logger.info(f"成功创建工具存根文件: {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"创建工具存根文件失败: {str(e)}")
        return False


def create_system_tool_stub(tool_path: str) -> bool:
    """
    创建系统工具的存根文件
    
    Args:
        tool_path: 工具路径
        
    Returns:
        bool: 是否成功创建
    """
    # 与create_generated_tool_stub类似的实现
    return create_generated_tool_stub(tool_path)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Agent依赖验证工具')
    parser.add_argument('-a', '--agent', type=str, help='要验证的Agent名称')
    parser.add_argument('-v', '--version', type=str, default='latest', help='Agent版本')
    parser.add_argument('--all', action='store_true', help='验证所有Agent')
    parser.add_argument('--fix', action='store_true', help='自动修复依赖问题')
    
    args = parser.parse_args()
    
    if args.all:
        print("验证所有Agent...")
        results = validate_all_agents()
        print(json.dumps(results, ensure_ascii=False, indent=2))
    
    elif args.agent:
        print(f"验证Agent: {args.agent}")
        
        if args.fix:
            results = fix_agent_dependencies(args.agent, args.version, auto_fix=True)
        else:
            results = validate_agent_dependencies(args.agent, args.version)
        
        print(json.dumps(results, ensure_ascii=False, indent=2))
    
    else:
        parser.print_help()