#!/usr/bin/env python3
"""
工具构建项目管理工具

提供工具项目初始化、配置管理、状态跟踪等功能，支持工具构建的完整生命周期管理
"""

import os
import json
import logging
import yaml
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pathlib import Path

from strands import tool

logger = logging.getLogger(__name__)

BASE_TOOLS_DIR = Path("tools") / "generated_tools"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@tool
def initialize_tool_project(tool_name: str, description: str = "") -> str:
    """
    初始化工具项目目录结构
    
    Args:
        tool_name: 工具项目名称，将作为目录名使用（格式：tool_build_xxxx）
        description: 工具项目描述
        
    Returns:
        str: 操作结果信息，包含创建的目录结构
    """
    try:
        # 验证工具名称
        if not tool_name or not tool_name.strip():
            return "错误：工具名称不能为空"
        
        tool_name = tool_name.strip()
        
        # 验证命名格式
        if not tool_name.startswith("tool_build_"):
            return f"错误：工具名称必须以 'tool_build_' 开头，当前为: {tool_name}"
        
        # 清理工具名称，移除不安全字符
        if "/" in tool_name or "\\" in tool_name or ".." in tool_name:
            return "错误：工具名称不能包含路径分隔符或相对路径"

        tool_root = BASE_TOOLS_DIR / tool_name
        reused_project = tool_root.exists()

        # 创建目录结构
        tool_root.mkdir(parents=True, exist_ok=True)
        
        files_created = []
        
        # 创建 config.yaml
        config_path = tool_root / "config.yaml"
        config_content = {
            "tool_project": {
                "name": tool_name,
                "description": description or f"工具项目：{tool_name}",
                "version": "1.0.0",
                "created_date": _utc_now(),
                "status": "initialized"
            }
        }
        
        if not config_path.exists():
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_content, f, default_flow_style=False, allow_unicode=True, indent=2)
            files_created.append("config.yaml")
        
        # 创建 status.yaml
        status_path = tool_root / "status.yaml"
        if not status_path.exists():
            status_content = {
                "tool_project": tool_name,
                "status": "initialized",
                "created_at": _utc_now(),
                "last_updated": _utc_now(),
                "stages": {
                    "requirements_analyzer": {"status": False, "doc_path": ""},
                    "tool_designer": {"status": False, "doc_path": ""},
                    "tool_developer": {"status": False, "doc_path": ""},
                    "tool_validator": {"status": False, "doc_path": ""},
                    "tool_documenter": {"status": False, "doc_path": ""}
                },
                "tools": []
            }

            with open(status_path, 'w', encoding='utf-8') as f:
                yaml.dump(status_content, f, default_flow_style=False, allow_unicode=True, indent=2)
            files_created.append("status.yaml")
        
        # 创建 stages 目录用于存放阶段文档
        stages_dir = tool_root / "stages"
        stages_dir.mkdir(exist_ok=True)

        result = {
            "status": "success",
            "message": f"工具项目 '{tool_name}' 初始化成功",
            "project_path": str(tool_root),
            "directories_created": [
                "stages/"
            ],
            "files_created": files_created,
            "created_date": _utc_now(),
            "reused": reused_project,
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except PermissionError:
        return f"错误：没有权限创建工具项目目录"
    except OSError as e:
        return f"错误：文件系统操作失败: {str(e)}"
    except Exception as e:
        return f"工具项目初始化时出现错误: {str(e)}"


@tool
def get_tool_project_config(tool_name: str) -> str:
    """
    获取工具项目配置信息
    
    Args:
        tool_name: 工具项目名称
        
    Returns:
        str: JSON格式的配置信息
    """
    try:
        if not tool_name or not tool_name.strip():
            return "错误：工具名称不能为空"
        
        tool_name = tool_name.strip()
        tool_root = BASE_TOOLS_DIR / tool_name
        
        if not tool_root.exists():
            return f"错误：工具项目 '{tool_name}' 不存在"
        
        config_path = tool_root / "config.yaml"
        
        if not config_path.exists():
            return f"错误：工具项目 '{tool_name}' 的配置文件不存在"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f) or {}
        
        file_stat = config_path.stat()
        import time
        
        result = {
            "status": "success",
            "tool_name": tool_name,
            "config_file_path": str(config_path),
            "config_data": config_data,
            "file_size": file_stat.st_size,
            "modified_time": time.ctime(file_stat.st_mtime),
            "query_date": _utc_now()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"获取工具项目配置时出现错误: {str(e)}"


@tool
def get_tool_project_status(tool_name: str) -> str:
    """
    获取工具项目状态信息
    
    Args:
        tool_name: 工具项目名称
        
    Returns:
        str: JSON格式的状态信息
    """
    try:
        if not tool_name or not tool_name.strip():
            return "错误：工具名称不能为空"
        
        tool_name = tool_name.strip()
        tool_root = BASE_TOOLS_DIR / tool_name
        
        if not tool_root.exists():
            return f"错误：工具项目 '{tool_name}' 不存在"
        
        status_path = tool_root / "status.yaml"
        
        if not status_path.exists():
            return f"错误：工具项目 '{tool_name}' 的状态文件不存在"
        
        with open(status_path, 'r', encoding='utf-8') as f:
            status_data = yaml.safe_load(f) or {}
        
        result = {
            "status": "success",
            "tool_name": tool_name,
            "status_data": status_data,
            "query_date": _utc_now()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"获取工具项目状态时出现错误: {str(e)}"


@tool
def update_tool_project_stage(
    tool_name: str,
    stage_name: str,
    status: bool,
    doc_path: str = "",
    summary: str = ""
) -> str:
    """
    更新工具项目阶段状态
    
    Args:
        tool_name: 工具项目名称
        stage_name: 阶段名称
        status: 阶段状态（True表示完成）
        doc_path: 阶段文档路径
        summary: 阶段总结
        
    Returns:
        str: 操作结果信息
    """
    try:
        if not tool_name or not tool_name.strip():
            return "错误：工具名称不能为空"
        
        if not stage_name or not stage_name.strip():
            return "错误：阶段名称不能为空"
        
        tool_name = tool_name.strip()
        stage_name = stage_name.strip()
        
        tool_root = BASE_TOOLS_DIR / tool_name
        
        if not tool_root.exists():
            return f"错误：工具项目 '{tool_name}' 不存在"
        
        status_path = tool_root / "status.yaml"
        
        if not status_path.exists():
            return f"错误：工具项目 '{tool_name}' 的状态文件不存在"
        
        with open(status_path, 'r', encoding='utf-8') as f:
            status_data = yaml.safe_load(f) or {}
        
        # 更新阶段状态
        stages = status_data.setdefault("stages", {})
        if stage_name not in stages:
            stages[stage_name] = {"status": False, "doc_path": ""}
        
        stages[stage_name]["status"] = status
        if doc_path:
            stages[stage_name]["doc_path"] = doc_path
        if summary:
            stages[stage_name]["summary"] = summary
        stages[stage_name]["updated_at"] = _utc_now()
        
        status_data["last_updated"] = _utc_now()
        
        # 计算总体进度
        total_stages = len(stages)
        completed_stages = sum(1 for s in stages.values() if s.get("status", False))
        status_data["progress"] = {
            "total": total_stages,
            "completed": completed_stages,
            "percentage": round((completed_stages / total_stages) * 100, 1) if total_stages > 0 else 0
        }
        
        with open(status_path, 'w', encoding='utf-8') as f:
            yaml.dump(status_data, f, default_flow_style=False, allow_unicode=True, indent=2)
        
        result = {
            "status": "success",
            "message": f"工具项目 '{tool_name}' 的阶段 '{stage_name}' 状态更新成功",
            "tool_name": tool_name,
            "stage_name": stage_name,
            "new_status": status,
            "doc_path": doc_path,
            "progress": status_data.get("progress", {}),
            "updated_date": _utc_now()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"更新工具项目阶段状态时出现错误: {str(e)}"


@tool
def write_tool_stage_document(
    tool_name: str,
    stage_name: str,
    content: str
) -> str:
    """
    将阶段文档写入工具项目的 stages 目录
    
    Args:
        tool_name: 工具项目名称
        stage_name: 阶段名称
        content: 文档内容
        
    Returns:
        str: 操作结果信息
    """
    try:
        if not tool_name or not tool_name.strip():
            return "错误：工具名称不能为空"
        
        if not stage_name or not stage_name.strip():
            return "错误：阶段名称不能为空"
        
        if content is None:
            return "错误：内容不能为None"
        
        tool_name = tool_name.strip()
        stage_name = stage_name.strip()
        
        tool_root = BASE_TOOLS_DIR / tool_name
        
        if not tool_root.exists():
            return f"错误：工具项目 '{tool_name}' 不存在，请先使用 initialize_tool_project 初始化"
        
        stages_dir = tool_root / "stages"
        stages_dir.mkdir(exist_ok=True)
        
        stage_file_path = stages_dir / f"{stage_name}.json"
        
        with open(stage_file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        result = {
            "status": "success",
            "message": f"成功写入阶段文档到 '{stage_file_path}'",
            "tool_name": tool_name,
            "stage_name": stage_name,
            "file_path": str(stage_file_path),
            "content_length": len(content),
            "updated_date": _utc_now()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except PermissionError:
        return f"错误：没有权限写入文件"
    except Exception as e:
        return f"写入阶段文档时出现错误: {str(e)}"


@tool
def get_tool_stage_document(tool_name: str, stage_name: str) -> str:
    """
    读取工具项目的阶段文档
    
    Args:
        tool_name: 工具项目名称
        stage_name: 阶段名称
        
    Returns:
        str: 文档内容或错误信息
    """
    try:
        if not tool_name or not tool_name.strip():
            return "错误：工具名称不能为空"
        
        if not stage_name or not stage_name.strip():
            return "错误：阶段名称不能为空"
        
        tool_name = tool_name.strip()
        stage_name = stage_name.strip()
        
        tool_root = BASE_TOOLS_DIR / tool_name
        
        if not tool_root.exists():
            return f"错误：工具项目 '{tool_name}' 不存在"
        
        stage_file_path = tool_root / "stages" / f"{stage_name}.json"
        
        if not stage_file_path.exists():
            return f"错误：阶段文档 '{stage_file_path}' 不存在"
        
        with open(stage_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        file_stat = stage_file_path.stat()
        import time
        
        result = {
            "status": "success",
            "tool_name": tool_name,
            "stage_name": stage_name,
            "file_path": str(stage_file_path),
            "content": content,
            "content_length": len(content),
            "file_size": file_stat.st_size,
            "modified_time": time.ctime(file_stat.st_mtime),
            "query_date": _utc_now()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except PermissionError:
        return f"错误：没有权限读取文件"
    except Exception as e:
        return f"读取阶段文档时出现错误: {str(e)}"


@tool
def register_tool(
    tool_name: str,
    tool_function_name: str,
    tool_file_path: str,
    description: str = "",
    parameters: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    注册工具到工具项目
    
    Args:
        tool_name: 工具项目名称
        tool_function_name: 工具函数名称
        tool_file_path: 工具文件路径（相对于工具项目根目录）
        description: 工具描述
        parameters: 工具参数列表
        
    Returns:
        str: 操作结果信息
    """
    try:
        if not tool_name or not tool_name.strip():
            return "错误：工具名称不能为空"
        
        if not tool_function_name or not tool_function_name.strip():
            return "错误：工具函数名称不能为空"
        
        tool_name = tool_name.strip()
        tool_function_name = tool_function_name.strip()
        
        tool_root = BASE_TOOLS_DIR / tool_name
        
        if not tool_root.exists():
            return f"错误：工具项目 '{tool_name}' 不存在"
        
        status_path = tool_root / "status.yaml"
        
        if not status_path.exists():
            return f"错误：工具项目 '{tool_name}' 的状态文件不存在"
        
        with open(status_path, 'r', encoding='utf-8') as f:
            status_data = yaml.safe_load(f) or {}
        
        tools = status_data.setdefault("tools", [])
        
        # 检查是否已存在
        existing_tool = None
        for tool_entry in tools:
            if tool_entry.get("function_name") == tool_function_name:
                existing_tool = tool_entry
                break
        
        tool_entry = {
            "function_name": tool_function_name,
            "file_path": tool_file_path,
            "description": description,
            "parameters": parameters or [],
            "registered_at": _utc_now()
        }
        
        if existing_tool:
            # 更新现有工具
            existing_tool.update(tool_entry)
            existing_tool["updated_at"] = _utc_now()
        else:
            # 添加新工具
            tools.append(tool_entry)
        
        status_data["last_updated"] = _utc_now()
        
        with open(status_path, 'w', encoding='utf-8') as f:
            yaml.dump(status_data, f, default_flow_style=False, allow_unicode=True, indent=2)
        
        result = {
            "status": "success",
            "message": f"工具 '{tool_function_name}' 注册成功",
            "tool_name": tool_name,
            "tool_function_name": tool_function_name,
            "total_tools": len(tools),
            "updated_date": _utc_now()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"注册工具时出现错误: {str(e)}"


@tool
def generate_tool_file(
    tool_name: str,
    file_name: str,
    content: str
) -> str:
    """
    在工具项目目录中生成工具文件
    
    Args:
        tool_name: 工具项目名称
        file_name: 文件名（例如：my_tool.py）
        content: 文件内容
        
    Returns:
        str: 操作结果信息
    """
    try:
        if not tool_name or not tool_name.strip():
            return "错误：工具名称不能为空"
        
        if not file_name or not file_name.strip():
            return "错误：文件名不能为空"
        
        if content is None:
            return "错误：内容不能为None"
        
        tool_name = tool_name.strip()
        file_name = file_name.strip()
        
        # 验证文件名安全性
        if "/" in file_name or "\\" in file_name or ".." in file_name:
            return "错误：文件名不能包含路径分隔符或相对路径"
        
        tool_root = BASE_TOOLS_DIR / tool_name
        
        if not tool_root.exists():
            return f"错误：工具项目 '{tool_name}' 不存在，请先使用 initialize_tool_project 初始化"
        
        file_path = tool_root / file_name
        
        # 检查文件是否已存在
        if file_path.exists():
            return f"错误：文件 '{file_name}' 已存在于工具项目目录中，请使用不同的名称或删除现有文件"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        result = {
            "status": "success",
            "message": f"成功创建工具文件 '{file_name}'",
            "tool_name": tool_name,
            "file_name": file_name,
            "file_path": str(file_path),
            "content_length": len(content),
            "created_date": _utc_now()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except PermissionError:
        return f"错误：没有权限写入文件"
    except OSError as e:
        return f"错误：文件系统操作失败: {str(e)}"
    except Exception as e:
        return f"生成工具文件时出现错误: {str(e)}"


@tool
def generate_tool_readme(
    tool_name: str,
    readme_content: str
) -> str:
    """
    生成工具项目的 README.md 文件
    
    Args:
        tool_name: 工具项目名称
        readme_content: README 内容
        
    Returns:
        str: 操作结果信息
    """
    try:
        if not tool_name or not tool_name.strip():
            return "错误：工具名称不能为空"
        
        if readme_content is None:
            return "错误：README 内容不能为None"
        
        tool_name = tool_name.strip()
        
        tool_root = BASE_TOOLS_DIR / tool_name
        
        if not tool_root.exists():
            return f"错误：工具项目 '{tool_name}' 不存在"
        
        readme_path = tool_root / "README.md"
        
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        result = {
            "status": "success",
            "message": f"成功生成 README.md",
            "tool_name": tool_name,
            "readme_path": str(readme_path),
            "content_length": len(readme_content),
            "created_date": _utc_now()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except PermissionError:
        return f"错误：没有权限写入文件"
    except Exception as e:
        return f"生成 README 时出现错误: {str(e)}"

