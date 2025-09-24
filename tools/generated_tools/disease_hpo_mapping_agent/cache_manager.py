#!/usr/bin/env python3
"""
本地缓存管理工具

提供缓存管理功能，用于缓存常见疾病的HPO映射结果，提高查询效率
"""

import json
import os
import time
import hashlib
import shutil
from typing import Dict, List, Any, Optional, Union
import logging
from pathlib import Path
from strands import tool

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 默认缓存目录
DEFAULT_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache", "disease_hpo_mapper")

# 确保缓存目录存在
os.makedirs(DEFAULT_CACHE_DIR, exist_ok=True)


@tool
def cache_data(key: str, data: str, expiration_hours: int = 720, cache_dir: str = None) -> str:
    """
    将数据缓存到本地文件系统
    
    Args:
        key (str): 缓存键名，用于标识缓存项
        data (str): 要缓存的数据（字符串格式）
        expiration_hours (int): 缓存过期时间（小时），默认为720小时（30天）
        cache_dir (str): 缓存目录路径，如果不提供则使用默认目录
    
    Returns:
        str: JSON格式的缓存结果，包含缓存状态信息
    """
    try:
        # 使用默认缓存目录或指定目录
        cache_directory = cache_dir if cache_dir else DEFAULT_CACHE_DIR
        os.makedirs(cache_directory, exist_ok=True)
        
        # 生成缓存文件路径
        cache_key = _sanitize_key(key)
        cache_file = os.path.join(cache_directory, f"{cache_key}.json")
        
        # 创建缓存项
        cache_item = {
            "key": key,
            "data": data,
            "created_at": time.time(),
            "expires_at": time.time() + (expiration_hours * 3600),
            "expiration_hours": expiration_hours
        }
        
        # 写入缓存文件
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_item, f, ensure_ascii=False, indent=2)
        
        # 获取文件大小
        file_size = os.path.getsize(cache_file)
        
        return json.dumps({
            "success": True,
            "message": f"数据已成功缓存，键名: {key}",
            "key": key,
            "cache_file": cache_file,
            "expiration_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(cache_item["expires_at"])),
            "file_size_bytes": file_size
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"缓存数据时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"缓存失败: {str(e)}",
            "key": key
        }, ensure_ascii=False, indent=2)


@tool
def get_cached_data(key: str, cache_dir: str = None) -> str:
    """
    从本地缓存中获取数据
    
    Args:
        key (str): 缓存键名
        cache_dir (str): 缓存目录路径，如果不提供则使用默认目录
    
    Returns:
        str: JSON格式的缓存数据，如果缓存不存在或已过期则返回错误信息
    """
    try:
        # 使用默认缓存目录或指定目录
        cache_directory = cache_dir if cache_dir else DEFAULT_CACHE_DIR
        
        # 生成缓存文件路径
        cache_key = _sanitize_key(key)
        cache_file = os.path.join(cache_directory, f"{cache_key}.json")
        
        # 检查缓存文件是否存在
        if not os.path.exists(cache_file):
            return json.dumps({
                "success": False,
                "error": f"缓存不存在，键名: {key}",
                "key": key
            }, ensure_ascii=False, indent=2)
        
        # 读取缓存文件
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_item = json.load(f)
        
        # 检查缓存是否过期
        if time.time() > cache_item.get("expires_at", 0):
            return json.dumps({
                "success": False,
                "error": f"缓存已过期，键名: {key}",
                "key": key,
                "expired_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(cache_item.get("expires_at", 0)))
            }, ensure_ascii=False, indent=2)
        
        # 更新访问时间
        os.utime(cache_file, None)
        
        return json.dumps({
            "success": True,
            "key": key,
            "data": cache_item.get("data", ""),
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(cache_item.get("created_at", 0))),
            "expires_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(cache_item.get("expires_at", 0))),
            "remaining_hours": max(0, (cache_item.get("expires_at", 0) - time.time()) / 3600)
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"获取缓存数据时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"获取缓存失败: {str(e)}",
            "key": key
        }, ensure_ascii=False, indent=2)


