#!/usr/bin/env python3
"""
文献评估格式化工具

将文献评估结果转换为标准化的JSON格式，支持多维度评估结果的结构化展示和存储
"""

import json
import os
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from datetime import datetime
import logging
import jsonschema

from strands import tool

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("assessment_formatter")

# 评估报告JSON模式定义
ASSESSMENT_SCHEMA = {
    "type": "object",
    "required": ["overall_assessment", "dimensions"],
    "properties": {
        "metadata": {
            "type": "object",
            "properties": {
                "assessment_id": {"type": "string"},
                "assessment_date": {"type": "string", "format": "date-time"},
                "literature_title": {"type": "string"},
                "research_id": {"type": "string"},
                "version": {"type": "string"}
            }
        },
        "overall_assessment": {
            "type": "object",
            "required": ["score", "level", "summary"],
            "properties": {
                "score": {"type": "number", "minimum": 0, "maximum": 100},
                "level": {"type": "string"},
                "summary": {"type": "string"}
            }
        },
        "dimensions": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "required": ["score", "level", "issues"],
                "properties": {
                    "score": {"type": "number", "minimum": 0, "maximum": 100},
                    "level": {"type": "string"},
                    "issues": {"type": "array", "items": {"type": "string"}},
                    "detailed_analysis": {"type": "object"}
                }
            }
        },
        "problems": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["dimension", "description"],
                "properties": {
                    "dimension": {"type": "string"},
                    "severity": {"type": "string", "enum": ["critical", "major", "minor", "suggestion"]},
                    "description": {"type": "string"},
                    "location": {"type": "string"},
                    "recommendation": {"type": "string"}
                }
            }
        },
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["dimension", "description"],
                "properties": {
                    "dimension": {"type": "string"},
                    "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                    "description": {"type": "string"},
                    "expected_impact": {"type": "string"}
                }
            }
        }
    }
}

@tool
def assessment_formatter(
    assessment_data: Union[Dict[str, Any], str], 
    research_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    format_output: bool = True,
    validate_schema: bool = True
) -> str:
    """
    将文献评估结果转换为标准化的JSON格式，支持多维度评估结果的结构化展示和存储
    
    Args:
        assessment_data (Union[Dict[str, Any], str]): 评估数据（必需），可以是字典或JSON字符串
        research_id (Optional[str]): 研究ID，用于指定缓存目录（可选）
        metadata (Optional[Dict[str, Any]]): 元数据对象（可选）
        format_output (bool): 是否美化输出（可选，默认True）
        validate_schema (bool): 是否验证JSON结构（可选，默认True）
        
    Returns:
        str: 标准化的JSON格式评估报告，包含总体评分、各维度评分、问题列表和修正建议
    """
    try:
        # 1. 解析评估数据
        if isinstance(assessment_data, str):
            try:
                assessment_data = json.loads(assessment_data)
            except json.JSONDecodeError as e:
                return json.dumps({
                    "error": f"无效的JSON字符串: {str(e)}",
                    "status": "failed"
                }, ensure_ascii=False, indent=2 if format_output else None)
        
        if not isinstance(assessment_data, dict):
            return json.dumps({
                "error": "评估数据必须是字典或有效的JSON字符串",
                "status": "failed"
            }, ensure_ascii=False, indent=2 if format_output else None)
        
        # 2. 设置缓存目录（如果提供了research_id）
        cache_dir = None
        if research_id:
            cache_dir = setup_cache_directory(research_id)
        
        # 3. 处理元数据
        formatted_assessment = process_assessment_data(assessment_data, research_id, metadata)
        
        # 4. 验证JSON结构（如果需要）
        if validate_schema:
            try:
                jsonschema.validate(instance=formatted_assessment, schema=ASSESSMENT_SCHEMA)
            except jsonschema.exceptions.ValidationError as e:
                logger.warning(f"评估报告不符合预定义模式: {str(e)}")
                formatted_assessment["schema_validation"] = {
                    "valid": False,
                    "error": str(e)
                }
        
        # 5. 缓存结果（如果提供了research_id）
        if research_id and cache_dir:
            cache_assessment_report(formatted_assessment, research_id, cache_dir)
        
        # 6. 返回格式化的JSON
        indent = 2 if format_output else None
        return json.dumps(formatted_assessment, ensure_ascii=False, indent=indent)
        
    except Exception as e:
        logger.error(f"格式化评估报告时发生错误: {str(e)}", exc_info=True)
        return json.dumps({
            "error": f"格式化评估报告失败: {str(e)}",
            "status": "failed"
        }, ensure_ascii=False, indent=2 if format_output else None)


