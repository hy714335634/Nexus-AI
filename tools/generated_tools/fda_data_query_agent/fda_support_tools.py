#!/usr/bin/env python3
"""
FDA数据查询支持工具

提供缓存管理、数据解析、错误处理等支持功能，配合FDA API工具使用。
"""

import os
import json
import hashlib
import time
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from datetime import datetime, timedelta
from strands import tool


# 缓存配置
DEFAULT_CACHE_DIR = ".cache/fda_data_query_agent"
DEFAULT_CACHE_EXPIRATION_HOURS = 24
MAX_CACHE_SIZE_MB = 500


def _ensure_cache_dir(cache_dir: str = None) -> str:
    """
    确保缓存目录存在
    
    Args:
        cache_dir: 缓存目录路径
        
    Returns:
        缓存目录的绝对路径
    """
    if not cache_dir:
        cache_dir = DEFAULT_CACHE_DIR
    
    # 创建缓存目录
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    
    # 创建子目录
    subdirs = ["drugs", "devices", "food", "adverse_events", "recalls", "comprehensive"]
    for subdir in subdirs:
        Path(os.path.join(cache_dir, subdir)).mkdir(exist_ok=True)
    
    return cache_dir


def _generate_cache_key(query_params: Dict[str, Any]) -> str:
    """
    生成缓存键（基于查询参数的哈希值）
    
    Args:
        query_params: 查询参数
        
    Returns:
        SHA256哈希值
    """
    # 将参数转换为排序后的JSON字符串
    params_str = json.dumps(query_params, sort_keys=True)
    # 生成SHA256哈希
    return hashlib.sha256(params_str.encode()).hexdigest()


def _get_cache_file_path(cache_dir: str, category: str, cache_key: str) -> str:
    """
    获取缓存文件路径
    
    Args:
        cache_dir: 缓存目录
        category: 数据类别
        cache_key: 缓存键
        
    Returns:
        缓存文件的完整路径
    """
    return os.path.join(cache_dir, category, f"{cache_key}.json")


@tool
def cache_query_result(
    query_type: str,
    query_params: Dict[str, Any],
    result_data: str,
    cache_dir: str = None,
    expiration_hours: int = DEFAULT_CACHE_EXPIRATION_HOURS
) -> str:
    """
    缓存FDA查询结果
    
    Args:
        query_type (str): 查询类型（drugs/devices/food/adverse_events/recalls/comprehensive）
        query_params (Dict[str, Any]): 查询参数
        result_data (str): 查询结果（JSON字符串）
        cache_dir (str): 缓存目录，默认使用.cache/fda_data_query_agent
        expiration_hours (int): 缓存过期时间（小时），默认24小时
        
    Returns:
        str: JSON格式的缓存操作结果
        
    Example:
        >>> params = {"search_term": "aspirin", "limit": 10}
        >>> result = cache_query_result("drugs", params, query_result_json)
        >>> data = json.loads(result)
        >>> print(data["cache_key"])
    """
    try:
        # 确保缓存目录存在
        cache_dir = _ensure_cache_dir(cache_dir)
        
        # 生成缓存键
        cache_key = _generate_cache_key(query_params)
        
        # 解析结果数据
        try:
            result_obj = json.loads(result_data)
        except json.JSONDecodeError:
            return json.dumps({
                "status": "error",
                "error_message": "无效的JSON数据"
            }, ensure_ascii=False)
        
        # 构建缓存条目
        cache_entry = {
            "cache_key": cache_key,
            "query_type": query_type,
            "query_params": query_params,
            "cached_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=expiration_hours)).isoformat(),
            "expiration_hours": expiration_hours,
            "hit_count": 0,
            "data": result_obj
        }
        
        # 获取缓存文件路径
        cache_file = _get_cache_file_path(cache_dir, query_type, cache_key)
        
        # 写入缓存文件
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_entry, f, ensure_ascii=False, indent=2)
        
        # 检查缓存大小并清理
        _cleanup_cache_if_needed(cache_dir)
        
        return json.dumps({
            "status": "success",
            "cache_key": cache_key,
            "cache_file": cache_file,
            "cached_at": cache_entry["cached_at"],
            "expires_at": cache_entry["expires_at"]
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e)
        }, ensure_ascii=False)


