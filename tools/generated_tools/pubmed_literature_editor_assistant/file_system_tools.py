#!/usr/bin/env python3
"""
文件系统操作工具

提供文件系统操作功能，用于管理工作目录和缓存：
- 创建、读取、写入、删除文件和目录
- 管理工作目录和缓存
- 处理JSON和文本文件
- 支持research_id参数，用于指定缓存和工作目录
"""

import json
import os
import shutil
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from strands import tool


# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _ensure_directory(path: str) -> str:
    """确保目录存在，如果不存在则创建"""
    os.makedirs(path, exist_ok=True)
    return path


def _get_base_dir(research_id: str) -> str:
    """获取基础目录路径"""
    base_dir = f".cache/pmc_literature/{research_id}"
    return _ensure_directory(base_dir)


def _get_editor_dir(research_id: str, version: str = "v1") -> str:
    """获取编辑目录路径"""
    editor_dir = f".cache/pmc_literature/{research_id}/feedback/editor/{version}"
    return _ensure_directory(editor_dir)


def _get_verification_dir(research_id: str, version: str = "v1") -> str:
    """获取验证目录路径"""
    verification_dir = f".cache/pmc_literature/{research_id}/feedback/editor/{version}/verification"
    return _ensure_directory(verification_dir)


def _get_status_file_path(research_id: str) -> str:
    """获取状态文件路径"""
    status_dir = _get_base_dir(research_id)
    return os.path.join(status_dir, "step6.status")


@tool
def create_directory(research_id: str, directory_path: str, version: str = "v1") -> str:
    """
    创建目录
    
    Args:
        research_id (str): 研究ID，用于指定工作目录
        directory_path (str): 要创建的目录路径（相对于工作目录）
        version (str): 版本号，默认v1
        
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 获取基础目录
        base_dir = _get_base_dir(research_id)
        
        # 构建完整目录路径
        if directory_path.startswith("/"):
            directory_path = directory_path[1:]
        full_path = os.path.join(base_dir, directory_path)
        
        # 创建目录
        os.makedirs(full_path, exist_ok=True)
        
        return json.dumps({
            "status": "success",
            "research_id": research_id,
            "directory_path": directory_path,
            "full_path": full_path,
            "message": f"目录已创建: {full_path}"
        }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"创建目录失败: {e}")
        return json.dumps({
            "status": "error", 
            "message": f"创建目录失败: {e}"
        }, ensure_ascii=False)


@tool
def list_directory(research_id: str, directory_path: str = "", version: str = "v1") -> str:
    """
    列出目录内容
    
    Args:
        research_id (str): 研究ID，用于指定工作目录
        directory_path (str): 要列出的目录路径（相对于工作目录），默认为根目录
        version (str): 版本号，默认v1
        
    Returns:
        str: JSON格式的目录内容
    """
    try:
        # 获取基础目录
        base_dir = _get_base_dir(research_id)
        
        # 构建完整目录路径
        if directory_path:
            if directory_path.startswith("/"):
                directory_path = directory_path[1:]
            full_path = os.path.join(base_dir, directory_path)
        else:
            full_path = base_dir
        
        # 检查目录是否存在
        if not os.path.exists(full_path):
            return json.dumps({
                "status": "error", 
                "message": f"目录不存在: {full_path}"
            }, ensure_ascii=False)
        
        # 列出目录内容
        files = []
        directories = []
        
        for item in os.listdir(full_path):
            item_path = os.path.join(full_path, item)
            if os.path.isfile(item_path):
                files.append({
                    "name": item,
                    "path": os.path.join(directory_path, item),
                    "size": os.path.getsize(item_path),
                    "modified": datetime.fromtimestamp(os.path.getmtime(item_path)).isoformat()
                })
            elif os.path.isdir(item_path):
                directories.append({
                    "name": item,
                    "path": os.path.join(directory_path, item)
                })
        
        return json.dumps({
            "status": "success",
            "research_id": research_id,
            "directory_path": directory_path,
            "full_path": full_path,
            "files": files,
            "directories": directories
        }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"列出目录内容失败: {e}")
        return json.dumps({
            "status": "error", 
            "message": f"列出目录内容失败: {e}"
        }, ensure_ascii=False)


@tool
def read_file(research_id: str, file_path: str) -> str:
    """
    读取文件内容
    
    Args:
        research_id (str): 研究ID，用于指定工作目录
        file_path (str): 要读取的文件路径（相对于工作目录）
        
    Returns:
        str: JSON格式的文件内容
    """
    try:
        # 获取基础目录
        base_dir = _get_base_dir(research_id)
        
        # 构建完整文件路径
        if file_path.startswith("/"):
            file_path = file_path[1:]
        full_path = os.path.join(base_dir, file_path)
        
        # 检查文件是否存在
        if not os.path.exists(full_path):
            return json.dumps({
                "status": "error", 
                "message": f"文件不存在: {full_path}"
            }, ensure_ascii=False)
        
        # 读取文件内容
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        return json.dumps({
            "status": "success",
            "research_id": research_id,
            "file_path": file_path,
            "full_path": full_path,
            "content": content
        }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"读取文件失败: {e}")
        return json.dumps({
            "status": "error", 
            "message": f"读取文件失败: {e}"
        }, ensure_ascii=False)


@tool
def write_file(research_id: str, file_path: str, content: str) -> str:
    """
    写入文件内容
    
    Args:
        research_id (str): 研究ID，用于指定工作目录
        file_path (str): 要写入的文件路径（相对于工作目录）
        content (str): 要写入的内容
        
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 获取基础目录
        base_dir = _get_base_dir(research_id)
        
        # 构建完整文件路径
        if file_path.startswith("/"):
            file_path = file_path[1:]
        full_path = os.path.join(base_dir, file_path)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # 写入文件内容
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return json.dumps({
            "status": "success",
            "research_id": research_id,
            "file_path": file_path,
            "full_path": full_path,
            "message": f"内容已写入文件: {full_path}"
        }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"写入文件失败: {e}")
        return json.dumps({
            "status": "error", 
            "message": f"写入文件失败: {e}"
        }, ensure_ascii=False)


