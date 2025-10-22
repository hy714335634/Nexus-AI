#!/usr/bin/env python3
"""
缓存管理工具

提供任务缓存和进度跟踪功能，支持断点续传和任务状态管理
"""

import os
import json
import time
import csv
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

from strands import tool


@tool
def cache_task_progress(task_id: str, progress_data: str, 
                       overwrite: bool = False) -> str:
    """
    缓存任务进度数据
    
    Args:
        task_id: 任务唯一标识符
        progress_data: 任务进度数据(JSON字符串)
        overwrite: 是否覆盖现有缓存，默认为False
    
    Returns:
        JSON格式的缓存结果
    """
    try:
        # 解析进度数据
        try:
            progress = json.loads(progress_data) if isinstance(progress_data, str) else progress_data
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"解析进度数据失败: {str(e)}",
                "task_id": task_id,
                "cache_path": None
            }, ensure_ascii=False)
        
        # 确保缓存目录存在
        cache_dir = Path(".cache/company_info_search_agent")
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 构建缓存文件路径
        cache_file = cache_dir / f"{task_id}_progress.json"
        
        # 检查是否存在现有缓存
        if cache_file.exists() and not overwrite:
            return json.dumps({
                "status": "error",
                "message": f"任务缓存已存在，请使用overwrite=True覆盖或使用新的task_id",
                "task_id": task_id,
                "cache_path": str(cache_file)
            }, ensure_ascii=False)
        
        # 添加元数据
        progress["_metadata"] = {
            "task_id": task_id,
            "last_updated": time.time(),
            "cache_version": "1.0"
        }
        
        # 写入缓存文件
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
        
        return json.dumps({
            "status": "success",
            "message": f"成功缓存任务进度数据",
            "task_id": task_id,
            "cache_path": str(cache_file),
            "last_updated": progress["_metadata"]["last_updated"]
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"缓存任务进度时发生错误: {str(e)}",
            "task_id": task_id,
            "cache_path": None
        }, ensure_ascii=False)


@tool
def get_task_progress(task_id: str) -> str:
    """
    获取任务进度数据
    
    Args:
        task_id: 任务唯一标识符
    
    Returns:
        JSON格式的任务进度数据
    """
    try:
        # 构建缓存文件路径
        cache_dir = Path(".cache/company_info_search_agent")
        cache_file = cache_dir / f"{task_id}_progress.json"
        
        # 检查缓存文件是否存在
        if not cache_file.exists():
            return json.dumps({
                "status": "error",
                "message": f"任务缓存不存在: {task_id}",
                "task_id": task_id,
                "progress_data": None
            }, ensure_ascii=False)
        
        # 读取缓存文件
        with open(cache_file, "r", encoding="utf-8") as f:
            progress_data = json.load(f)
        
        return json.dumps({
            "status": "success",
            "message": f"成功获取任务进度数据",
            "task_id": task_id,
            "last_updated": progress_data.get("_metadata", {}).get("last_updated", 0),
            "progress_data": progress_data
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"获取任务进度时发生错误: {str(e)}",
            "task_id": task_id,
            "progress_data": None
        }, ensure_ascii=False)


@tool
def cache_company_info(task_id: str, company_name: str, company_data: str, 
                      overwrite: bool = False) -> str:
    """
    缓存单个公司的信息
    
    Args:
        task_id: 任务唯一标识符
        company_name: 公司名称
        company_data: 公司信息数据(JSON字符串)
        overwrite: 是否覆盖现有缓存，默认为False
    
    Returns:
        JSON格式的缓存结果
    """
    try:
        # 解析公司数据
        try:
            company_info = json.loads(company_data) if isinstance(company_data, str) else company_data
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"解析公司数据失败: {str(e)}",
                "task_id": task_id,
                "company_name": company_name,
                "cache_path": None
            }, ensure_ascii=False)
        
        # 确保缓存目录存在
        cache_dir = Path(f".cache/company_info_search_agent/{task_id}")
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 构建缓存文件路径 - 使用安全的文件名
        safe_name = "".join(c if c.isalnum() else "_" for c in company_name)
        cache_file = cache_dir / f"{safe_name}.json"
        
        # 检查是否存在现有缓存
        if cache_file.exists() and not overwrite:
            return json.dumps({
                "status": "error",
                "message": f"公司缓存已存在，请使用overwrite=True覆盖",
                "task_id": task_id,
                "company_name": company_name,
                "cache_path": str(cache_file)
            }, ensure_ascii=False)
        
        # 添加元数据
        company_info["_metadata"] = {
            "task_id": task_id,
            "company_name": company_name,
            "last_updated": time.time(),
            "cache_version": "1.0"
        }
        
        # 写入缓存文件
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(company_info, f, ensure_ascii=False, indent=2)
        
        return json.dumps({
            "status": "success",
            "message": f"成功缓存公司信息",
            "task_id": task_id,
            "company_name": company_name,
            "cache_path": str(cache_file),
            "last_updated": company_info["_metadata"]["last_updated"]
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"缓存公司信息时发生错误: {str(e)}",
            "task_id": task_id,
            "company_name": company_name,
            "cache_path": None
        }, ensure_ascii=False)


