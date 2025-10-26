#!/usr/bin/env python3
"""
Literature Batch Processor Tool

提供分批次处理文献的功能，支持：
- 加载被标记的文献元数据
- 分批次获取文献
- 跟踪处理状态
- 从断点继续处理
"""

import json
import os
from typing import Dict, List, Any, Optional
import logging
from pathlib import Path
from datetime import datetime

from strands import tool

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _find_cache_directory(research_id: str) -> Optional[Path]:
    """
    根据research_id查找对应的缓存目录
    
    Args:
        research_id: 研究ID，如 "literature_search_20251024"
        
    Returns:
        缓存目录路径，如果未找到则返回None
    """
    cache_root = Path(".cache/pmc_literature")
    
    # 尝试多种可能的路径
    possible_paths = [
        cache_root / research_id,
        cache_root / f"literature_search_{research_id}",
        Path(research_id)  # 如果已经是完整路径
    ]
    
    for path in possible_paths:
        if path.exists() and path.is_dir():
            logger.info(f"找到缓存目录: {path}")
            return path
    
    logger.error(f"未找到缓存目录，research_id: {research_id}")
    return None


def _load_manifest(cache_dir: Path) -> Dict[str, Any]:
    """
    加载manifest.json文件
    
    Args:
        cache_dir: 缓存目录路径
        
    Returns:
        manifest内容
    """
    manifest_path = cache_dir / "manifest.json"
    
    if not manifest_path.exists():
        logger.warning(f"manifest.json不存在，尝试查找其他元数据文件")
        # 查找meta_data目录下的JSON文件
        meta_data_dir = cache_dir / "meta_data"
        if meta_data_dir.exists():
            metadata_files = list(meta_data_dir.glob("*.json"))
            manifest = {
                "metadata": []
            }
            for meta_file in metadata_files:
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                        manifest["metadata"].append(meta)
                except Exception as e:
                    logger.error(f"读取元数据文件失败: {meta_file}, {e}")
            return manifest
        
        return {"metadata": []}
    
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
            
            # 统计包含的文献数量
            if "marked_literature" in manifest:
                by_year = manifest["marked_literature"].get("by_year", {})
                total_count = sum(len(year_data.get("literature", [])) for year_data in by_year.values())
                logger.info(f"成功加载manifest.json，包含{total_count}篇被标记的文献")
            elif "metadata" in manifest:
                total_count = len(manifest.get("metadata", []))
                logger.info(f"成功加载manifest.json，包含{total_count}条元数据")
            else:
                logger.info(f"成功加载manifest.json")
            
            return manifest
    except Exception as e:
        logger.error(f"加载manifest.json失败: {e}")
        return {"metadata": []}


def _load_status_file(cache_dir: Path) -> Dict[str, Any]:
    """
    加载状态文件
    
    Args:
        cache_dir: 缓存目录路径
        
    Returns:
        状态信息
    """
    status_path = cache_dir / "batch_processing_status.json"
    
    if not status_path.exists():
        return {
            "current_batch": 0,
            "processed_papers": [],
            "total_papers": 0,
            "start_time": datetime.now().isoformat(),
            "last_update": None
        }
    
    try:
        with open(status_path, 'r', encoding='utf-8') as f:
            status = json.load(f)
            logger.info(f"成功加载状态文件，当前批次: {status.get('current_batch', 0)}")
            return status
    except Exception as e:
        logger.error(f"加载状态文件失败: {e}")
        return {
            "current_batch": 0,
            "processed_papers": [],
            "total_papers": 0,
            "start_time": datetime.now().isoformat(),
            "last_update": None
        }


def _save_status_file(cache_dir: Path, status: Dict[str, Any]):
    """
    保存状态文件
    
    Args:
        cache_dir: 缓存目录路径
        status: 状态信息
    """
    status_path = cache_dir / "batch_processing_status.json"
    
    status["last_update"] = datetime.now().isoformat()
    
    try:
        with open(status_path, 'w', encoding='utf-8') as f:
            json.dump(status, f, indent=2, ensure_ascii=False)
        logger.info(f"状态文件已保存: {status_path}")
    except Exception as e:
        logger.error(f"保存状态文件失败: {e}")