@tool
def get_cached_result(
    query_type: str,
    query_params: Dict[str, Any],
    cache_dir: str = None,
    allow_expired: bool = False,
    max_expired_days: int = 7
) -> str:
    """
    从缓存中获取FDA查询结果
    
    Args:
        query_type (str): 查询类型（drugs/devices/food/adverse_events/recalls/comprehensive）
        query_params (Dict[str, Any]): 查询参数
        cache_dir (str): 缓存目录，默认使用.cache/fda_data_query_agent
        allow_expired (bool): 是否允许返回过期的缓存数据，默认False
        max_expired_days (int): 允许的最大过期天数（当allow_expired=True时），默认7天
        
    Returns:
        str: JSON格式的缓存查询结果，如果未找到则返回未命中状态
        
    Example:
        >>> params = {"search_term": "aspirin", "limit": 10}
        >>> result = get_cached_result("drugs", params)
        >>> data = json.loads(result)
        >>> if data["status"] == "hit":
        >>>     print(data["data"])
    """
    try:
        # 确保缓存目录存在
        cache_dir = _ensure_cache_dir(cache_dir)
        
        # 生成缓存键
        cache_key = _generate_cache_key(query_params)
        
        # 获取缓存文件路径
        cache_file = _get_cache_file_path(cache_dir, query_type, cache_key)
        
        # 检查缓存文件是否存在
        if not os.path.exists(cache_file):
            return json.dumps({
                "status": "miss",
                "cache_key": cache_key,
                "message": "缓存未命中"
            }, ensure_ascii=False)
        
        # 读取缓存文件
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_entry = json.load(f)
        
        # 检查缓存是否过期
        expires_at = datetime.fromisoformat(cache_entry["expires_at"])
        now = datetime.now()
        is_expired = now > expires_at
        
        # 如果过期且不允许返回过期数据
        if is_expired and not allow_expired:
            return json.dumps({
                "status": "expired",
                "cache_key": cache_key,
                "cached_at": cache_entry["cached_at"],
                "expires_at": cache_entry["expires_at"],
                "message": "缓存已过期"
            }, ensure_ascii=False)
        
        # 如果过期但允许返回过期数据，检查是否超过最大过期天数
        if is_expired:
            days_expired = (now - expires_at).days
            if days_expired > max_expired_days:
                return json.dumps({
                    "status": "too_old",
                    "cache_key": cache_key,
                    "days_expired": days_expired,
                    "message": f"缓存过期超过{max_expired_days}天"
                }, ensure_ascii=False)
        
        # 更新命中次数
        cache_entry["hit_count"] += 1
        cache_entry["last_hit_at"] = now.isoformat()
        
        # 写回缓存文件
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_entry, f, ensure_ascii=False, indent=2)
        
        # 返回缓存数据
        return json.dumps({
            "status": "hit",
            "cache_key": cache_key,
            "cached_at": cache_entry["cached_at"],
            "expires_at": cache_entry["expires_at"],
            "is_expired": is_expired,
            "hit_count": cache_entry["hit_count"],
            "data": cache_entry["data"]
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e)
        }, ensure_ascii=False)