@tool
def delete_cache(key: str, cache_dir: str = None) -> str:
    """
    删除指定的缓存项
    
    Args:
        key (str): 缓存键名
        cache_dir (str): 缓存目录路径，如果不提供则使用默认目录
    
    Returns:
        str: JSON格式的删除结果
    """
    try:
        # 使用默认缓存目录或指定目录
        cache_directory = cache_dir if cache_dir else DEFAULT_CACHE_DIR
        
        # 生成缓存文件路径
        cache_key = _sanitize_key(key)
        cache_file = os.path.join(cache_directory, f"{cache_key}.json")
        
        # 检查缓存文件是否存在
        if not os.path.exists(cache_file):
            return json.dumps({
                "success": False,
                "error": f"缓存不存在，键名: {key}",
                "key": key
            }, ensure_ascii=False, indent=2)
        
        # 删除缓存文件
        os.remove(cache_file)
        
        return json.dumps({
            "success": True,
            "message": f"缓存已成功删除，键名: {key}",
            "key": key
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"删除缓存时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"删除缓存失败: {str(e)}",
            "key": key
        }, ensure_ascii=False, indent=2)


@tool
def clear_cache(cache_dir: str = None, older_than_hours: int = None) -> str:
    """
    清除所有缓存或指定时间之前的缓存
    
    Args:
        cache_dir (str): 缓存目录路径，如果不提供则使用默认目录
        older_than_hours (int): 如果提供，只清除指定小时数之前的缓存
    
    Returns:
        str: JSON格式的清除结果
    """
    try:
        # 使用默认缓存目录或指定目录
        cache_directory = cache_dir if cache_dir else DEFAULT_CACHE_DIR
        
        # 确保缓存目录存在
        if not os.path.exists(cache_directory):
            return json.dumps({
                "success": False,
                "error": f"缓存目录不存在: {cache_directory}"
            }, ensure_ascii=False, indent=2)
        
        # 获取所有缓存文件
        cache_files = [f for f in os.listdir(cache_directory) if f.endswith('.json')]
        
        # 如果没有缓存文件
        if not cache_files:
            return json.dumps({
                "success": True,
                "message": "缓存目录为空，无需清理",
                "cache_directory": cache_directory
            }, ensure_ascii=False, indent=2)
        
        # 清除缓存
        deleted_count = 0
        skipped_count = 0
        
        for cache_file in cache_files:
            file_path = os.path.join(cache_directory, cache_file)
            
            # 如果指定了时间限制
            if older_than_hours is not None:
                file_mtime = os.path.getmtime(file_path)
                if time.time() - file_mtime < older_than_hours * 3600:
                    skipped_count += 1
                    continue
            
            # 删除文件
            os.remove(file_path)
            deleted_count += 1
        
        return json.dumps({
            "success": True,
            "message": f"缓存清理完成，已删除 {deleted_count} 个缓存项" + 
                      (f"，跳过 {skipped_count} 个较新的缓存项" if older_than_hours else ""),
            "cache_directory": cache_directory,
            "deleted_count": deleted_count,
            "skipped_count": skipped_count,
            "older_than_hours": older_than_hours
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"清除缓存时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"清除缓存失败: {str(e)}",
            "cache_directory": cache_dir if cache_dir else DEFAULT_CACHE_DIR
        }, ensure_ascii=False, indent=2)