@tool
def load_marked_literature(research_id: str) -> Dict[str, Any]:
    """
    加载被标记的文献元数据
    
    Args:
        research_id: 研究ID，对应.cache/pmc_literature下的目录名
    
    Returns:
        包含文献元数据和缓存目录信息的字典
    """
    try:
        cache_dir = _find_cache_directory(research_id)
        if not cache_dir:
            return {
                "success": False,
                "error": f"未找到缓存目录，research_id: {research_id}"
            }
        
        manifest = _load_manifest(cache_dir)
        
        # 筛选被标记的文献
        marked_literature = []
        
        # 首先尝试从manifest.json的结构化格式加载（由Screen Assistant生成）
        if "marked_literature" in manifest:
            by_year = manifest["marked_literature"].get("by_year", {})
            for year, year_data in by_year.items():
                for lit in year_data.get("literature", []):
                    marked_literature.append(lit)
        # 如果没有marked_literature，尝试metadata字段
        elif "metadata" in manifest:
            for meta in manifest.get("metadata", []):
                # 检查标记字段
                if meta.get("marked", False) or meta.get("is_relevant", False) or meta.get("should_reference", False):
                    marked_literature.append(meta)
        
        logger.info(f"找到{len(marked_literature)}篇被标记的文献")
        
        return {
            "success": True,
            "cache_dir": str(cache_dir),
            "marked_literature": marked_literature,
            "total_count": len(marked_literature)
        }
        
    except Exception as e:
        logger.error(f"加载被标记文献失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@tool
def get_next_batch(research_id: str, batch_size: int = 10) -> Dict[str, Any]:
    """
    获取下一批待处理的文献
    
    Args:
        research_id: 研究ID
        batch_size: 每批处理的文献数量
    
    Returns:
        包含下一批文献信息的字典
    """
    try:
        cache_dir = _find_cache_directory(research_id)
        if not cache_dir:
            return {
                "success": False,
                "error": f"未找到缓存目录，research_id: {research_id}"
            }
        
        # 加载状态
        status = _load_status_file(cache_dir)
        
        # 加载被标记的文献
        result = load_marked_literature(research_id)
        if not result.get("success"):
            return result
        
        marked_literature = result["marked_literature"]
        processed_papers = set(status.get("processed_papers", []))
        
        # 找出未处理的文献
        unprocessed = []
        for paper in marked_literature:
            pmcid = paper.get("pmcid") or paper.get("PMCID")
            if pmcid and pmcid not in processed_papers:
                unprocessed.append(paper)
        
        # 判断是否还有未处理的文献
        if not unprocessed:
            return {
                "success": True,
                "has_more": False,
                "message": "所有文献已处理完成",
                "current_batch": status.get("current_batch", 0),
                "papers": []
            }
        
        # 获取下一批文献
        next_batch = unprocessed[:batch_size]
        current_batch = status.get("current_batch", 0) + 1
        
        logger.info(f"获取批次{current_batch}，包含{len(next_batch)}篇文献")
        
        return {
            "success": True,
            "has_more": len(unprocessed) > batch_size,
            "current_batch": current_batch,
            "total_batches": (len(unprocessed) + batch_size - 1) // batch_size,
            "papers": next_batch,
            "paper_count": len(next_batch)
        }
        
    except Exception as e:
        logger.error(f"获取下一批文献失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@tool
def mark_batch_completed(research_id: str, processed_pmcids: List[str]) -> Dict[str, Any]:
    """
    标记一批文献处理完成
    
    Args:
        research_id: 研究ID
        processed_pmcids: 已处理的PMCID列表
    
    Returns:
        操作结果
    """
    try:
        cache_dir = _find_cache_directory(research_id)
        if not cache_dir:
            return {
                "success": False,
                "error": f"未找到缓存目录，research_id: {research_id}"
            }
        
        # 加载状态
        status = _load_status_file(cache_dir)
        
        # 更新已处理列表
        processed_papers = set(status.get("processed_papers", []))
        processed_papers.update(processed_pmcids)
        status["processed_papers"] = list(processed_papers)
        status["current_batch"] = status.get("current_batch", 0) + 1
        
        # 保存状态
        _save_status_file(cache_dir, status)
        
        logger.info(f"标记批次完成，已处理{len(processed_papers)}篇文献")
        
        return {
            "success": True,
            "processed_count": len(processed_papers),
            "current_batch": status["current_batch"]
        }
        
    except Exception as e:
        logger.error(f"标记批次完成失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@tool
def get_processing_status(research_id: str) -> Dict[str, Any]:
    """
    获取处理状态
    
    Args:
        research_id: 研究ID
    
    Returns:
        包含处理状态的字典
    """
    try:
        cache_dir = _find_cache_directory(research_id)
        if not cache_dir:
            return {
                "success": False,
                "error": f"未找到缓存目录，research_id: {research_id}"
            }
        
        # 加载状态
        status = _load_status_file(cache_dir)
        
        # 加载被标记的文献
        result = load_marked_literature(research_id)
        if not result.get("success"):
            return result
        
        total_count = result["total_count"]
        processed_count = len(status.get("processed_papers", []))
        progress = (processed_count / total_count * 100) if total_count > 0 else 0
        
        return {
            "success": True,
            "total_papers": total_count,
            "processed_papers": processed_count,
            "remaining_papers": total_count - processed_count,
            "progress_percent": round(progress, 2),
            "current_batch": status.get("current_batch", 0),
            "start_time": status.get("start_time"),
            "last_update": status.get("last_update")
        }
        
    except Exception as e:
        logger.error(f"获取处理状态失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@tool
def get_latest_review(research_id: str) -> Dict[str, Any]:
    """
    获取最新的文献综述内容
    
    Args:
        research_id: 研究ID
    
    Returns:
        包含最新综述内容的字典
    """
    try:
        cache_dir = _find_cache_directory(research_id)
        if not cache_dir:
            return {
                "success": False,
                "error": f"未找到缓存目录，research_id: {research_id}"
            }
        
        # 查找最新的综述文件
        review_dir = cache_dir / "reviews"
        if not review_dir.exists():
            return {
                "success": True,
                "has_review": False,
                "content": ""
            }
        
        # 按时间排序获取最新的综述文件
        review_files = sorted(review_dir.glob("review_batch_*.md"), key=lambda x: x.stat().st_mtime, reverse=True)
        
        if not review_files:
            return {
                "success": True,
                "has_review": False,
                "content": ""
            }
        
        latest_file = review_files[0]
        
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.info(f"成功加载最新综述: {latest_file.name}")
            
            return {
                "success": True,
                "has_review": True,
                "content": content,
                "file_name": latest_file.name,
                "file_path": str(latest_file)
            }
        except Exception as e:
            logger.error(f"读取综述文件失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        
    except Exception as e:
        logger.error(f"获取最新综述失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }

