#!/usr/bin/env python3
"""
工具验证器

为Agent Build Workflow提供工具存在性验证功能
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from strands import tool

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@tool
def validate_tool_path(tool_path: str) -> str:
    """
    验证工具路径是否存在
    
    Args:
        tool_path: 工具路径，如 "strands_tools/calculator" 或 "tools/system_tools/project_manager/get_project_status"
        
    Returns:
        str: JSON格式的验证结果
    """
    try:
        # 导入验证函数
        from nexus_utils.agent_factory import get_tool_by_path, get_tool_by_name
        
        result = {
            "tool_path": tool_path,
            "exists": False,
            "validation_method": None,
            "error": None
        }
        
        # 尝试通过路径导入工具
        tool_obj = get_tool_by_path(tool_path)
        
        if tool_obj:
            result["exists"] = True
            result["validation_method"] = "path_import"
        else:
            # 尝试通过名称导入
            tool_name = tool_path.split('/')[-1]
            tool_obj = get_tool_by_name(tool_name)
            
            if tool_obj:
                result["exists"] = True
                result["validation_method"] = "name_import"
            else:
                result["error"] = f"工具不存在: {tool_path}"
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"验证工具路径时出错: {str(e)}")
        return json.dumps({
            "tool_path": tool_path,
            "exists": False,
            "validation_method": None,
            "error": f"验证过程中出现错误: {str(e)}"
        }, ensure_ascii=False)


@tool
def validate_tool_list(tool_paths: List[str]) -> str:
    """
    批量验证工具路径列表
    
    Args:
        tool_paths: 工具路径列表
        
    Returns:
        str: JSON格式的批量验证结果
    """
    try:
        results = {
            "total_tools": len(tool_paths),
            "valid_tools": 0,
            "invalid_tools": 0,
            "tool_results": [],
            "summary": {
                "all_valid": True,
                "missing_tools": [],
                "valid_tools": []
            }
        }
        
        for tool_path in tool_paths:
            # 验证单个工具
            validation_result_str = validate_tool_path(tool_path)
            validation_result = json.loads(validation_result_str)
            
            results["tool_results"].append(validation_result)
            
            if validation_result["exists"]:
                results["valid_tools"] += 1
                results["summary"]["valid_tools"].append(tool_path)
            else:
                results["invalid_tools"] += 1
                results["summary"]["missing_tools"].append(tool_path)
                results["summary"]["all_valid"] = False
        
        return json.dumps(results, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"批量验证工具时出错: {str(e)}")
        return json.dumps({
            "error": f"批量验证工具时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def suggest_tool_alternatives(tool_path: str) -> str:
    """
    为无效的工具路径建议替代方案
    
    Args:
        tool_path: 无效的工具路径
        
    Returns:
        str: JSON格式的建议结果
    """
    try:
        from tools.system_tools.agent_build_workflow.tool_template_provider import search_tools_by_name, list_all_tools
        
        # 提取工具名称
        tool_name = tool_path.split('/')[-1]
        
        suggestions = {
            "original_path": tool_path,
            "tool_name": tool_name,
            "suggestions": [],
            "similar_tools": [],
            "available_categories": []
        }
        
        # 搜索相似名称的工具
        try:
            search_result = search_tools_by_name(tool_name)
            search_data = json.loads(search_result)
            
            if search_data.get("total_matches", 0) > 0:
                for tool_info in search_data["matching_tools"]:
                    if tool_info["type"] == "builtin":
                        suggested_path = f"strands_tools/{tool_info['name']}"
                    else:
                        file_path = tool_info.get("file_path", "")
                        if file_path:
                            # 构建正确的工具路径
                            module_path = file_path.replace("/", ".").replace(".py", "")
                            suggested_path = f"{module_path}/{tool_info['name']}"
                        else:
                            suggested_path = f"unknown_path/{tool_info['name']}"
                    
                    suggestions["suggestions"].append({
                        "name": tool_info["name"],
                        "type": tool_info["type"],
                        "suggested_path": suggested_path,
                        "description": tool_info.get("description", "")
                    })
        
        except Exception as e:
            logger.warning(f"搜索工具时出错: {str(e)}")
        
        # 获取所有可用工具类别
        try:
            all_tools_result = list_all_tools()
            all_tools_data = json.loads(all_tools_result)
            
            # 提取类别信息
            if "system_tools" in all_tools_data:
                suggestions["available_categories"].append("system_tools")
            if "template_tools" in all_tools_data:
                suggestions["available_categories"].append("template_tools")
            if "generated_tools" in all_tools_data:
                suggestions["available_categories"].append("generated_tools")
        
        except Exception as e:
            logger.warning(f"获取工具类别时出错: {str(e)}")
        
        return json.dumps(suggestions, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"建议工具替代方案时出错: {str(e)}")
        return json.dumps({
            "original_path": tool_path,
            "error": f"建议工具替代方案时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def get_correct_tool_paths(project_name: str) -> str:
    """
    获取项目的正确工具路径格式
    
    Args:
        project_name: 项目名称
        
    Returns:
        str: JSON格式的正确路径示例
    """
    try:
        path_examples = {
            "project_name": project_name,
            "path_formats": {
                "strands_tools": {
                    "format": "strands_tools/{tool_name}",
                    "examples": [
                        "strands_tools/calculator",
                        "strands_tools/file_read",
                        "strands_tools/python_repl",
                        "strands_tools/current_time"
                    ]
                },
                "system_tools": {
                    "format": "tools/system_tools/{category}/{script_name}/{function_name}",
                    "examples": [
                        "tools/system_tools/agent_build_workflow/project_manager/get_project_status",
                        "tools/system_tools/agent_build_workflow/tool_template_provider/list_all_tools"
                    ]
                },
                "generated_tools": {
                    "format": f"tools/generated_tools/{project_name}/{{script_name}}/{{function_name}}",
                    "examples": [
                        f"tools/generated_tools/{project_name}/data_processor/process_data",
                        f"tools/generated_tools/{project_name}/api_client/make_request"
                    ]
                }
            },
            "validation_tips": [
                "使用validate_tool_path验证每个工具路径",
                "对于generated_tools，确保脚本文件已经存在",
                "对于system_tools，检查tools/system_tools目录结构",
                "对于strands_tools，使用标准工具名称"
            ]
        }
        
        return json.dumps(path_examples, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"获取正确工具路径时出错: {str(e)}")
        return json.dumps({
            "project_name": project_name,
            "error": f"获取正确工具路径时出错: {str(e)}"
        }, ensure_ascii=False)


if __name__ == "__main__":
    # 测试工具验证功能
    test_tools = [
        "strands_tools/calculator",
        "strands_tools/file_read",
        "tools/system_tools/agent_build_workflow/project_manager/get_project_status",
        "invalid_tool_path"
    ]
    
    print("测试工具验证功能:")
    result = validate_tool_list(test_tools)
    print(result)