@tool
def delete_file(research_id: str, file_path: str) -> str:
    """
    删除文件
    
    Args:
        research_id (str): 研究ID，用于指定工作目录
        file_path (str): 要删除的文件路径（相对于工作目录）
        
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 获取基础目录
        base_dir = _get_base_dir(research_id)
        
        # 构建完整文件路径
        if file_path.startswith("/"):
            file_path = file_path[1:]
        full_path = os.path.join(base_dir, file_path)
        
        # 检查文件是否存在
        if not os.path.exists(full_path):
            return json.dumps({
                "status": "error", 
                "message": f"文件不存在: {full_path}"
            }, ensure_ascii=False)
        
        # 删除文件
        os.remove(full_path)
        
        return json.dumps({
            "status": "success",
            "research_id": research_id,
            "file_path": file_path,
            "full_path": full_path,
            "message": f"文件已删除: {full_path}"
        }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"删除文件失败: {e}")
        return json.dumps({
            "status": "error", 
            "message": f"删除文件失败: {e}"
        }, ensure_ascii=False)


@tool
def copy_file(research_id: str, source_path: str, target_path: str) -> str:
    """
    复制文件
    
    Args:
        research_id (str): 研究ID，用于指定工作目录
        source_path (str): 源文件路径（相对于工作目录）
        target_path (str): 目标文件路径（相对于工作目录）
        
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 获取基础目录
        base_dir = _get_base_dir(research_id)
        
        # 构建完整文件路径
        if source_path.startswith("/"):
            source_path = source_path[1:]
        if target_path.startswith("/"):
            target_path = target_path[1:]
        
        full_source_path = os.path.join(base_dir, source_path)
        full_target_path = os.path.join(base_dir, target_path)
        
        # 检查源文件是否存在
        if not os.path.exists(full_source_path):
            return json.dumps({
                "status": "error", 
                "message": f"源文件不存在: {full_source_path}"
            }, ensure_ascii=False)
        
        # 确保目标目录存在
        os.makedirs(os.path.dirname(full_target_path), exist_ok=True)
        
        # 复制文件
        shutil.copy2(full_source_path, full_target_path)
        
        return json.dumps({
            "status": "success",
            "research_id": research_id,
            "source_path": source_path,
            "target_path": target_path,
            "message": f"文件已复制: {full_source_path} -> {full_target_path}"
        }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"复制文件失败: {e}")
        return json.dumps({
            "status": "error", 
            "message": f"复制文件失败: {e}"
        }, ensure_ascii=False)


