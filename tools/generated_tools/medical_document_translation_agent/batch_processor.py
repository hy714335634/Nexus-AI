#!/usr/bin/env python3
"""
batch_processor.py - 医学文档批量处理工具

该工具提供了批量处理医学文档翻译的功能，包括管理翻译队列、
提供进度反馈、生成批量翻译报告和管理翻译历史记录。
"""

import os
import json
import uuid
import datetime
import time
import threading
from typing import Dict, List, Any, Optional, Union, Tuple, Set
from pathlib import Path
import shutil

try:
    import docx
    from docx import Document
except ImportError:
    raise ImportError("请安装python-docx库: pip install python-docx")

from strands import tool


# 默认缓存目录
DEFAULT_CACHE_DIR = os.path.join(".cache", "medical_translator", "batch")

# 任务状态
TASK_STATUS = {
    "pending": "等待处理",
    "processing": "处理中",
    "completed": "已完成",
    "failed": "处理失败",
    "cancelled": "已取消"
}


@tool
def create_batch_task(file_paths: List[str], 
                     source_lang: str, 
                     target_lang: str,
                     glossary_name: Optional[str] = None,
                     domain: str = "general",
                     task_name: Optional[str] = None,
                     description: Optional[str] = None,
                     priority: int = 1,
                     cache_dir: Optional[str] = None) -> str:
    """
    创建批量翻译任务
    
    Args:
        file_paths (List[str]): 要翻译的文档路径列表
        source_lang (str): 源语言代码
        target_lang (str): 目标语言代码
        glossary_name (Optional[str]): 词库名称（可选）
        domain (str): 医学领域
        task_name (Optional[str]): 任务名称（可选）
        description (Optional[str]): 任务描述（可选）
        priority (int): 任务优先级（1-5，1为最高）
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的任务创建结果
    """
    try:
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        os.makedirs(cache_dir, exist_ok=True)
        
        # 验证文件路径
        valid_files = []
        invalid_files = []
        
        for file_path in file_paths:
            if os.path.exists(file_path):
                if file_path.lower().endswith('.docx'):
                    valid_files.append(file_path)
                else:
                    invalid_files.append({
                        "path": file_path,
                        "reason": "不支持的文件格式，仅支持.docx格式"
                    })
            else:
                invalid_files.append({
                    "path": file_path,
                    "reason": "文件不存在"
                })
        
        if not valid_files:
            return json.dumps({
                "success": False,
                "error": "没有有效的文件可处理",
                "invalid_files": invalid_files
            }, ensure_ascii=False)
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 创建任务目录
        task_dir = os.path.join(cache_dir, task_id)
        os.makedirs(task_dir, exist_ok=True)
        
        # 创建源文件目录和结果目录
        source_dir = os.path.join(task_dir, "source")
        result_dir = os.path.join(task_dir, "result")
        os.makedirs(source_dir, exist_ok=True)
        os.makedirs(result_dir, exist_ok=True)
        
        # 复制源文件到任务目录
        file_items = []
        for file_path in valid_files:
            file_name = os.path.basename(file_path)
            dest_path = os.path.join(source_dir, file_name)
            shutil.copy2(file_path, dest_path)
            
            file_items.append({
                "file_id": str(uuid.uuid4()),
                "original_path": file_path,
                "file_name": file_name,
                "source_path": dest_path,
                "result_path": os.path.join(result_dir, file_name),
                "status": "pending",
                "progress": 0.0,
                "start_time": None,
                "end_time": None,
                "error": None
            })
        
        # 创建任务信息
        task_info = {
            "task_id": task_id,
            "task_name": task_name or f"翻译任务 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "description": description or f"批量翻译{len(valid_files)}个文档",
            "created_time": datetime.datetime.now().isoformat(),
            "updated_time": datetime.datetime.now().isoformat(),
            "status": "pending",
            "priority": max(1, min(5, priority)),  # 确保优先级在1-5之间
            "source_lang": source_lang,
            "target_lang": target_lang,
            "glossary_name": glossary_name,
            "domain": domain,
            "total_files": len(valid_files),
            "completed_files": 0,
            "failed_files": 0,
            "overall_progress": 0.0,
            "start_time": None,
            "end_time": None,
            "files": file_items,
            "invalid_files": invalid_files
        }
        
        # 保存任务信息
        task_file = os.path.join(task_dir, "task.json")
        with open(task_file, 'w', encoding='utf-8') as f:
            json.dump(task_info, f, ensure_ascii=False, indent=2)
        
        # 更新任务索引
        _update_task_index(task_info, cache_dir)
        
        return json.dumps({
            "success": True,
            "task_id": task_id,
            "task_name": task_info["task_name"],
            "valid_files": len(valid_files),
            "invalid_files": len(invalid_files),
            "status": "pending",
            "message": "批量翻译任务已创建"
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"创建批量任务时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def list_batch_tasks(status: Optional[str] = None, 
                    limit: int = 10, 
                    cache_dir: Optional[str] = None) -> str:
    """
    列出批量翻译任务
    
    Args:
        status (Optional[str]): 任务状态过滤（pending, processing, completed, failed, cancelled）
        limit (int): 返回的最大任务数量
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的任务列表
    """
    try:
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        
        if not os.path.exists(cache_dir):
            return json.dumps({
                "success": True,
                "tasks": [],
                "total": 0,
                "message": "没有找到任何任务"
            }, ensure_ascii=False)
        
        # 读取任务索引
        index_file = os.path.join(cache_dir, "task_index.json")
        
        if not os.path.exists(index_file):
            return json.dumps({
                "success": True,
                "tasks": [],
                "total": 0,
                "message": "没有找到任何任务"
            }, ensure_ascii=False)
        
        with open(index_file, 'r', encoding='utf-8') as f:
            task_index = json.load(f)
        
        # 过滤任务
        tasks = task_index.get("tasks", [])
        
        if status:
            tasks = [task for task in tasks if task.get("status") == status]
        
        # 按更新时间排序
        tasks.sort(key=lambda x: x.get("updated_time", ""), reverse=True)
        
        # 限制返回数量
        tasks = tasks[:limit]
        
        # 简化任务信息
        simplified_tasks = []
        for task in tasks:
            simplified_tasks.append({
                "task_id": task.get("task_id"),
                "task_name": task.get("task_name"),
                "status": task.get("status"),
                "priority": task.get("priority"),
                "created_time": task.get("created_time"),
                "updated_time": task.get("updated_time"),
                "total_files": task.get("total_files"),
                "completed_files": task.get("completed_files"),
                "failed_files": task.get("failed_files"),
                "overall_progress": task.get("overall_progress")
            })
        
        return json.dumps({
            "success": True,
            "tasks": simplified_tasks,
            "total": len(simplified_tasks),
            "filtered_by_status": status
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"列出批量任务时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def get_batch_task(task_id: str, cache_dir: Optional[str] = None) -> str:
    """
    获取批量翻译任务详情
    
    Args:
        task_id (str): 任务ID
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的任务详情
    """
    try:
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        
        # 构建任务文件路径
        task_dir = os.path.join(cache_dir, task_id)
        task_file = os.path.join(task_dir, "task.json")
        
        if not os.path.exists(task_file):
            return json.dumps({
                "success": False,
                "error": f"任务不存在: {task_id}"
            }, ensure_ascii=False)
        
        # 读取任务信息
        with open(task_file, 'r', encoding='utf-8') as f:
            task_info = json.load(f)
        
        return json.dumps({
            "success": True,
            "task": task_info
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"获取任务详情时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def start_batch_task(task_id: str, cache_dir: Optional[str] = None) -> str:
    """
    启动批量翻译任务
    
    Args:
        task_id (str): 任务ID
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的启动结果
    """
    try:
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        
        # 构建任务文件路径
        task_dir = os.path.join(cache_dir, task_id)
        task_file = os.path.join(task_dir, "task.json")
        
        if not os.path.exists(task_file):
            return json.dumps({
                "success": False,
                "error": f"任务不存在: {task_id}"
            }, ensure_ascii=False)
        
        # 读取任务信息
        with open(task_file, 'r', encoding='utf-8') as f:
            task_info = json.load(f)
        
        # 检查任务状态
        if task_info.get("status") == "processing":
            return json.dumps({
                "success": False,
                "error": "任务已在处理中"
            }, ensure_ascii=False)
        
        if task_info.get("status") == "completed":
            return json.dumps({
                "success": False,
                "error": "任务已完成"
            }, ensure_ascii=False)
        
        # 更新任务状态
        task_info["status"] = "processing"
        task_info["start_time"] = datetime.datetime.now().isoformat()
        task_info["updated_time"] = datetime.datetime.now().isoformat()
        
        # 保存任务信息
        with open(task_file, 'w', encoding='utf-8') as f:
            json.dump(task_info, f, ensure_ascii=False, indent=2)
        
        # 更新任务索引
        _update_task_index(task_info, cache_dir)
        
        # 启动后台处理线程
        threading.Thread(target=_process_batch_task, args=(task_id, cache_dir)).start()
        
        return json.dumps({
            "success": True,
            "task_id": task_id,
            "status": "processing",
            "message": "批量翻译任务已启动"
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"启动批量任务时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def cancel_batch_task(task_id: str, cache_dir: Optional[str] = None) -> str:
    """
    取消批量翻译任务
    
    Args:
        task_id (str): 任务ID
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的取消结果
    """
    try:
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        
        # 构建任务文件路径
        task_dir = os.path.join(cache_dir, task_id)
        task_file = os.path.join(task_dir, "task.json")
        
        if not os.path.exists(task_file):
            return json.dumps({
                "success": False,
                "error": f"任务不存在: {task_id}"
            }, ensure_ascii=False)
        
        # 读取任务信息
        with open(task_file, 'r', encoding='utf-8') as f:
            task_info = json.load(f)
        
        # 检查任务状态
        if task_info.get("status") == "completed":
            return json.dumps({
                "success": False,
                "error": "任务已完成，无法取消"
            }, ensure_ascii=False)
        
        if task_info.get("status") == "cancelled":
            return json.dumps({
                "success": False,
                "error": "任务已取消"
            }, ensure_ascii=False)
        
        # 更新任务状态
        task_info["status"] = "cancelled"
        task_info["updated_time"] = datetime.datetime.now().isoformat()
        
        # 更新未完成文件的状态
        for file_item in task_info.get("files", []):
            if file_item.get("status") == "pending" or file_item.get("status") == "processing":
                file_item["status"] = "cancelled"
        
        # 保存任务信息
        with open(task_file, 'w', encoding='utf-8') as f:
            json.dump(task_info, f, ensure_ascii=False, indent=2)
        
        # 更新任务索引
        _update_task_index(task_info, cache_dir)
        
        return json.dumps({
            "success": True,
            "task_id": task_id,
            "status": "cancelled",
            "message": "批量翻译任务已取消"
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"取消批量任务时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def get_batch_progress(task_id: str, cache_dir: Optional[str] = None) -> str:
    """
    获取批量翻译任务进度
    
    Args:
        task_id (str): 任务ID
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的进度信息
    """
    try:
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        
        # 构建任务文件路径
        task_dir = os.path.join(cache_dir, task_id)
        task_file = os.path.join(task_dir, "task.json")
        
        if not os.path.exists(task_file):
            return json.dumps({
                "success": False,
                "error": f"任务不存在: {task_id}"
            }, ensure_ascii=False)
        
        # 读取任务信息
        with open(task_file, 'r', encoding='utf-8') as f:
            task_info = json.load(f)
        
        # 提取进度信息
        progress_info = {
            "task_id": task_id,
            "task_name": task_info.get("task_name"),
            "status": task_info.get("status"),
            "overall_progress": task_info.get("overall_progress", 0.0),
            "total_files": task_info.get("total_files", 0),
            "completed_files": task_info.get("completed_files", 0),
            "failed_files": task_info.get("failed_files", 0),
            "start_time": task_info.get("start_time"),
            "end_time": task_info.get("end_time"),
            "updated_time": task_info.get("updated_time"),
            "files": []
        }
        
        # 提取文件进度信息
        for file_item in task_info.get("files", []):
            progress_info["files"].append({
                "file_id": file_item.get("file_id"),
                "file_name": file_item.get("file_name"),
                "status": file_item.get("status"),
                "progress": file_item.get("progress", 0.0),
                "start_time": file_item.get("start_time"),
                "end_time": file_item.get("end_time"),
                "error": file_item.get("error")
            })
        
        # 计算预计剩余时间
        if (progress_info["status"] == "processing" and 
            progress_info["overall_progress"] > 0 and 
            progress_info["start_time"]):
            
            start_time = datetime.datetime.fromisoformat(progress_info["start_time"])
            now = datetime.datetime.now()
            elapsed_seconds = (now - start_time).total_seconds()
            
            if elapsed_seconds > 0 and progress_info["overall_progress"] > 0:
                total_estimated_seconds = elapsed_seconds / progress_info["overall_progress"]
                remaining_seconds = total_estimated_seconds - elapsed_seconds
                
                # 格式化剩余时间
                remaining_minutes = int(remaining_seconds / 60)
                remaining_seconds = int(remaining_seconds % 60)
                
                progress_info["estimated_remaining_time"] = f"{remaining_minutes}分{remaining_seconds}秒"
        
        return json.dumps({
            "success": True,
            "progress": progress_info
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"获取任务进度时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def generate_batch_report(task_id: str, 
                         include_details: bool = True,
                         cache_dir: Optional[str] = None) -> str:
    """
    生成批量翻译任务报告
    
    Args:
        task_id (str): 任务ID
        include_details (bool): 是否包含详细信息
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的报告
    """
    try:
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        
        # 构建任务文件路径
        task_dir = os.path.join(cache_dir, task_id)
        task_file = os.path.join(task_dir, "task.json")
        
        if not os.path.exists(task_file):
            return json.dumps({
                "success": False,
                "error": f"任务不存在: {task_id}"
            }, ensure_ascii=False)
        
        # 读取任务信息
        with open(task_file, 'r', encoding='utf-8') as f:
            task_info = json.load(f)
        
        # 创建报告
        report = {
            "report_id": str(uuid.uuid4()),
            "generated_time": datetime.datetime.now().isoformat(),
            "task_id": task_id,
            "task_name": task_info.get("task_name"),
            "description": task_info.get("description"),
            "status": task_info.get("status"),
            "source_lang": task_info.get("source_lang"),
            "target_lang": task_info.get("target_lang"),
            "glossary_name": task_info.get("glossary_name"),
            "domain": task_info.get("domain"),
            "summary": {
                "total_files": task_info.get("total_files", 0),
                "completed_files": task_info.get("completed_files", 0),
                "failed_files": task_info.get("failed_files", 0),
                "overall_progress": task_info.get("overall_progress", 0.0),
                "start_time": task_info.get("start_time"),
                "end_time": task_info.get("end_time"),
                "duration": _calculate_duration(
                    task_info.get("start_time"), 
                    task_info.get("end_time") or datetime.datetime.now().isoformat()
                )
            }
        }
        
        # 添加详细信息
        if include_details:
            file_details = []
            
            for file_item in task_info.get("files", []):
                file_detail = {
                    "file_id": file_item.get("file_id"),
                    "file_name": file_item.get("file_name"),
                    "status": file_item.get("status"),
                    "progress": file_item.get("progress", 0.0),
                    "start_time": file_item.get("start_time"),
                    "end_time": file_item.get("end_time"),
                    "duration": _calculate_duration(
                        file_item.get("start_time"), 
                        file_item.get("end_time") or datetime.datetime.now().isoformat()
                    ),
                    "error": file_item.get("error"),
                    "original_path": file_item.get("original_path"),
                    "result_path": file_item.get("result_path") if file_item.get("status") == "completed" else None
                }
                
                file_details.append(file_detail)
            
            report["file_details"] = file_details
        
        # 保存报告
        report_file = os.path.join(task_dir, f"report_{report['report_id']}.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return json.dumps({
            "success": True,
            "report": report,
            "report_file": report_file
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"生成任务报告时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def get_translation_history(limit: int = 10, 
                           status: Optional[str] = None,
                           cache_dir: Optional[str] = None) -> str:
    """
    获取翻译历史记录
    
    Args:
        limit (int): 返回的最大记录数量
        status (Optional[str]): 任务状态过滤
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的历史记录
    """
    try:
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        
        # 读取任务索引
        index_file = os.path.join(cache_dir, "task_index.json")
        
        if not os.path.exists(index_file):
            return json.dumps({
                "success": True,
                "history": [],
                "total": 0,
                "message": "没有找到任何历史记录"
            }, ensure_ascii=False)
        
        with open(index_file, 'r', encoding='utf-8') as f:
            task_index = json.load(f)
        
        # 过滤任务
        tasks = task_index.get("tasks", [])
        
        if status:
            tasks = [task for task in tasks if task.get("status") == status]
        
        # 按更新时间排序
        tasks.sort(key=lambda x: x.get("updated_time", ""), reverse=True)
        
        # 限制返回数量
        tasks = tasks[:limit]
        
        # 构建历史记录
        history = []
        for task in tasks:
            history_item = {
                "task_id": task.get("task_id"),
                "task_name": task.get("task_name"),
                "description": task.get("description"),
                "status": task.get("status"),
                "created_time": task.get("created_time"),
                "updated_time": task.get("updated_time"),
                "source_lang": task.get("source_lang"),
                "target_lang": task.get("target_lang"),
                "glossary_name": task.get("glossary_name"),
                "domain": task.get("domain"),
                "total_files": task.get("total_files"),
                "completed_files": task.get("completed_files"),
                "failed_files": task.get("failed_files")
            }
            
            history.append(history_item)
        
        return json.dumps({
            "success": True,
            "history": history,
            "total": len(history),
            "filtered_by_status": status
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"获取翻译历史记录时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def get_result_files(task_id: str, cache_dir: Optional[str] = None) -> str:
    """
    获取批量翻译任务的结果文件
    
    Args:
        task_id (str): 任务ID
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的结果文件列表
    """
    try:
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        
        # 构建任务文件路径
        task_dir = os.path.join(cache_dir, task_id)
        task_file = os.path.join(task_dir, "task.json")
        
        if not os.path.exists(task_file):
            return json.dumps({
                "success": False,
                "error": f"任务不存在: {task_id}"
            }, ensure_ascii=False)
        
        # 读取任务信息
        with open(task_file, 'r', encoding='utf-8') as f:
            task_info = json.load(f)
        
        # 获取结果文件
        result_files = []
        
        for file_item in task_info.get("files", []):
            if file_item.get("status") == "completed":
                result_path = file_item.get("result_path")
                
                if result_path and os.path.exists(result_path):
                    result_files.append({
                        "file_id": file_item.get("file_id"),
                        "file_name": file_item.get("file_name"),
                        "original_path": file_item.get("original_path"),
                        "result_path": result_path
                    })
        
        return json.dumps({
            "success": True,
            "task_id": task_id,
            "task_name": task_info.get("task_name"),
            "result_files": result_files,
            "total_results": len(result_files)
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"获取结果文件时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def clean_batch_cache(days_old: int = 30, cache_dir: Optional[str] = None) -> str:
    """
    清理批量翻译缓存
    
    Args:
        days_old (int): 清理指定天数以前的缓存
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的清理结果
    """
    try:
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        
        if not os.path.exists(cache_dir):
            return json.dumps({
                "success": True,
                "message": "缓存目录不存在，无需清理",
                "deleted_count": 0
            }, ensure_ascii=False)
        
        # 计算截止日期
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_old)
        
        # 读取任务索引
        index_file = os.path.join(cache_dir, "task_index.json")
        
        if not os.path.exists(index_file):
            return json.dumps({
                "success": True,
                "message": "任务索引不存在，无需清理",
                "deleted_count": 0
            }, ensure_ascii=False)
        
        with open(index_file, 'r', encoding='utf-8') as f:
            task_index = json.load(f)
        
        # 筛选要删除的任务
        tasks = task_index.get("tasks", [])
        tasks_to_keep = []
        tasks_to_delete = []
        
        for task in tasks:
            updated_time = task.get("updated_time")
            
            if updated_time:
                task_date = datetime.datetime.fromisoformat(updated_time)
                
                if task_date < cutoff_date:
                    tasks_to_delete.append(task)
                else:
                    tasks_to_keep.append(task)
        
        # 删除任务目录
        deleted_count = 0
        for task in tasks_to_delete:
            task_id = task.get("task_id")
            task_dir = os.path.join(cache_dir, task_id)
            
            if os.path.exists(task_dir):
                shutil.rmtree(task_dir)
                deleted_count += 1
        
        # 更新任务索引
        task_index["tasks"] = tasks_to_keep
        task_index["last_updated"] = datetime.datetime.now().isoformat()
        
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(task_index, f, ensure_ascii=False, indent=2)
        
        return json.dumps({
            "success": True,
            "message": f"已清理{deleted_count}个{days_old}天前的任务",
            "deleted_count": deleted_count,
            "remaining_count": len(tasks_to_keep)
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"清理缓存时出错: {str(e)}"
        }, ensure_ascii=False)


# 辅助函数
def _update_task_index(task_info: Dict[str, Any], cache_dir: str) -> None:
    """
    更新任务索引
    
    Args:
        task_info (Dict[str, Any]): 任务信息
        cache_dir (str): 缓存目录
    """
    # 读取任务索引
    index_file = os.path.join(cache_dir, "task_index.json")
    
    if os.path.exists(index_file):
        with open(index_file, 'r', encoding='utf-8') as f:
            task_index = json.load(f)
    else:
        task_index = {
            "tasks": [],
            "last_updated": datetime.datetime.now().isoformat()
        }
    
    # 提取索引信息
    task_id = task_info.get("task_id")
    index_info = {
        "task_id": task_id,
        "task_name": task_info.get("task_name"),
        "description": task_info.get("description"),
        "status": task_info.get("status"),
        "priority": task_info.get("priority"),
        "created_time": task_info.get("created_time"),
        "updated_time": task_info.get("updated_time"),
        "source_lang": task_info.get("source_lang"),
        "target_lang": task_info.get("target_lang"),
        "glossary_name": task_info.get("glossary_name"),
        "domain": task_info.get("domain"),
        "total_files": task_info.get("total_files"),
        "completed_files": task_info.get("completed_files"),
        "failed_files": task_info.get("failed_files"),
        "overall_progress": task_info.get("overall_progress")
    }
    
    # 更新或添加任务索引
    found = False
    for i, task in enumerate(task_index["tasks"]):
        if task.get("task_id") == task_id:
            task_index["tasks"][i] = index_info
            found = True
            break
    
    if not found:
        task_index["tasks"].append(index_info)
    
    # 更新索引文件
    task_index["last_updated"] = datetime.datetime.now().isoformat()
    
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(task_index, f, ensure_ascii=False, indent=2)


def _calculate_duration(start_time: Optional[str], end_time: Optional[str]) -> Optional[str]:
    """
    计算持续时间
    
    Args:
        start_time (Optional[str]): 开始时间
        end_time (Optional[str]): 结束时间
        
    Returns:
        Optional[str]: 持续时间字符串
    """
    if not start_time or not end_time:
        return None
    
    try:
        start = datetime.datetime.fromisoformat(start_time)
        end = datetime.datetime.fromisoformat(end_time)
        
        duration_seconds = (end - start).total_seconds()
        
        hours = int(duration_seconds // 3600)
        minutes = int((duration_seconds % 3600) // 60)
        seconds = int(duration_seconds % 60)
        
        if hours > 0:
            return f"{hours}小时{minutes}分{seconds}秒"
        else:
            return f"{minutes}分{seconds}秒"
    except:
        return None


def _process_batch_task(task_id: str, cache_dir: str) -> None:
    """
    处理批量翻译任务（后台线程）
    
    Args:
        task_id (str): 任务ID
        cache_dir (str): 缓存目录
    """
    # 构建任务文件路径
    task_dir = os.path.join(cache_dir, task_id)
    task_file = os.path.join(task_dir, "task.json")
    
    try:
        # 读取任务信息
        with open(task_file, 'r', encoding='utf-8') as f:
            task_info = json.load(f)
        
        # 导入必要的模块
        import sys
        import importlib.util
        
        # 导入翻译引擎和文档处理模块
        docx_processor_path = os.path.join("tools", "generated_tools", "medical_document_translation_agent", "docx_processor.py")
        translation_engine_path = os.path.join("tools", "generated_tools", "medical_document_translation_agent", "translation_engine.py")
        
        docx_processor_spec = importlib.util.spec_from_file_location("docx_processor", docx_processor_path)
        translation_engine_spec = importlib.util.spec_from_file_location("translation_engine", translation_engine_path)
        
        docx_processor = importlib.util.module_from_spec(docx_processor_spec)
        translation_engine = importlib.util.module_from_spec(translation_engine_spec)
        
        docx_processor_spec.loader.exec_module(docx_processor)
        translation_engine_spec.loader.exec_module(translation_engine)
        
        # 处理每个文件
        for i, file_item in enumerate(task_info["files"]):
            # 检查任务是否已取消
            with open(task_file, 'r', encoding='utf-8') as f:
                current_task_info = json.load(f)
            
            if current_task_info.get("status") == "cancelled":
                break
            
            # 只处理等待中的文件
            if file_item["status"] != "pending":
                continue
            
            # 更新文件状态
            file_item["status"] = "processing"
            file_item["start_time"] = datetime.datetime.now().isoformat()
            file_item["progress"] = 0.0
            
            # 保存任务信息
            with open(task_file, 'w', encoding='utf-8') as f:
                json.dump(task_info, f, ensure_ascii=False, indent=2)
            
            # 更新任务索引
            _update_task_index(task_info, cache_dir)
            
            try:
                # 读取源文档
                source_path = file_item["source_path"]
                result_path = file_item["result_path"]
                
                # 读取文档内容
                read_result = json.loads(docx_processor.read_docx(source_path, "json", False))
                
                if "error" in read_result:
                    raise Exception(read_result["error"])
                
                # 更新进度
                file_item["progress"] = 0.1
                with open(task_file, 'w', encoding='utf-8') as f:
                    json.dump(task_info, f, ensure_ascii=False, indent=2)
                
                # 提取文档结构
                document_data = read_result
                
                # 翻译段落内容
                if "content" in document_data and "paragraphs" in document_data["content"]:
                    total_paragraphs = len(document_data["content"]["paragraphs"])
                    
                    for p_idx, paragraph in enumerate(document_data["content"]["paragraphs"]):
                        # 翻译段落文本
                        if paragraph.get("text"):
                            translation_result = json.loads(translation_engine.translate_text(
                                paragraph["text"],
                                task_info["source_lang"],
                                task_info["target_lang"],
                                task_info["glossary_name"],
                                task_info["domain"],
                                True,
                                None
                            ))
                            
                            if "translation" in translation_result:
                                paragraph["text"] = translation_result["translation"]
                        
                        # 翻译格式化文本块
                        if "runs" in paragraph:
                            for run in paragraph["runs"]:
                                if run.get("text"):
                                    translation_result = json.loads(translation_engine.translate_text(
                                        run["text"],
                                        task_info["source_lang"],
                                        task_info["target_lang"],
                                        task_info["glossary_name"],
                                        task_info["domain"],
                                        True,
                                        None
                                    ))
                                    
                                    if "translation" in translation_result:
                                        run["text"] = translation_result["translation"]
                        
                        # 更新进度
                        progress = 0.1 + 0.6 * ((p_idx + 1) / total_paragraphs)
                        file_item["progress"] = round(progress, 2)
                        with open(task_file, 'w', encoding='utf-8') as f:
                            json.dump(task_info, f, ensure_ascii=False, indent=2)
                
                # 翻译表格内容
                if "content" in document_data and "tables" in document_data["content"]:
                    total_tables = len(document_data["content"]["tables"])
                    
                    for t_idx, table in enumerate(document_data["content"]["tables"]):
                        if "cells" in table:
                            total_cells = len(table["cells"])
                            
                            for c_idx, cell in enumerate(table["cells"]):
                                # 翻译单元格文本
                                if cell.get("text"):
                                    translation_result = json.loads(translation_engine.translate_text(
                                        cell["text"],
                                        task_info["source_lang"],
                                        task_info["target_lang"],
                                        task_info["glossary_name"],
                                        task_info["domain"],
                                        True,
                                        None
                                    ))
                                    
                                    if "translation" in translation_result:
                                        cell["text"] = translation_result["translation"]
                                
                                # 翻译单元格中的段落
                                if "paragraphs" in cell:
                                    for para in cell["paragraphs"]:
                                        if para.get("text"):
                                            translation_result = json.loads(translation_engine.translate_text(
                                                para["text"],
                                                task_info["source_lang"],
                                                task_info["target_lang"],
                                                task_info["glossary_name"],
                                                task_info["domain"],
                                                True,
                                                None
                                            ))
                                            
                                            if "translation" in translation_result:
                                                para["text"] = translation_result["translation"]
                                        
                                        # 翻译格式化文本块
                                        if "runs" in para:
                                            for run in para["runs"]:
                                                if run.get("text"):
                                                    translation_result = json.loads(translation_engine.translate_text(
                                                        run["text"],
                                                        task_info["source_lang"],
                                                        task_info["target_lang"],
                                                        task_info["glossary_name"],
                                                        task_info["domain"],
                                                        True,
                                                        None
                                                    ))
                                                    
                                                    if "translation" in translation_result:
                                                        run["text"] = translation_result["translation"]
                                
                                # 更新进度
                                if total_cells > 0:
                                    progress = 0.7 + 0.2 * ((t_idx * total_cells + c_idx + 1) / (total_tables * total_cells))
                                    file_item["progress"] = round(progress, 2)
                                    with open(task_file, 'w', encoding='utf-8') as f:
                                        json.dump(task_info, f, ensure_ascii=False, indent=2)
                
                # 翻译页眉页脚
                if "content" in document_data:
                    # 翻译页眉
                    if "headers" in document_data["content"]:
                        for header in document_data["content"]["headers"]:
                            if "paragraphs" in header:
                                for para in header["paragraphs"]:
                                    if para.get("text"):
                                        translation_result = json.loads(translation_engine.translate_text(
                                            para["text"],
                                            task_info["source_lang"],
                                            task_info["target_lang"],
                                            task_info["glossary_name"],
                                            task_info["domain"],
                                            True,
                                            None
                                        ))
                                        
                                        if "translation" in translation_result:
                                            para["text"] = translation_result["translation"]
                    
                    # 翻译页脚
                    if "footers" in document_data["content"]:
                        for footer in document_data["content"]["footers"]:
                            if "paragraphs" in footer:
                                for para in footer["paragraphs"]:
                                    if para.get("text"):
                                        translation_result = json.loads(translation_engine.translate_text(
                                            para["text"],
                                            task_info["source_lang"],
                                            task_info["target_lang"],
                                            task_info["glossary_name"],
                                            task_info["domain"],
                                            True,
                                            None
                                        ))
                                        
                                        if "translation" in translation_result:
                                            para["text"] = translation_result["translation"]
                
                # 更新进度
                file_item["progress"] = 0.9
                with open(task_file, 'w', encoding='utf-8') as f:
                    json.dump(task_info, f, ensure_ascii=False, indent=2)
                
                # 创建翻译后的文档
                create_result = json.loads(docx_processor.create_docx(document_data, result_path))
                
                if "error" in create_result:
                    raise Exception(create_result["error"])
                
                # 更新文件状态
                file_item["status"] = "completed"
                file_item["end_time"] = datetime.datetime.now().isoformat()
                file_item["progress"] = 1.0
                
                # 更新任务计数
                task_info["completed_files"] += 1
                
            except Exception as e:
                # 更新文件状态
                file_item["status"] = "failed"
                file_item["end_time"] = datetime.datetime.now().isoformat()
                file_item["error"] = str(e)
                
                # 更新任务计数
                task_info["failed_files"] += 1
            
            # 更新总体进度
            total_files = task_info["total_files"]
            if total_files > 0:
                task_info["overall_progress"] = round((task_info["completed_files"] + task_info["failed_files"]) / total_files, 2)
            
            # 保存任务信息
            task_info["updated_time"] = datetime.datetime.now().isoformat()
            with open(task_file, 'w', encoding='utf-8') as f:
                json.dump(task_info, f, ensure_ascii=False, indent=2)
            
            # 更新任务索引
            _update_task_index(task_info, cache_dir)
        
        # 检查是否所有文件都已处理
        all_processed = all(file_item["status"] in ["completed", "failed", "cancelled"] for file_item in task_info["files"])
        
        if all_processed:
            # 更新任务状态
            task_info["status"] = "completed"
            task_info["end_time"] = datetime.datetime.now().isoformat()
            task_info["updated_time"] = datetime.datetime.now().isoformat()
            
            # 保存任务信息
            with open(task_file, 'w', encoding='utf-8') as f:
                json.dump(task_info, f, ensure_ascii=False, indent=2)
            
            # 更新任务索引
            _update_task_index(task_info, cache_dir)
    
    except Exception as e:
        # 处理整体任务失败
        try:
            # 读取任务信息
            with open(task_file, 'r', encoding='utf-8') as f:
                task_info = json.load(f)
            
            # 更新任务状态
            task_info["status"] = "failed"
            task_info["end_time"] = datetime.datetime.now().isoformat()
            task_info["updated_time"] = datetime.datetime.now().isoformat()
            task_info["error"] = str(e)
            
            # 保存任务信息
            with open(task_file, 'w', encoding='utf-8') as f:
                json.dump(task_info, f, ensure_ascii=False, indent=2)
            
            # 更新任务索引
            _update_task_index(task_info, cache_dir)
        except:
            pass