@tool
def clear_cache(
    cache_dir: str = None,
    query_type: Optional[str] = None,
    older_than_hours: Optional[int] = None
) -> str:
    """
    清理缓存数据
    
    Args:
        cache_dir (str): 缓存目录，默认使用.cache/fda_data_query_agent
        query_type (Optional[str]): 要清理的查询类型，如果不提供则清理所有类型
        older_than_hours (Optional[int]): 清理超过指定小时数的缓存，如果不提供则清理所有缓存
        
    Returns:
        str: JSON格式的清理结果
        
    Example:
        >>> result = clear_cache(older_than_hours=48)  # 清理超过48小时的缓存
        >>> data = json.loads(result)
        >>> print(data["deleted_count"])
    """
    try:
        # 确保缓存目录存在
        cache_dir = _ensure_cache_dir(cache_dir)
        
        deleted_count = 0
        total_size_deleted = 0
        
        # 确定要清理的目录
        if query_type:
            target_dirs = [os.path.join(cache_dir, query_type)]
        else:
            target_dirs = [
                os.path.join(cache_dir, d) for d in 
                ["drugs", "devices", "food", "adverse_events", "recalls", "comprehensive"]
                if os.path.exists(os.path.join(cache_dir, d))
            ]
        
        # 遍历目录清理缓存
        for target_dir in target_dirs:
            if not os.path.exists(target_dir):
                continue
                
            for filename in os.listdir(target_dir):
                if not filename.endswith('.json'):
                    continue
                
                filepath = os.path.join(target_dir, filename)
                
                # 如果指定了时间限制，检查缓存时间
                if older_than_hours is not None:
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            cache_entry = json.load(f)
                        
                        cached_at = datetime.fromisoformat(cache_entry["cached_at"])
                        age_hours = (datetime.now() - cached_at).total_seconds() / 3600
                        
                        if age_hours < older_than_hours:
                            continue
                    except:
                        pass  # 如果无法读取，删除该文件
                
                # 获取文件大小
                file_size = os.path.getsize(filepath)
                
                # 删除文件
                os.remove(filepath)
                deleted_count += 1
                total_size_deleted += file_size
        
        return json.dumps({
            "status": "success",
            "deleted_count": deleted_count,
            "total_size_deleted_mb": round(total_size_deleted / (1024 * 1024), 2),
            "query_type": query_type or "all",
            "older_than_hours": older_than_hours
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e)
        }, ensure_ascii=False)


@tool
def get_cache_stats(cache_dir: str = None) -> str:
    """
    获取缓存统计信息
    
    Args:
        cache_dir (str): 缓存目录，默认使用.cache/fda_data_query_agent
        
    Returns:
        str: JSON格式的缓存统计信息
        
    Example:
        >>> result = get_cache_stats()
        >>> data = json.loads(result)
        >>> print(data["total_entries"])
    """
    try:
        # 确保缓存目录存在
        cache_dir = _ensure_cache_dir(cache_dir)
        
        stats = {
            "total_entries": 0,
            "total_size_mb": 0,
            "by_type": {},
            "expired_entries": 0,
            "oldest_entry": None,
            "newest_entry": None
        }
        
        # 统计各类型的缓存
        categories = ["drugs", "devices", "food", "adverse_events", "recalls", "comprehensive"]
        
        oldest_time = None
        newest_time = None
        
        for category in categories:
            category_dir = os.path.join(cache_dir, category)
            if not os.path.exists(category_dir):
                continue
            
            category_stats = {
                "count": 0,
                "size_mb": 0,
                "expired": 0,
                "total_hits": 0
            }
            
            for filename in os.listdir(category_dir):
                if not filename.endswith('.json'):
                    continue
                
                filepath = os.path.join(category_dir, filename)
                file_size = os.path.getsize(filepath)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        cache_entry = json.load(f)
                    
                    # 统计基本信息
                    category_stats["count"] += 1
                    category_stats["size_mb"] += file_size
                    category_stats["total_hits"] += cache_entry.get("hit_count", 0)
                    
                    # 检查是否过期
                    expires_at = datetime.fromisoformat(cache_entry["expires_at"])
                    if datetime.now() > expires_at:
                        category_stats["expired"] += 1
                        stats["expired_entries"] += 1
                    
                    # 更新最早和最新时间
                    cached_at = datetime.fromisoformat(cache_entry["cached_at"])
                    if oldest_time is None or cached_at < oldest_time:
                        oldest_time = cached_at
                    if newest_time is None or cached_at > newest_time:
                        newest_time = cached_at
                        
                except:
                    pass
            
            # 转换大小为MB
            category_stats["size_mb"] = round(category_stats["size_mb"] / (1024 * 1024), 2)
            
            stats["by_type"][category] = category_stats
            stats["total_entries"] += category_stats["count"]
            stats["total_size_mb"] += category_stats["size_mb"]
        
        # 格式化时间
        if oldest_time:
            stats["oldest_entry"] = oldest_time.isoformat()
        if newest_time:
            stats["newest_entry"] = newest_time.isoformat()
        
        stats["total_size_mb"] = round(stats["total_size_mb"], 2)
        stats["cache_dir"] = cache_dir
        
        return json.dumps({
            "status": "success",
            "stats": stats
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e)
        }, ensure_ascii=False)