@tool
def move_file(research_id: str, source_path: str, target_path: str) -> str:
    """
    移动文件
    
    Args:
        research_id (str): 研究ID，用于指定工作目录
        source_path (str): 源文件路径（相对于工作目录）
        target_path (str): 目标文件路径（相对于工作目录）
        
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 获取基础目录
        base_dir = _get_base_dir(research_id)
        
        # 构建完整文件路径
        if source_path.startswith("/"):
            source_path = source_path[1:]
        if target_path.startswith("/"):
            target_path = target_path[1:]
        
        full_source_path = os.path.join(base_dir, source_path)
        full_target_path = os.path.join(base_dir, target_path)
        
        # 检查源文件是否存在
        if not os.path.exists(full_source_path):
            return json.dumps({
                "status": "error", 
                "message": f"源文件不存在: {full_source_path}"
            }, ensure_ascii=False)
        
        # 确保目标目录存在
        os.makedirs(os.path.dirname(full_target_path), exist_ok=True)
        
        # 移动文件
        shutil.move(full_source_path, full_target_path)
        
        return json.dumps({
            "status": "success",
            "research_id": research_id,
            "source_path": source_path,
            "target_path": target_path,
            "message": f"文件已移动: {full_source_path} -> {full_target_path}"
        }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"移动文件失败: {e}")
        return json.dumps({
            "status": "error", 
            "message": f"移动文件失败: {e}"
        }, ensure_ascii=False)


@tool
def check_file_exists(research_id: str, file_path: str) -> str:
    """
    检查文件是否存在
    
    Args:
        research_id (str): 研究ID，用于指定工作目录
        file_path (str): 要检查的文件路径（相对于工作目录）
        
    Returns:
        str: JSON格式的检查结果
    """
    try:
        # 获取基础目录
        base_dir = _get_base_dir(research_id)
        
        # 构建完整文件路径
        if file_path.startswith("/"):
            file_path = file_path[1:]
        full_path = os.path.join(base_dir, file_path)
        
        # 检查文件是否存在
        exists = os.path.exists(full_path)
        is_file = os.path.isfile(full_path) if exists else False
        
        return json.dumps({
            "status": "success",
            "research_id": research_id,
            "file_path": file_path,
            "full_path": full_path,
            "exists": exists,
            "is_file": is_file
        }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"检查文件失败: {e}")
        return json.dumps({
            "status": "error", 
            "message": f"检查文件失败: {e}"
        }, ensure_ascii=False)


@tool
def get_file_info(research_id: str, file_path: str) -> str:
    """
    获取文件信息
    
    Args:
        research_id (str): 研究ID，用于指定工作目录
        file_path (str): 要获取信息的文件路径（相对于工作目录）
        
    Returns:
        str: JSON格式的文件信息
    """
    try:
        # 获取基础目录
        base_dir = _get_base_dir(research_id)
        
        # 构建完整文件路径
        if file_path.startswith("/"):
            file_path = file_path[1:]
        full_path = os.path.join(base_dir, file_path)
        
        # 检查文件是否存在
        if not os.path.exists(full_path):
            return json.dumps({
                "status": "error", 
                "message": f"文件不存在: {full_path}"
            }, ensure_ascii=False)
        
        # 获取文件信息
        stat_info = os.stat(full_path)
        
        file_info = {
            "name": os.path.basename(full_path),
            "path": file_path,
            "full_path": full_path,
            "size": stat_info.st_size,
            "created": datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
            "accessed": datetime.fromtimestamp(stat_info.st_atime).isoformat(),
            "is_file": os.path.isfile(full_path),
            "is_dir": os.path.isdir(full_path)
        }
        
        return json.dumps({
            "status": "success",
            "research_id": research_id,
            "file_info": file_info
        }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"获取文件信息失败: {e}")
        return json.dumps({
            "status": "error", 
            "message": f"获取文件信息失败: {e}"
        }, ensure_ascii=False)


@tool
def read_json_file(research_id: str, file_path: str) -> str:
    """
    读取JSON文件
    
    Args:
        research_id (str): 研究ID，用于指定工作目录
        file_path (str): 要读取的JSON文件路径（相对于工作目录）
        
    Returns:
        str: JSON格式的文件内容
    """
    try:
        # 获取基础目录
        base_dir = _get_base_dir(research_id)
        
        # 构建完整文件路径
        if file_path.startswith("/"):
            file_path = file_path[1:]
        full_path = os.path.join(base_dir, file_path)
        
        # 检查文件是否存在
        if not os.path.exists(full_path):
            return json.dumps({
                "status": "error", 
                "message": f"文件不存在: {full_path}"
            }, ensure_ascii=False)
        
        # 读取JSON文件
        with open(full_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return json.dumps({
            "status": "success",
            "research_id": research_id,
            "file_path": file_path,
            "full_path": full_path,
            "data": data
        }, ensure_ascii=False)
    
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {e}")
        return json.dumps({
            "status": "error", 
            "message": f"JSON解析失败: {e}"
        }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"读取JSON文件失败: {e}")
        return json.dumps({
            "status": "error", 
            "message": f"读取JSON文件失败: {e}"
        }, ensure_ascii=False)


@tool
def write_json_file(research_id: str, file_path: str, data: Dict[str, Any]) -> str:
    """
    写入JSON文件
    
    Args:
        research_id (str): 研究ID，用于指定工作目录
        file_path (str): 要写入的JSON文件路径（相对于工作目录）
        data (Dict[str, Any]): 要写入的JSON数据
        
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 获取基础目录
        base_dir = _get_base_dir(research_id)
        
        # 构建完整文件路径
        if file_path.startswith("/"):
            file_path = file_path[1:]
        full_path = os.path.join(base_dir, file_path)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # 写入JSON文件
        with open(full_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return json.dumps({
            "status": "success",
            "research_id": research_id,
            "file_path": file_path,
            "full_path": full_path,
            "message": f"JSON数据已写入文件: {full_path}"
        }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"写入JSON文件失败: {e}")
        return json.dumps({
            "status": "error", 
            "message": f"写入JSON文件失败: {e}"
        }, ensure_ascii=False)


@tool
def update_status_file(research_id: str, status: str, progress: int, current_step: str, result_path: str = "") -> str:
    """
    更新处理状态文件
    
    Args:
        research_id (str): 研究ID
        status (str): 处理状态（started, in_progress, completed, failed）
        progress (int): 处理进度（0-100）
        current_step (str): 当前步骤
        result_path (str): 结果文件路径（可选）
        
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 获取状态文件路径
        status_file = _get_status_file_path(research_id)
        
        # 准备状态数据
        status_data = {
            "research_id": research_id,
            "status": status,
            "progress": max(0, min(progress, 100)),  # 确保进度在0-100范围内
            "current_step": current_step,
            "result_path": result_path,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 写入状态文件
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(status_data, f, ensure_ascii=False, indent=2)
        
        return json.dumps({
            "status": "success",
            "research_id": research_id,
            "status_file": status_file,
            "status_data": status_data,
            "message": f"状态已更新: {status_file}"
        }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"更新状态文件失败: {e}")
        return json.dumps({
            "status": "error", 
            "message": f"更新状态文件失败: {e}"
        }, ensure_ascii=False)


@tool
def get_status_file(research_id: str) -> str:
    """
    获取处理状态文件内容
    
    Args:
        research_id (str): 研究ID
        
    Returns:
        str: JSON格式的状态文件内容
    """
    try:
        # 获取状态文件路径
        status_file = _get_status_file_path(research_id)
        
        # 检查状态文件是否存在
        if not os.path.exists(status_file):
            return json.dumps({
                "status": "success",
                "research_id": research_id,
                "status_file": status_file,
                "status_data": {"status": "not_started"},
                "message": f"状态文件不存在: {status_file}"
            }, ensure_ascii=False)
        
        # 读取状态文件
        with open(status_file, "r", encoding="utf-8") as f:
            status_data = json.load(f)
        
        return json.dumps({
            "status": "success",
            "research_id": research_id,
            "status_file": status_file,
            "status_data": status_data
        }, ensure_ascii=False)
    
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {e}")
        return json.dumps({
            "status": "error", 
            "message": f"JSON解析失败: {e}"
        }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"获取状态文件失败: {e}")
        return json.dumps({
            "status": "error", 
            "message": f"获取状态文件失败: {e}"
        }, ensure_ascii=False)