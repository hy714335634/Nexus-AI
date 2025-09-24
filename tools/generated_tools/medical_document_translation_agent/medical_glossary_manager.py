#!/usr/bin/env python3
"""
medical_glossary_manager.py - 医学词库管理工具

该工具提供了导入、管理和查询医学专业词汇词库的功能。
支持Excel、CSV、JSON等格式的词库导入和解析，
并提供术语的增删改查、版本管理和高效查询匹配功能。
"""

import os
import json
import csv
import re
import hashlib
import datetime
from typing import Dict, List, Any, Optional, Union, Tuple, Set
from io import StringIO
from pathlib import Path
import shutil

try:
    import pandas as pd
    from pandas import DataFrame
except ImportError:
    raise ImportError("请安装pandas库: pip install pandas")

from strands import tool


# 默认词库缓存目录
DEFAULT_CACHE_DIR = os.path.join(".cache", "medical_translator", "glossaries")


@tool
def import_glossary(file_path: str, 
                    source_lang_column: str, 
                    target_lang_column: str, 
                    category_column: Optional[str] = None, 
                    glossary_name: Optional[str] = None,
                    cache_dir: Optional[str] = None) -> str:
    """
    导入医学词库文件（支持Excel、CSV、JSON格式）
    
    Args:
        file_path (str): 词库文件路径
        source_lang_column (str): 源语言列名
        target_lang_column (str): 目标语言列名
        category_column (Optional[str]): 分类列名（可选）
        glossary_name (Optional[str]): 词库名称（可选，默认使用文件名）
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的导入结果
    """
    try:
        # 验证文件是否存在
        if not os.path.exists(file_path):
            return json.dumps({
                "success": False,
                "error": f"文件不存在: {file_path}"
            }, ensure_ascii=False)
        
        # 确定词库名称
        if not glossary_name:
            glossary_name = os.path.splitext(os.path.basename(file_path))[0]
        
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        os.makedirs(cache_dir, exist_ok=True)
        
        # 根据文件扩展名确定导入方式
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
        elif file_ext == '.csv':
            df = pd.read_csv(file_path)
        elif file_ext == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            df = pd.DataFrame(data)
        else:
            return json.dumps({
                "success": False,
                "error": f"不支持的文件格式: {file_ext}，支持的格式有: .xlsx, .xls, .csv, .json"
            }, ensure_ascii=False)
        
        # 验证必要的列是否存在
        required_columns = [source_lang_column, target_lang_column]
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return json.dumps({
                "success": False,
                "error": f"缺少必要的列: {', '.join(missing_columns)}"
            }, ensure_ascii=False)
        
        # 添加分类信息
        if category_column and category_column in df.columns:
            categories = df[category_column].fillna('未分类').tolist()
        else:
            categories = ['未分类'] * len(df)
        
        # 创建词库数据
        glossary_data = []
        term_count = 0
        
        for i, row in df.iterrows():
            if pd.isna(row[source_lang_column]) or pd.isna(row[target_lang_column]):
                continue  # 跳过空值
            
            source_term = str(row[source_lang_column]).strip()
            target_term = str(row[target_lang_column]).strip()
            
            if not source_term or not target_term:
                continue  # 跳过空字符串
            
            term_id = hashlib.md5(f"{source_term}:{target_term}".encode()).hexdigest()
            
            term_entry = {
                "term_id": term_id,
                "source_term": source_term,
                "target_term": target_term,
                "category": categories[i],
                "confidence": 1.0,  # 导入的词库默认置信度为1.0
                "usage_count": 0,
                "last_updated": datetime.datetime.now().isoformat()
            }
            
            # 添加其他可能的列
            for col in df.columns:
                if col not in [source_lang_column, target_lang_column, category_column] and not pd.isna(row[col]):
                    term_entry[col] = str(row[col])
            
            glossary_data.append(term_entry)
            term_count += 1
        
        # 保存词库到缓存目录
        glossary_file = os.path.join(cache_dir, f"{glossary_name}.json")
        
        # 检查是否存在现有词库
        existing_terms = {}
        if os.path.exists(glossary_file):
            with open(glossary_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                
            if "terms" in existing_data:
                for term in existing_data["terms"]:
                    existing_terms[term["term_id"]] = term
                
                # 更新元数据
                metadata = existing_data.get("metadata", {})
                metadata["last_updated"] = datetime.datetime.now().isoformat()
                metadata["term_count"] = len(existing_terms) + term_count
                
                if "version" in metadata:
                    metadata["version"] = str(float(metadata["version"]) + 0.1)
                else:
                    metadata["version"] = "1.0"
            else:
                # 创建新的元数据
                metadata = {
                    "name": glossary_name,
                    "created": datetime.datetime.now().isoformat(),
                    "last_updated": datetime.datetime.now().isoformat(),
                    "term_count": term_count,
                    "version": "1.0",
                    "source_language": source_lang_column,
                    "target_language": target_lang_column
                }
        else:
            # 创建新的元数据
            metadata = {
                "name": glossary_name,
                "created": datetime.datetime.now().isoformat(),
                "last_updated": datetime.datetime.now().isoformat(),
                "term_count": term_count,
                "version": "1.0",
                "source_language": source_lang_column,
                "target_language": target_lang_column
            }
        
        # 合并新旧词条
        for term in glossary_data:
            existing_terms[term["term_id"]] = term
        
        # 创建最终词库数据
        final_glossary = {
            "metadata": metadata,
            "terms": list(existing_terms.values())
        }
        
        # 保存词库
        with open(glossary_file, 'w', encoding='utf-8') as f:
            json.dump(final_glossary, f, ensure_ascii=False, indent=2)
        
        # 创建索引
        create_glossary_index(glossary_name, cache_dir)
        
        return json.dumps({
            "success": True,
            "glossary_name": glossary_name,
            "term_count": len(final_glossary["terms"]),
            "file_path": glossary_file,
            "metadata": metadata
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"导入词库时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def list_glossaries(cache_dir: Optional[str] = None) -> str:
    """
    列出所有可用的医学词库
    
    Args:
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的词库列表
    """
    try:
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        
        if not os.path.exists(cache_dir):
            return json.dumps({
                "success": True,
                "glossaries": [],
                "message": "词库目录不存在，没有可用的词库"
            }, ensure_ascii=False)
        
        glossaries = []
        
        # 遍历目录查找词库文件
        for file_name in os.listdir(cache_dir):
            if file_name.endswith('.json') and not file_name.endswith('_index.json'):
                file_path = os.path.join(cache_dir, file_name)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        glossary_data = json.load(f)
                    
                    if "metadata" in glossary_data:
                        metadata = glossary_data["metadata"]
                        term_count = len(glossary_data.get("terms", []))
                        
                        glossary_info = {
                            "name": metadata.get("name", os.path.splitext(file_name)[0]),
                            "version": metadata.get("version", "1.0"),
                            "term_count": term_count,
                            "source_language": metadata.get("source_language", "未知"),
                            "target_language": metadata.get("target_language", "未知"),
                            "last_updated": metadata.get("last_updated", "未知"),
                            "file_path": file_path
                        }
                        
                        glossaries.append(glossary_info)
                except:
                    # 忽略无法解析的文件
                    pass
        
        return json.dumps({
            "success": True,
            "glossaries": glossaries,
            "total_count": len(glossaries)
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"列出词库时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def search_term(term: str, 
                glossary_name: str, 
                is_source_lang: bool = True, 
                exact_match: bool = False,
                max_results: int = 10,
                cache_dir: Optional[str] = None) -> str:
    """
    在词库中搜索术语
    
    Args:
        term (str): 要搜索的术语
        glossary_name (str): 词库名称
        is_source_lang (bool): 是否在源语言中搜索，False表示在目标语言中搜索
        exact_match (bool): 是否精确匹配
        max_results (int): 最大结果数量
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的搜索结果
    """
    try:
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        
        # 构建词库文件路径
        glossary_file = os.path.join(cache_dir, f"{glossary_name}.json")
        
        if not os.path.exists(glossary_file):
            return json.dumps({
                "success": False,
                "error": f"词库不存在: {glossary_name}"
            }, ensure_ascii=False)
        
        # 加载词库
        with open(glossary_file, 'r', encoding='utf-8') as f:
            glossary_data = json.load(f)
        
        if "terms" not in glossary_data:
            return json.dumps({
                "success": False,
                "error": f"词库格式无效: {glossary_name}"
            }, ensure_ascii=False)
        
        # 确定搜索字段
        search_field = "source_term" if is_source_lang else "target_term"
        result_field = "target_term" if is_source_lang else "source_term"
        
        # 搜索结果
        results = []
        
        # 使用索引进行快速搜索
        index_file = os.path.join(cache_dir, f"{glossary_name}_index.json")
        if os.path.exists(index_file) and not exact_match:
            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            if search_field in index_data:
                index = index_data[search_field]
                
                # 模糊搜索
                term_lower = term.lower()
                matched_terms = []
                
                # 前缀匹配
                for prefix in [term_lower[:i] for i in range(1, len(term_lower) + 1)]:
                    if prefix in index:
                        matched_terms.extend(index[prefix])
                
                # 去重
                matched_terms = list(set(matched_terms))
                
                # 获取完整术语信息
                term_dict = {t["term_id"]: t for t in glossary_data["terms"]}
                
                for term_id in matched_terms[:max_results]:
                    if term_id in term_dict:
                        results.append(term_dict[term_id])
        else:
            # 没有索引或需要精确匹配，直接搜索
            for term_entry in glossary_data["terms"]:
                if exact_match:
                    if term_entry[search_field].lower() == term.lower():
                        results.append(term_entry)
                else:
                    if term.lower() in term_entry[search_field].lower():
                        results.append(term_entry)
                
                if len(results) >= max_results:
                    break
        
        # 更新使用计数
        for result in results:
            result["usage_count"] = result.get("usage_count", 0) + 1
        
        # 保存更新后的词库
        with open(glossary_file, 'w', encoding='utf-8') as f:
            json.dump(glossary_data, f, ensure_ascii=False, indent=2)
        
        return json.dumps({
            "success": True,
            "term": term,
            "is_source_lang": is_source_lang,
            "exact_match": exact_match,
            "results": results,
            "result_count": len(results)
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"搜索术语时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def add_term(source_term: str, 
             target_term: str, 
             glossary_name: str, 
             category: str = "未分类", 
             confidence: float = 1.0,
             cache_dir: Optional[str] = None) -> str:
    """
    向词库添加新术语
    
    Args:
        source_term (str): 源语言术语
        target_term (str): 目标语言术语
        glossary_name (str): 词库名称
        category (str): 术语分类
        confidence (float): 置信度（0.0-1.0）
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        
        # 构建词库文件路径
        glossary_file = os.path.join(cache_dir, f"{glossary_name}.json")
        
        # 如果词库不存在，创建新词库
        if not os.path.exists(glossary_file):
            metadata = {
                "name": glossary_name,
                "created": datetime.datetime.now().isoformat(),
                "last_updated": datetime.datetime.now().isoformat(),
                "term_count": 1,
                "version": "1.0",
                "source_language": "source",
                "target_language": "target"
            }
            
            glossary_data = {
                "metadata": metadata,
                "terms": []
            }
        else:
            # 加载现有词库
            with open(glossary_file, 'r', encoding='utf-8') as f:
                glossary_data = json.load(f)
            
            # 更新元数据
            if "metadata" in glossary_data:
                glossary_data["metadata"]["last_updated"] = datetime.datetime.now().isoformat()
                glossary_data["metadata"]["term_count"] = len(glossary_data.get("terms", [])) + 1
            else:
                glossary_data["metadata"] = {
                    "name": glossary_name,
                    "created": datetime.datetime.now().isoformat(),
                    "last_updated": datetime.datetime.now().isoformat(),
                    "term_count": 1,
                    "version": "1.0",
                    "source_language": "source",
                    "target_language": "target"
                }
        
        # 生成术语ID
        term_id = hashlib.md5(f"{source_term}:{target_term}".encode()).hexdigest()
        
        # 检查是否已存在相同的术语
        if "terms" in glossary_data:
            for i, term in enumerate(glossary_data["terms"]):
                if term.get("term_id") == term_id:
                    # 更新现有术语
                    glossary_data["terms"][i] = {
                        "term_id": term_id,
                        "source_term": source_term,
                        "target_term": target_term,
                        "category": category,
                        "confidence": confidence,
                        "usage_count": term.get("usage_count", 0),
                        "last_updated": datetime.datetime.now().isoformat()
                    }
                    
                    # 保存更新后的词库
                    with open(glossary_file, 'w', encoding='utf-8') as f:
                        json.dump(glossary_data, f, ensure_ascii=False, indent=2)
                    
                    # 更新索引
                    create_glossary_index(glossary_name, cache_dir)
                    
                    return json.dumps({
                        "success": True,
                        "message": "术语已更新",
                        "term_id": term_id
                    }, ensure_ascii=False)
        
        # 添加新术语
        new_term = {
            "term_id": term_id,
            "source_term": source_term,
            "target_term": target_term,
            "category": category,
            "confidence": confidence,
            "usage_count": 0,
            "last_updated": datetime.datetime.now().isoformat()
        }
        
        if "terms" not in glossary_data:
            glossary_data["terms"] = []
        
        glossary_data["terms"].append(new_term)
        
        # 保存更新后的词库
        with open(glossary_file, 'w', encoding='utf-8') as f:
            json.dump(glossary_data, f, ensure_ascii=False, indent=2)
        
        # 更新索引
        create_glossary_index(glossary_name, cache_dir)
        
        return json.dumps({
            "success": True,
            "message": "术语已添加",
            "term_id": term_id
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"添加术语时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def delete_term(term_id: str, 
                glossary_name: str, 
                cache_dir: Optional[str] = None) -> str:
    """
    从词库中删除术语
    
    Args:
        term_id (str): 术语ID
        glossary_name (str): 词库名称
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        
        # 构建词库文件路径
        glossary_file = os.path.join(cache_dir, f"{glossary_name}.json")
        
        if not os.path.exists(glossary_file):
            return json.dumps({
                "success": False,
                "error": f"词库不存在: {glossary_name}"
            }, ensure_ascii=False)
        
        # 加载词库
        with open(glossary_file, 'r', encoding='utf-8') as f:
            glossary_data = json.load(f)
        
        if "terms" not in glossary_data:
            return json.dumps({
                "success": False,
                "error": f"词库格式无效: {glossary_name}"
            }, ensure_ascii=False)
        
        # 查找并删除术语
        found = False
        for i, term in enumerate(glossary_data["terms"]):
            if term.get("term_id") == term_id:
                del glossary_data["terms"][i]
                found = True
                break
        
        if not found:
            return json.dumps({
                "success": False,
                "error": f"术语不存在: {term_id}"
            }, ensure_ascii=False)
        
        # 更新元数据
        if "metadata" in glossary_data:
            glossary_data["metadata"]["last_updated"] = datetime.datetime.now().isoformat()
            glossary_data["metadata"]["term_count"] = len(glossary_data["terms"])
        
        # 保存更新后的词库
        with open(glossary_file, 'w', encoding='utf-8') as f:
            json.dump(glossary_data, f, ensure_ascii=False, indent=2)
        
        # 更新索引
        create_glossary_index(glossary_name, cache_dir)
        
        return json.dumps({
            "success": True,
            "message": "术语已删除",
            "term_id": term_id
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"删除术语时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def update_term(term_id: str, 
                glossary_name: str, 
                source_term: Optional[str] = None, 
                target_term: Optional[str] = None, 
                category: Optional[str] = None, 
                confidence: Optional[float] = None,
                cache_dir: Optional[str] = None) -> str:
    """
    更新词库中的术语
    
    Args:
        term_id (str): 术语ID
        glossary_name (str): 词库名称
        source_term (Optional[str]): 源语言术语（可选）
        target_term (Optional[str]): 目标语言术语（可选）
        category (Optional[str]): 术语分类（可选）
        confidence (Optional[float]): 置信度（可选，0.0-1.0）
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        
        # 构建词库文件路径
        glossary_file = os.path.join(cache_dir, f"{glossary_name}.json")
        
        if not os.path.exists(glossary_file):
            return json.dumps({
                "success": False,
                "error": f"词库不存在: {glossary_name}"
            }, ensure_ascii=False)
        
        # 加载词库
        with open(glossary_file, 'r', encoding='utf-8') as f:
            glossary_data = json.load(f)
        
        if "terms" not in glossary_data:
            return json.dumps({
                "success": False,
                "error": f"词库格式无效: {glossary_name}"
            }, ensure_ascii=False)
        
        # 查找并更新术语
        found = False
        for i, term in enumerate(glossary_data["terms"]):
            if term.get("term_id") == term_id:
                # 更新术语字段
                if source_term is not None:
                    term["source_term"] = source_term
                
                if target_term is not None:
                    term["target_term"] = target_term
                
                if category is not None:
                    term["category"] = category
                
                if confidence is not None:
                    term["confidence"] = confidence
                
                # 更新最后修改时间
                term["last_updated"] = datetime.datetime.now().isoformat()
                
                # 如果源语言或目标语言术语发生变化，生成新的ID
                if (source_term is not None or target_term is not None):
                    new_source = source_term if source_term is not None else term["source_term"]
                    new_target = target_term if target_term is not None else term["target_term"]
                    new_term_id = hashlib.md5(f"{new_source}:{new_target}".encode()).hexdigest()
                    
                    if new_term_id != term_id:
                        term["term_id"] = new_term_id
                
                found = True
                break
        
        if not found:
            return json.dumps({
                "success": False,
                "error": f"术语不存在: {term_id}"
            }, ensure_ascii=False)
        
        # 更新元数据
        if "metadata" in glossary_data:
            glossary_data["metadata"]["last_updated"] = datetime.datetime.now().isoformat()
        
        # 保存更新后的词库
        with open(glossary_file, 'w', encoding='utf-8') as f:
            json.dump(glossary_data, f, ensure_ascii=False, indent=2)
        
        # 更新索引
        create_glossary_index(glossary_name, cache_dir)
        
        return json.dumps({
            "success": True,
            "message": "术语已更新",
            "term_id": term["term_id"]
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"更新术语时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def export_glossary(glossary_name: str, 
                    output_format: str = "json", 
                    output_path: Optional[str] = None,
                    cache_dir: Optional[str] = None) -> str:
    """
    导出词库到指定格式
    
    Args:
        glossary_name (str): 词库名称
        output_format (str): 输出格式（json, csv, excel）
        output_path (Optional[str]): 输出文件路径（可选，默认使用词库名称）
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        
        # 构建词库文件路径
        glossary_file = os.path.join(cache_dir, f"{glossary_name}.json")
        
        if not os.path.exists(glossary_file):
            return json.dumps({
                "success": False,
                "error": f"词库不存在: {glossary_name}"
            }, ensure_ascii=False)
        
        # 加载词库
        with open(glossary_file, 'r', encoding='utf-8') as f:
            glossary_data = json.load(f)
        
        if "terms" not in glossary_data:
            return json.dumps({
                "success": False,
                "error": f"词库格式无效: {glossary_name}"
            }, ensure_ascii=False)
        
        # 确定输出路径
        if not output_path:
            output_path = f"{glossary_name}_export"
        
        # 根据输出格式导出
        if output_format.lower() == "json":
            output_file = f"{output_path}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(glossary_data, f, ensure_ascii=False, indent=2)
        
        elif output_format.lower() == "csv":
            output_file = f"{output_path}.csv"
            
            # 转换为DataFrame
            df = pd.DataFrame(glossary_data["terms"])
            
            # 保存为CSV
            df.to_csv(output_file, index=False, encoding='utf-8')
        
        elif output_format.lower() == "excel":
            output_file = f"{output_path}.xlsx"
            
            # 转换为DataFrame
            df = pd.DataFrame(glossary_data["terms"])
            
            # 保存为Excel
            df.to_excel(output_file, index=False)
        
        else:
            return json.dumps({
                "success": False,
                "error": f"不支持的输出格式: {output_format}，支持的格式有: json, csv, excel"
            }, ensure_ascii=False)
        
        return json.dumps({
            "success": True,
            "message": f"词库已导出为{output_format}格式",
            "file_path": output_file,
            "term_count": len(glossary_data["terms"])
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"导出词库时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def create_glossary_version(glossary_name: str, 
                            version_name: Optional[str] = None,
                            cache_dir: Optional[str] = None) -> str:
    """
    创建词库的版本快照
    
    Args:
        glossary_name (str): 词库名称
        version_name (Optional[str]): 版本名称（可选，默认使用时间戳）
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        
        # 构建词库文件路径
        glossary_file = os.path.join(cache_dir, f"{glossary_name}.json")
        
        if not os.path.exists(glossary_file):
            return json.dumps({
                "success": False,
                "error": f"词库不存在: {glossary_name}"
            }, ensure_ascii=False)
        
        # 确定版本名称
        if not version_name:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            version_name = f"v_{timestamp}"
        
        # 创建版本目录
        versions_dir = os.path.join(cache_dir, "versions")
        os.makedirs(versions_dir, exist_ok=True)
        
        # 构建版本文件路径
        version_file = os.path.join(versions_dir, f"{glossary_name}_{version_name}.json")
        
        # 复制词库文件作为版本快照
        shutil.copy2(glossary_file, version_file)
        
        # 加载词库以更新元数据
        with open(glossary_file, 'r', encoding='utf-8') as f:
            glossary_data = json.load(f)
        
        # 更新版本信息
        if "metadata" in glossary_data:
            if "versions" not in glossary_data["metadata"]:
                glossary_data["metadata"]["versions"] = []
            
            glossary_data["metadata"]["versions"].append({
                "name": version_name,
                "created": datetime.datetime.now().isoformat(),
                "file_path": version_file,
                "term_count": len(glossary_data.get("terms", []))
            })
            
            # 更新当前版本
            current_version = glossary_data["metadata"].get("version", "1.0")
            try:
                version_number = float(current_version) + 0.1
                glossary_data["metadata"]["version"] = str(version_number)
            except:
                glossary_data["metadata"]["version"] = "1.1"
            
            # 保存更新后的词库
            with open(glossary_file, 'w', encoding='utf-8') as f:
                json.dump(glossary_data, f, ensure_ascii=False, indent=2)
        
        return json.dumps({
            "success": True,
            "message": "词库版本已创建",
            "version_name": version_name,
            "file_path": version_file
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"创建词库版本时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def list_glossary_versions(glossary_name: str, 
                           cache_dir: Optional[str] = None) -> str:
    """
    列出词库的所有版本
    
    Args:
        glossary_name (str): 词库名称
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的版本列表
    """
    try:
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        
        # 构建词库文件路径
        glossary_file = os.path.join(cache_dir, f"{glossary_name}.json")
        
        if not os.path.exists(glossary_file):
            return json.dumps({
                "success": False,
                "error": f"词库不存在: {glossary_name}"
            }, ensure_ascii=False)
        
        # 加载词库
        with open(glossary_file, 'r', encoding='utf-8') as f:
            glossary_data = json.load(f)
        
        # 获取版本信息
        versions = []
        
        if "metadata" in glossary_data and "versions" in glossary_data["metadata"]:
            versions = glossary_data["metadata"]["versions"]
        
        # 检查版本文件是否存在
        valid_versions = []
        for version in versions:
            file_path = version.get("file_path")
            if file_path and os.path.exists(file_path):
                valid_versions.append(version)
        
        # 添加当前版本
        current_version = {
            "name": "current",
            "created": glossary_data.get("metadata", {}).get("last_updated", "未知"),
            "file_path": glossary_file,
            "term_count": len(glossary_data.get("terms", [])),
            "version": glossary_data.get("metadata", {}).get("version", "1.0"),
            "is_current": True
        }
        
        valid_versions.append(current_version)
        
        return json.dumps({
            "success": True,
            "glossary_name": glossary_name,
            "versions": valid_versions,
            "version_count": len(valid_versions)
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"列出词库版本时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def restore_glossary_version(glossary_name: str, 
                             version_name: str, 
                             cache_dir: Optional[str] = None) -> str:
    """
    恢复词库到指定版本
    
    Args:
        glossary_name (str): 词库名称
        version_name (str): 版本名称
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        
        # 构建词库文件路径
        glossary_file = os.path.join(cache_dir, f"{glossary_name}.json")
        
        if not os.path.exists(glossary_file):
            return json.dumps({
                "success": False,
                "error": f"词库不存在: {glossary_name}"
            }, ensure_ascii=False)
        
        # 加载词库
        with open(glossary_file, 'r', encoding='utf-8') as f:
            glossary_data = json.load(f)
        
        # 查找版本
        version_file = None
        
        if "metadata" in glossary_data and "versions" in glossary_data["metadata"]:
            for version in glossary_data["metadata"]["versions"]:
                if version.get("name") == version_name:
                    version_file = version.get("file_path")
                    break
        
        if not version_file or not os.path.exists(version_file):
            return json.dumps({
                "success": False,
                "error": f"版本不存在或文件丢失: {version_name}"
            }, ensure_ascii=False)
        
        # 先创建当前版本的备份
        backup_version_name = f"backup_before_restore_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        create_glossary_version(glossary_name, backup_version_name, cache_dir)
        
        # 恢复版本
        with open(version_file, 'r', encoding='utf-8') as f:
            version_data = json.load(f)
        
        # 保留原始元数据中的版本历史
        if "metadata" in version_data and "metadata" in glossary_data:
            version_data["metadata"]["versions"] = glossary_data["metadata"].get("versions", [])
        
        # 更新恢复信息
        if "metadata" in version_data:
            version_data["metadata"]["last_updated"] = datetime.datetime.now().isoformat()
            version_data["metadata"]["restored_from"] = version_name
        
        # 保存恢复后的词库
        with open(glossary_file, 'w', encoding='utf-8') as f:
            json.dump(version_data, f, ensure_ascii=False, indent=2)
        
        # 更新索引
        create_glossary_index(glossary_name, cache_dir)
        
        return json.dumps({
            "success": True,
            "message": f"词库已恢复到版本: {version_name}",
            "backup_version": backup_version_name,
            "term_count": len(version_data.get("terms", []))
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"恢复词库版本时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def match_terms(text: str, 
                glossary_name: str, 
                is_source_lang: bool = True,
                min_confidence: float = 0.7,
                cache_dir: Optional[str] = None) -> str:
    """
    在文本中匹配词库术语
    
    Args:
        text (str): 要匹配的文本
        glossary_name (str): 词库名称
        is_source_lang (bool): 是否在源语言中匹配，False表示在目标语言中匹配
        min_confidence (float): 最小置信度阈值
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的匹配结果
    """
    try:
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        
        # 构建词库文件路径
        glossary_file = os.path.join(cache_dir, f"{glossary_name}.json")
        
        if not os.path.exists(glossary_file):
            return json.dumps({
                "success": False,
                "error": f"词库不存在: {glossary_name}"
            }, ensure_ascii=False)
        
        # 加载词库
        with open(glossary_file, 'r', encoding='utf-8') as f:
            glossary_data = json.load(f)
        
        if "terms" not in glossary_data:
            return json.dumps({
                "success": False,
                "error": f"词库格式无效: {glossary_name}"
            }, ensure_ascii=False)
        
        # 确定匹配字段
        match_field = "source_term" if is_source_lang else "target_term"
        result_field = "target_term" if is_source_lang else "source_term"
        
        # 按长度排序术语，优先匹配长术语
        sorted_terms = sorted(
            [t for t in glossary_data["terms"] if t.get("confidence", 1.0) >= min_confidence],
            key=lambda x: len(x.get(match_field, "")),
            reverse=True
        )
        
        # 匹配结果
        matches = []
        matched_positions = set()
        
        # 对每个术语进行匹配
        for term in sorted_terms:
            source = term.get(match_field, "")
            if not source:
                continue
            
            # 查找所有匹配位置
            for match in re.finditer(r'\b' + re.escape(source) + r'\b', text):
                start, end = match.span()
                
                # 检查是否与已匹配的位置重叠
                overlap = False
                for pos_start, pos_end in matched_positions:
                    if (start < pos_end and end > pos_start):
                        overlap = True
                        break
                
                if not overlap:
                    matches.append({
                        "term_id": term.get("term_id"),
                        "source": source,
                        "target": term.get(result_field),
                        "category": term.get("category", "未分类"),
                        "confidence": term.get("confidence", 1.0),
                        "position": {
                            "start": start,
                            "end": end
                        }
                    })
                    
                    # 记录已匹配位置
                    matched_positions.add((start, end))
                    
                    # 更新使用计数
                    term["usage_count"] = term.get("usage_count", 0) + 1
        
        # 按位置排序匹配结果
        matches.sort(key=lambda x: x["position"]["start"])
        
        # 保存更新后的词库
        with open(glossary_file, 'w', encoding='utf-8') as f:
            json.dump(glossary_data, f, ensure_ascii=False, indent=2)
        
        return json.dumps({
            "success": True,
            "text_length": len(text),
            "matches": matches,
            "match_count": len(matches)
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"匹配术语时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def merge_glossaries(glossary_names: List[str], 
                     output_name: str, 
                     conflict_strategy: str = "newer",
                     cache_dir: Optional[str] = None) -> str:
    """
    合并多个词库
    
    Args:
        glossary_names (List[str]): 要合并的词库名称列表
        output_name (str): 输出词库名称
        conflict_strategy (str): 冲突处理策略（newer, higher_confidence, keep_first）
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        
        if not glossary_names:
            return json.dumps({
                "success": False,
                "error": "没有提供词库名称"
            }, ensure_ascii=False)
        
        # 验证所有词库是否存在
        for name in glossary_names:
            glossary_file = os.path.join(cache_dir, f"{name}.json")
            if not os.path.exists(glossary_file):
                return json.dumps({
                    "success": False,
                    "error": f"词库不存在: {name}"
                }, ensure_ascii=False)
        
        # 合并词库
        merged_terms = {}
        metadata_list = []
        
        for name in glossary_names:
            glossary_file = os.path.join(cache_dir, f"{name}.json")
            
            with open(glossary_file, 'r', encoding='utf-8') as f:
                glossary_data = json.load(f)
            
            if "metadata" in glossary_data:
                metadata_list.append(glossary_data["metadata"])
            
            if "terms" in glossary_data:
                for term in glossary_data["terms"]:
                    term_id = term.get("term_id")
                    
                    if term_id in merged_terms:
                        # 处理冲突
                        if conflict_strategy == "newer":
                            existing_date = datetime.datetime.fromisoformat(
                                merged_terms[term_id].get("last_updated", "1970-01-01T00:00:00")
                            )
                            current_date = datetime.datetime.fromisoformat(
                                term.get("last_updated", "1970-01-01T00:00:00")
                            )
                            
                            if current_date > existing_date:
                                merged_terms[term_id] = term
                        
                        elif conflict_strategy == "higher_confidence":
                            existing_confidence = merged_terms[term_id].get("confidence", 0.0)
                            current_confidence = term.get("confidence", 0.0)
                            
                            if current_confidence > existing_confidence:
                                merged_terms[term_id] = term
                        
                        # keep_first策略下保留第一个遇到的术语，不需要额外处理
                    else:
                        merged_terms[term_id] = term
        
        # 创建合并后的词库
        merged_glossary = {
            "metadata": {
                "name": output_name,
                "created": datetime.datetime.now().isoformat(),
                "last_updated": datetime.datetime.now().isoformat(),
                "term_count": len(merged_terms),
                "version": "1.0",
                "merged_from": glossary_names,
                "conflict_strategy": conflict_strategy
            },
            "terms": list(merged_terms.values())
        }
        
        # 继承源语言和目标语言设置
        if metadata_list:
            first_metadata = metadata_list[0]
            if "source_language" in first_metadata:
                merged_glossary["metadata"]["source_language"] = first_metadata["source_language"]
            if "target_language" in first_metadata:
                merged_glossary["metadata"]["target_language"] = first_metadata["target_language"]
        
        # 保存合并后的词库
        output_file = os.path.join(cache_dir, f"{output_name}.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(merged_glossary, f, ensure_ascii=False, indent=2)
        
        # 创建索引
        create_glossary_index(output_name, cache_dir)
        
        return json.dumps({
            "success": True,
            "message": "词库已成功合并",
            "output_name": output_name,
            "term_count": len(merged_terms),
            "source_glossaries": glossary_names
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"合并词库时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def get_glossary_statistics(glossary_name: str, 
                            cache_dir: Optional[str] = None) -> str:
    """
    获取词库的统计信息
    
    Args:
        glossary_name (str): 词库名称
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的统计信息
    """
    try:
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        
        # 构建词库文件路径
        glossary_file = os.path.join(cache_dir, f"{glossary_name}.json")
        
        if not os.path.exists(glossary_file):
            return json.dumps({
                "success": False,
                "error": f"词库不存在: {glossary_name}"
            }, ensure_ascii=False)
        
        # 加载词库
        with open(glossary_file, 'r', encoding='utf-8') as f:
            glossary_data = json.load(f)
        
        if "terms" not in glossary_data:
            return json.dumps({
                "success": False,
                "error": f"词库格式无效: {glossary_name}"
            }, ensure_ascii=False)
        
        # 基本统计
        terms = glossary_data.get("terms", [])
        term_count = len(terms)
        
        # 分类统计
        categories = {}
        for term in terms:
            category = term.get("category", "未分类")
            if category in categories:
                categories[category] += 1
            else:
                categories[category] = 1
        
        # 使用频率统计
        usage_stats = {
            "never_used": 0,
            "low_usage": 0,  # 1-10次
            "medium_usage": 0,  # 11-50次
            "high_usage": 0  # 50次以上
        }
        
        for term in terms:
            usage_count = term.get("usage_count", 0)
            
            if usage_count == 0:
                usage_stats["never_used"] += 1
            elif usage_count <= 10:
                usage_stats["low_usage"] += 1
            elif usage_count <= 50:
                usage_stats["medium_usage"] += 1
            else:
                usage_stats["high_usage"] += 1
        
        # 置信度统计
        confidence_stats = {
            "high": 0,  # 0.8-1.0
            "medium": 0,  # 0.5-0.8
            "low": 0  # <0.5
        }
        
        for term in terms:
            confidence = term.get("confidence", 1.0)
            
            if confidence >= 0.8:
                confidence_stats["high"] += 1
            elif confidence >= 0.5:
                confidence_stats["medium"] += 1
            else:
                confidence_stats["low"] += 1
        
        # 术语长度统计
        source_length_stats = {
            "short": 0,  # 1-3个字符
            "medium": 0,  # 4-10个字符
            "long": 0  # >10个字符
        }
        
        target_length_stats = {
            "short": 0,  # 1-3个字符
            "medium": 0,  # 4-10个字符
            "long": 0  # >10个字符
        }
        
        for term in terms:
            source_length = len(term.get("source_term", ""))
            target_length = len(term.get("target_term", ""))
            
            # 源语言长度
            if source_length <= 3:
                source_length_stats["short"] += 1
            elif source_length <= 10:
                source_length_stats["medium"] += 1
            else:
                source_length_stats["long"] += 1
            
            # 目标语言长度
            if target_length <= 3:
                target_length_stats["short"] += 1
            elif target_length <= 10:
                target_length_stats["medium"] += 1
            else:
                target_length_stats["long"] += 1
        
        # 最近更新统计
        now = datetime.datetime.now()
        update_stats = {
            "last_day": 0,
            "last_week": 0,
            "last_month": 0,
            "older": 0
        }
        
        for term in terms:
            if "last_updated" in term:
                try:
                    update_time = datetime.datetime.fromisoformat(term["last_updated"])
                    delta = now - update_time
                    
                    if delta.days < 1:
                        update_stats["last_day"] += 1
                    elif delta.days < 7:
                        update_stats["last_week"] += 1
                    elif delta.days < 30:
                        update_stats["last_month"] += 1
                    else:
                        update_stats["older"] += 1
                except:
                    update_stats["older"] += 1
            else:
                update_stats["older"] += 1
        
        # 构建统计结果
        statistics = {
            "glossary_name": glossary_name,
            "term_count": term_count,
            "categories": categories,
            "usage_statistics": usage_stats,
            "confidence_statistics": confidence_stats,
            "source_length_statistics": source_length_stats,
            "target_length_statistics": target_length_stats,
            "update_statistics": update_stats,
            "metadata": glossary_data.get("metadata", {})
        }
        
        return json.dumps({
            "success": True,
            "statistics": statistics
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"获取词库统计信息时出错: {str(e)}"
        }, ensure_ascii=False)


# 辅助函数
def create_glossary_index(glossary_name: str, cache_dir: str) -> bool:
    """
    为词库创建索引，加速术语查询
    
    Args:
        glossary_name (str): 词库名称
        cache_dir (str): 缓存目录
        
    Returns:
        bool: 是否成功创建索引
    """
    try:
        # 构建词库文件路径
        glossary_file = os.path.join(cache_dir, f"{glossary_name}.json")
        
        if not os.path.exists(glossary_file):
            return False
        
        # 加载词库
        with open(glossary_file, 'r', encoding='utf-8') as f:
            glossary_data = json.load(f)
        
        if "terms" not in glossary_data:
            return False
        
        # 创建索引
        source_index = {}
        target_index = {}
        
        for term in glossary_data["terms"]:
            term_id = term.get("term_id")
            source_term = term.get("source_term", "").lower()
            target_term = term.get("target_term", "").lower()
            
            # 为源语言术语创建索引
            for i in range(1, len(source_term) + 1):
                prefix = source_term[:i]
                if prefix not in source_index:
                    source_index[prefix] = []
                
                if term_id not in source_index[prefix]:
                    source_index[prefix].append(term_id)
            
            # 为目标语言术语创建索引
            for i in range(1, len(target_term) + 1):
                prefix = target_term[:i]
                if prefix not in target_index:
                    target_index[prefix] = []
                
                if term_id not in target_index[prefix]:
                    target_index[prefix].append(term_id)
        
        # 保存索引
        index_data = {
            "source_term": source_index,
            "target_term": target_index,
            "created": datetime.datetime.now().isoformat(),
            "glossary_name": glossary_name
        }
        
        index_file = os.path.join(cache_dir, f"{glossary_name}_index.json")
        
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False)
        
        return True
        
    except Exception:
        return False