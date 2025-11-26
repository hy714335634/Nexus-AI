#!/usr/bin/env python3
"""
工具验证器

为Agent Build Workflow提供工具存在性验证功能
"""

import os
import json
import logging
import re
import urllib.request
import urllib.error
import urllib.parse
import difflib
from typing import Dict, List, Any, Optional
try:
    from importlib.metadata import metadata, PackageNotFoundError
except ImportError:
    # Python < 3.8 兼容
    from importlib_metadata import metadata, PackageNotFoundError
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




@tool
def verify_library_dependencies(library_name: str, library_version: str = "latest") -> str:
    """
    验证 Python 库是否支持项目要求的 Python 版本
    
    从 pyproject.toml 中读取项目要求的 Python 版本，然后查询 PyPI API
    检查指定库是否支持该 Python 版本。
    
    Args:
        library_name: Python 库名称，如 "requests", "pandas" 等
        library_version: 库的版本号，默认为 "latest"（最新版本）
        
    Returns:
        str: JSON格式的验证结果，包含：
            - project_python_version: 项目要求的 Python 版本
            - library_name: 库名称
            - library_version: 库版本
            - is_compatible: 是否兼容
            - library_python_requirement: 库要求的 Python 版本
            - error: 错误信息（如果有）
    """
    try:
        # 1. 优先从已安装包的元数据中获取 Python 版本要求（不依赖文件路径）
        project_python_version = None
        
        try:
            # 尝试从已安装的 nexus-ai 包元数据中读取（不依赖文件路径）
            pkg_metadata = metadata("nexus-ai")
            # 从元数据中提取 Requires-Python（字段名大小写敏感，标准格式为 "Requires-Python"）
            requires_python = pkg_metadata.get("Requires-Python", "")
            if requires_python:
                project_python_version = requires_python.strip()
                # logger.info(f"从包元数据中获取 Python 版本要求: {project_python_version}")
        except PackageNotFoundError:
            # 如果包未安装，回退到读取 pyproject.toml 文件
            # logger.info("包未安装，尝试从 pyproject.toml 文件读取")
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = current_dir
            # 向上查找直到找到 pyproject.toml 或到达文件系统根目录
            for _ in range(10):  # 最多向上查找10级
                pyproject_path = os.path.join(project_root, "pyproject.toml")
                if os.path.exists(pyproject_path):
                    break
                parent_dir = os.path.dirname(project_root)
                if parent_dir == project_root:  # 已到达根目录
                    break
                project_root = parent_dir
            else:
                # 如果循环结束仍未找到，尝试当前工作目录
                pyproject_path = os.path.join(os.getcwd(), "pyproject.toml")
            
            if os.path.exists(pyproject_path):
                with open(pyproject_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # 使用正则表达式提取 requires-python
                    match = re.search(r'requires-python\s*=\s*["\']([^"\']+)["\']', content)
                    if match:
                        project_python_version = match.group(1)
                        logger.info(f"从 pyproject.toml 文件中获取 Python 版本要求: {project_python_version}")
        
        if not project_python_version:
            return json.dumps({
                "error": "无法获取项目 Python 版本要求（包未安装且无法找到 pyproject.toml 文件）",
                "library_name": library_name,
                "library_version": library_version,
                "suggestion": "请确保项目已安装（pip install -e .）或 pyproject.toml 文件存在"
            }, ensure_ascii=False)
        
        # 2. 查询 PyPI API 获取库信息
        pypi_url = f"https://pypi.org/pypi/{library_name}/json"
        
        try:
            with urllib.request.urlopen(pypi_url, timeout=10) as response:
                pypi_data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # 包不存在时，从 PyPI 搜索页面提取结果
                suggestions = []
                try:
                    # 访问 PyPI 搜索页面
                    search_url = f"https://pypi.org/search/?q={urllib.parse.quote(library_name)}"
                    req = urllib.request.Request(search_url)
                    req.add_header('User-Agent', 'Mozilla/5.0 (compatible; Nexus-AI/1.0)')
                    
                    with urllib.request.urlopen(req, timeout=10) as search_response:
                        html_content = search_response.read().decode("utf-8")
                        
                        # 提取搜索结果中的包名
                        # PyPI 搜索结果页面的包名通常在 <a class="package-snippet" href="/project/包名/"> 或类似结构中
                        # 使用多种模式来匹配，确保能提取到第一个结果（如 mem0ai）
                        patterns = [
                            # 匹配搜索结果中的包链接，优先匹配搜索结果区域
                            r'<a[^>]*class="[^"]*package-snippet[^"]*"[^>]*href="/project/([^/"]+)/"',
                            r'<a[^>]*href="/project/([^/"]+)/"[^>]*class="[^"]*package-snippet[^"]*"',
                            # 匹配搜索结果中的包名（在搜索结果列表区域）
                            r'<span[^>]*class="[^"]*package-snippet__name[^"]*"[^>]*>([^<]+)</span>',
                            # 通用模式：匹配所有 /project/包名/ 链接
                            r'href="/project/([^/"]+)/"',
                        ]
                        
                        seen = set()
                        query_lower = library_name.lower()
                            
                except Exception as search_error:
                    logger.warning(f"搜索 PyPI 时出错: {str(search_error)}")
                
                result = {
                    "error": f"库 '{library_name}' 在 PyPI 上不存在",
                    "library_name": library_name,
                    "library_version": library_version,
                    "project_python_version": project_python_version,
                }
                
                result["message"] = f"未找到 '{library_name}'，请检查包名称"
                
                return json.dumps(result, ensure_ascii=False, indent=2)
            else:
                return json.dumps({
                    "error": f"查询 PyPI API 时出错: HTTP {e.code}",
                    "library_name": library_name,
                    "library_version": library_version,
                    "project_python_version": project_python_version
                }, ensure_ascii=False)
        except urllib.error.URLError as e:
            return json.dumps({
                "error": f"网络连接错误: {str(e)}",
                "library_name": library_name,
                "library_version": library_version,
                "project_python_version": project_python_version
            }, ensure_ascii=False)
        
        # 3. 获取指定版本或最新版本的信息
        if library_version == "latest":
            # 获取最新版本
            latest_version = pypi_data.get("info", {}).get("version")
            if not latest_version:
                return json.dumps({
                    "error": "无法获取库的最新版本信息",
                    "library_name": library_name,
                    "project_python_version": project_python_version
                }, ensure_ascii=False)
            library_version = latest_version
        
        # 获取指定版本的发布信息
        releases = pypi_data.get("releases", {})
        if library_version not in releases:
            available_versions = list(releases.keys())[:10]  # 显示前10个可用版本
            return json.dumps({
                "error": f"库 '{library_name}' 不存在版本 '{library_version}'",
                "library_name": library_name,
                "library_version": library_version,
                "available_versions": available_versions,
                "project_python_version": project_python_version
            }, ensure_ascii=False)
        
        # 4. 检查库的 Python 版本要求
        # 从 info 中获取 requires_python（这是所有版本的通用要求）
        library_python_requirement = pypi_data.get("info", {}).get("requires_python")
        
        # 也可以从特定版本的元数据中获取
        version_releases = releases.get(library_version, [])
        if version_releases:
            # 尝试从第一个发布文件中获取元数据
            for release in version_releases:
                if release.get("packagetype") == "bdist_wheel":
                    # 对于 wheel 文件，需要解析文件名或查询额外信息
                    # 这里我们主要使用 info 中的 requires_python
                    break
        
        # 5. 比较版本要求
        is_compatible = True
        compatibility_reason = ""
        
        if library_python_requirement:
            project_match = re.match(r'>=?(\d+)\.(\d+)', project_python_version)
            if project_match:
                project_major = int(project_match.group(1))
                project_minor = int(project_match.group(2))
                
                # 解析库要求的 Python 版本
                # 处理各种格式：">=3.8", ">=3.8,<4.0", "~=3.8", "3.8.*" 等
                lib_requirements = library_python_requirement.split(",")
                for req in lib_requirements:
                    req = req.strip()
                    # 提取最低版本要求
                    req_match = re.match(r'>=?(\d+)\.(\d+)', req)
                    if req_match:
                        lib_major = int(req_match.group(1))
                        lib_minor = int(req_match.group(2))
                        
                        # 检查项目版本是否满足库的要求
                        if project_major < lib_major or (project_major == lib_major and project_minor < lib_minor):
                            is_compatible = False
                            compatibility_reason = f"项目 Python 版本 {project_python_version} 不满足库要求 {library_python_requirement}"
                            break
                        
                        # 检查是否有上限要求（如 "<4.0"）
                        upper_match = re.search(r'<(\d+)\.(\d+)', req)
                        if upper_match:
                            upper_major = int(upper_match.group(1))
                            if project_major >= upper_major:
                                is_compatible = False
                                compatibility_reason = f"项目 Python 版本 {project_python_version} 超过库要求的上限 {library_python_requirement}"
                                break
        else:
            # 如果库没有明确指定 Python 版本要求，假设兼容
            compatibility_reason = "库未明确指定 Python 版本要求，假设兼容"
        
        # 6. 构建返回结果
        result = {
            "project_python_version": project_python_version,
            "library_name": library_name,
            "library_version": library_version,
            "is_compatible": is_compatible,
            "library_python_requirement": library_python_requirement or "未指定",
            "compatibility_reason": compatibility_reason if not is_compatible else "兼容",
            "pypi_url": f"https://pypi.org/project/{library_name}/{library_version}/"
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"验证库依赖时出错: {str(e)}")
        return json.dumps({
            "error": f"验证库依赖时出错: {str(e)}",
            "library_name": library_name,
            "library_version": library_version
        }, ensure_ascii=False)

if __name__ == "__main__":
    # 测试工具验证功能
    test_tools = [
        "strands_tools/calculator",
        "strands_tools/file_read",
        "tools/system_tools/agent_build_workflow/project_manager/get_project_status",
        "invalid_tool_path"
    ]
    
    # print("测试工具验证功能:")
    # result = validate_tool_list(test_tools)
    # print(result)

    print("测试库依赖验证功能:")
    print("--------------查询men0-ai 1.0.1------------------")
    result = verify_library_dependencies("men0-ai", "1.0.1")
    print(result)
    print()
    print("--------------查询mem0ai 1.0.1------------------")
    result = verify_library_dependencies("mem0ai", "1.0.1")
    print(result)
    print()
    print("--------------查询mem0ai 2.0.1------------------")
    result = verify_library_dependencies("mem0ai", "2.0.1")
    print(result)
    print()
    print("--------------查询requests latest------------------")
    result = verify_library_dependencies("requests", "latest")
    print(result)