@tool
def list_cache(cache_dir: str = None, include_expired: bool = True, include_content: bool = False) -> str:
    """
    列出所有缓存项
    
    Args:
        cache_dir (str): 缓存目录路径，如果不提供则使用默认目录
        include_expired (bool): 是否包含已过期的缓存项
        include_content (bool): 是否包含缓存内容
    
    Returns:
        str: JSON格式的缓存列表
    """
    try:
        # 使用默认缓存目录或指定目录
        cache_directory = cache_dir if cache_dir else DEFAULT_CACHE_DIR
        
        # 确保缓存目录存在
        if not os.path.exists(cache_directory):
            return json.dumps({
                "success": False,
                "error": f"缓存目录不存在: {cache_directory}"
            }, ensure_ascii=False, indent=2)
        
        # 获取所有缓存文件
        cache_files = [f for f in os.listdir(cache_directory) if f.endswith('.json')]
        
        # 如果没有缓存文件
        if not cache_files:
            return json.dumps({
                "success": True,
                "message": "缓存目录为空",
                "cache_directory": cache_directory,
                "cache_items": []
            }, ensure_ascii=False, indent=2)
        
        # 收集缓存项信息
        cache_items = []
        expired_count = 0
        valid_count = 0
        
        for cache_file in cache_files:
            file_path = os.path.join(cache_directory, cache_file)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    cache_item = json.load(f)
                
                # 检查是否过期
                is_expired = time.time() > cache_item.get("expires_at", 0)
                
                # 如果已过期且不包含过期项，则跳过
                if is_expired and not include_expired:
                    continue
                
                # 统计过期和有效项
                if is_expired:
                    expired_count += 1
                else:
                    valid_count += 1
                
                # 创建缓存项信息
                item_info = {
                    "key": cache_item.get("key", cache_file[:-5]),
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(cache_item.get("created_at", 0))),
                    "expires_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(cache_item.get("expires_at", 0))),
                    "is_expired": is_expired,
                    "file_size_bytes": os.path.getsize(file_path),
                    "remaining_hours": max(0, (cache_item.get("expires_at", 0) - time.time()) / 3600) if not is_expired else 0
                }
                
                # 如果需要包含内容
                if include_content:
                    item_info["data"] = cache_item.get("data", "")
                
                cache_items.append(item_info)
                
            except Exception as e:
                logger.warning(f"读取缓存文件 {cache_file} 时出错: {str(e)}")
                cache_items.append({
                    "key": cache_file[:-5],
                    "error": f"读取失败: {str(e)}",
                    "file_size_bytes": os.path.getsize(file_path)
                })
        
        # 按剩余时间排序
        cache_items.sort(key=lambda x: x.get("remaining_hours", 0), reverse=True)
        
        return json.dumps({
            "success": True,
            "cache_directory": cache_directory,
            "total_items": len(cache_items),
            "valid_items": valid_count,
            "expired_items": expired_count,
            "include_expired": include_expired,
            "include_content": include_content,
            "cache_items": cache_items
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"列出缓存时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"列出缓存失败: {str(e)}",
            "cache_directory": cache_dir if cache_dir else DEFAULT_CACHE_DIR
        }, ensure_ascii=False, indent=2)


@tool
def get_cache_stats(cache_dir: str = None) -> str:
    """
    获取缓存统计信息
    
    Args:
        cache_dir (str): 缓存目录路径，如果不提供则使用默认目录
    
    Returns:
        str: JSON格式的缓存统计信息
    """
    try:
        # 使用默认缓存目录或指定目录
        cache_directory = cache_dir if cache_dir else DEFAULT_CACHE_DIR
        
        # 确保缓存目录存在
        if not os.path.exists(cache_directory):
            return json.dumps({
                "success": False,
                "error": f"缓存目录不存在: {cache_directory}"
            }, ensure_ascii=False, indent=2)
        
        # 获取所有缓存文件
        cache_files = [f for f in os.listdir(cache_directory) if f.endswith('.json')]
        
        # 统计信息
        total_size = 0
        expired_count = 0
        valid_count = 0
        oldest_time = time.time()
        newest_time = 0
        
        # 收集统计信息
        for cache_file in cache_files:
            file_path = os.path.join(cache_directory, cache_file)
            file_size = os.path.getsize(file_path)
            total_size += file_size
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    cache_item = json.load(f)
                
                # 检查是否过期
                if time.time() > cache_item.get("expires_at", 0):
                    expired_count += 1
                else:
                    valid_count += 1
                
                # 更新最早和最新时间
                created_at = cache_item.get("created_at", 0)
                oldest_time = min(oldest_time, created_at)
                newest_time = max(newest_time, created_at)
                
            except Exception as e:
                logger.warning(f"读取缓存文件 {cache_file} 时出错: {str(e)}")
        
        # 格式化时间
        oldest_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(oldest_time)) if oldest_time < time.time() else "N/A"
        newest_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(newest_time)) if newest_time > 0 else "N/A"
        
        return json.dumps({
            "success": True,
            "cache_directory": cache_directory,
            "total_items": len(cache_files),
            "valid_items": valid_count,
            "expired_items": expired_count,
            "total_size_bytes": total_size,
            "total_size_kb": round(total_size / 1024, 2),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "oldest_item_time": oldest_time_str,
            "newest_item_time": newest_time_str,
            "cache_age_days": round((time.time() - oldest_time) / (24 * 3600), 2) if oldest_time < time.time() else 0
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"获取缓存统计信息时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"获取缓存统计信息失败: {str(e)}",
            "cache_directory": cache_dir if cache_dir else DEFAULT_CACHE_DIR
        }, ensure_ascii=False, indent=2)