def setup_cache_directory(research_id: str) -> Path:
    """
    设置缓存目录，统一到 .cache/pmc_literature/<research_id>/feedback/reviewer/<version>/verification/
    版本选择规则：
      - 若存在 step5.status，则取 latest_version + 1
      - 否则扫描 feedback/reviewer 下的数字子目录最大值 + 1；未找到则为 1
    """
    # 安全处理research_id，避免路径遍历攻击
    safe_id = sanitize_filename(research_id)

    base_dir = Path(".cache/pmc_literature") / safe_id / "feedback" / "reviewer"
    base_dir.mkdir(parents=True, exist_ok=True)

    # 优先读取一次运行固定版本
    marker = Path(".cache/pmc_literature") / safe_id / ".current_run_version"
    version = None
    try:
        if marker.exists():
            with open(marker, "r", encoding="utf-8") as f:
                version = int(f.read().strip())
    except Exception:
        version = None

    # 尝试从 step5.status 判定版本
    if version is None:
        status_path = Path(".cache/pmc_literature") / safe_id / "step5.status"
        if status_path.exists():
            try:
                with open(status_path, "r", encoding="utf-8") as f:
                    status = json.load(f)
                latest = int(status.get("latest_version", 0))
                version = latest + 1 if latest >= 0 else 1
            except Exception:
                version = None

    # 扫描目录作为兜底
    if version is None:
        max_found = 0
        for sub in base_dir.glob("*"):
            if sub.is_dir():
                try:
                    v = int(sub.name)
                    if v > max_found:
                        max_found = v
                except Exception:
                    continue
        version = max_found + 1 if max_found >= 0 else 1

    cache_dir = base_dir / str(version) / "verification"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def sanitize_filename(filename: str) -> str:
    """
    安全处理文件名，避免路径遍历攻击
    
    Args:
        filename: 原始文件名
        
    Returns:
        str: 安全的文件名
    """
    # 移除路径分隔符和其他不安全字符
    unsafe_chars = ['/', '\\', '..', ':', '*', '?', '"', '<', '>', '|']
    safe_name = filename
    for char in unsafe_chars:
        safe_name = safe_name.replace(char, '_')
    
    # 如果文件名为空，使用默认名称
    if not safe_name:
        safe_name = "default"
    
    return safe_name