def _cleanup_cache_if_needed(cache_dir: str) -> None:
    """
    如果缓存大小超过限制，使用LRU策略清理
    
    Args:
        cache_dir: 缓存目录
    """
    try:
        # 获取缓存统计
        stats_result = get_cache_stats(cache_dir)
        stats_data = json.loads(stats_result)
        
        if stats_data["status"] != "success":
            return
        
        total_size_mb = stats_data["stats"]["total_size_mb"]
        
        # 如果未超过限制，不需要清理
        if total_size_mb <= MAX_CACHE_SIZE_MB:
            return
        
        # 收集所有缓存文件及其最后访问时间
        cache_files = []
        categories = ["drugs", "devices", "food", "adverse_events", "recalls", "comprehensive"]
        
        for category in categories:
            category_dir = os.path.join(cache_dir, category)
            if not os.path.exists(category_dir):
                continue
            
            for filename in os.listdir(category_dir):
                if not filename.endswith('.json'):
                    continue
                
                filepath = os.path.join(category_dir, filename)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        cache_entry = json.load(f)
                    
                    last_access = cache_entry.get("last_hit_at", cache_entry["cached_at"])
                    last_access_time = datetime.fromisoformat(last_access)
                    file_size = os.path.getsize(filepath)
                    
                    cache_files.append({
                        "path": filepath,
                        "last_access": last_access_time,
                        "size": file_size
                    })
                except:
                    pass
        
        # 按最后访问时间排序（LRU）
        cache_files.sort(key=lambda x: x["last_access"])
        
        # 删除最旧的文件，直到缓存大小降到限制以下
        current_size_mb = total_size_mb
        for cache_file in cache_files:
            if current_size_mb <= MAX_CACHE_SIZE_MB * 0.8:  # 降到80%
                break
            
            os.remove(cache_file["path"])
            current_size_mb -= cache_file["size"] / (1024 * 1024)
            
    except:
        pass  # 清理失败不影响主流程


@tool
def parse_fda_drug_data(raw_data: str) -> str:
    """
    解析FDA药物数据，提取关键字段
    
    Args:
        raw_data (str): 原始FDA药物数据（JSON字符串）
        
    Returns:
        str: JSON格式的解析后数据，包含结构化的关键字段
        
    Example:
        >>> result = parse_fda_drug_data(query_result)
        >>> data = json.loads(result)
        >>> print(data["parsed_results"][0]["brand_name"])
    """
    try:
        # 解析原始数据
        try:
            raw_obj = json.loads(raw_data)
        except json.JSONDecodeError:
            return json.dumps({
                "status": "error",
                "error_message": "无效的JSON数据"
            }, ensure_ascii=False)
        
        # 提取结果数组
        results = raw_obj.get("data", {}).get("results", [])
        
        if not results:
            return json.dumps({
                "status": "success",
                "parsed_results": [],
                "message": "无数据可解析"
            }, ensure_ascii=False)
        
        # 解析每个结果
        parsed_results = []
        for item in results:
            openfda = item.get("openfda", {})
            
            parsed_item = {
                # 基本信息
                "brand_name": openfda.get("brand_name", ["Unknown"])[0] if openfda.get("brand_name") else "Unknown",
                "generic_name": openfda.get("generic_name", ["Unknown"])[0] if openfda.get("generic_name") else "Unknown",
                "manufacturer_name": openfda.get("manufacturer_name", ["Unknown"])[0] if openfda.get("manufacturer_name") else "Unknown",
                
                # 批准信息
                "application_number": openfda.get("application_number", ["Unknown"])[0] if openfda.get("application_number") else "Unknown",
                "product_type": openfda.get("product_type", ["Unknown"])[0] if openfda.get("product_type") else "Unknown",
                
                # 代码信息
                "ndc_codes": openfda.get("product_ndc", []),
                "spl_id": openfda.get("spl_id", ["Unknown"])[0] if openfda.get("spl_id") else "Unknown",
                
                # 标签信息
                "indications_and_usage": item.get("indications_and_usage", ["Not available"])[0] if item.get("indications_and_usage") else "Not available",
                "dosage_and_administration": item.get("dosage_and_administration", ["Not available"])[0] if item.get("dosage_and_administration") else "Not available",
                "warnings": item.get("warnings", ["Not available"])[0] if item.get("warnings") else "Not available",
                "adverse_reactions": item.get("adverse_reactions", ["Not available"])[0] if item.get("adverse_reactions") else "Not available",
                
                # 给药途径
                "route": openfda.get("route", []),
                
                # 来源信息
                "source": item.get("_fda_source", {})
            }
            
            parsed_results.append(parsed_item)
        
        return json.dumps({
            "status": "success",
            "parsed_count": len(parsed_results),
            "parsed_results": parsed_results
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e)
        }, ensure_ascii=False)


