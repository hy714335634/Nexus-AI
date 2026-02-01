#!/usr/bin/env python3
"""
搜索结果格式化和标准化模块
"""

from typing import List, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)


def _standardize_results(raw_results: List[Dict], engine: str) -> List[Dict[str, Any]]:
    """
    标准化不同搜索引擎的结果格式
    
    Args:
        raw_results: 原始搜索结果列表
        engine: 搜索引擎名称
        
    Returns:
        list: 标准化后的结果列表
    """
    from .utils import clean_html, normalize_url, truncate_text
    
    standardized = []
    for idx, result in enumerate(raw_results, 1):
        try:
            standardized_result = {
                'title': clean_html(result.get('title', '')),
                'url': normalize_url(result.get('url', '')),
                'snippet': truncate_text(clean_html(result.get('snippet', '')), max_length=300),
                'rank': idx,
                'source': engine
            }
            
            # 只添加有效的结果（至少有标题或URL）
            if standardized_result['title'] or standardized_result['url']:
                standardized.append(standardized_result)
        except Exception as e:
            logger.warning(f"标准化第 {idx} 个结果失败: {e}")
            continue
    
    return standardized


def _format_as_markdown(results: List[Dict], query: str = "", engine: str = "") -> str:
    """
    将搜索结果格式化为Markdown
    
    Args:
        results: 标准化的搜索结果列表
        query: 搜索查询（可选）
        engine: 使用的搜索引擎（可选）
        
    Returns:
        str: Markdown格式的搜索结果
    """
    if not results:
        return "## 搜索结果\n\n无搜索结果"
    
    markdown = "# 搜索结果\n\n"
    
    if query:
        markdown += f"**查询**: {query}\n\n"
    if engine:
        markdown += f"**搜索引擎**: {engine}\n\n"
    
    markdown += f"**结果数量**: {len(results)}\n\n"
    markdown += "---\n\n"
    
    for result in results:
        markdown += f"## {result['rank']}. {result['title']}\n\n"
        markdown += f"**链接**: [{result['url']}]({result['url']})\n\n"
        
        if result['snippet']:
            markdown += f"**摘要**: {result['snippet']}\n\n"
        
        markdown += f"**来源**: {result['source']}\n\n"
        markdown += "---\n\n"
    
    return markdown


def _format_as_text(results: List[Dict], query: str = "", engine: str = "") -> str:
    """
    将搜索结果格式化为纯文本
    
    Args:
        results: 标准化的搜索结果列表
        query: 搜索查询（可选）
        engine: 使用的搜索引擎（可选）
        
    Returns:
        str: 纯文本格式的搜索结果
    """
    if not results:
        return "搜索结果\n" + "="*50 + "\n\n无搜索结果"
    
    text = "搜索结果\n" + "="*50 + "\n\n"
    
    if query:
        text += f"查询: {query}\n"
    if engine:
        text += f"搜索引擎: {engine}\n"
    
    text += f"结果数量: {len(results)}\n\n"
    text += "-"*50 + "\n\n"
    
    for result in results:
        text += f"{result['rank']}. {result['title']}\n"
        text += f"链接: {result['url']}\n"
        
        if result['snippet']:
            text += f"摘要: {result['snippet']}\n"
        
        text += f"来源: {result['source']}\n"
        text += "-"*50 + "\n\n"
    
    return text


def _format_results(results: List[Dict], format_type: str = "json", 
                    query: str = "", engine: str = "", 
                    include_metadata: bool = True,
                    search_time_ms: int = 0) -> str:
    """
    根据指定格式类型格式化搜索结果
    
    Args:
        results: 标准化的搜索结果列表
        format_type: 输出格式（json/markdown/text）
        query: 搜索查询
        engine: 使用的搜索引擎
        include_metadata: 是否包含元数据
        search_time_ms: 搜索耗时（毫秒）
        
    Returns:
        str: 格式化后的搜索结果
    """
    if format_type == "markdown":
        return _format_as_markdown(results, query, engine)
    elif format_type == "text":
        return _format_as_text(results, query, engine)
    else:  # json
        import time
        response = {
            'status': 'success',
            'engine_used': engine,
            'query': query,
            'results': results,
            'total_results': len(results)
        }
        
        if include_metadata:
            response['metadata'] = {
                'search_time_ms': search_time_ms,
                'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