@tool
def cached_operation(operation_key: str, operation_func: str, operation_args: Dict[str, Any], 
                    expiration_hours: int = 720, force_refresh: bool = False, cache_dir: str = None) -> str:
    """
    执行带缓存的操作，如果缓存存在且未过期则返回缓存结果，否则执行操作并缓存结果
    
    Args:
        operation_key (str): 操作的唯一标识符
        operation_func (str): 要执行的操作函数名称
        operation_args (Dict[str, Any]): 操作函数的参数
        expiration_hours (int): 缓存过期时间（小时），默认为720小时（30天）
        force_refresh (bool): 是否强制刷新缓存
        cache_dir (str): 缓存目录路径，如果不提供则使用默认目录
    
    Returns:
        str: 操作结果或缓存的结果
    """
    try:
        # 使用默认缓存目录或指定目录
        cache_directory = cache_dir if cache_dir else DEFAULT_CACHE_DIR
        
        # 生成缓存键
        cache_key = _sanitize_key(f"{operation_key}_{hash(json.dumps(operation_args, sort_keys=True))}")
        cache_file = os.path.join(cache_directory, f"{cache_key}.json")
        
        # 如果不强制刷新，尝试从缓存获取
        if not force_refresh and os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_item = json.load(f)
                
                # 检查缓存是否过期
                if time.time() <= cache_item.get("expires_at", 0):
                    logger.info(f"使用缓存结果: {operation_key}")
                    
                    # 更新访问时间
                    os.utime(cache_file, None)
                    
                    return json.dumps({
                        "success": True,
                        "from_cache": True,
                        "operation_key": operation_key,
                        "result": cache_item.get("data", ""),
                        "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(cache_item.get("created_at", 0))),
                        "expires_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(cache_item.get("expires_at", 0))),
                        "remaining_hours": max(0, (cache_item.get("expires_at", 0) - time.time()) / 3600)
                    }, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f"读取缓存失败，将执行操作: {str(e)}")
        
        # 执行操作
        logger.info(f"执行操作: {operation_func}")
        
        # 这里应该实现调用指定函数的逻辑
        # 由于我们不能直接动态调用函数，这里返回一个提示信息
        return json.dumps({
            "success": False,
            "error": "cached_operation工具需要与具体的操作函数集成使用",
            "operation_key": operation_key,
            "operation_func": operation_func,
            "suggestion": "请在您的代码中实现动态调用函数的逻辑，或者直接使用cache_data和get_cached_data工具"
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"执行缓存操作时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"执行缓存操作失败: {str(e)}",
            "operation_key": operation_key
        }, ensure_ascii=False, indent=2)


# 辅助函数

def _sanitize_key(key: str) -> str:
    """
    将缓存键转换为安全的文件名
    
    Args:
        key (str): 原始缓存键
    
    Returns:
        str: 安全的文件名
    """
    # 使用MD5哈希生成安全的文件名
    return hashlib.md5(key.encode('utf-8')).hexdigest()


def _is_json_serializable(obj: Any) -> bool:
    """
    检查对象是否可以序列化为JSON
    
    Args:
        obj (Any): 要检查的对象
    
    Returns:
        bool: 是否可以序列化为JSON
    """
    try:
        json.dumps(obj)
        return True
    except (TypeError, OverflowError):
        return False