@tool
def get_company_info(task_id: str, company_name: str) -> str:
    """
    获取缓存的公司信息
    
    Args:
        task_id: 任务唯一标识符
        company_name: 公司名称
    
    Returns:
        JSON格式的公司信息数据
    """
    try:
        # 构建缓存文件路径
        safe_name = "".join(c if c.isalnum() else "_" for c in company_name)
        cache_dir = Path(f".cache/company_info_search_agent/{task_id}")
        cache_file = cache_dir / f"{safe_name}.json"
        
        # 检查缓存文件是否存在
        if not cache_file.exists():
            return json.dumps({
                "status": "error",
                "message": f"公司缓存不存在: {company_name}",
                "task_id": task_id,
                "company_name": company_name,
                "company_data": None
            }, ensure_ascii=False)
        
        # 读取缓存文件
        with open(cache_file, "r", encoding="utf-8") as f:
            company_data = json.load(f)
        
        return json.dumps({
            "status": "success",
            "message": f"成功获取公司信息",
            "task_id": task_id,
            "company_name": company_name,
            "last_updated": company_data.get("_metadata", {}).get("last_updated", 0),
            "company_data": company_data
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"获取公司信息时发生错误: {str(e)}",
            "task_id": task_id,
            "company_name": company_name,
            "company_data": None
        }, ensure_ascii=False)


@tool
def list_cached_companies(task_id: str) -> str:
    """
    列出任务中已缓存的所有公司
    
    Args:
        task_id: 任务唯一标识符
    
    Returns:
        JSON格式的缓存公司列表
    """
    try:
        # 构建缓存目录路径
        cache_dir = Path(f".cache/company_info_search_agent/{task_id}")
        
        # 检查缓存目录是否存在
        if not cache_dir.exists():
            return json.dumps({
                "status": "error",
                "message": f"任务缓存目录不存在: {task_id}",
                "task_id": task_id,
                "cached_companies": []
            }, ensure_ascii=False)
        
        # 获取所有JSON文件
        json_files = list(cache_dir.glob("*.json"))
        
        # 提取公司信息
        cached_companies = []
        for file in json_files:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    company_name = data.get("_metadata", {}).get("company_name", file.stem)
                    last_updated = data.get("_metadata", {}).get("last_updated", 0)
                    
                    cached_companies.append({
                        "company_name": company_name,
                        "file_name": file.name,
                        "last_updated": last_updated,
                        "last_updated_readable": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(last_updated))
                    })
            except Exception:
                # 如果读取失败，使用文件名作为公司名
                cached_companies.append({
                    "company_name": file.stem,
                    "file_name": file.name,
                    "last_updated": os.path.getmtime(file),
                    "last_updated_readable": time.strftime("%Y-%m-%d %H:%M:%S", 
                                                         time.localtime(os.path.getmtime(file)))
                })
        
        # 按最后更新时间排序
        cached_companies.sort(key=lambda x: x["last_updated"], reverse=True)
        
        return json.dumps({
            "status": "success",
            "message": f"成功获取缓存公司列表",
            "task_id": task_id,
            "total_companies": len(cached_companies),
            "cached_companies": cached_companies
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"列出缓存公司时发生错误: {str(e)}",
            "task_id": task_id,
            "cached_companies": []
        }, ensure_ascii=False)


@tool
def export_results_to_csv(task_id: str, output_path: str, 
                         include_fields: Optional[List[str]] = None) -> str:
    """
    将任务结果导出为CSV文件
    
    Args:
        task_id: 任务唯一标识符
        output_path: 输出CSV文件路径
        include_fields: 要包含的字段列表，如果不提供则包含所有字段
    
    Returns:
        JSON格式的导出结果
    """
    try:
        # 构建缓存目录路径
        cache_dir = Path(f".cache/company_info_search_agent/{task_id}")
        
        # 检查缓存目录是否存在
        if not cache_dir.exists():
            return json.dumps({
                "status": "error",
                "message": f"任务缓存目录不存在: {task_id}",
                "task_id": task_id,
                "output_path": output_path
            }, ensure_ascii=False)
        
        # 获取所有JSON文件
        json_files = list(cache_dir.glob("*.json"))
        
        if not json_files:
            return json.dumps({
                "status": "error",
                "message": f"任务缓存中没有公司数据: {task_id}",
                "task_id": task_id,
                "output_path": output_path
            }, ensure_ascii=False)
        
        # 收集所有公司数据
        companies_data = []
        for file in json_files:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # 移除元数据
                    if "_metadata" in data:
                        metadata = data.pop("_metadata")
                        # 保留公司名称
                        if "company_name" in metadata:
                            data["company_name"] = metadata["company_name"]
                    companies_data.append(data)
            except Exception as e:
                print(f"读取文件 {file} 时出错: {e}")
        
        if not companies_data:
            return json.dumps({
                "status": "error",
                "message": f"无法读取任何公司数据: {task_id}",
                "task_id": task_id,
                "output_path": output_path
            }, ensure_ascii=False)
        
        # 确定CSV字段
        all_fields = set()
        for company in companies_data:
            all_fields.update(company.keys())
        
        # 如果指定了字段，验证它们是否存在
        if include_fields:
            fields = [field for field in include_fields if field in all_fields]
            if not fields:
                fields = list(all_fields)
        else:
            fields = list(all_fields)
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 写入CSV文件
        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for company in companies_data:
                writer.writerow(company)
        
        return json.dumps({
            "status": "success",
            "message": f"成功导出任务结果到CSV文件",
            "task_id": task_id,
            "output_path": output_path,
            "total_companies": len(companies_data),
            "fields_exported": fields
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"导出结果到CSV时发生错误: {str(e)}",
            "task_id": task_id,
            "output_path": output_path
        }, ensure_ascii=False)


