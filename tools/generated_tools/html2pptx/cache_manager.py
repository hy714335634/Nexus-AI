"""
缓存管理工具，用于实现本地缓存机制。

此模块提供了一组工具函数，用于管理本地缓存，包括缓存的创建、读取、更新和删除，
以及缓存策略的配置和管理。用于解决Token限制问题，提高处理效率。
"""

import os
import json
import time
import shutil
import hashlib
import tempfile
import pickle
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from pathlib import Path
from datetime import datetime, timedelta
from strands import tool


@tool
def initialize_cache(
    cache_dir: str = None,
    max_size_mb: int = 500,
    expiration_days: int = 7,
    create_if_missing: bool = True
) -> str:
    """
    初始化缓存系统。

    Args:
        cache_dir (str, optional): 缓存目录路径，如果不提供则使用系统临时目录下的子目录
        max_size_mb (int): 缓存最大大小（MB）
        expiration_days (int): 缓存项过期天数
        create_if_missing (bool): 如果缓存目录不存在，是否创建
        
    Returns:
        str: JSON格式的初始化结果
    """
    try:
        # 确定缓存目录
        if not cache_dir:
            cache_dir = os.path.join(tempfile.gettempdir(), "html2pptx_cache")
        
        # 创建缓存目录（如果需要）
        if not os.path.exists(cache_dir):
            if create_if_missing:
                os.makedirs(cache_dir)
            else:
                raise FileNotFoundError(f"缓存目录不存在: {cache_dir}")
        
        # 创建或更新缓存配置文件
        config = {
            "created_at": datetime.now().isoformat(),
            "max_size_mb": max_size_mb,
            "expiration_days": expiration_days,
            "version": "1.0"
        }
        
        config_path = os.path.join(cache_dir, "cache_config.json")
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        # 创建缓存子目录
        subdirs = ["images", "html", "data", "temp"]
        for subdir in subdirs:
            subdir_path = os.path.join(cache_dir, subdir)
            if not os.path.exists(subdir_path):
                os.makedirs(subdir_path)
        
        # 获取缓存统计信息
        stats = _get_cache_stats(cache_dir)
        
        # 构建响应
        response = {
            "status": "success",
            "message": "缓存系统初始化成功",
            "cache_dir": cache_dir,
            "config": config,
            "stats": stats
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "缓存系统初始化失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def cache_item(
    key: str,
    value: Any,
    cache_dir: str = None,
    category: str = "data",
    expiration_hours: int = 168,  # 7天
    serialize_method: str = "auto"
) -> str:
    """
    将项目存储到缓存中。

    Args:
        key (str): 缓存键
        value (Any): 要缓存的值
        cache_dir (str, optional): 缓存目录路径，如果不提供则使用系统临时目录下的子目录
        category (str): 缓存类别，可选值: "data", "images", "html", "temp"
        expiration_hours (int): 过期时间（小时）
        serialize_method (str): 序列化方法，可选值: "auto", "json", "pickle", "binary"
        
    Returns:
        str: JSON格式的缓存结果
    """
    try:
        # 确定缓存目录
        if not cache_dir:
            cache_dir = os.path.join(tempfile.gettempdir(), "html2pptx_cache")
        
        # 检查缓存目录是否存在
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        
        # 验证类别
        valid_categories = ["data", "images", "html", "temp"]
        if category not in valid_categories:
            category = "data"  # 默认使用data类别
        
        # 确保类别子目录存在
        category_dir = os.path.join(cache_dir, category)
        if not os.path.exists(category_dir):
            os.makedirs(category_dir)
        
        # 生成缓存键的哈希值作为文件名
        key_hash = hashlib.md5(key.encode()).hexdigest()
        
        # 确定序列化方法
        if serialize_method == "auto":
            # 根据值类型自动选择序列化方法
            if isinstance(value, (str, int, float, bool, list, dict)) and not isinstance(value, bytes):
                serialize_method = "json"
            else:
                serialize_method = "pickle"
        
        # 序列化数据
        if serialize_method == "json":
            # JSON序列化
            data_file = os.path.join(category_dir, f"{key_hash}.json")
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(value, f, ensure_ascii=False)
            content_type = "application/json"
        elif serialize_method == "pickle":
            # Pickle序列化
            data_file = os.path.join(category_dir, f"{key_hash}.pkl")
            with open(data_file, 'wb') as f:
                pickle.dump(value, f)
            content_type = "application/octet-stream"
        elif serialize_method == "binary":
            # 二进制数据
            if not isinstance(value, bytes):
                raise TypeError("使用binary序列化方法时，值必须是bytes类型")
            data_file = os.path.join(category_dir, f"{key_hash}.bin")
            with open(data_file, 'wb') as f:
                f.write(value)
            content_type = "application/octet-stream"
        else:
            raise ValueError(f"不支持的序列化方法: {serialize_method}")
        
        # 创建元数据文件
        metadata = {
            "key": key,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=expiration_hours)).isoformat(),
            "category": category,
            "content_type": content_type,
            "serialization": serialize_method,
            "size_bytes": os.path.getsize(data_file)
        }
        
        metadata_file = os.path.join(category_dir, f"{key_hash}.meta")
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        # 构建响应
        response = {
            "status": "success",
            "message": "项目已成功缓存",
            "key": key,
            "key_hash": key_hash,
            "category": category,
            "file_path": data_file,
            "size_bytes": metadata["size_bytes"],
            "expires_at": metadata["expires_at"],
            "serialization": serialize_method
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "缓存项目失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def retrieve_cached_item(
    key: str,
    cache_dir: str = None,
    category: str = None,
    default_value: Any = None
) -> str:
    """
    从缓存中检索项目。

    Args:
        key (str): 缓存键
        cache_dir (str, optional): 缓存目录路径，如果不提供则使用系统临时目录下的子目录
        category (str, optional): 缓存类别，如果不提供则搜索所有类别
        default_value (Any, optional): 如果项目不存在或已过期，返回的默认值
        
    Returns:
        str: JSON格式的检索结果，包含项目值和元数据
    """
    try:
        # 确定缓存目录
        if not cache_dir:
            cache_dir = os.path.join(tempfile.gettempdir(), "html2pptx_cache")
        
        # 检查缓存目录是否存在
        if not os.path.exists(cache_dir):
            raise FileNotFoundError(f"缓存目录不存在: {cache_dir}")
        
        # 生成缓存键的哈希值
        key_hash = hashlib.md5(key.encode()).hexdigest()
        
        # 确定要搜索的类别目录
        if category:
            categories = [category]
        else:
            categories = ["data", "images", "html", "temp"]
        
        # 在类别目录中查找元数据文件
        metadata_file = None
        for cat in categories:
            cat_dir = os.path.join(cache_dir, cat)
            if os.path.exists(cat_dir):
                temp_metadata_file = os.path.join(cat_dir, f"{key_hash}.meta")
                if os.path.exists(temp_metadata_file):
                    metadata_file = temp_metadata_file
                    category = cat
                    break
        
        # 如果找不到元数据文件，返回默认值
        if not metadata_file:
            return json.dumps({
                "status": "not_found",
                "message": "缓存项目不存在",
                "key": key,
                "value": default_value
            }, ensure_ascii=False, indent=2)
        
        # 读取元数据
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # 检查项目是否过期
        if "expires_at" in metadata:
            expires_at = datetime.fromisoformat(metadata["expires_at"])
            if expires_at < datetime.now():
                # 项目已过期，删除文件
                _delete_cache_files(cache_dir, key_hash, category)
                return json.dumps({
                    "status": "expired",
                    "message": "缓存项目已过期",
                    "key": key,
                    "value": default_value,
                    "expired_at": metadata["expires_at"]
                }, ensure_ascii=False, indent=2)
        
        # 确定数据文件路径和序列化方法
        serialization = metadata.get("serialization", "json")
        cat_dir = os.path.join(cache_dir, category)
        
        if serialization == "json":
            data_file = os.path.join(cat_dir, f"{key_hash}.json")
            if not os.path.exists(data_file):
                raise FileNotFoundError(f"缓存数据文件不存在: {data_file}")
            
            with open(data_file, 'r', encoding='utf-8') as f:
                value = json.load(f)
        
        elif serialization == "pickle":
            data_file = os.path.join(cat_dir, f"{key_hash}.pkl")
            if not os.path.exists(data_file):
                raise FileNotFoundError(f"缓存数据文件不存在: {data_file}")
            
            with open(data_file, 'rb') as f:
                value = pickle.load(f)
        
        elif serialization == "binary":
            data_file = os.path.join(cat_dir, f"{key_hash}.bin")
            if not os.path.exists(data_file):
                raise FileNotFoundError(f"缓存数据文件不存在: {data_file}")
            
            with open(data_file, 'rb') as f:
                value = f.read()
            
            # 二进制数据不能直接JSON序列化，返回文件路径
            return json.dumps({
                "status": "success",
                "message": "缓存项目检索成功（二进制数据）",
                "key": key,
                "file_path": data_file,
                "metadata": metadata,
                "is_binary": True
            }, ensure_ascii=False, indent=2)
        
        else:
            raise ValueError(f"不支持的序列化方法: {serialization}")
        
        # 构建响应
        response = {
            "status": "success",
            "message": "缓存项目检索成功",
            "key": key,
            "value": value,
            "metadata": metadata
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "检索缓存项目失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def delete_cached_item(
    key: str,
    cache_dir: str = None,
    category: str = None
) -> str:
    """
    从缓存中删除项目。

    Args:
        key (str): 缓存键
        cache_dir (str, optional): 缓存目录路径，如果不提供则使用系统临时目录下的子目录
        category (str, optional): 缓存类别，如果不提供则搜索所有类别
        
    Returns:
        str: JSON格式的删除结果
    """
    try:
        # 确定缓存目录
        if not cache_dir:
            cache_dir = os.path.join(tempfile.gettempdir(), "html2pptx_cache")
        
        # 检查缓存目录是否存在
        if not os.path.exists(cache_dir):
            raise FileNotFoundError(f"缓存目录不存在: {cache_dir}")
        
        # 生成缓存键的哈希值
        key_hash = hashlib.md5(key.encode()).hexdigest()
        
        # 确定要搜索的类别目录
        if category:
            categories = [category]
        else:
            categories = ["data", "images", "html", "temp"]
        
        # 在类别目录中查找并删除文件
        deleted_files = []
        found = False
        
        for cat in categories:
            cat_dir = os.path.join(cache_dir, cat)
            if os.path.exists(cat_dir):
                # 检查元数据文件
                metadata_file = os.path.join(cat_dir, f"{key_hash}.meta")
                if os.path.exists(metadata_file):
                    # 读取元数据以确定序列化方法
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        serialization = metadata.get("serialization", "json")
                    except:
                        serialization = "json"  # 默认假设为JSON
                    
                    # 删除数据文件
                    if serialization == "json":
                        data_file = os.path.join(cat_dir, f"{key_hash}.json")
                    elif serialization == "pickle":
                        data_file = os.path.join(cat_dir, f"{key_hash}.pkl")
                    elif serialization == "binary":
                        data_file = os.path.join(cat_dir, f"{key_hash}.bin")
                    else:
                        data_file = None
                    
                    if data_file and os.path.exists(data_file):
                        os.remove(data_file)
                        deleted_files.append(data_file)
                    
                    # 删除元数据文件
                    os.remove(metadata_file)
                    deleted_files.append(metadata_file)
                    
                    found = True
        
        # 构建响应
        if found:
            response = {
                "status": "success",
                "message": "缓存项目已删除",
                "key": key,
                "deleted_files": deleted_files
            }
        else:
            response = {
                "status": "not_found",
                "message": "缓存项目不存在",
                "key": key
            }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "删除缓存项目失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def clear_cache(
    cache_dir: str = None,
    category: str = None,
    older_than_days: int = None
) -> str:
    """
    清理缓存。

    Args:
        cache_dir (str, optional): 缓存目录路径，如果不提供则使用系统临时目录下的子目录
        category (str, optional): 要清理的缓存类别，如果不提供则清理所有类别
        older_than_days (int, optional): 清理指定天数之前的缓存项目，如果不提供则清理所有项目
        
    Returns:
        str: JSON格式的清理结果
    """
    try:
        # 确定缓存目录
        if not cache_dir:
            cache_dir = os.path.join(tempfile.gettempdir(), "html2pptx_cache")
        
        # 检查缓存目录是否存在
        if not os.path.exists(cache_dir):
            raise FileNotFoundError(f"缓存目录不存在: {cache_dir}")
        
        # 确定要清理的类别目录
        if category:
            categories = [category]
        else:
            categories = ["data", "images", "html", "temp"]
        
        # 获取清理前的统计信息
        before_stats = _get_cache_stats(cache_dir)
        
        # 清理缓存
        deleted_files = 0
        deleted_bytes = 0
        cutoff_date = datetime.now() - timedelta(days=older_than_days) if older_than_days else None
        
        for cat in categories:
            cat_dir = os.path.join(cache_dir, cat)
            if os.path.exists(cat_dir):
                # 获取目录中的所有文件
                files = os.listdir(cat_dir)
                
                # 查找元数据文件
                meta_files = [f for f in files if f.endswith('.meta')]
                
                for meta_file in meta_files:
                    meta_path = os.path.join(cat_dir, meta_file)
                    key_hash = meta_file[:-5]  # 移除.meta后缀
                    
                    try:
                        # 读取元数据
                        with open(meta_path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        
                        # 检查创建日期
                        if cutoff_date and "created_at" in metadata:
                            created_at = datetime.fromisoformat(metadata["created_at"])
                            if created_at > cutoff_date:
                                # 文件不够旧，跳过
                                continue
                        
                        # 删除相关文件
                        deleted_count, deleted_size = _delete_cache_files(cache_dir, key_hash, cat)
                        deleted_files += deleted_count
                        deleted_bytes += deleted_size
                    
                    except Exception as e:
                        # 如果读取元数据失败，尝试删除可能的相关文件
                        _delete_cache_files(cache_dir, key_hash, cat)
        
        # 获取清理后的统计信息
        after_stats = _get_cache_stats(cache_dir)
        
        # 构建响应
        response = {
            "status": "success",
            "message": "缓存清理完成",
            "deleted_files": deleted_files,
            "deleted_bytes": deleted_bytes,
            "deleted_mb": round(deleted_bytes / (1024 * 1024), 2),
            "before_cleanup": before_stats,
            "after_cleanup": after_stats
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "清理缓存失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def get_cache_info(
    cache_dir: str = None,
    include_items: bool = False
) -> str:
    """
    获取缓存系统信息。

    Args:
        cache_dir (str, optional): 缓存目录路径，如果不提供则使用系统临时目录下的子目录
        include_items (bool): 是否包含缓存项目列表
        
    Returns:
        str: JSON格式的缓存信息
    """
    try:
        # 确定缓存目录
        if not cache_dir:
            cache_dir = os.path.join(tempfile.gettempdir(), "html2pptx_cache")
        
        # 检查缓存目录是否存在
        if not os.path.exists(cache_dir):
            raise FileNotFoundError(f"缓存目录不存在: {cache_dir}")
        
        # 读取缓存配置
        config_path = os.path.join(cache_dir, "cache_config.json")
        config = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except:
                pass
        
        # 获取缓存统计信息
        stats = _get_cache_stats(cache_dir)
        
        # 构建基本响应
        response = {
            "status": "success",
            "cache_dir": cache_dir,
            "config": config,
            "stats": stats
        }
        
        # 如果需要，获取缓存项目列表
        if include_items:
            items = []
            categories = ["data", "images", "html", "temp"]
            
            for category in categories:
                cat_dir = os.path.join(cache_dir, category)
                if os.path.exists(cat_dir):
                    # 获取目录中的所有元数据文件
                    meta_files = [f for f in os.listdir(cat_dir) if f.endswith('.meta')]
                    
                    for meta_file in meta_files:
                        try:
                            meta_path = os.path.join(cat_dir, meta_file)
                            with open(meta_path, 'r', encoding='utf-8') as f:
                                metadata = json.load(f)
                            
                            # 添加项目信息
                            items.append({
                                "key": metadata.get("key", "unknown"),
                                "category": metadata.get("category", category),
                                "created_at": metadata.get("created_at", "unknown"),
                                "expires_at": metadata.get("expires_at", "unknown"),
                                "size_bytes": metadata.get("size_bytes", 0),
                                "content_type": metadata.get("content_type", "unknown"),
                                "serialization": metadata.get("serialization", "unknown")
                            })
                        except:
                            # 跳过无法读取的元数据文件
                            continue
            
            response["items"] = items
            response["item_count"] = len(items)
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "获取缓存信息失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def cached_operation(
    operation_key: str,
    operation_func_name: str,
    operation_args: Dict[str, Any],
    cache_dir: str = None,
    category: str = "data",
    expiration_hours: int = 168,  # 7天
    force_refresh: bool = False
) -> str:
    """
    执行缓存操作，如果缓存存在且未过期则使用缓存，否则执行操作并缓存结果。

    Args:
        operation_key (str): 操作的唯一标识符
        operation_func_name (str): 要执行的操作函数名称（字符串形式）
        operation_args (Dict[str, Any]): 操作函数的参数
        cache_dir (str, optional): 缓存目录路径，如果不提供则使用系统临时目录下的子目录
        category (str): 缓存类别
        expiration_hours (int): 缓存过期时间（小时）
        force_refresh (bool): 是否强制刷新缓存
        
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 确定缓存目录
        if not cache_dir:
            cache_dir = os.path.join(tempfile.gettempdir(), "html2pptx_cache")
        
        # 检查缓存目录是否存在
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        
        # 生成操作键
        # 注意：这里我们无法直接执行operation_func_name，因为它只是一个字符串名称
        # 实际使用时，需要在调用此函数前确保operation_func_name是可调用的
        
        # 检查是否需要强制刷新
        if not force_refresh:
            # 尝试从缓存获取结果
            cached_result_json = retrieve_cached_item(
                key=operation_key,
                cache_dir=cache_dir,
                category=category
            )
            
            cached_result = json.loads(cached_result_json)
            
            if cached_result["status"] == "success":
                # 缓存命中
                cached_result["cache_hit"] = True
                return json.dumps(cached_result, ensure_ascii=False, indent=2)
        
        # 缓存未命中或强制刷新，执行操作
        # 注意：在实际使用中，这里应该是执行operation_func_name，但在这个工具中我们无法直接执行
        # 相反，我们返回一个指示需要执行操作的结果
        
        response = {
            "status": "cache_miss",
            "message": "缓存未命中或强制刷新，需要执行操作",
            "operation_key": operation_key,
            "operation_func_name": operation_func_name,
            "operation_args": operation_args,
            "cache_info": {
                "cache_dir": cache_dir,
                "category": category,
                "expiration_hours": expiration_hours
            },
            "next_steps": "执行操作，然后使用cache_item函数缓存结果"
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "缓存操作失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


# 辅助函数

def _get_cache_stats(cache_dir: str) -> Dict[str, Any]:
    """获取缓存统计信息"""
    stats = {
        "total_size_bytes": 0,
        "total_size_mb": 0,
        "total_files": 0,
        "categories": {}
    }
    
    # 检查缓存目录是否存在
    if not os.path.exists(cache_dir):
        return stats
    
    # 统计各类别的文件数量和大小
    categories = ["data", "images", "html", "temp"]
    
    for category in categories:
        cat_dir = os.path.join(cache_dir, category)
        if os.path.exists(cat_dir):
            category_stats = {
                "size_bytes": 0,
                "size_mb": 0,
                "files": 0,
                "items": 0
            }
            
            # 统计文件
            for root, _, files in os.walk(cat_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_size = os.path.getsize(file_path)
                    
                    category_stats["size_bytes"] += file_size
                    category_stats["files"] += 1
                    
                    # 统计总数
                    stats["total_size_bytes"] += file_size
                    stats["total_files"] += 1
            
            # 统计缓存项目数量（通过元数据文件）
            meta_files = [f for f in os.listdir(cat_dir) if f.endswith('.meta')]
            category_stats["items"] = len(meta_files)
            
            # 转换为MB
            category_stats["size_mb"] = round(category_stats["size_bytes"] / (1024 * 1024), 2)
            
            # 添加到统计信息
            stats["categories"][category] = category_stats
    
    # 转换总大小为MB
    stats["total_size_mb"] = round(stats["total_size_bytes"] / (1024 * 1024), 2)
    
    return stats


def _delete_cache_files(cache_dir: str, key_hash: str, category: str) -> Tuple[int, int]:
    """删除与缓存键相关的文件，返回删除的文件数量和字节数"""
    deleted_count = 0
    deleted_bytes = 0
    
    cat_dir = os.path.join(cache_dir, category)
    if not os.path.exists(cat_dir):
        return deleted_count, deleted_bytes
    
    # 可能的文件扩展名
    extensions = [".meta", ".json", ".pkl", ".bin"]
    
    for ext in extensions:
        file_path = os.path.join(cat_dir, f"{key_hash}{ext}")
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            try:
                os.remove(file_path)
                deleted_count += 1
                deleted_bytes += file_size
            except:
                pass
    
    return deleted_count, deleted_bytes