@tool
def parse_fda_device_data(raw_data: str) -> str:
    """
    解析FDA医疗设备数据，提取关键字段
    
    Args:
        raw_data (str): 原始FDA设备数据（JSON字符串）
        
    Returns:
        str: JSON格式的解析后数据，包含结构化的关键字段
    """
    try:
        # 解析原始数据
        try:
            raw_obj = json.loads(raw_data)
        except json.JSONDecodeError:
            return json.dumps({
                "status": "error",
                "error_message": "无效的JSON数据"
            }, ensure_ascii=False)
        
        # 提取结果数组
        results = raw_obj.get("data", {}).get("results", [])
        
        if not results:
            return json.dumps({
                "status": "success",
                "parsed_results": [],
                "message": "无数据可解析"
            }, ensure_ascii=False)
        
        # 解析每个结果
        parsed_results = []
        for item in results:
            openfda = item.get("openfda", {})
            
            parsed_item = {
                # 基本信息
                "device_name": item.get("device_name", "Unknown"),
                "device_class": item.get("device_class", "Unknown"),
                "product_code": item.get("product_code", "Unknown"),
                
                # 申请人信息
                "applicant": item.get("applicant", "Unknown"),
                "contact": item.get("contact", "Unknown"),
                
                # 批准信息
                "k_number": item.get("k_number", "Unknown"),
                "clearance_type": item.get("clearance_type", "Unknown"),
                "decision_date": item.get("decision_date", "Unknown"),
                "decision_description": item.get("decision_description", "Unknown"),
                
                # 设备描述
                "statement": item.get("statement", "Not available"),
                
                # 医学专业
                "medical_specialty": openfda.get("medical_specialty_description", "Unknown"),
                
                # 来源信息
                "source": item.get("_fda_source", {})
            }
            
            parsed_results.append(parsed_item)
        
        return json.dumps({
            "status": "success",
            "parsed_count": len(parsed_results),
            "parsed_results": parsed_results
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e)
        }, ensure_ascii=False)


@tool
def validate_search_parameters(
    search_term: str,
    search_field: str,
    query_type: str,
    limit: int = 10
) -> str:
    """
    验证FDA查询参数的有效性
    
    Args:
        search_term (str): 搜索词
        search_field (str): 搜索字段
        query_type (str): 查询类型（drugs/devices/food/adverse_events/recalls）
        limit (int): 结果数量限制
        
    Returns:
        str: JSON格式的验证结果
        
    Example:
        >>> result = validate_search_parameters("aspirin", "openfda.brand_name", "drugs")
        >>> data = json.loads(result)
        >>> if data["is_valid"]:
        >>>     print("参数有效")
    """
    try:
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": []
        }
        
        # 验证搜索词
        if not search_term or not search_term.strip():
            validation_result["is_valid"] = False
            validation_result["errors"].append("搜索词不能为空")
        elif len(search_term) < 2:
            validation_result["warnings"].append("搜索词过短，可能无法找到结果")
        elif len(search_term) > 200:
            validation_result["warnings"].append("搜索词过长，建议简化")
        
        # 验证查询类型
        valid_query_types = ["drugs", "devices", "food", "adverse_events", "recalls"]
        if query_type not in valid_query_types:
            validation_result["is_valid"] = False
            validation_result["errors"].append(f"无效的查询类型：{query_type}")
            validation_result["suggestions"].append(f"有效的查询类型：{', '.join(valid_query_types)}")
        
        # 验证搜索字段
        valid_fields = {
            "drugs": [
                "openfda.brand_name", "openfda.generic_name", "openfda.substance_name",
                "openfda.manufacturer_name", "openfda.product_ndc", "application_number"
            ],
            "devices": [
                "device_name", "openfda.device_name", "applicant", "product_code", "k_number"
            ],
            "food": [
                "product_description", "recalling_firm", "recall_number", "reason_for_recall"
            ],
            "adverse_events": [
                "patient.drug.openfda.brand_name", "patient.drug.openfda.generic_name",
                "patient.drug.medicinalproduct", "device.brand_name", "device.generic_name"
            ],
            "recalls": [
                "product_description", "recalling_firm", "recall_number", "reason_for_recall"
            ]
        }
        
        if query_type in valid_fields and search_field not in valid_fields[query_type]:
            validation_result["warnings"].append(f"搜索字段可能不适用于{query_type}类型")
            validation_result["suggestions"].append(f"建议使用：{', '.join(valid_fields[query_type][:3])}")
        
        # 验证结果数量限制
        if limit < 1:
            validation_result["is_valid"] = False
            validation_result["errors"].append("结果数量限制必须大于0")
        elif limit > 100:
            validation_result["warnings"].append("结果数量限制过大，将被限制为100")
        
        return json.dumps({
            "status": "success",
            "validation": validation_result
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e)
        }, ensure_ascii=False)