def process_assessment_data(
    assessment_data: Dict[str, Any], 
    research_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    处理评估数据，添加元数据和提取问题列表
    
    Args:
        assessment_data: 评估数据
        research_id: 研究ID
        metadata: 元数据对象
        
    Returns:
        Dict[str, Any]: 处理后的评估报告
    """
    # 创建新的评估报告对象
    formatted_assessment = {}
    
    # 1. 处理元数据
    formatted_assessment["metadata"] = generate_metadata(assessment_data, research_id, metadata)
    
    # 2. 复制总体评估
    if "overall_assessment" in assessment_data:
        formatted_assessment["overall_assessment"] = assessment_data["overall_assessment"]
    
    # 3. 复制维度评估
    if "dimensions" in assessment_data:
        formatted_assessment["dimensions"] = assessment_data["dimensions"]
    
    # 4. 提取问题列表
    formatted_assessment["problems"] = extract_problems(assessment_data)
    
    # 5. 提取建议列表
    formatted_assessment["recommendations"] = extract_recommendations(assessment_data)
    
    return formatted_assessment


def generate_metadata(
    assessment_data: Dict[str, Any], 
    research_id: Optional[str], 
    custom_metadata: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    生成评估报告元数据
    
    Args:
        assessment_data: 评估数据
        research_id: 研究ID
        custom_metadata: 自定义元数据
        
    Returns:
        Dict[str, Any]: 元数据对象
    """
    # 基本元数据
    metadata = {
        "assessment_id": generate_assessment_id(),
        "assessment_date": datetime.now().isoformat(),
        "version": "1.0"
    }
    
    # 添加research_id（如果提供）
    if research_id:
        metadata["research_id"] = research_id
    
    # 尝试从评估数据中提取文献标题
    if "title" in assessment_data:
        metadata["literature_title"] = assessment_data["title"]
    
    # 合并自定义元数据（如果提供）
    if custom_metadata:
        metadata.update(custom_metadata)
    
    return metadata


def generate_assessment_id() -> str:
    """
    生成唯一的评估ID
    
    Returns:
        str: 评估ID
    """
    # 使用时间戳和随机数生成唯一ID
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_suffix = hashlib.md5(os.urandom(32)).hexdigest()[:8]
    return f"assessment_{timestamp}_{random_suffix}"


def extract_problems(assessment_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    从评估数据中提取问题列表
    
    Args:
        assessment_data: 评估数据
        
    Returns:
        List[Dict[str, Any]]: 问题列表
    """
    problems = []
    
    # 如果已经有格式化的问题列表，直接返回
    if "problems" in assessment_data and isinstance(assessment_data["problems"], list):
        return assessment_data["problems"]
    
    # 从各维度中提取问题
    if "dimensions" in assessment_data:
        for dimension_name, dimension_data in assessment_data["dimensions"].items():
            if "issues" in dimension_data and isinstance(dimension_data["issues"], list):
                for issue in dimension_data["issues"]:
                    # 确定问题严重性
                    severity = determine_severity(dimension_data.get("score", 0), issue)
                    
                    problem = {
                        "dimension": dimension_name,
                        "severity": severity,
                        "description": issue,
                        "recommendation": generate_recommendation_for_issue(issue, dimension_name)
                    }
                    
                    # 尝试从问题描述中提取位置信息
                    location = extract_location_from_issue(issue)
                    if location:
                        problem["location"] = location
                    
                    problems.append(problem)
    
    return problems


def determine_severity(dimension_score: float, issue: str) -> str:
    """
    根据维度评分和问题描述确定问题严重性
    
    Args:
        dimension_score: 维度评分
        issue: 问题描述
        
    Returns:
        str: 问题严重性（critical, major, minor, suggestion）
    """
    # 根据关键词判断严重性
    critical_keywords = ["缺失", "严重", "错误", "不一致", "矛盾", "幻觉"]
    major_keywords = ["薄弱", "不足", "过度", "缺乏"]
    minor_keywords = ["可以改进", "建议", "考虑"]
    
    for keyword in critical_keywords:
        if keyword in issue:
            return "critical"
    
    for keyword in major_keywords:
        if keyword in issue:
            return "major"
    
    for keyword in minor_keywords:
        if keyword in issue:
            return "minor"
    
    # 根据维度评分判断严重性
    if dimension_score < 50:
        return "critical"
    elif dimension_score < 70:
        return "major"
    elif dimension_score < 85:
        return "minor"
    else:
        return "suggestion"


def extract_location_from_issue(issue: str) -> Optional[str]:
    """
    从问题描述中提取位置信息
    
    Args:
        issue: 问题描述
        
    Returns:
        Optional[str]: 位置信息
    """
    # 常见的位置关键词
    location_patterns = [
        r"在(.*?)部分",
        r"(.*?)部分",
        r"(.*?)章节"
    ]
    
    for pattern in location_patterns:
        import re
        match = re.search(pattern, issue)
        if match:
            return match.group(1)
    
    return None


def generate_recommendation_for_issue(issue: str, dimension: str) -> str:
    """
    为问题生成建议
    
    Args:
        issue: 问题描述
        dimension: 问题所属维度
        
    Returns:
        str: 建议内容
    """
    # 根据维度和问题描述生成建议
    if "缺失" in issue or "缺少" in issue:
        return f"添加{extract_missing_element(issue)}以增强{get_dimension_name(dimension)}"
    
    if "薄弱" in issue:
        return f"增强{extract_weak_element(issue)}的内容和质量"
    
    if "不一致" in issue:
        return "确保整个文档中的数据、引用和术语保持一致"
    
    if "过度" in issue:
        return "避免过度解读结果，使用更谨慎的表述"
    
    # 默认建议
    return f"修正{issue}以提高文献质量"


def extract_missing_element(issue: str) -> str:
    """
    从问题描述中提取缺失的元素
    
    Args:
        issue: 问题描述
        
    Returns:
        str: 缺失的元素
    """
    import re
    match = re.search(r"缺[失少](.*?)(?:的|$)", issue)
    if match:
        return match.group(1)
    return "必要的内容"


def extract_weak_element(issue: str) -> str:
    """
    从问题描述中提取薄弱的元素
    
    Args:
        issue: 问题描述
        
    Returns:
        str: 薄弱的元素
    """
    import re
    match = re.search(r"(.*?)(?:部分|章节)薄弱", issue)
    if match:
        return match.group(1)
    return "相关部分"


def get_dimension_name(dimension: str) -> str:
    """
    获取维度的中文名称
    
    Args:
        dimension: 维度代码
        
    Returns:
        str: 维度中文名称
    """
    dimension_names = {
        "structure_completeness": "结构完整性",
        "scientific_accuracy": "科学准确性",
        "methodology_soundness": "方法论合理性",
        "reference_quality": "引用质量",
        "conclusion_validity": "结论有效性",
        "information_completeness": "信息完整性"
    }
    
    return dimension_names.get(dimension, dimension)


def extract_recommendations(assessment_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    从评估数据中提取建议列表
    
    Args:
        assessment_data: 评估数据
        
    Returns:
        List[Dict[str, Any]]: 建议列表
    """
    recommendations = []
    
    # 如果已经有格式化的建议列表，直接返回
    if "recommendations" in assessment_data and isinstance(assessment_data["recommendations"], list):
        return assessment_data["recommendations"]
    
    # 从各维度中提取建议
    if "dimensions" in assessment_data:
        for dimension_name, dimension_data in assessment_data["dimensions"].items():
            if "detailed_analysis" in dimension_data and "recommendations" in dimension_data["detailed_analysis"]:
                dimension_recommendations = dimension_data["detailed_analysis"]["recommendations"]
                if isinstance(dimension_recommendations, list):
                    for rec in dimension_recommendations:
                        # 确定建议优先级
                        priority = determine_priority(dimension_data.get("score", 0), rec)
                        
                        recommendation = {
                            "dimension": dimension_name,
                            "priority": priority,
                            "description": rec,
                            "expected_impact": generate_expected_impact(rec, priority)
                        }
                        
                        recommendations.append(recommendation)
    
    return recommendations


def determine_priority(dimension_score: float, recommendation: str) -> str:
    """
    根据维度评分和建议内容确定优先级
    
    Args:
        dimension_score: 维度评分
        recommendation: 建议内容
        
    Returns:
        str: 优先级（high, medium, low）
    """
    # 根据关键词判断优先级
    high_keywords = ["添加", "增加", "修正", "解决", "必须"]
    medium_keywords = ["改进", "增强", "考虑", "建议"]
    
    for keyword in high_keywords:
        if keyword in recommendation:
            return "high"
    
    for keyword in medium_keywords:
        if keyword in recommendation:
            return "medium"
    
    # 根据维度评分判断优先级
    if dimension_score < 60:
        return "high"
    elif dimension_score < 80:
        return "medium"
    else:
        return "low"


def generate_expected_impact(recommendation: str, priority: str) -> str:
    """
    生成建议的预期影响
    
    Args:
        recommendation: 建议内容
        priority: 优先级
        
    Returns:
        str: 预期影响
    """
    # 根据优先级和建议内容生成预期影响
    if priority == "high":
        return "显著提高文献质量和可信度"
    elif priority == "medium":
        return "改善文献的专业性和完整性"
    else:
        return "细节优化，提升整体质量"


def cache_assessment_report(report: Dict[str, Any], research_id: str, cache_dir: Path) -> None:
    """
    缓存评估报告
    
    Args:
        report: 评估报告
        research_id: 研究ID
        cache_dir: 缓存目录
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    assessment_id = report.get("metadata", {}).get("assessment_id", "unknown")
    
    # 创建带时间戳的文件名
    cache_file = cache_dir / f"assessment_{assessment_id}_{timestamp}.json"
    
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    # 更新最新评估报告的链接
    latest_file = cache_dir / "latest_assessment.json"
    with open(latest_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    logger.info(f"评估报告已缓存至 {cache_file}")