#!/usr/bin/env python3
"""
Review Writer Tool

提供将文献综述写入固定目录位置的功能
支持：
- 按批次写入综述
- 自动创建目录结构
- 保留历史版本
"""

import json
import os
from typing import Dict, Any, Optional
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
        research_id: 研究ID
        
    Returns:
        缓存目录路径
    """
    cache_root = Path(".cache/pmc_literature")
    
    possible_paths = [
        cache_root / research_id,
        cache_root / f"literature_search_{research_id}",
        Path(research_id)
    ]
    
    for path in possible_paths:
        if path.exists() and path.is_dir():
            return path
    
    return None


@tool
def write_batch_review(research_id: str, batch_number: int, review_content: str, 
                       user_requirement: str = None) -> Dict[str, Any]:
    """
    将批次文献综述写入指定目录
    
    Args:
        research_id: 研究ID
        batch_number: 批次编号
        review_content: 综述内容
        user_requirement: 用户研究需求（可选）
    
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
        
        # 创建reviews目录
        reviews_dir = cache_dir / "reviews"
        reviews_dir.mkdir(exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"review_batch_{batch_number:03d}_{timestamp}.md"
        filepath = reviews_dir / filename
        
        # 构建完整的综述内容
        full_content = f"""# 文献综述 - 批次 {batch_number}

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

"""
        
        if user_requirement:
            full_content += f"**研究需求**: {user_requirement}\n\n"
        
        full_content += "---\n\n"
        full_content += review_content
        
        # 写入文件
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(full_content)
            
            logger.info(f"成功写入批次综述: {filepath}")
            
            return {
                "success": True,
                "file_path": str(filepath),
                "file_name": filename,
                "batch_number": batch_number
            }
        except Exception as e:
            logger.error(f"写入文件失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        
    except Exception as e:
        logger.error(f"写入批次综述失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@tool
def write_final_review(research_id: str, review_content: str, 
                      user_requirement: str = None) -> Dict[str, Any]:
    """
    写入最终文献综述
    
    Args:
        research_id: 研究ID
        review_content: 综述内容
        user_requirement: 用户研究需求（可选）
    
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
        
        # 创建reviews目录
        reviews_dir = cache_dir / "reviews"
        reviews_dir.mkdir(exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"final_review_{timestamp}.md"
        filepath = reviews_dir / filename
        
        # 构建完整的综述内容
        full_content = f"""# 最终文献综述

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

"""
        
        if user_requirement:
            full_content += f"**研究需求**: {user_requirement}\n\n"
        
        full_content += "---\n\n"
        full_content += review_content
        
        # 写入文件
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(full_content)
            
            logger.info(f"成功写入最终综述: {filepath}")
            
            return {
                "success": True,
                "file_path": str(filepath),
                "file_name": filename
            }
        except Exception as e:
            logger.error(f"写入文件失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        
    except Exception as e:
        logger.error(f"写入最终综述失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@tool
def get_review_history(research_id: str) -> Dict[str, Any]:
    """
    获取综述历史记录
    
    Args:
        research_id: 研究ID
    
    Returns:
        包含综述历史记录的字典
    """
    try:
        cache_dir = _find_cache_directory(research_id)
        if not cache_dir:
            return {
                "success": False,
                "error": f"未找到缓存目录，research_id: {research_id}"
            }
        
        reviews_dir = cache_dir / "reviews"
        if not reviews_dir.exists():
            return {
                "success": True,
                "reviews": []
            }
        
        # 获取所有综述文件
        review_files = sorted(reviews_dir.glob("*.md"), key=lambda x: x.stat().st_mtime)
        
        reviews = []
        for review_file in review_files:
            reviews.append({
                "file_name": review_file.name,
                "file_path": str(review_file),
                "file_size": review_file.stat().st_size,
                "modified_time": datetime.fromtimestamp(review_file.stat().st_mtime).isoformat()
            })
        
        logger.info(f"找到{len(reviews)}份综述文件")
        
        return {
            "success": True,
            "reviews": reviews,
            "total_count": len(reviews)
        }
        
    except Exception as e:
        logger.error(f"获取综述历史失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }

