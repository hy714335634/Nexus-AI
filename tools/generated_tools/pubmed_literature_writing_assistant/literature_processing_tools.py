#!/usr/bin/env python3
"""
PubMed文献处理工具

提供文献元数据加载、文献综述版本管理和处理状态跟踪功能
"""

import json
import os
import time
import uuid
import shutil
from pathlib import Path
from typing import Dict, List, Union, Optional, Any
from datetime import datetime
import threading
from strands import tool

@tool
def count_literature_content(file_path: str) -> str:
    """
    统计指定文件的文献综述内容字数，并给出建议
    
    Args:
        file_path (str): 文件路径
    Returns:
        str: JSON格式统计结果
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    count = len(content)
    print(f"文献综述内容字数: {count}")
    if count > 100000:
        return json.dumps({
            "status": "error",
            "message": "文献综述内容字数过长，建议减少内容长度至100000字以下",
            "count": count
        }, ensure_ascii=False)
    elif count < 10000:
        return json.dumps({
            "status": "error",
            "message": "文献综述内容过于简短，请补充必要详细内容",
            "count": count
        }, ensure_ascii=False)
    else:
        return json.dumps({
            "status": "success",
            "message": "文献综述内容字数统计成功",
            "count": count
        }, ensure_ascii=False)

@tool
def save_literature_content(research_id: str, content: str, version: str) -> str:
    """
    保存文献综述内容到文件
    
    Args:
        research_id (str): 研究ID，对应.cache/pmc_literature下的目录名
        content (str): 综述内容（Markdown格式）
        version (str): 版本标识，如"initial"、"final"或数字版本号
        
    Returns:
        str: JSON格式的保存状态和文件路径信息
    """
    try:
        # 构建保存目录路径
        cache_dir = Path(".cache/pmc_literature")
        research_dir = cache_dir / research_id
        reviews_dir = research_dir / "reviews"
        
        # 确保目录存在
        os.makedirs(reviews_dir, exist_ok=True)
        
        # 格式化版本标识
        version_str = str(version).lower()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 构建文件名
        if version_str in ["initial", "final"]:
            filename = f"review_{version_str}_{timestamp}.md"
        else:
            filename = f"review_v{version_str}_{timestamp}.md"
        
        file_path = reviews_dir / filename
        
        # 保存文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 返回成功结果
        return json.dumps({
            "status": "success",
            "message": f"文献综述版本 '{version}' 保存成功",
            "research_id": research_id,
            "version": version_str,
            "timestamp": timestamp,
            "file_path": str(file_path),
            "file_size": os.path.getsize(file_path)
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"保存文献综述版本时发生错误: {str(e)}"
        }, ensure_ascii=False)


@tool
def load_literature_fulltext(research_id: str, pmcid: str) -> str:
    """
    加载指定research_id和pmcid下的文献全文
    
    Args:
        research_id (str): 研究ID，对应.cache/pmc_literature下的目录名
        pmcid (str): 文献PMCID
    """
    try:
        # 构建文献全文路径
        cache_dir = Path(".cache/pmc_literature")
        research_dir = cache_dir / research_id
        paper_dir = research_dir / "paper"
        paper_path = paper_dir / f"{pmcid}.txt"
        
        # 检查目录和文件是否存在
        if not paper_path.exists():
            return json.dumps({
                "status": "error",
                "message": f"文献全文不存在",
                "path_checked": str(paper_path)
            }, ensure_ascii=False)
        
        # 读取并返回文献全文
        try:
            with open(paper_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return json.dumps({
                    "status": "success",
                    "content": content
                }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"读取文献全文文件时发生错误: {str(e)}"
            }, ensure_ascii=False)
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"加载文献全文时发生错误: {str(e)}"
        }, ensure_ascii=False)


@tool
def get_metadata_from_pmcid(research_id: str, pmcid: str) -> str:
    """
    从PMCID获取文献元数据
    
    Args:
        research_id (str): 研究ID
        pmcid (str): 文献PMCID
    Returns:
        str: JSON格式的文献元数据
    """
    try:
        # 构建文献全文路径
        cache_dir = Path(".cache/pmc_literature")
        research_dir = cache_dir / research_id
        metadata_path = research_dir / "manifest.json"
        
        # 检查目录和文件是否存在
        if not metadata_path.exists():
            return json.dumps({
                "status": "error",
                "message": f"manifest.json文件不存在",
                "path_checked": str(metadata_path)
            }, ensure_ascii=False)
        
        # 读取并解析metadata.json文件
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
            if "marked_literature" in metadata:
                for year_data in metadata["marked_literature"]["by_year"].values():
                    for literature in year_data["literature"]:
                        if literature["pmcid"] == pmcid:
                            return json.dumps({
                                "status": "success",
                                "message": "文献元数据加载成功",
                                "metadata": literature
                            }, ensure_ascii=False)
            return json.dumps({
                "status": "error",
                "message": "文献元数据不存在"
            }, ensure_ascii=False)
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"获取文献元数据时发生错误: {str(e)}"
        }, ensure_ascii=False)

@tool
def load_literature_metadata(research_id: str) -> str:
    """
    加载指定research_id下的manifest.json文件，获取所有推荐文献的元数据
    
    Args:
        research_id (str): 研究ID，对应.cache/pmc_literature下的目录名
        
    Returns:
        str: JSON格式的文献元数据列表或错误信息
    """
    try:
        # 构建manifest.json文件路径
        cache_dir = Path(".cache/pmc_literature")
        research_dir = cache_dir / research_id
        manifest_path = research_dir / "manifest.json"
        
        # 检查目录和文件是否存在
        if not research_dir.exists():
            return json.dumps({
                "status": "error",
                "message": f"研究ID '{research_id}' 对应的目录不存在",
                "path_checked": str(research_dir)
            }, ensure_ascii=False)
            
        if not manifest_path.exists():
            return json.dumps({
                "status": "error",
                "message": f"manifest.json文件不存在",
                "path_checked": str(manifest_path)
            }, ensure_ascii=False)
        
        # 读取并解析manifest.json文件
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)
            
            # 处理不同的manifest.json格式
            if isinstance(manifest_data, dict):
                # 如果manifest是字典格式，尝试提取文献列表
                if "marked_literature" in manifest_data:
                    # 处理marked_literature格式
                    marked_lit = manifest_data["marked_literature"]
                    all_literature = []
                    # 从by_year中提取所有文献
                    if isinstance(marked_lit, dict) and "by_year" in marked_lit:
                        for year_data in marked_lit["by_year"].values():
                            if isinstance(year_data, dict) and "literature" in year_data:
                                all_literature.extend(year_data["literature"])
                    elif isinstance(marked_lit, dict) and "literature" in marked_lit:
                        all_literature = marked_lit["literature"]
                    elif isinstance(marked_lit, list):
                        all_literature = marked_lit
                    metadata = all_literature
                elif "literature" in manifest_data:
                    metadata = manifest_data["literature"]
                else:
                    # 如果都没有，返回原始数据
                    metadata = manifest_data
            elif isinstance(manifest_data, list):
                metadata = manifest_data
            else:
                metadata = [manifest_data]
            
            # 返回成功结果
            literature_count = len(metadata) if isinstance(metadata, list) else 1
            return json.dumps({
                "status": "success",
                "message": "文献元数据加载成功",
                "research_id": research_id,
                "literature_count": literature_count,
                "metadata": metadata
            }, ensure_ascii=False)
            
        except json.JSONDecodeError as e:
            return json.dumps({
                "status": "error",
                "message": f"manifest.json解析错误: {str(e)}",
                "file_path": str(manifest_path)
            }, ensure_ascii=False)
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"加载文献元数据时发生错误: {str(e)}"
        }, ensure_ascii=False)


@tool
def save_review_version(research_id: str, content: str, version: Union[str, int]) -> str:
    """
    保存文献综述的特定版本
    
    Args:
        research_id (str): 研究ID，对应.cache/pmc_literature下的目录名, 请使用用户提供的id，不要自动生成
        content (str): 综述内容
        version (str, int): 版本标识，可以是数字或"initial"、"final"等特殊标记
        
    Returns:
        str: JSON格式的保存状态和文件路径信息
    """
    try:
        # 构建保存目录路径
        cache_dir = Path(".cache/pmc_literature")
        research_dir = cache_dir / research_id
        reviews_dir = research_dir / "reviews"
        
        # 确保目录存在
        os.makedirs(reviews_dir, exist_ok=True)
        
        # 格式化版本标识
        version_str = str(version).lower()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 构建文件名
        if version_str in ["initial", "final"]:
            filename = f"review_{version_str}_{timestamp}.md"
        else:
            filename = f"review_v{version_str}_{timestamp}.md"
        
        file_path = reviews_dir / filename
        
        # 保存文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 返回成功结果
        return json.dumps({
            "status": "success",
            "message": f"文献综述版本 '{version}' 保存成功",
            "research_id": research_id,
            "version": version_str,
            "timestamp": timestamp,
            "file_path": str(file_path),
            "file_size": os.path.getsize(file_path)
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"保存文献综述版本时发生错误: {str(e)}"
        }, ensure_ascii=False)


@tool
def get_processing_status(research_id: str, session_id: str) -> str:
    """
    获取当前文献处理状态（仅返回基本信息，不暴露具体进度）
    
    Args:
        research_id (str): 研究ID，对应.cache/pmc_literature下的目录名, 请使用用户提供的id，不要自动生成
        session_id (str): 会话ID，用于标识特定处理会话
        
    Returns:
        str: JSON格式的处理状态信息
    """
    try:
        # 构建状态文件路径
        cache_dir = Path(".cache/pmc_literature")
        research_dir = cache_dir / research_id
        status_dir = research_dir / "status"
        status_file = status_dir / f"{session_id}.json"
        
        # 确保目录存在
        os.makedirs(status_dir, exist_ok=True)
        
        # 如果状态文件不存在，创建初始状态
        if not status_file.exists():
            initial_status = {
                "research_id": research_id,
                "session_id": session_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "processed_literature": [],
                "current_version": None,
                "total_literature": 0,
                "completed": False
            }
            
            # 尝试从manifest.json获取文献总数
            try:
                manifest_path = research_dir / "manifest.json"
                if manifest_path.exists():
                    with open(manifest_path, 'r', encoding='utf-8') as f:
                        manifest_data = json.load(f)
                    
                    # 处理不同的manifest.json格式
                    if isinstance(manifest_data, dict):
                        if "marked_literature" in manifest_data:
                            marked_lit = manifest_data["marked_literature"]
                            all_literature = []
                            if isinstance(marked_lit, dict) and "by_year" in marked_lit:
                                for year_data in marked_lit["by_year"].values():
                                    if isinstance(year_data, dict) and "literature" in year_data:
                                        all_literature.extend(year_data["literature"])
                            elif isinstance(marked_lit, dict) and "literature" in marked_lit:
                                all_literature = marked_lit["literature"]
                            elif isinstance(marked_lit, list):
                                all_literature = marked_lit
                            initial_status["total_literature"] = len(all_literature)
                        elif "literature" in manifest_data:
                            initial_status["total_literature"] = len(manifest_data["literature"]) if isinstance(manifest_data["literature"], list) else 1
                        else:
                            initial_status["total_literature"] = 1
                    elif isinstance(manifest_data, list):
                        initial_status["total_literature"] = len(manifest_data)
                    else:
                        initial_status["total_literature"] = 1
            except Exception:
                pass  # 忽略manifest.json读取错误
            
            # 保存初始状态
            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump(initial_status, f, ensure_ascii=False, indent=2)
            
            return json.dumps({
                "status": "success",
                "message": "已创建初始处理状态",
                "exists": False,
                "is_completed": False,
                "processed_count": 0,
                "total_literature": initial_status.get("total_literature", 0),
                "pending_count": initial_status.get("total_literature", 0),
                "processed_literature": [],
                "current_version": None
            }, ensure_ascii=False)
        
        # 读取现有状态文件
        try:
            with open(status_file, 'r', encoding='utf-8') as f:
                processing_status = json.load(f)
            
            # 返回详细信息
            processed_count = len(processing_status.get("processed_literature", []))
            total_count = processing_status.get("total_literature", 0)
            processed_ids = processing_status.get("processed_literature", [])
            
            return json.dumps({
                "status": "success",
                "message": "获取处理状态成功",
                "exists": True,
                "is_completed": processing_status.get("completed", False),
                "current_version": processing_status.get("current_version"),
                "processed_count": processed_count,
                "total_literature": total_count,
                "pending_count": total_count - processed_count,
                "processed_literature": processed_ids,
                "created_at": processing_status.get("created_at"),
                "updated_at": processing_status.get("updated_at")
            }, ensure_ascii=False)
            
        except json.JSONDecodeError as e:
            return json.dumps({
                "status": "error",
                "message": f"状态文件解析错误: {str(e)}"
            }, ensure_ascii=False)
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"获取处理状态时发生错误: {str(e)}"
        }, ensure_ascii=False)


# 文件锁，用于处理并发更新
_file_locks = {}
_lock_lock = threading.Lock()

def _get_file_lock(file_path: str) -> threading.Lock:
    """获取文件锁"""
    with _lock_lock:
        if file_path not in _file_locks:
            _file_locks[file_path] = threading.Lock()
        return _file_locks[file_path]


@tool
def get_new_literature_fulltext(research_id: str, session_id: str) -> str:
    """
    获取未处理的文献全文和元数据（包含所有未处理文献）
    
    Args:
        research_id (str): 研究ID，对应.cache/pmc_literature下的目录名
        session_id (str): 会话ID，用于标识特定处理会话
        
    Returns:
        str: JSON格式的未处理文献列表，包含元数据和全文内容
    """
    try:
        # 构建路径
        cache_dir = Path(".cache/pmc_literature")
        research_dir = cache_dir / research_id
        manifest_path = research_dir / "manifest.json"
        status_dir = research_dir / "status"
        status_file = status_dir / f"{session_id}.json"
        
        # 读取manifest.json
        if not manifest_path.exists():
            return json.dumps({
                "status": "error",
                "message": "manifest.json文件不存在"
            }, ensure_ascii=False)
        
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest_data = json.load(f)
        
        # 读取已处理文献列表
        processed_ids = []
        if status_file.exists():
            with open(status_file, 'r', encoding='utf-8') as f:
                status = json.load(f)
                processed_ids = status.get("processed_literature", [])
        
        # 处理不同的manifest.json格式
        if isinstance(manifest_data, dict):
            if "marked_literature" in manifest_data:
                marked_lit = manifest_data["marked_literature"]
                all_metadata = []
                if isinstance(marked_lit, dict) and "by_year" in marked_lit:
                    for year_data in marked_lit["by_year"].values():
                        if isinstance(year_data, dict) and "literature" in year_data:
                            all_metadata.extend(year_data["literature"])
                elif isinstance(marked_lit, dict) and "literature" in marked_lit:
                    all_metadata = marked_lit["literature"]
                elif isinstance(marked_lit, list):
                    all_metadata = marked_lit
            elif "literature" in manifest_data:
                all_metadata = manifest_data["literature"]
            else:
                all_metadata = list(manifest_data.values()) if manifest_data else []
        elif isinstance(manifest_data, list):
            all_metadata = manifest_data
        else:
            all_metadata = [manifest_data]
        
        # 筛选未处理的文献并加载全文
        pending_literatures = []
        paper_dir = research_dir / "paper"
        
        for meta in all_metadata:
            lit_id = meta.get("pmcid") or meta.get("id") or meta.get("pmid")
            
            if lit_id and lit_id not in processed_ids:
                paper_path = paper_dir / f"{lit_id}.txt"
                
                # 加载全文
                fulltext = ""
                if paper_path.exists():
                    try:
                        with open(paper_path, 'r', encoding='utf-8') as f:
                            fulltext = f.read()
                    except Exception:
                        pass
                
                pending_literatures.append({
                    "pmcid": lit_id,
                    "metadata": meta,
                    "fulltext": fulltext,
                    "has_fulltext": len(fulltext) > 0
                })
        
        return json.dumps({
            "status": "success",
            "message": f"找到 {len(pending_literatures)} 篇未处理文献",
            "pending_count": len(pending_literatures),
            "literatures": pending_literatures
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"获取未处理文献时发生错误: {str(e)}"
        }, ensure_ascii=False)


@tool
def get_pre_generated_literature(research_id: str) -> str:
    """
    获取最新生成的文献综述版本内容
    
    Args:
        research_id (str): 研究ID，对应.cache/pmc_literature下的目录名
        
    Returns:
        str: JSON格式的最新综述内容和文件信息
    """
    try:
        cache_dir = Path(".cache/pmc_literature")
        research_dir = cache_dir / research_id
        reviews_dir = research_dir / "reviews"
        
        # 检查目录是否存在
        if not reviews_dir.exists():
            return json.dumps({
                "status": "success",
                "message": "暂无已生成的综述",
                "has_content": False
            }, ensure_ascii=False)
        
        # 方法1：尝试从status文件读取当前版本路径
        status_file = research_dir / "step4.status"
        if status_file.exists():
            try:
                with open(status_file, 'r', encoding='utf-8') as f:
                    status = json.load(f)
                
                if status.get("version_file_path"):
                    version_path = status["version_file_path"]
                    file_path = Path(version_path) if not os.path.isabs(version_path) else Path(version_path)
                    
                    if file_path.exists():
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        return json.dumps({
                            "status": "success",
                            "message": "从status获取最新综述成功",
                            "has_content": True,
                            "file_path": str(file_path),
                            "file_name": file_path.name,
                            "content": content,
                            "file_size": len(content)
                        }, ensure_ascii=False)
            except Exception:
                pass  # 如果status读取失败，继续用文件排序方法
        
        # 方法2：按文件名中的版本号排序
        def extract_version(filename: str) -> tuple:
            """提取版本号和优先级
            返回: (priority, version_number, timestamp_str)
            initial=0, 数字版本直接比较"""
            name = filename.name
            if name.startswith("review_initial_"):
                timestamp = name.replace("review_initial_", "").replace(".md", "")
                return (0, 0, timestamp)
            elif name.startswith("review_v"):
                # review_v{version}_{timestamp}.md
                parts = name.replace("review_v", "").replace(".md", "").split("_")
                if parts:
                    try:
                        version_num = int(parts[0])
                        timestamp = "_".join(parts[1:]) if len(parts) > 1 else ""
                        return (1, version_num, timestamp)
                    except:
                        return (2, 0, name)  # 无法解析，放到最后
            elif name.startswith("review_final_"):
                timestamp = name.replace("review_final_", "").replace(".md", "")
                return (3, 999999, timestamp)  # final 放到最后但优先级最高
            return (4, -1, name)  # 未知格式
        
        review_files = list(reviews_dir.glob("review_*.md"))
        
        if not review_files:
            return json.dumps({
                "status": "success",
                "message": "暂无已生成的综述",
                "has_content": False
            }, ensure_ascii=False)
        
        # 按版本号排序
        sorted_files = sorted(review_files, key=extract_version)
        latest_file = sorted_files[-1]  # 获取版本号最大的
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return json.dumps({
            "status": "success",
            "message": "获取最新综述成功",
            "has_content": True,
            "file_path": str(latest_file),
            "file_name": latest_file.name,
            "content": content,
            "file_size": len(content)
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"获取已生成综述时发生错误: {str(e)}"
        }, ensure_ascii=False)

@tool
def mark_all_metadata_processed(research_id: str, session_id: str, version: str = "initial") -> str:
    """
    标记所有文献的元数据已处理（用于initial版本生成后）
    
    Args:
        research_id (str): 研究ID，对应.cache/pmc_literature下的目录名
        session_id (str): 会话ID，用于标识特定处理会话
        version (str): 当前版本标识
        
    Returns:
        str: JSON格式的更新后的处理状态
    """
    try:
        # 构建状态文件路径
        cache_dir = Path(".cache/pmc_literature")
        research_dir = cache_dir / research_id
        status_dir = research_dir / "status"
        status_file = status_dir / f"{session_id}.json"
        
        # 确保目录存在
        os.makedirs(status_dir, exist_ok=True)
        
        # 获取文件锁
        file_lock = _get_file_lock(str(status_file))
        
        with file_lock:
            # 读取现有状态
            if not status_file.exists():
                return json.dumps({
                    "status": "error",
                    "message": "状态文件不存在，请先创建"
                }, ensure_ascii=False)
            
            with open(status_file, 'r', encoding='utf-8') as f:
                processing_status = json.load(f)
            
            # 获取所有文献ID
            try:
                manifest_path = research_dir / "manifest.json"
                if not manifest_path.exists():
                    return json.dumps({
                        "status": "error",
                        "message": "manifest.json文件不存在"
                    }, ensure_ascii=False)
                
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest_data = json.load(f)
                
                # 处理不同的manifest.json格式
                all_literature = []
                if isinstance(manifest_data, dict):
                    if "marked_literature" in manifest_data:
                        marked_lit = manifest_data["marked_literature"]
                        if isinstance(marked_lit, dict) and "by_year" in marked_lit:
                            for year_data in marked_lit["by_year"].values():
                                if isinstance(year_data, dict) and "literature" in year_data:
                                    all_literature.extend(year_data["literature"])
                        elif isinstance(marked_lit, dict) and "literature" in marked_lit:
                            all_literature = marked_lit["literature"]
                        elif isinstance(marked_lit, list):
                            all_literature = marked_lit
                    elif "literature" in manifest_data:
                        all_literature = manifest_data["literature"]
                elif isinstance(manifest_data, list):
                    all_literature = manifest_data
                
                # 提取所有文献ID
                all_ids = []
                for meta in all_literature:
                    lit_id = meta.get("pmcid") or meta.get("id") or meta.get("pmid")
                    if lit_id and lit_id not in all_ids:
                        all_ids.append(lit_id)
                
                # 更新已处理列表
                processing_status["processed_literature"] = all_ids
                processing_status["current_version"] = version
                processing_status["updated_at"] = datetime.now().isoformat()
                
                # 保存状态
                with open(status_file, 'w', encoding='utf-8') as f:
                    json.dump(processing_status, f, ensure_ascii=False, indent=2)
                
                return json.dumps({
                    "status": "success",
                    "message": f"已标记 {len(all_ids)} 篇文献的元数据为已处理",
                    "processed_count": len(all_ids),
                    "total_literature": processing_status.get("total_literature", 0),
                    "current_version": version
                }, ensure_ascii=False)
                
            except Exception as e:
                return json.dumps({
                    "status": "error",
                    "message": f"处理manifest.json时出错: {str(e)}"
                }, ensure_ascii=False)
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"标记元数据已处理时发生错误: {str(e)}"
        }, ensure_ascii=False)


@tool
def update_processing_status(
    research_id: str, 
    session_id: str, 
    processed_literature_id: str, 
    current_version: Union[str, int]
) -> str:
    """
    更新文献处理进度状态
    
    Args:
        research_id (str): 研究ID，对应.cache/pmc_literature下的目录名, 请使用用户提供的id，不要自动生成
        session_id (str): 会话ID，用于标识特定处理会话
        processed_literature_id (str): 已处理的文献ID
        current_version (str, int): 当前综述版本
        
    Returns:
        str: JSON格式的更新后的处理状态
    """
    try:
        # 构建状态文件路径
        cache_dir = Path(".cache/pmc_literature")
        research_dir = cache_dir / research_id
        status_dir = research_dir / "status"
        status_file = status_dir / f"{session_id}.json"
        
        # 确保目录存在
        os.makedirs(status_dir, exist_ok=True)
        
        # 获取文件锁
        file_lock = _get_file_lock(str(status_file))
        
        with file_lock:
            # 读取现有状态或创建新状态
            if status_file.exists():
                try:
                    with open(status_file, 'r', encoding='utf-8') as f:
                        processing_status = json.load(f)
                except json.JSONDecodeError:
                    # 文件损坏，创建新状态
                    processing_status = {
                        "research_id": research_id,
                        "session_id": session_id,
                        "created_at": datetime.now().isoformat(),
                        "processed_literature": [],
                        "current_version": None,
                        "total_literature": 0,
                        "completed": False
                    }
            else:
                # 创建新状态
                processing_status = {
                    "research_id": research_id,
                    "session_id": session_id,
                    "created_at": datetime.now().isoformat(),
                    "processed_literature": [],
                    "current_version": None,
                    "total_literature": 0,
                    "completed": False
                }
                
                # 尝试从manifest.json获取文献总数
                try:
                    manifest_path = research_dir / "manifest.json"
                    if manifest_path.exists():
                        with open(manifest_path, 'r', encoding='utf-8') as f:
                            manifest_data = json.load(f)
                        
                        # 处理不同的manifest.json格式
                        if isinstance(manifest_data, dict):
                            if "marked_literature" in manifest_data:
                                marked_lit = manifest_data["marked_literature"]
                                all_literature = []
                                if isinstance(marked_lit, dict) and "by_year" in marked_lit:
                                    for year_data in marked_lit["by_year"].values():
                                        if isinstance(year_data, dict) and "literature" in year_data:
                                            all_literature.extend(year_data["literature"])
                                elif isinstance(marked_lit, dict) and "literature" in marked_lit:
                                    all_literature = marked_lit["literature"]
                                elif isinstance(marked_lit, list):
                                    all_literature = marked_lit
                                processing_status["total_literature"] = len(all_literature)
                            elif "literature" in manifest_data:
                                processing_status["total_literature"] = len(manifest_data["literature"]) if isinstance(manifest_data["literature"], list) else 1
                            else:
                                processing_status["total_literature"] = 1
                        elif isinstance(manifest_data, list):
                            processing_status["total_literature"] = len(manifest_data)
                        else:
                            processing_status["total_literature"] = 1
                except Exception:
                    pass  # 忽略manifest.json读取错误
            
            # 更新状态
            # 忽略特殊标记符（如"all"、"initial_marker"等），这些不应作为文献ID
            if processed_literature_id and processed_literature_id.lower() not in ["all", "initial_marker", "none", "null"]:
                if processed_literature_id not in processing_status["processed_literature"]:
                    processing_status["processed_literature"].append(processed_literature_id)
            
            processing_status["current_version"] = str(current_version)
            processing_status["updated_at"] = datetime.now().isoformat()
            
            # 检查是否所有文献都已处理
            total = processing_status.get("total_literature", 0)
            processed = len(processing_status["processed_literature"])
            
            if total > 0 and processed >= total:
                processing_status["completed"] = True
            
            # 创建备份
            if status_file.exists():
                backup_file = status_dir / f"{session_id}_backup_{int(time.time())}.json"
                shutil.copy2(status_file, backup_file)
            
            # 保存更新后的状态
            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump(processing_status, f, ensure_ascii=False, indent=2)
            
            # 计算进度百分比
            progress_percentage = (processed / total * 100) if total > 0 else 0
            
            return json.dumps({
                "status": "success",
                "message": "处理状态更新成功",
                "research_id": research_id,
                "session_id": session_id,
                "processing_status": processing_status,
                "progress": {
                    "processed": processed,
                    "total": total,
                    "percentage": round(progress_percentage, 2)
                }
            }, ensure_ascii=False)
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"更新处理状态时发生错误: {str(e)}"
        }, ensure_ascii=False)


@tool
def append_literature_content_part(research_id: str, version: str, part_id: int, content: str) -> str:
    """
    分段追加文献综述内容到文件，用于处理长文本避免token限制，请仅在必须时使用
    
    Args:
        research_id (str): 研究ID，对应.cache/pmc_literature下的目录名
        version (str): 版本标识，如"initial"、"final"或数字版本号
        part_id (int): 分段ID，用于标识当前写入的部分（1、2、3...等数字）
        content (str): 当前分段的内容（Markdown格式）
        
    Returns:
        str: JSON格式的写入状态和内容长度信息
    """
    try:
        # 构建保存目录路径
        cache_dir = Path(".cache/pmc_literature")
        research_dir = cache_dir / research_id
        reviews_dir = research_dir / "reviews"
        
        # 确保目录存在
        os.makedirs(reviews_dir, exist_ok=True)
        
        # 格式化版本标识
        version_str = str(version).lower()
        
        # 查找或创建文件：查找该版本的最新文件或创建新文件
        # 优先查找已存在的同版本文件
        if version_str in ["initial", "final"]:
            pattern = f"review_{version_str}_*.md"
        else:
            pattern = f"review_v{version_str}_*.md"
        
        existing_files = list(reviews_dir.glob(pattern))
        
        if existing_files and part_id != 1:
            # 如果已有同名版本文件且不是第一部分，使用最新的文件
            file_path = max(existing_files, key=lambda p: p.stat().st_mtime)
            write_mode = 'a'
        else:
            # 创建新文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if version_str in ["initial", "final"]:
                filename = f"review_{version_str}_{timestamp}.md"
            else:
                filename = f"review_v{version_str}_{timestamp}.md"
            file_path = reviews_dir / filename
            write_mode = 'w'
        
        # 写入文件
        if write_mode == 'a':
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(f"\n\n<!-- Part {part_id} -->\n\n")
                f.write(content)
        else:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        # 获取文件大小
        file_size = os.path.getsize(file_path)
        content_length = len(content)
        
        # 返回简洁的结果
        return json.dumps({
            "status": "success",
            "part_id": part_id,
            "content_length": content_length,
            "file_size": file_size,
            "file_path": str(file_path)
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "part_id": part_id,
            "message": str(e)
        }, ensure_ascii=False)