@tool
def generate_task_report(task_id: str) -> str:
    """
    生成任务报告，包括处理状态和统计信息
    
    Args:
        task_id: 任务唯一标识符
    
    Returns:
        JSON格式的任务报告
    """
    try:
        # 获取任务进度
        progress_cache_file = Path(f".cache/company_info_search_agent/{task_id}_progress.json")
        if not progress_cache_file.exists():
            return json.dumps({
                "status": "error",
                "message": f"任务进度缓存不存在: {task_id}",
                "task_id": task_id,
                "report": None
            }, ensure_ascii=False)
        
        with open(progress_cache_file, "r", encoding="utf-8") as f:
            progress_data = json.load(f)
        
        # 获取已缓存的公司列表
        cache_dir = Path(f".cache/company_info_search_agent/{task_id}")
        if not cache_dir.exists():
            cached_companies = []
            processed_count = 0
        else:
            json_files = list(cache_dir.glob("*.json"))
            cached_companies = []
            for file in json_files:
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        company_name = data.get("_metadata", {}).get("company_name", file.stem)
                        last_updated = data.get("_metadata", {}).get("last_updated", 0)
                        
                        cached_companies.append({
                            "company_name": company_name,
                            "file_name": file.name,
                            "last_updated": last_updated,
                            "last_updated_readable": time.strftime("%Y-%m-%d %H:%M:%S", 
                                                                 time.localtime(last_updated))
                        })
                except Exception:
                    # 如果读取失败，使用文件名作为公司名
                    cached_companies.append({
                        "company_name": file.stem,
                        "file_name": file.name,
                        "last_updated": os.path.getmtime(file),
                        "last_updated_readable": time.strftime("%Y-%m-%d %H:%M:%S", 
                                                             time.localtime(os.path.getmtime(file)))
                    })
            
            processed_count = len(cached_companies)
        
        # 计算任务统计信息
        total_companies = progress_data.get("total_companies", 0)
        processed_companies = progress_data.get("processed_companies", processed_count)
        failed_companies = progress_data.get("failed_companies", [])
        
        completion_rate = 0 if total_companies == 0 else (processed_companies / total_companies) * 100
        failure_rate = 0 if total_companies == 0 else (len(failed_companies) / total_companies) * 100
        
        # 计算处理时间
        start_time = progress_data.get("start_time", 0)
        last_updated = progress_data.get("_metadata", {}).get("last_updated", time.time())
        processing_time = last_updated - start_time if start_time > 0 else 0
        
        # 构建报告
        report = {
            "task_id": task_id,
            "report_time": time.time(),
            "report_time_readable": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "task_status": {
                "total_companies": total_companies,
                "processed_companies": processed_companies,
                "failed_companies": len(failed_companies),
                "completion_rate": round(completion_rate, 2),
                "failure_rate": round(failure_rate, 2),
                "is_completed": processed_companies >= total_companies,
                "current_batch": progress_data.get("current_batch", 0),
                "last_processed_index": progress_data.get("last_processed_index", 0)
            },
            "time_statistics": {
                "start_time": start_time,
                "start_time_readable": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time)) if start_time > 0 else "未知",
                "last_updated": last_updated,
                "last_updated_readable": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(last_updated)),
                "processing_time_seconds": round(processing_time, 2),
                "processing_time_readable": _format_time_duration(processing_time),
                "average_time_per_company": round(processing_time / processed_companies, 2) if processed_companies > 0 else 0
            },
            "failed_companies_details": failed_companies,
            "recent_processed": sorted(cached_companies, key=lambda x: x["last_updated"], reverse=True)[:5] if cached_companies else []
        }
        
        return json.dumps({
            "status": "success",
            "message": f"成功生成任务报告",
            "task_id": task_id,
            "report": report
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"生成任务报告时发生错误: {str(e)}",
            "task_id": task_id,
            "report": None
        }, ensure_ascii=False)


def _format_time_duration(seconds: float) -> str:
    """格式化时间持续时间为人类可读形式"""
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}分钟"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}小时"