@tool
def generate_query_suggestions(
    failed_query: str,
    query_type: str,
    error_message: Optional[str] = None
) -> str:
    """
    为失败的查询生成改进建议
    
    Args:
        failed_query (str): 失败的查询词
        query_type (str): 查询类型
        error_message (Optional[str]): 错误信息
        
    Returns:
        str: JSON格式的查询建议
        
    Example:
        >>> result = generate_query_suggestions("asprin", "drugs", "No results found")
        >>> data = json.loads(result)
        >>> print(data["suggestions"])
    """
    try:
        suggestions = {
            "original_query": failed_query,
            "query_type": query_type,
            "suggestions": [],
            "examples": [],
            "possible_reasons": []
        }
        
        # 分析可能的原因
        if error_message and "not found" in error_message.lower():
            suggestions["possible_reasons"].extend([
                "产品名称拼写可能不正确",
                "产品可能未获FDA批准或数据未公开",
                "搜索词可能过于具体或包含不必要的信息"
            ])
        elif error_message and ("timeout" in error_message.lower() or "unavailable" in error_message.lower()):
            suggestions["possible_reasons"].extend([
                "FDA API暂时不可用",
                "网络连接问题",
                "请求超时"
            ])
        else:
            suggestions["possible_reasons"].append("查询参数可能不正确")
        
        # 生成改进建议
        if query_type == "drugs":
            suggestions["suggestions"].extend([
                "尝试使用药物的通用名（generic name）而非商品名",
                "使用活性成分名称进行搜索",
                "检查拼写，常见错误：asprin→aspirin",
                "使用更简单的搜索词，去除剂型和规格信息",
                "尝试搜索制造商名称"
            ])
            suggestions["examples"].extend([
                "aspirin",
                "acetaminophen",
                "ibuprofen",
                "Pfizer"
            ])
        elif query_type == "devices":
            suggestions["suggestions"].extend([
                "使用设备的通用名称",
                "尝试搜索制造商名称",
                "使用产品代码进行搜索",
                "检查设备名称的拼写"
            ])
            suggestions["examples"].extend([
                "pacemaker",
                "insulin pump",
                "Medtronic"
            ])
        elif query_type == "food":
            suggestions["suggestions"].extend([
                "使用产品类别而非具体品牌",
                "搜索召回原因（如salmonella）",
                "使用公司名称进行搜索"
            ])
            suggestions["examples"].extend([
                "salmonella",
                "listeria",
                "peanut butter"
            ])
        
        # 添加通用建议
        suggestions["suggestions"].extend([
            "简化搜索词，使用核心关键词",
            "如果使用商品名未找到，尝试使用通用名",
            "检查是否有拼写错误",
            "稍后重试（如果是API问题）"
        ])
        
        return json.dumps({
            "status": "success",
            "suggestions": suggestions
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e)
        }, ensure_ascii=False)


