#!/usr/bin/env python3
"""
JSON处理工具

提供JSON数据处理功能，用于生成结构化输出：
- JSON数据验证
- JSON数据转换
- JSON数据合并
- JSON数据过滤
- JSON数据排序
- 生成编辑反馈JSON
"""

import json
import os
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from strands import tool


# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _ensure_directory(path: str) -> str:
    """确保目录存在，如果不存在则创建"""
    os.makedirs(path, exist_ok=True)
    return path


def _get_cache_dir(research_id: str, version: str = "v1") -> str:
    """获取缓存目录路径"""
    cache_dir = f".cache/pmc_literature/{research_id}/feedback/editor/{version}"
    return _ensure_directory(cache_dir)


def _get_verification_dir(research_id: str, version: str = "v1") -> str:
    """获取验证目录路径"""
    verification_dir = f".cache/pmc_literature/{research_id}/feedback/editor/{version}/verification"
    return _ensure_directory(verification_dir)


def _get_status_file_path(research_id: str) -> str:
    """获取状态文件路径"""
    status_dir = f".cache/pmc_literature/{research_id}"
    _ensure_directory(status_dir)
    return os.path.join(status_dir, "step6.status")


def _update_status(research_id: str, status: str, progress: int, current_step: str, result_path: str = "") -> None:
    """更新处理状态文件"""
    status_file = _get_status_file_path(research_id)
    status_data = {
        "research_id": research_id,
        "status": status,  # "started", "in_progress", "completed", "failed"
        "progress": progress,  # 0-100
        "current_step": current_step,
        "result_path": result_path,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(status_data, f, ensure_ascii=False, indent=2)


@tool
def validate_json(json_data: str) -> str:
    """
    验证JSON数据格式是否有效
    
    Args:
        json_data (str): 要验证的JSON字符串
        
    Returns:
        str: JSON格式的验证结果
    """
    try:
        # 尝试解析JSON数据
        data = json.loads(json_data)
        
        return json.dumps({
            "status": "success",
            "valid": True,
            "message": "JSON格式有效"
        }, ensure_ascii=False)
    
    except json.JSONDecodeError as e:
        logger.error(f"JSON验证失败: {e}")
        return json.dumps({
            "status": "error",
            "valid": False,
            "message": f"JSON格式无效: {e}",
            "error_position": {
                "line": e.lineno,
                "column": e.colno,
                "position": e.pos
            }
        }, ensure_ascii=False)


@tool
def convert_to_json(data: str, source_format: str) -> str:
    """
    将其他格式的数据转换为JSON
    
    Args:
        data (str): 要转换的数据
        source_format (str): 源数据格式，可选值：text, csv, yaml, xml
        
    Returns:
        str: JSON格式的转换结果
    """
    try:
        # 验证源格式参数
        valid_formats = ["text", "csv", "yaml", "xml"]
        if source_format not in valid_formats:
            return json.dumps({
                "status": "error",
                "message": f"无效的源格式: {source_format}，有效值为: {', '.join(valid_formats)}"
            }, ensure_ascii=False)
        
        # 根据源格式进行转换
        if source_format == "text":
            # 将文本转换为简单的JSON对象
            result = {"text": data}
        
        elif source_format == "csv":
            import csv
            from io import StringIO
            
            # 将CSV转换为JSON数组
            result = []
            csv_reader = csv.DictReader(StringIO(data))
            for row in csv_reader:
                result.append(dict(row))
        
        elif source_format == "yaml":
            import yaml
            
            # 将YAML转换为JSON
            result = yaml.safe_load(data)
        
        elif source_format == "xml":
            import xmltodict
            
            # 将XML转换为JSON
            result = xmltodict.parse(data)
        
        return json.dumps({
            "status": "success",
            "source_format": source_format,
            "result": result
        }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"转换失败: {e}")
        return json.dumps({
            "status": "error",
            "message": f"转换失败: {e}"
        }, ensure_ascii=False)


@tool
def merge_json(json1: Dict[str, Any], json2: Dict[str, Any], merge_strategy: str = "deep") -> str:
    """
    合并两个JSON对象
    
    Args:
        json1 (Dict[str, Any]): 第一个JSON对象
        json2 (Dict[str, Any]): 第二个JSON对象
        merge_strategy (str): 合并策略，可选值：deep（深度合并）, shallow（浅合并）, override（覆盖）
        
    Returns:
        str: JSON格式的合并结果
    """
    try:
        # 验证合并策略参数
        valid_strategies = ["deep", "shallow", "override"]
        if merge_strategy not in valid_strategies:
            return json.dumps({
                "status": "error",
                "message": f"无效的合并策略: {merge_strategy}，有效值为: {', '.join(valid_strategies)}"
            }, ensure_ascii=False)
        
        # 根据合并策略进行合并
        if merge_strategy == "override":
            # 直接用第二个JSON覆盖第一个JSON
            result = {**json1, **json2}
        
        elif merge_strategy == "shallow":
            # 浅合并，只合并顶层键
            result = json1.copy()
            for key, value in json2.items():
                if key not in result:
                    result[key] = value
        
        elif merge_strategy == "deep":
            # 深度合并，递归合并嵌套结构
            def deep_merge(source, destination):
                for key, value in source.items():
                    if key in destination:
                        if isinstance(value, dict) and isinstance(destination[key], dict):
                            deep_merge(value, destination[key])
                        elif isinstance(value, list) and isinstance(destination[key], list):
                            destination[key].extend(value)
                        else:
                            destination[key] = value
                    else:
                        destination[key] = value
                return destination
            
            result = deep_merge(json2, json1.copy())
        
        return json.dumps({
            "status": "success",
            "merge_strategy": merge_strategy,
            "result": result
        }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"合并失败: {e}")
        return json.dumps({
            "status": "error",
            "message": f"合并失败: {e}"
        }, ensure_ascii=False)


@tool
def filter_json(json_data: Dict[str, Any], filter_criteria: Dict[str, Any]) -> str:
    """
    根据条件过滤JSON数据
    
    Args:
        json_data (Dict[str, Any]): 要过滤的JSON数据
        filter_criteria (Dict[str, Any]): 过滤条件，格式为{key: value}或{key: {operator: value}}
        
    Returns:
        str: JSON格式的过滤结果
    """
    try:
        # 定义过滤函数
        def match_criteria(item, criteria):
            for key, condition in criteria.items():
                if key not in item:
                    return False
                
                if isinstance(condition, dict) and "operator" in condition:
                    operator = condition["operator"]
                    value = condition["value"]
                    
                    if operator == "eq":
                        if item[key] != value:
                            return False
                    elif operator == "neq":
                        if item[key] == value:
                            return False
                    elif operator == "gt":
                        if not (isinstance(item[key], (int, float)) and item[key] > value):
                            return False
                    elif operator == "lt":
                        if not (isinstance(item[key], (int, float)) and item[key] < value):
                            return False
                    elif operator == "gte":
                        if not (isinstance(item[key], (int, float)) and item[key] >= value):
                            return False
                    elif operator == "lte":
                        if not (isinstance(item[key], (int, float)) and item[key] <= value):
                            return False
                    elif operator == "contains":
                        if not (isinstance(item[key], str) and value in item[key]):
                            return False
                    elif operator == "starts_with":
                        if not (isinstance(item[key], str) and item[key].startswith(value)):
                            return False
                    elif operator == "ends_with":
                        if not (isinstance(item[key], str) and item[key].endswith(value)):
                            return False
                    else:
                        return False
                else:
                    if item[key] != condition:
                        return False
            
            return True
        
        # 应用过滤条件
        if isinstance(json_data, list):
            # 如果是列表，过滤列表中的每个项
            filtered_data = [item for item in json_data if match_criteria(item, filter_criteria)]
        else:
            # 如果是单个对象，直接应用过滤条件
            filtered_data = json_data if match_criteria(json_data, filter_criteria) else {}
        
        return json.dumps({
            "status": "success",
            "filter_criteria": filter_criteria,
            "result": filtered_data
        }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"过滤失败: {e}")
        return json.dumps({
            "status": "error",
            "message": f"过滤失败: {e}"
        }, ensure_ascii=False)


@tool
def sort_json_array(json_array: List[Dict[str, Any]], sort_key: str, sort_order: str = "asc") -> str:
    """
    对JSON数组进行排序
    
    Args:
        json_array (List[Dict[str, Any]]): 要排序的JSON数组
        sort_key (str): 排序键
        sort_order (str): 排序顺序，可选值：asc（升序）, desc（降序）
        
    Returns:
        str: JSON格式的排序结果
    """
    try:
        # 验证排序顺序参数
        valid_orders = ["asc", "desc"]
        if sort_order not in valid_orders:
            return json.dumps({
                "status": "error",
                "message": f"无效的排序顺序: {sort_order}，有效值为: {', '.join(valid_orders)}"
            }, ensure_ascii=False)
        
        # 检查数组中的每个项是否都有排序键
        for item in json_array:
            if sort_key not in item:
                return json.dumps({
                    "status": "error",
                    "message": f"排序键 '{sort_key}' 在某些项中不存在"
                }, ensure_ascii=False)
        
        # 对数组进行排序
        reverse = (sort_order == "desc")
        sorted_array = sorted(json_array, key=lambda x: x[sort_key], reverse=reverse)
        
        return json.dumps({
            "status": "success",
            "sort_key": sort_key,
            "sort_order": sort_order,
            "result": sorted_array
        }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"排序失败: {e}")
        return json.dumps({
            "status": "error",
            "message": f"排序失败: {e}"
        }, ensure_ascii=False)


@tool
def extract_json_path(json_data: Dict[str, Any], json_path: str) -> str:
    """
    从JSON数据中提取指定路径的值
    
    Args:
        json_data (Dict[str, Any]): JSON数据
        json_path (str): JSON路径表达式，例如：data.items[0].name
        
    Returns:
        str: JSON格式的提取结果
    """
    try:
        # 解析JSON路径
        path_parts = []
        current_part = ""
        in_brackets = False
        
        for char in json_path:
            if char == "." and not in_brackets:
                if current_part:
                    path_parts.append(current_part)
                    current_part = ""
            elif char == "[":
                if current_part:
                    path_parts.append(current_part)
                    current_part = ""
                in_brackets = True
            elif char == "]":
                if in_brackets:
                    path_parts.append(int(current_part) if current_part.isdigit() else current_part)
                    current_part = ""
                    in_brackets = False
            else:
                current_part += char
        
        if current_part:
            path_parts.append(current_part)
        
        # 提取值
        result = json_data
        for part in path_parts:
            if isinstance(result, dict):
                if part not in result:
                    return json.dumps({
                        "status": "error",
                        "message": f"路径 '{json_path}' 中的键 '{part}' 不存在"
                    }, ensure_ascii=False)
                result = result[part]
            elif isinstance(result, list):
                if not isinstance(part, int):
                    return json.dumps({
                        "status": "error",
                        "message": f"路径 '{json_path}' 中的索引 '{part}' 不是有效的整数"
                    }, ensure_ascii=False)
                if part >= len(result):
                    return json.dumps({
                        "status": "error",
                        "message": f"路径 '{json_path}' 中的索引 '{part}' 超出范围"
                    }, ensure_ascii=False)
                result = result[part]
            else:
                return json.dumps({
                    "status": "error",
                    "message": f"路径 '{json_path}' 中的 '{part}' 不是有效的键或索引"
                }, ensure_ascii=False)
        
        return json.dumps({
            "status": "success",
            "json_path": json_path,
            "result": result
        }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"提取失败: {e}")
        return json.dumps({
            "status": "error",
            "message": f"提取失败: {e}"
        }, ensure_ascii=False)


@tool
def generate_editor_feedback(research_id: str, feedback_data: Dict[str, Any], version: str = "v1") -> str:
    """
    生成编辑反馈JSON文件
    
    Args:
        research_id (str): 研究ID，用于指定工作目录
        feedback_data (Dict[str, Any]): 编辑反馈数据
        version (str): 版本号，默认v1
        
    Returns:
        str: JSON格式的操作结果，包含生成的文件路径
    """
    try:
        # 更新状态
        _update_status(research_id, "in_progress", 80, "生成编辑反馈文件")
        
        # 获取工作目录
        cache_dir = _get_cache_dir(research_id, version)
        
        # 生成时间戳
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        
        # 构建文件名
        file_name = f"editor_{version}_{timestamp}.json"
        file_path = os.path.join(cache_dir, file_name)
        
        # 添加元数据
        feedback_data.update({
            "metadata": {
                "research_id": research_id,
                "version": version,
                "timestamp": datetime.utcnow().isoformat(),
                "generator": "pubmed_literature_editor_assistant"
            }
        })
        
        # 写入文件
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(feedback_data, f, ensure_ascii=False, indent=2)
        
        # 更新状态为完成
        _update_status(research_id, "completed", 100, "编辑反馈生成完成", file_path)
        
        return json.dumps({
            "status": "success",
            "file_path": file_path,
            "message": f"编辑反馈已生成: {file_path}"
        }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"生成编辑反馈失败: {e}")
        _update_status(research_id, "failed", 0, f"生成编辑反馈失败: {e}")
        return json.dumps({
            "status": "error", 
            "message": f"生成编辑反馈失败: {e}"
        }, ensure_ascii=False)


@tool
def create_editor_feedback_template(research_id: str, article_info: Dict[str, Any], version: str = "v1") -> str:
    """
    创建编辑反馈模板
    
    Args:
        research_id (str): 研究ID，用于指定工作目录
        article_info (Dict[str, Any]): 文章基本信息
        version (str): 版本号，默认v1
        
    Returns:
        str: JSON格式的模板数据
    """
    try:
        # 创建编辑反馈模板
        template = {
            "article_info": {
                "title": article_info.get("title", ""),
                "authors": article_info.get("authors", []),
                "submission_date": article_info.get("submission_date", datetime.utcnow().isoformat())
            },
            "evaluation": {
                "originality": {
                    "score": 0,  # 0-100
                    "comments": ""
                },
                "methodology": {
                    "score": 0,  # 0-100
                    "comments": ""
                },
                "significance": {
                    "score": 0,  # 0-100
                    "comments": ""
                },
                "presentation": {
                    "score": 0,  # 0-100
                    "comments": ""
                },
                "overall": {
                    "score": 0,  # 0-100
                    "comments": ""
                }
            },
            "literature_review": {
                "coverage": {
                    "score": 0,  # 0-100
                    "comments": ""
                },
                "relevance": {
                    "score": 0,  # 0-100
                    "comments": ""
                },
                "missing_references": []
            },
            "decision": {
                "recommendation": "",  # "accept", "minor_revision", "major_revision", "reject"
                "rationale": ""
            },
            "comments": {
                "strengths": [],
                "weaknesses": [],
                "major_revisions": [],
                "minor_revisions": []
            },
            "metadata": {
                "research_id": research_id,
                "version": version,
                "timestamp": datetime.utcnow().isoformat(),
                "generator": "pubmed_literature_editor_assistant",
                "template_version": "1.0"
            }
        }
        
        return json.dumps({
            "status": "success",
            "template": template
        }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"创建模板失败: {e}")
        return json.dumps({
            "status": "error", 
            "message": f"创建模板失败: {e}"
        }, ensure_ascii=False)


@tool
def validate_editor_feedback(feedback_data: Dict[str, Any]) -> str:
    """
    验证编辑反馈数据是否符合要求
    
    Args:
        feedback_data (Dict[str, Any]): 编辑反馈数据
        
    Returns:
        str: JSON格式的验证结果
    """
    try:
        # 定义必需的字段
        required_fields = {
            "article_info": ["title", "authors"],
            "evaluation": ["originality", "methodology", "significance", "presentation", "overall"],
            "decision": ["recommendation", "rationale"],
            "comments": ["strengths", "weaknesses"]
        }
        
        # 验证必需的字段
        errors = []
        
        for section, fields in required_fields.items():
            if section not in feedback_data:
                errors.append(f"缺少必需的部分: {section}")
                continue
            
            for field in fields:
                if field not in feedback_data[section]:
                    errors.append(f"在 {section} 部分缺少必需的字段: {field}")
        
        # 验证评分范围
        if "evaluation" in feedback_data:
            for category, data in feedback_data["evaluation"].items():
                if "score" in data and not (0 <= data["score"] <= 100):
                    errors.append(f"评分 {category} 必须在0-100范围内")
        
        # 验证决策建议
        if "decision" in feedback_data and "recommendation" in feedback_data["decision"]:
            valid_recommendations = ["accept", "minor_revision", "major_revision", "reject"]
            if feedback_data["decision"]["recommendation"] not in valid_recommendations:
                errors.append(f"无效的决策建议: {feedback_data['decision']['recommendation']}，有效值为: {', '.join(valid_recommendations)}")
        
        # 返回验证结果
        if errors:
            return json.dumps({
                "status": "error",
                "valid": False,
                "errors": errors
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "status": "success",
                "valid": True,
                "message": "编辑反馈数据有效"
            }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"验证失败: {e}")
        return json.dumps({
            "status": "error",
            "message": f"验证失败: {e}"
        }, ensure_ascii=False)