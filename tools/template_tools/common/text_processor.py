#!/usr/bin/env python3
"""
文本处理工具模板

提供文本分析、格式转换、内容提取等功能
"""

import re
import json
import yaml
import csv
from typing import Dict, List, Any, Optional
from pathlib import Path
from strands import tool


@tool
def text_analyzer(text: str, analysis_type: str = "basic") -> str:
    """
    文本分析工具
    
    Args:
        text (str): 要分析的文本内容
        analysis_type (str): 分析类型 (basic, sentiment, keywords, summary)
        
    Returns:
        str: JSON格式的分析结果
    """
    try:
        result = {
            "text_length": len(text),
            "word_count": len(text.split()),
            "character_count": len(text.replace(" ", "")),
            "line_count": len(text.splitlines()),
            "analysis_type": analysis_type
        }
        
        if analysis_type == "basic":
            # 基本统计信息
            result.update({
                "average_word_length": sum(len(word) for word in text.split()) / len(text.split()) if text.split() else 0,
                "unique_words": len(set(text.lower().split())),
                "sentence_count": len(re.split(r'[.!?]+', text.strip()))
            })
            
        elif analysis_type == "keywords":
            # 关键词提取
            words = re.findall(r'\b\w+\b', text.lower())
            word_freq = {}
            for word in words:
                if len(word) > 3:  # 过滤短词
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            # 获取前10个高频词
            keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
            result["keywords"] = [{"word": word, "frequency": freq} for word, freq in keywords]
            
        elif analysis_type == "summary":
            # 简单摘要（取前3句话）
            sentences = re.split(r'[.!?]+', text.strip())
            summary = ". ".join(sentences[:3]) + "."
            result["summary"] = summary
            
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)


@tool
def format_converter(content: str, source_format: str, target_format: str) -> str:
    """
    格式转换工具
    
    Args:
        content (str): 要转换的内容
        source_format (str): 源格式 (json, yaml, csv, text)
        target_format (str): 目标格式 (json, yaml, csv, text)
        
    Returns:
        str: 转换后的内容
    """
    try:
        # 解析源格式
        if source_format == "json":
            data = json.loads(content)
        elif source_format == "yaml":
            data = yaml.safe_load(content)
        elif source_format == "csv":
            # 简单的CSV解析
            lines = content.strip().split('\n')
            headers = lines[0].split(',')
            data = []
            for line in lines[1:]:
                values = line.split(',')
                data.append(dict(zip(headers, values)))
        elif source_format == "text":
            data = {"content": content}
        else:
            raise ValueError(f"不支持的源格式: {source_format}")
        
        # 转换为目标格式
        if target_format == "json":
            return json.dumps(data, ensure_ascii=False, indent=2)
        elif target_format == "yaml":
            return yaml.dump(data, default_flow_style=False, allow_unicode=True)
        elif target_format == "csv":
            if isinstance(data, list) and data:
                headers = list(data[0].keys())
                csv_content = ','.join(headers) + '\n'
                for row in data:
                    csv_content += ','.join(str(row.get(h, '')) for h in headers) + '\n'
                return csv_content
            else:
                return "无数据可转换"
        elif target_format == "text":
            return str(data)
        else:
            raise ValueError(f"不支持的目标格式: {target_format}")
            
    except Exception as e:
        return f"格式转换错误: {str(e)}"


@tool
def content_extractor(text: str, extraction_type: str = "links") -> str:
    """
    内容提取工具
    
    Args:
        text (str): 要提取内容的文本
        extraction_type (str): 提取类型 (links, emails, phone_numbers, dates)
        
    Returns:
        str: JSON格式的提取结果
    """
    try:
        result = {"extraction_type": extraction_type, "matches": []}
        
        if extraction_type == "links":
            # 提取链接
            url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
            matches = re.findall(url_pattern, text)
            result["matches"] = [{"type": "url", "value": match} for match in matches]
            
        elif extraction_type == "emails":
            # 提取邮箱
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            matches = re.findall(email_pattern, text)
            result["matches"] = [{"type": "email", "value": match} for match in matches]
            
        elif extraction_type == "phone_numbers":
            # 提取电话号码
            phone_pattern = r'(\+?1?[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
            matches = re.findall(phone_pattern, text)
            result["matches"] = [{"type": "phone", "value": ''.join(match)} for match in matches]
            
        elif extraction_type == "dates":
            # 提取日期
            date_pattern = r'\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4}'
            matches = re.findall(date_pattern, text)
            result["matches"] = [{"type": "date", "value": match} for match in matches]
            
        else:
            raise ValueError(f"不支持的提取类型: {extraction_type}")
        
        result["count"] = len(result["matches"])
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)


@tool
def text_cleaner(text: str, cleaning_options: List[str] = None) -> str:
    """
    文本清理工具
    
    Args:
        text (str): 要清理的文本
        cleaning_options (List[str]): 清理选项 (remove_extra_spaces, remove_special_chars, normalize_whitespace, lowercase)
        
    Returns:
        str: 清理后的文本
    """
    try:
        if cleaning_options is None:
            cleaning_options = ["remove_extra_spaces", "normalize_whitespace"]
        
        cleaned_text = text
        
        if "remove_extra_spaces" in cleaning_options:
            cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
            
        if "remove_special_chars" in cleaning_options:
            cleaned_text = re.sub(r'[^\w\s]', '', cleaned_text)
            
        if "normalize_whitespace" in cleaning_options:
            cleaned_text = ' '.join(cleaned_text.split())
            
        if "lowercase" in cleaning_options:
            cleaned_text = cleaned_text.lower()
            
        return cleaned_text
        
    except Exception as e:
        return f"文本清理错误: {str(e)}"