@tool
def format_fda_response(
    raw_data: str,
    format_type: str = "summary",
    include_source: bool = True
) -> str:
    """
    格式化FDA查询响应，使其更易读
    
    Args:
        raw_data (str): 原始FDA查询结果（JSON字符串）
        format_type (str): 格式类型，可选值:
            - summary: 摘要格式（默认）
            - detailed: 详细格式
            - minimal: 最小格式
        include_source (bool): 是否包含来源信息，默认True
        
    Returns:
        str: JSON格式的格式化结果
        
    Example:
        >>> result = format_fda_response(query_result, "summary")
        >>> data = json.loads(result)
        >>> print(data["formatted_text"])
    """
    try:
        # 解析原始数据
        try:
            raw_obj = json.loads(raw_data)
        except json.JSONDecodeError:
            return json.dumps({
                "status": "error",
                "error_message": "无效的JSON数据"
            }, ensure_ascii=False)
        
        # 检查查询状态
        if raw_obj.get("status") == "error":
            return json.dumps({
                "status": "success",
                "formatted_text": f"查询失败：{raw_obj.get('error_message', '未知错误')}\n建议：\n" + 
                                "\n".join(f"- {s}" for s in raw_obj.get("suggestions", []))
            }, ensure_ascii=False)
        
        query_type = raw_obj.get("query_type", "unknown")
        results = raw_obj.get("data", {}).get("results", [])
        
        if not results:
            return json.dumps({
                "status": "success",
                "formatted_text": "未找到匹配的FDA数据。\n\n请尝试：\n- 检查拼写\n- 使用更通用的搜索词\n- 尝试使用产品的通用名"
            }, ensure_ascii=False)
        
        formatted_lines = []
        
        # 添加查询摘要
        formatted_lines.append(f"FDA {query_type.upper()} 查询结果")
        formatted_lines.append("=" * 50)
        formatted_lines.append(f"找到 {len(results)} 条结果（共 {raw_obj.get('total_results', len(results))} 条）\n")
        
        # 格式化每个结果
        for idx, item in enumerate(results[:10], 1):  # 最多显示10条
            formatted_lines.append(f"\n【结果 {idx}】")
            formatted_lines.append("-" * 40)
            
            if query_type == "drugs":
                openfda = item.get("openfda", {})
                formatted_lines.append(f"品牌名: {openfda.get('brand_name', ['Unknown'])[0] if openfda.get('brand_name') else 'Unknown'}")
                formatted_lines.append(f"通用名: {openfda.get('generic_name', ['Unknown'])[0] if openfda.get('generic_name') else 'Unknown'}")
                formatted_lines.append(f"制造商: {openfda.get('manufacturer_name', ['Unknown'])[0] if openfda.get('manufacturer_name') else 'Unknown'}")
                
                if format_type == "detailed":
                    formatted_lines.append(f"申请号: {openfda.get('application_number', ['Unknown'])[0] if openfda.get('application_number') else 'Unknown'}")
                    if item.get("indications_and_usage"):
                        formatted_lines.append(f"适应症: {item['indications_and_usage'][0][:200]}...")
                        
            elif query_type == "devices":
                formatted_lines.append(f"设备名称: {item.get('device_name', 'Unknown')}")
                formatted_lines.append(f"设备分类: Class {item.get('device_class', 'Unknown')}")
                formatted_lines.append(f"制造商: {item.get('applicant', 'Unknown')}")
                
                if format_type == "detailed":
                    formatted_lines.append(f"510(k)号: {item.get('k_number', 'Unknown')}")
                    formatted_lines.append(f"批准日期: {item.get('decision_date', 'Unknown')}")
            
            # 添加来源信息
            if include_source and "_fda_source" in item:
                source = item["_fda_source"]
                formatted_lines.append(f"\n来源: FDA openFDA API")
                if "official_link" in source:
                    formatted_lines.append(f"官方链接: {source['official_link']}")
        
        # 如果结果超过10条，添加提示
        if len(results) > 10:
            formatted_lines.append(f"\n注意：仅显示前10条结果，共有{len(results)}条结果")
        
        formatted_text = "\n".join(formatted_lines)
        
        return json.dumps({
            "status": "success",
            "formatted_text": formatted_text,
            "format_type": format_type,
            "result_count": len(results)
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e)
        }, ensure_ascii=False)
