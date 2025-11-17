"""
技术文档质量审核工具集

为document_reviewer_agent提供全面的文档质量评估和审核功能。
包括多维度质量评估、问题识别、反馈生成和审核决策等核心功能。

Author: Tools Developer
Created: 2025-11-17
Version: 1.0.0
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from strands import tool


# ==================== 数据模型定义 ====================

class DocumentContent:
    """文档内容数据模型"""
    def __init__(self, data: Dict[str, Any]):
        self.title = data.get("title", "")
        self.sections = data.get("sections", [])
        self.metadata = data.get("metadata", {})
        self.version = data.get("version", "1.0")
        self.created_at = data.get("created_at", "")
        self.modified_at = data.get("modified_at", "")


class QualityDimension:
    """质量维度定义"""
    CONTENT_COMPLETENESS = "content_completeness"
    TECHNICAL_ACCURACY = "technical_accuracy"
    LOGICAL_COHERENCE = "logical_coherence"
    FORMAT_COMPLIANCE = "format_compliance"
    LANGUAGE_EXPRESSION = "language_expression"


class IssueSeverity:
    """问题严重程度"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IssueType:
    """问题类型"""
    TECHNICAL_ERROR = "technical_error"
    STRUCTURAL_ISSUE = "structural_issue"
    FORMATTING_ERROR = "formatting_error"
    LANGUAGE_ISSUE = "language_issue"
    COMPLETENESS_ISSUE = "completeness_issue"
    CONSISTENCY_ISSUE = "consistency_issue"


# ==================== 辅助函数 ====================

def _validate_document_content(document: Dict[str, Any]) -> Tuple[bool, str]:
    """验证文档内容的基本格式"""
    if not isinstance(document, dict):
        return False, "文档内容必须是字典格式"
    
    if not document.get("title"):
        return False, "文档缺少标题"
    
    if not document.get("sections"):
        return False, "文档缺少章节内容"
    
    if not isinstance(document.get("sections"), list):
        return False, "章节内容必须是列表格式"
    
    return True, "验证通过"


def _calculate_section_quality(section: Dict[str, Any]) -> float:
    """计算单个章节的质量分数"""
    score = 100.0
    
    # 检查章节标题
    if not section.get("title"):
        score -= 20
    
    # 检查章节内容
    content = section.get("content", "")
    if not content:
        score -= 30
    elif len(content) < 50:
        score -= 15
    
    # 检查内容长度合理性
    if len(content) > 10000:
        score -= 5
    
    # 检查是否有子章节
    if section.get("subsections") and len(section["subsections"]) > 0:
        score += 5
    
    return max(0.0, min(100.0, score))


def _count_technical_terms(text: str) -> int:
    """统计技术术语数量（简化版）"""
    # 常见技术术语模式
    patterns = [
        r'\b[A-Z]{2,}\b',  # 大写缩写
        r'\b\w+\(\)',  # 函数调用
        r'\b\w+\.\w+',  # 点号分隔的术语
        r'`[^`]+`',  # 代码标记
    ]
    
    count = 0
    for pattern in patterns:
        count += len(re.findall(pattern, text))
    
    return count


def _check_code_blocks(text: str) -> Dict[str, Any]:
    """检查代码块的格式"""
    code_blocks = re.findall(r'```[\s\S]*?```', text)
    
    return {
        "count": len(code_blocks),
        "has_language_tags": sum(1 for block in code_blocks if re.match(r'```\w+', block)),
        "total_blocks": len(code_blocks)
    }


def _analyze_sentence_complexity(text: str) -> Dict[str, Any]:
    """分析句子复杂度"""
    sentences = re.split(r'[.!?。！？]', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        return {"avg_length": 0, "max_length": 0, "complexity_score": 0}
    
    lengths = [len(s) for s in sentences]
    avg_length = sum(lengths) / len(lengths)
    max_length = max(lengths)
    
    # 复杂度评分：基于平均句子长度
    if avg_length < 50:
        complexity_score = 100
    elif avg_length < 100:
        complexity_score = 80
    elif avg_length < 150:
        complexity_score = 60
    else:
        complexity_score = 40
    
    return {
        "avg_length": avg_length,
        "max_length": max_length,
        "complexity_score": complexity_score,
        "sentence_count": len(sentences)
    }


def _check_list_formatting(text: str) -> Dict[str, Any]:
    """检查列表格式"""
    unordered_lists = re.findall(r'^\s*[-*+]\s+.+$', text, re.MULTILINE)
    ordered_lists = re.findall(r'^\s*\d+\.\s+.+$', text, re.MULTILINE)
    
    return {
        "unordered_count": len(unordered_lists),
        "ordered_count": len(ordered_lists),
        "total_lists": len(unordered_lists) + len(ordered_lists)
    }


def _check_heading_structure(sections: List[Dict[str, Any]]) -> Dict[str, Any]:
    """检查标题结构"""
    heading_levels = []
    
    for section in sections:
        if section.get("level"):
            heading_levels.append(section["level"])
        
        # 递归检查子章节
        if section.get("subsections"):
            subsection_info = _check_heading_structure(section["subsections"])
            heading_levels.extend(subsection_info["levels"])
    
    return {
        "levels": heading_levels,
        "max_level": max(heading_levels) if heading_levels else 0,
        "min_level": min(heading_levels) if heading_levels else 0,
        "level_count": len(heading_levels)
    }


# ==================== 核心工具函数 ====================

@tool
def assess_document_quality(
    document: Dict[str, Any],
    dimensions: Optional[List[str]] = None,
    detailed_analysis: bool = True
) -> str:
    """
    从多个维度评估技术文档质量
    
    该工具对技术文档进行全面的质量评估，包括内容完整性、技术准确性、
    逻辑连贯性、格式规范性和语言表达等多个维度。每个维度提供0-100的评分，
    并给出详细的分析说明。
    
    Args:
        document (Dict[str, Any]): 文档内容对象，包含title、sections等字段
        dimensions (Optional[List[str]]): 要评估的维度列表，可选值：
            - content_completeness: 内容完整性
            - technical_accuracy: 技术准确性
            - logical_coherence: 逻辑连贯性
            - format_compliance: 格式规范性
            - language_expression: 语言表达
            如果不提供，则评估所有维度
        detailed_analysis (bool): 是否生成详细分析，默认为True
    
    Returns:
        str: JSON格式的评估结果，包含各维度评分和详细分析
        
    Example:
        >>> result = assess_document_quality(document_dict)
        >>> data = json.loads(result)
        >>> print(data['overall_score'])
    """
    try:
        # 验证文档内容
        is_valid, error_msg = _validate_document_content(document)
        if not is_valid:
            return json.dumps({
                "status": "error",
                "error": error_msg,
                "timestamp": datetime.utcnow().isoformat()
            }, ensure_ascii=False, indent=2)
        
        # 默认评估所有维度
        if dimensions is None:
            dimensions = [
                QualityDimension.CONTENT_COMPLETENESS,
                QualityDimension.TECHNICAL_ACCURACY,
                QualityDimension.LOGICAL_COHERENCE,
                QualityDimension.FORMAT_COMPLIANCE,
                QualityDimension.LANGUAGE_EXPRESSION
            ]
        
        doc_obj = DocumentContent(document)
        dimension_scores = {}
        dimension_details = {}
        
        # 评估每个维度
        for dimension in dimensions:
            if dimension == QualityDimension.CONTENT_COMPLETENESS:
                score, details = _assess_content_completeness(doc_obj, detailed_analysis)
                dimension_scores[dimension] = score
                if detailed_analysis:
                    dimension_details[dimension] = details
            
            elif dimension == QualityDimension.TECHNICAL_ACCURACY:
                score, details = _assess_technical_accuracy(doc_obj, detailed_analysis)
                dimension_scores[dimension] = score
                if detailed_analysis:
                    dimension_details[dimension] = details
            
            elif dimension == QualityDimension.LOGICAL_COHERENCE:
                score, details = _assess_logical_coherence(doc_obj, detailed_analysis)
                dimension_scores[dimension] = score
                if detailed_analysis:
                    dimension_details[dimension] = details
            
            elif dimension == QualityDimension.FORMAT_COMPLIANCE:
                score, details = _assess_format_compliance(doc_obj, detailed_analysis)
                dimension_scores[dimension] = score
                if detailed_analysis:
                    dimension_details[dimension] = details
            
            elif dimension == QualityDimension.LANGUAGE_EXPRESSION:
                score, details = _assess_language_expression(doc_obj, detailed_analysis)
                dimension_scores[dimension] = score
                if detailed_analysis:
                    dimension_details[dimension] = details
        
        # 计算总分
        overall_score = sum(dimension_scores.values()) / len(dimension_scores)
        
        result = {
            "status": "success",
            "overall_score": round(overall_score, 2),
            "dimension_scores": {k: round(v, 2) for k, v in dimension_scores.items()},
            "grade": _get_grade(overall_score),
            "assessment_summary": _generate_assessment_summary(overall_score, dimension_scores),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if detailed_analysis:
            result["dimension_details"] = dimension_details
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": f"评估过程发生错误: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }, ensure_ascii=False, indent=2)


def _assess_content_completeness(doc: DocumentContent, detailed: bool) -> Tuple[float, Dict[str, Any]]:
    """评估内容完整性"""
    score = 100.0
    issues = []
    
    # 检查标题
    if not doc.title or len(doc.title) < 5:
        score -= 10
        issues.append("文档标题过短或缺失")
    
    # 检查章节数量
    if len(doc.sections) < 3:
        score -= 15
        issues.append("文档章节数量过少，建议至少包含3个主要章节")
    
    # 检查每个章节的内容
    empty_sections = 0
    short_sections = 0
    for section in doc.sections:
        content = section.get("content", "")
        if not content:
            empty_sections += 1
        elif len(content) < 100:
            short_sections += 1
    
    if empty_sections > 0:
        score -= empty_sections * 10
        issues.append(f"存在{empty_sections}个空章节")
    
    if short_sections > 0:
        score -= short_sections * 5
        issues.append(f"存在{short_sections}个内容过少的章节（少于100字）")
    
    # 检查是否有概述或介绍
    has_intro = any(
        section.get("title", "").lower() in ["概述", "introduction", "overview", "简介"]
        for section in doc.sections
    )
    if not has_intro:
        score -= 10
        issues.append("缺少概述或介绍章节")
    
    # 检查是否有结论或总结
    has_conclusion = any(
        section.get("title", "").lower() in ["总结", "conclusion", "summary", "结论"]
        for section in doc.sections
    )
    if not has_conclusion:
        score -= 5
        issues.append("缺少总结或结论章节")
    
    score = max(0.0, min(100.0, score))
    
    details = {
        "score": score,
        "section_count": len(doc.sections),
        "empty_sections": empty_sections,
        "short_sections": short_sections,
        "has_introduction": has_intro,
        "has_conclusion": has_conclusion,
        "issues": issues
    }
    
    return score, details


def _assess_technical_accuracy(doc: DocumentContent, detailed: bool) -> Tuple[float, Dict[str, Any]]:
    """评估技术准确性"""
    score = 100.0
    issues = []
    
    # 收集所有文本内容
    all_text = doc.title + "\n"
    for section in doc.sections:
        all_text += section.get("content", "") + "\n"
    
    # 检查技术术语使用
    technical_term_count = _count_technical_terms(all_text)
    if technical_term_count < 5:
        score -= 15
        issues.append("技术术语使用过少，可能缺乏技术深度")
    
    # 检查代码块
    code_info = _check_code_blocks(all_text)
    if code_info["count"] > 0 and code_info["has_language_tags"] < code_info["total_blocks"]:
        missing_tags = code_info["total_blocks"] - code_info["has_language_tags"]
        score -= missing_tags * 3
        issues.append(f"存在{missing_tags}个代码块缺少语言标记")
    
    # 检查是否有示例
    has_examples = "example" in all_text.lower() or "示例" in all_text or "```" in all_text
    if not has_examples:
        score -= 10
        issues.append("文档缺少示例或代码演示")
    
    # 检查是否有技术规格说明
    has_specs = any(
        keyword in all_text.lower()
        for keyword in ["parameter", "参数", "return", "返回", "type", "类型"]
    )
    if not has_specs:
        score -= 10
        issues.append("缺少技术规格说明（如参数、返回值等）")
    
    # 检查技术准确性指标
    accuracy_indicators = {
        "has_version_info": any(
            keyword in all_text.lower()
            for keyword in ["version", "版本", "v1.", "v2."]
        ),
        "has_api_reference": any(
            keyword in all_text.lower()
            for keyword in ["api", "endpoint", "接口", "method"]
        ),
        "has_error_handling": any(
            keyword in all_text.lower()
            for keyword in ["error", "exception", "错误", "异常"]
        )
    }
    
    score = max(0.0, min(100.0, score))
    
    details = {
        "score": score,
        "technical_term_count": technical_term_count,
        "code_blocks": code_info,
        "has_examples": has_examples,
        "accuracy_indicators": accuracy_indicators,
        "issues": issues
    }
    
    return score, details


def _assess_logical_coherence(doc: DocumentContent, detailed: bool) -> Tuple[float, Dict[str, Any]]:
    """评估逻辑连贯性"""
    score = 100.0
    issues = []
    
    # 检查章节顺序合理性
    section_titles = [s.get("title", "").lower() for s in doc.sections]
    
    # 理想的章节顺序关键词
    intro_keywords = ["概述", "introduction", "overview", "简介"]
    conclusion_keywords = ["总结", "conclusion", "summary", "结论"]
    
    intro_index = -1
    conclusion_index = -1
    
    for i, title in enumerate(section_titles):
        if any(kw in title for kw in intro_keywords):
            intro_index = i
        if any(kw in title for kw in conclusion_keywords):
            conclusion_index = i
    
    # 检查概述是否在前面
    if intro_index > 0:
        score -= 10
        issues.append("概述章节应该放在文档前部")
    
    # 检查总结是否在后面
    if conclusion_index != -1 and conclusion_index < len(section_titles) - 2:
        score -= 10
        issues.append("总结章节应该放在文档后部")
    
    # 检查章节内容的连贯性
    for i, section in enumerate(doc.sections):
        content = section.get("content", "")
        
        # 检查是否有过渡性语句
        if i > 0 and i < len(doc.sections) - 1:
            has_transition = any(
                keyword in content[:200].lower()
                for keyword in ["首先", "其次", "然后", "接下来", "此外", "另外", 
                               "first", "second", "next", "furthermore", "moreover"]
            )
            if not has_transition:
                score -= 3
                issues.append(f"章节 '{section.get('title')}' 缺少过渡性语句")
    
    # 检查内容深度递进
    section_lengths = [len(s.get("content", "")) for s in doc.sections]
    if len(section_lengths) > 2:
        # 检查是否有明显的深度变化
        length_variance = max(section_lengths) - min(section_lengths)
        if length_variance < 100:
            score -= 5
            issues.append("章节内容长度过于均匀，可能缺乏层次感")
    
    score = max(0.0, min(100.0, score))
    
    details = {
        "score": score,
        "section_order_score": 100 if intro_index <= 0 and (conclusion_index == -1 or conclusion_index >= len(section_titles) - 2) else 80,
        "has_proper_introduction": intro_index != -1,
        "has_proper_conclusion": conclusion_index != -1,
        "transition_quality": "good" if score >= 85 else "needs_improvement",
        "issues": issues
    }
    
    return score, details


def _assess_format_compliance(doc: DocumentContent, detailed: bool) -> Tuple[float, Dict[str, Any]]:
    """评估格式规范性"""
    score = 100.0
    issues = []
    
    # 收集所有文本内容
    all_text = ""
    for section in doc.sections:
        all_text += section.get("content", "") + "\n"
    
    # 检查标题格式
    heading_info = _check_heading_structure(doc.sections)
    if heading_info["max_level"] > 4:
        score -= 5
        issues.append("标题层级过深，建议不超过4级")
    
    # 检查列表格式
    list_info = _check_list_formatting(all_text)
    if list_info["total_lists"] == 0:
        score -= 5
        issues.append("文档缺少列表，建议使用列表提高可读性")
    
    # 检查代码块格式
    code_info = _check_code_blocks(all_text)
    if code_info["count"] > 0:
        if code_info["has_language_tags"] < code_info["total_blocks"]:
            score -= 10
            issues.append("部分代码块缺少语言标记")
    
    # 检查表格使用
    has_tables = "|" in all_text and "---" in all_text
    table_score = 100 if has_tables else 90
    
    # 检查链接格式
    links = re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', all_text)
    broken_links = [link for link in links if not link[1] or link[1].startswith("#")]
    if broken_links:
        score -= len(broken_links) * 2
        issues.append(f"存在{len(broken_links)}个可能有问题的链接")
    
    # 检查格式一致性
    consistency_score = 100.0
    
    # 检查标题大小写一致性
    title_cases = [s.get("title", "") for s in doc.sections]
    if title_cases:
        first_char_upper = sum(1 for t in title_cases if t and t[0].isupper())
        if 0 < first_char_upper < len(title_cases):
            consistency_score -= 10
            issues.append("章节标题大小写不一致")
    
    score = (score + table_score + consistency_score) / 3
    score = max(0.0, min(100.0, score))
    
    details = {
        "score": score,
        "heading_structure": heading_info,
        "list_usage": list_info,
        "code_blocks": code_info,
        "has_tables": has_tables,
        "link_count": len(links),
        "consistency_score": consistency_score,
        "issues": issues
    }
    
    return score, details


def _assess_language_expression(doc: DocumentContent, detailed: bool) -> Tuple[float, Dict[str, Any]]:
    """评估语言表达"""
    score = 100.0
    issues = []
    
    # 收集所有文本内容
    all_text = ""
    for section in doc.sections:
        all_text += section.get("content", "") + "\n"
    
    # 分析句子复杂度
    complexity_info = _analyze_sentence_complexity(all_text)
    
    # 句子长度评分
    if complexity_info["avg_length"] > 150:
        score -= 15
        issues.append("句子平均长度过长，建议简化表达")
    elif complexity_info["avg_length"] < 20:
        score -= 10
        issues.append("句子平均长度过短，可能影响表达完整性")
    
    # 检查专业性
    professional_words = sum(1 for word in ["实现", "配置", "部署", "优化", "架构", 
                                           "implement", "configure", "deploy", "optimize", "architecture"]
                            if word in all_text.lower())
    if professional_words < 5:
        score -= 10
        issues.append("专业术语使用不足，建议增加技术性表达")
    
    # 检查重复性
    words = re.findall(r'\b\w+\b', all_text)
    if words:
        unique_words = len(set(words))
        repetition_rate = 1 - (unique_words / len(words))
        if repetition_rate > 0.7:
            score -= 10
            issues.append("词汇重复率过高，建议丰富表达方式")
    
    # 检查标点符号使用
    punctuation_count = sum(1 for char in all_text if char in ",.!?;:，。！？；：")
    text_length = len(all_text)
    if text_length > 0:
        punctuation_ratio = punctuation_count / text_length
        if punctuation_ratio < 0.01:
            score -= 5
            issues.append("标点符号使用不足")
    
    # 检查段落结构
    paragraphs = all_text.split("\n\n")
    avg_paragraph_length = sum(len(p) for p in paragraphs) / len(paragraphs) if paragraphs else 0
    if avg_paragraph_length > 1000:
        score -= 10
        issues.append("段落平均长度过长，建议适当分段")
    
    score = max(0.0, min(100.0, score))
    
    details = {
        "score": score,
        "sentence_complexity": complexity_info,
        "professional_word_count": professional_words,
        "paragraph_count": len(paragraphs),
        "avg_paragraph_length": round(avg_paragraph_length, 2),
        "readability_score": complexity_info["complexity_score"],
        "issues": issues
    }
    
    return score, details


def _get_grade(score: float) -> str:
    """根据分数获取等级"""
    if score >= 90:
        return "优秀 (Excellent)"
    elif score >= 80:
        return "良好 (Good)"
    elif score >= 70:
        return "中等 (Fair)"
    elif score >= 60:
        return "及格 (Pass)"
    else:
        return "不及格 (Fail)"


def _generate_assessment_summary(overall_score: float, dimension_scores: Dict[str, float]) -> str:
    """生成评估总结"""
    grade = _get_grade(overall_score)
    
    # 找出最强和最弱的维度
    sorted_dimensions = sorted(dimension_scores.items(), key=lambda x: x[1], reverse=True)
    strongest = sorted_dimensions[0] if sorted_dimensions else ("", 0)
    weakest = sorted_dimensions[-1] if sorted_dimensions else ("", 0)
    
    dimension_names = {
        "content_completeness": "内容完整性",
        "technical_accuracy": "技术准确性",
        "logical_coherence": "逻辑连贯性",
        "format_compliance": "格式规范性",
        "language_expression": "语言表达"
    }
    
    summary = f"文档总体质量评级为{grade}（{overall_score:.1f}分）。"
    
    if strongest[0]:
        summary += f"最强维度是{dimension_names.get(strongest[0], strongest[0])}（{strongest[1]:.1f}分）。"
    
    if weakest[0] and weakest[1] < 70:
        summary += f"需要重点改进{dimension_names.get(weakest[0], weakest[0])}（{weakest[1]:.1f}分）。"
    
    return summary


@tool
def identify_document_issues(
    document: Dict[str, Any],
    focus_areas: Optional[List[str]] = None,
    severity_threshold: str = "low"
) -> str:
    """
    识别技术文档中存在的具体问题
    
    该工具深入分析文档内容，识别各类问题，包括技术错误、结构问题、
    格式错误等，并标注问题的位置、类型和严重程度。
    
    Args:
        document (Dict[str, Any]): 文档内容对象
        focus_areas (Optional[List[str]]): 关注的问题领域，可选值：
            - technical: 技术问题
            - structural: 结构问题
            - formatting: 格式问题
            - language: 语言问题
            - completeness: 完整性问题
            - consistency: 一致性问题
            如果不提供，则检查所有领域
        severity_threshold (str): 严重程度阈值，只返回达到该级别的问题
            - high: 只返回高严重度问题
            - medium: 返回中等及以上严重度问题
            - low: 返回所有问题（默认）
    
    Returns:
        str: JSON格式的问题列表，包含问题位置、类型、严重程度和描述
        
    Example:
        >>> result = identify_document_issues(document_dict)
        >>> data = json.loads(result)
        >>> print(data['issue_count'])
    """
    try:
        # 验证文档内容
        is_valid, error_msg = _validate_document_content(document)
        if not is_valid:
            return json.dumps({
                "status": "error",
                "error": error_msg,
                "timestamp": datetime.utcnow().isoformat()
            }, ensure_ascii=False, indent=2)
        
        # 默认检查所有领域
        if focus_areas is None:
            focus_areas = ["technical", "structural", "formatting", "language", "completeness", "consistency"]
        
        doc_obj = DocumentContent(document)
        all_issues = []
        
        # 识别各类问题
        if "technical" in focus_areas:
            all_issues.extend(_identify_technical_issues(doc_obj))
        
        if "structural" in focus_areas:
            all_issues.extend(_identify_structural_issues(doc_obj))
        
        if "formatting" in focus_areas:
            all_issues.extend(_identify_formatting_issues(doc_obj))
        
        if "language" in focus_areas:
            all_issues.extend(_identify_language_issues(doc_obj))
        
        if "completeness" in focus_areas:
            all_issues.extend(_identify_completeness_issues(doc_obj))
        
        if "consistency" in focus_areas:
            all_issues.extend(_identify_consistency_issues(doc_obj))
        
        # 根据严重程度过滤
        severity_order = {"high": 3, "medium": 2, "low": 1}
        threshold_level = severity_order.get(severity_threshold, 1)
        
        filtered_issues = [
            issue for issue in all_issues
            if severity_order.get(issue["severity"], 1) >= threshold_level
        ]
        
        # 按严重程度和位置排序
        filtered_issues.sort(key=lambda x: (
            -severity_order.get(x["severity"], 1),
            x.get("section_index", 999)
        ))
        
        result = {
            "status": "success",
            "issue_count": len(filtered_issues),
            "severity_distribution": _count_by_severity(filtered_issues),
            "type_distribution": _count_by_type(filtered_issues),
            "issues": filtered_issues,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": f"问题识别过程发生错误: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }, ensure_ascii=False, indent=2)


def _identify_technical_issues(doc: DocumentContent) -> List[Dict[str, Any]]:
    """识别技术问题"""
    issues = []
    
    for i, section in enumerate(doc.sections):
        content = section.get("content", "")
        section_title = section.get("title", f"章节{i+1}")
        
        # 检查代码块问题
        code_blocks = re.findall(r'```([\s\S]*?)```', content)
        for j, block in enumerate(code_blocks):
            if not block.strip():
                issues.append({
                    "type": IssueType.TECHNICAL_ERROR,
                    "severity": IssueSeverity.MEDIUM,
                    "location": f"{section_title} - 代码块{j+1}",
                    "section_index": i,
                    "description": "代码块为空",
                    "suggestion": "请添加有效的代码示例或删除空代码块"
                })
            
            # 检查是否有语言标记
            if not re.match(r'^\w+\s', block):
                issues.append({
                    "type": IssueType.FORMATTING_ERROR,
                    "severity": IssueSeverity.LOW,
                    "location": f"{section_title} - 代码块{j+1}",
                    "section_index": i,
                    "description": "代码块缺少语言标记",
                    "suggestion": "添加语言标记以启用语法高亮，如 ```python"
                })
        
        # 检查技术术语使用
        if len(content) > 200:
            technical_terms = _count_technical_terms(content)
            if technical_terms == 0:
                issues.append({
                    "type": IssueType.TECHNICAL_ERROR,
                    "severity": IssueSeverity.MEDIUM,
                    "location": section_title,
                    "section_index": i,
                    "description": "章节缺少技术术语，可能缺乏技术深度",
                    "suggestion": "增加技术术语和专业表达，提升文档的技术性"
                })
    
    return issues


def _identify_structural_issues(doc: DocumentContent) -> List[Dict[str, Any]]:
    """识别结构问题"""
    issues = []
    
    # 检查章节数量
    if len(doc.sections) < 3:
        issues.append({
            "type": IssueType.STRUCTURAL_ISSUE,
            "severity": IssueSeverity.HIGH,
            "location": "文档整体",
            "section_index": -1,
            "description": "文档章节数量过少",
            "suggestion": "技术文档建议至少包含3个主要章节：概述、详细内容、总结"
        })
    
    # 检查是否有概述
    has_intro = any(
        section.get("title", "").lower() in ["概述", "introduction", "overview", "简介"]
        for section in doc.sections
    )
    if not has_intro:
        issues.append({
            "type": IssueType.STRUCTURAL_ISSUE,
            "severity": IssueSeverity.MEDIUM,
            "location": "文档开头",
            "section_index": 0,
            "description": "缺少概述或介绍章节",
            "suggestion": "在文档开头添加概述章节，说明文档的目的和主要内容"
        })
    
    # 检查章节内容长度分布
    for i, section in enumerate(doc.sections):
        content = section.get("content", "")
        section_title = section.get("title", f"章节{i+1}")
        
        if not content:
            issues.append({
                "type": IssueType.COMPLETENESS_ISSUE,
                "severity": IssueSeverity.HIGH,
                "location": section_title,
                "section_index": i,
                "description": "章节内容为空",
                "suggestion": "添加章节内容或删除空章节"
            })
        elif len(content) < 50:
            issues.append({
                "type": IssueType.COMPLETENESS_ISSUE,
                "severity": IssueSeverity.MEDIUM,
                "location": section_title,
                "section_index": i,
                "description": "章节内容过少",
                "suggestion": "扩充章节内容，提供更详细的说明"
            })
    
    return issues


def _identify_formatting_issues(doc: DocumentContent) -> List[Dict[str, Any]]:
    """识别格式问题"""
    issues = []
    
    for i, section in enumerate(doc.sections):
        content = section.get("content", "")
        section_title = section.get("title", f"章节{i+1}")
        
        # 检查标题格式
        if not section.get("title"):
            issues.append({
                "type": IssueType.FORMATTING_ERROR,
                "severity": IssueSeverity.HIGH,
                "location": f"章节{i+1}",
                "section_index": i,
                "description": "章节缺少标题",
                "suggestion": "为每个章节添加清晰的标题"
            })
        
        # 检查多余空行
        if "\n\n\n" in content:
            issues.append({
                "type": IssueType.FORMATTING_ERROR,
                "severity": IssueSeverity.LOW,
                "location": section_title,
                "section_index": i,
                "description": "存在多余的空行",
                "suggestion": "删除多余的空行，保持格式整洁"
            })
        
        # 检查列表格式一致性
        unordered_markers = set(re.findall(r'^(\s*[-*+])\s+', content, re.MULTILINE))
        if len(unordered_markers) > 1:
            issues.append({
                "type": IssueType.FORMATTING_ERROR,
                "severity": IssueSeverity.LOW,
                "location": section_title,
                "section_index": i,
                "description": "无序列表标记不一致",
                "suggestion": "统一使用同一种列表标记（-、* 或 +）"
            })
    
    return issues


def _identify_language_issues(doc: DocumentContent) -> List[Dict[str, Any]]:
    """识别语言问题"""
    issues = []
    
    for i, section in enumerate(doc.sections):
        content = section.get("content", "")
        section_title = section.get("title", f"章节{i+1}")
        
        # 检查句子长度
        sentences = re.split(r'[.!?。！？]', content)
        long_sentences = [s for s in sentences if len(s) > 200]
        
        if long_sentences:
            issues.append({
                "type": IssueType.LANGUAGE_ISSUE,
                "severity": IssueSeverity.MEDIUM,
                "location": section_title,
                "section_index": i,
                "description": f"存在{len(long_sentences)}个过长的句子",
                "suggestion": "将长句拆分为多个短句，提高可读性"
            })
        
        # 检查被动语态（简化检查）
        passive_indicators = ["被", "由", "is", "are", "was", "were"]
        passive_count = sum(content.lower().count(indicator) for indicator in passive_indicators)
        if passive_count > len(content) / 100:
            issues.append({
                "type": IssueType.LANGUAGE_ISSUE,
                "severity": IssueSeverity.LOW,
                "location": section_title,
                "section_index": i,
                "description": "被动语态使用较多",
                "suggestion": "适当使用主动语态，使表达更直接"
            })
    
    return issues


def _identify_completeness_issues(doc: DocumentContent) -> List[Dict[str, Any]]:
    """识别完整性问题"""
    issues = []
    
    # 检查必要章节
    section_titles = [s.get("title", "").lower() for s in doc.sections]
    
    required_sections = {
        "概述": ["概述", "introduction", "overview", "简介"],
        "使用说明": ["使用", "usage", "how to", "getting started"],
        "参考": ["参考", "reference", "api", "文档"]
    }
    
    for section_name, keywords in required_sections.items():
        if not any(any(kw in title for kw in keywords) for title in section_titles):
            issues.append({
                "type": IssueType.COMPLETENESS_ISSUE,
                "severity": IssueSeverity.MEDIUM,
                "location": "文档整体",
                "section_index": -1,
                "description": f"缺少{section_name}相关章节",
                "suggestion": f"建议添加{section_name}章节，提供完整的文档结构"
            })
    
    return issues


def _identify_consistency_issues(doc: DocumentContent) -> List[Dict[str, Any]]:
    """识别一致性问题"""
    issues = []
    
    # 检查标题格式一致性
    title_patterns = []
    for section in doc.sections:
        title = section.get("title", "")
        if title:
            # 检查首字母大小写
            title_patterns.append(title[0].isupper())
    
    if title_patterns and not all(title_patterns) and any(title_patterns):
        issues.append({
            "type": IssueType.CONSISTENCY_ISSUE,
            "severity": IssueSeverity.LOW,
            "location": "所有章节标题",
            "section_index": -1,
            "description": "章节标题首字母大小写不一致",
            "suggestion": "统一章节标题的首字母大小写格式"
        })
    
    # 检查术语使用一致性
    all_text = " ".join(s.get("content", "") for s in doc.sections)
    
    # 常见的术语变体检查
    term_variants = [
        (["API", "api", "Api"], "API"),
        (["JSON", "json", "Json"], "JSON"),
        (["HTTP", "http", "Http"], "HTTP"),
    ]
    
    for variants, standard in term_variants:
        found_variants = [v for v in variants if v in all_text]
        if len(found_variants) > 1:
            issues.append({
                "type": IssueType.CONSISTENCY_ISSUE,
                "severity": IssueSeverity.LOW,
                "location": "文档整体",
                "section_index": -1,
                "description": f"术语'{standard}'的书写格式不一致",
                "suggestion": f"统一使用标准格式'{standard}'"
            })
    
    return issues


def _count_by_severity(issues: List[Dict[str, Any]]) -> Dict[str, int]:
    """按严重程度统计问题数量"""
    distribution = {
        IssueSeverity.HIGH: 0,
        IssueSeverity.MEDIUM: 0,
        IssueSeverity.LOW: 0
    }
    
    for issue in issues:
        severity = issue.get("severity", IssueSeverity.LOW)
        distribution[severity] = distribution.get(severity, 0) + 1
    
    return distribution


def _count_by_type(issues: List[Dict[str, Any]]) -> Dict[str, int]:
    """按类型统计问题数量"""
    distribution = {}
    
    for issue in issues:
        issue_type = issue.get("type", "unknown")
        distribution[issue_type] = distribution.get(issue_type, 0) + 1
    
    return distribution


@tool
def generate_review_feedback(
    quality_scores: Dict[str, float],
    issues: List[Dict[str, Any]],
    priority_strategy: str = "severity_first"
) -> str:
    """
    生成结构化的审核反馈信息
    
    该工具基于质量评估结果和识别的问题，生成具体的改进建议，
    包括问题描述、改进方案和优先级排序。
    
    Args:
        quality_scores (Dict[str, float]): 各维度质量评分
        issues (List[Dict[str, Any]]): 识别的问题列表
        priority_strategy (str): 优先级排序策略，可选值：
            - severity_first: 按严重程度优先（默认）
            - type_first: 按问题类型优先
            - location_first: 按文档位置优先
    
    Returns:
        str: JSON格式的结构化反馈信息
        
    Example:
        >>> result = generate_review_feedback(scores, issues)
        >>> data = json.loads(result)
        >>> print(data['feedback_summary'])
    """
    try:
        # 验证输入
        if not isinstance(quality_scores, dict):
            return json.dumps({
                "status": "error",
                "error": "quality_scores必须是字典格式",
                "timestamp": datetime.utcnow().isoformat()
            }, ensure_ascii=False, indent=2)
        
        if not isinstance(issues, list):
            return json.dumps({
                "status": "error",
                "error": "issues必须是列表格式",
                "timestamp": datetime.utcnow().isoformat()
            }, ensure_ascii=False, indent=2)
        
        # 计算总体评分
        overall_score = sum(quality_scores.values()) / len(quality_scores) if quality_scores else 0
        
        # 生成反馈项
        feedback_items = []
        
        # 按优先级排序问题
        sorted_issues = _sort_issues_by_priority(issues, priority_strategy)
        
        # 为每个问题生成反馈项
        for issue in sorted_issues:
            feedback_item = {
                "category": issue.get("type", "unknown"),
                "severity": issue.get("severity", IssueSeverity.LOW),
                "location": issue.get("location", "未指定"),
                "description": issue.get("description", ""),
                "suggestion": issue.get("suggestion", ""),
                "priority": _calculate_priority(issue, overall_score)
            }
            feedback_items.append(feedback_item)
        
        # 生成改进建议
        improvement_suggestions = _generate_improvement_suggestions(quality_scores, issues)
        
        # 生成反馈摘要
        feedback_summary = _generate_feedback_summary(overall_score, quality_scores, issues)
        
        # 生成关键行动项
        action_items = _generate_action_items(sorted_issues[:5])  # 取前5个最重要的问题
        
        result = {
            "status": "success",
            "overall_score": round(overall_score, 2),
            "feedback_summary": feedback_summary,
            "feedback_items": feedback_items,
            "improvement_suggestions": improvement_suggestions,
            "action_items": action_items,
            "priority_strategy": priority_strategy,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": f"反馈生成过程发生错误: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }, ensure_ascii=False, indent=2)


def _sort_issues_by_priority(issues: List[Dict[str, Any]], strategy: str) -> List[Dict[str, Any]]:
    """按优先级排序问题"""
    severity_order = {"high": 3, "medium": 2, "low": 1}
    
    if strategy == "severity_first":
        return sorted(issues, key=lambda x: (
            -severity_order.get(x.get("severity", "low"), 1),
            x.get("section_index", 999)
        ))
    elif strategy == "type_first":
        return sorted(issues, key=lambda x: (
            x.get("type", "unknown"),
            -severity_order.get(x.get("severity", "low"), 1)
        ))
    elif strategy == "location_first":
        return sorted(issues, key=lambda x: (
            x.get("section_index", 999),
            -severity_order.get(x.get("severity", "low"), 1)
        ))
    else:
        return issues


def _calculate_priority(issue: Dict[str, Any], overall_score: float) -> int:
    """计算问题的优先级（1-10，10为最高）"""
    severity_weights = {
        IssueSeverity.HIGH: 10,
        IssueSeverity.MEDIUM: 6,
        IssueSeverity.LOW: 3
    }
    
    base_priority = severity_weights.get(issue.get("severity", IssueSeverity.LOW), 3)
    
    # 如果整体分数低，提高优先级
    if overall_score < 70:
        base_priority = min(10, base_priority + 2)
    
    return base_priority


def _generate_improvement_suggestions(
    quality_scores: Dict[str, float],
    issues: List[Dict[str, Any]]
) -> List[str]:
    """生成改进建议"""
    suggestions = []
    
    dimension_names = {
        "content_completeness": "内容完整性",
        "technical_accuracy": "技术准确性",
        "logical_coherence": "逻辑连贯性",
        "format_compliance": "格式规范性",
        "language_expression": "语言表达"
    }
    
    # 针对低分维度生成建议
    for dimension, score in quality_scores.items():
        if score < 70:
            dim_name = dimension_names.get(dimension, dimension)
            suggestions.append(f"重点改进{dim_name}（当前{score:.1f}分）")
    
    # 针对高严重度问题生成建议
    high_severity_issues = [i for i in issues if i.get("severity") == IssueSeverity.HIGH]
    if high_severity_issues:
        suggestions.append(f"优先解决{len(high_severity_issues)}个高严重度问题")
    
    # 针对问题类型生成建议
    type_distribution = _count_by_type(issues)
    for issue_type, count in sorted(type_distribution.items(), key=lambda x: -x[1])[:3]:
        if count >= 3:
            suggestions.append(f"系统性解决{count}个{issue_type}类问题")
    
    return suggestions


def _generate_feedback_summary(
    overall_score: float,
    quality_scores: Dict[str, float],
    issues: List[Dict[str, Any]]
) -> str:
    """生成反馈摘要"""
    grade = _get_grade(overall_score)
    
    # 统计问题
    severity_dist = _count_by_severity(issues)
    high_count = severity_dist.get(IssueSeverity.HIGH, 0)
    medium_count = severity_dist.get(IssueSeverity.MEDIUM, 0)
    low_count = severity_dist.get(IssueSeverity.LOW, 0)
    
    # 找出最弱维度
    weakest_dim = min(quality_scores.items(), key=lambda x: x[1]) if quality_scores else ("", 0)
    
    dimension_names = {
        "content_completeness": "内容完整性",
        "technical_accuracy": "技术准确性",
        "logical_coherence": "逻辑连贯性",
        "format_compliance": "格式规范性",
        "language_expression": "语言表达"
    }
    
    summary = f"文档总体质量为{grade}（{overall_score:.1f}分）。"
    
    if len(issues) > 0:
        summary += f"共识别出{len(issues)}个问题："
        if high_count > 0:
            summary += f"{high_count}个高严重度、"
        if medium_count > 0:
            summary += f"{medium_count}个中等严重度、"
        if low_count > 0:
            summary += f"{low_count}个低严重度。"
    else:
        summary += "未发现明显问题。"
    
    if weakest_dim[0] and weakest_dim[1] < 70:
        dim_name = dimension_names.get(weakest_dim[0], weakest_dim[0])
        summary += f"建议重点改进{dim_name}（{weakest_dim[1]:.1f}分）。"
    
    return summary


def _generate_action_items(issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """生成关键行动项"""
    action_items = []
    
    for i, issue in enumerate(issues, 1):
        action_item = {
            "order": i,
            "action": f"修复 {issue.get('location', '未指定位置')} 的{issue.get('type', '问题')}",
            "description": issue.get("description", ""),
            "suggestion": issue.get("suggestion", ""),
            "severity": issue.get("severity", IssueSeverity.LOW),
            "estimated_effort": _estimate_effort(issue)
        }
        action_items.append(action_item)
    
    return action_items


def _estimate_effort(issue: Dict[str, Any]) -> str:
    """估算修复工作量"""
    severity = issue.get("severity", IssueSeverity.LOW)
    issue_type = issue.get("type", "")
    
    if severity == IssueSeverity.HIGH:
        if issue_type == IssueType.TECHNICAL_ERROR:
            return "高（需要深入技术修改）"
        elif issue_type == IssueType.STRUCTURAL_ISSUE:
            return "高（需要重构文档结构）"
        else:
            return "中等"
    elif severity == IssueSeverity.MEDIUM:
        return "中等"
    else:
        return "低"


@tool
def make_review_decision(
    quality_scores: Dict[str, float],
    pass_threshold: float = 75.0,
    dimension_thresholds: Optional[Dict[str, float]] = None
) -> str:
    """
    根据质量评估结果判断是否通过审核
    
    该工具基于多维度质量评分，应用预定义的通过标准，
    做出明确的通过/不通过决定，并提供总体质量评级。
    
    Args:
        quality_scores (Dict[str, float]): 各维度质量评分
        pass_threshold (float): 总体通过阈值，默认75.0分
        dimension_thresholds (Optional[Dict[str, float]]): 各维度的最低要求，
            如果某个维度低于其阈值，即使总分达标也不通过。
            例如：{"technical_accuracy": 70.0, "content_completeness": 65.0}
    
    Returns:
        str: JSON格式的审核决定，包含通过状态、总体评分和决策理由
        
    Example:
        >>> result = make_review_decision(scores)
        >>> data = json.loads(result)
        >>> print(data['decision'])  # 'pass' or 'fail'
    """
    try:
        # 验证输入
        if not isinstance(quality_scores, dict):
            return json.dumps({
                "status": "error",
                "error": "quality_scores必须是字典格式",
                "timestamp": datetime.utcnow().isoformat()
            }, ensure_ascii=False, indent=2)
        
        if not quality_scores:
            return json.dumps({
                "status": "error",
                "error": "quality_scores不能为空",
                "timestamp": datetime.utcnow().isoformat()
            }, ensure_ascii=False, indent=2)
        
        # 计算总体评分
        overall_score = sum(quality_scores.values()) / len(quality_scores)
        
        # 初始化决策
        decision = "pass"
        decision_reasons = []
        failing_dimensions = []
        
        # 检查总体评分
        if overall_score < pass_threshold:
            decision = "fail"
            decision_reasons.append(
                f"总体评分{overall_score:.1f}低于通过阈值{pass_threshold:.1f}"
            )
        
        # 检查各维度阈值
        if dimension_thresholds:
            for dimension, threshold in dimension_thresholds.items():
                if dimension in quality_scores:
                    dim_score = quality_scores[dimension]
                    if dim_score < threshold:
                        decision = "fail"
                        failing_dimensions.append({
                            "dimension": dimension,
                            "score": dim_score,
                            "threshold": threshold,
                            "gap": threshold - dim_score
                        })
                        decision_reasons.append(
                            f"{dimension}评分{dim_score:.1f}低于最低要求{threshold:.1f}"
                        )
        
        # 生成决策总结
        if decision == "pass":
            decision_summary = f"文档质量达到标准（总分{overall_score:.1f}），通过审核。"
        else:
            decision_summary = f"文档质量未达标准（总分{overall_score:.1f}），需要改进。"
        
        # 生成改进优先级
        improvement_priorities = []
        if failing_dimensions:
            # 按差距排序
            failing_dimensions.sort(key=lambda x: -x["gap"])
            for dim in failing_dimensions[:3]:
                improvement_priorities.append({
                    "dimension": dim["dimension"],
                    "current_score": dim["score"],
                    "required_score": dim["threshold"],
                    "improvement_needed": round(dim["gap"], 2),
                    "priority": "high" if dim["gap"] > 10 else "medium"
                })
        
        result = {
            "status": "success",
            "decision": decision,
            "overall_score": round(overall_score, 2),
            "pass_threshold": pass_threshold,
            "grade": _get_grade(overall_score),
            "decision_summary": decision_summary,
            "decision_reasons": decision_reasons,
            "failing_dimensions": failing_dimensions,
            "improvement_priorities": improvement_priorities,
            "quality_assessment": {
                "excellent_dimensions": [k for k, v in quality_scores.items() if v >= 90],
                "good_dimensions": [k for k, v in quality_scores.items() if 80 <= v < 90],
                "fair_dimensions": [k for k, v in quality_scores.items() if 70 <= v < 80],
                "poor_dimensions": [k for k, v in quality_scores.items() if v < 70]
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": f"审核决策过程发生错误: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }, ensure_ascii=False, indent=2)


@tool
def comprehensive_document_review(
    document: Dict[str, Any],
    pass_threshold: float = 75.0,
    dimension_thresholds: Optional[Dict[str, float]] = None,
    severity_threshold: str = "low"
) -> str:
    """
    执行完整的文档审核流程
    
    该工具是一个综合性工具，整合了质量评估、问题识别、反馈生成和审核决策
    四个核心功能，提供一站式的文档审核服务。
    
    Args:
        document (Dict[str, Any]): 文档内容对象
        pass_threshold (float): 总体通过阈值，默认75.0分
        dimension_thresholds (Optional[Dict[str, float]]): 各维度的最低要求
        severity_threshold (str): 问题严重程度阈值，默认"low"
    
    Returns:
        str: JSON格式的完整审核报告
        
    Example:
        >>> result = comprehensive_document_review(document_dict)
        >>> data = json.loads(result)
        >>> print(data['review_decision']['decision'])
    """
    try:
        # 验证文档内容
        is_valid, error_msg = _validate_document_content(document)
        if not is_valid:
            return json.dumps({
                "status": "error",
                "error": error_msg,
                "timestamp": datetime.utcnow().isoformat()
            }, ensure_ascii=False, indent=2)
        
        # 1. 质量评估
        assessment_result = json.loads(assess_document_quality(document, detailed_analysis=True))
        if assessment_result["status"] != "success":
            return json.dumps(assessment_result, ensure_ascii=False, indent=2)
        
        quality_scores = assessment_result["dimension_scores"]
        
        # 2. 问题识别
        issues_result = json.loads(identify_document_issues(
            document,
            severity_threshold=severity_threshold
        ))
        if issues_result["status"] != "success":
            return json.dumps(issues_result, ensure_ascii=False, indent=2)
        
        issues = issues_result["issues"]
        
        # 3. 反馈生成
        feedback_result = json.loads(generate_review_feedback(
            quality_scores,
            issues,
            priority_strategy="severity_first"
        ))
        if feedback_result["status"] != "success":
            return json.dumps(feedback_result, ensure_ascii=False, indent=2)
        
        # 4. 审核决策
        decision_result = json.loads(make_review_decision(
            quality_scores,
            pass_threshold,
            dimension_thresholds
        ))
        if decision_result["status"] != "success":
            return json.dumps(decision_result, ensure_ascii=False, indent=2)
        
        # 整合结果
        result = {
            "status": "success",
            "review_summary": {
                "document_title": document.get("title", "未命名文档"),
                "review_date": datetime.utcnow().isoformat(),
                "overall_score": assessment_result["overall_score"],
                "grade": assessment_result["grade"],
                "decision": decision_result["decision"],
                "issue_count": issues_result["issue_count"]
            },
            "quality_assessment": {
                "overall_score": assessment_result["overall_score"],
                "dimension_scores": assessment_result["dimension_scores"],
                "dimension_details": assessment_result.get("dimension_details", {}),
                "assessment_summary": assessment_result["assessment_summary"]
            },
            "identified_issues": {
                "total_count": issues_result["issue_count"],
                "severity_distribution": issues_result["severity_distribution"],
                "type_distribution": issues_result["type_distribution"],
                "issues": issues_result["issues"]
            },
            "review_feedback": {
                "feedback_summary": feedback_result["feedback_summary"],
                "feedback_items": feedback_result["feedback_items"],
                "improvement_suggestions": feedback_result["improvement_suggestions"],
                "action_items": feedback_result["action_items"]
            },
            "review_decision": {
                "decision": decision_result["decision"],
                "decision_summary": decision_result["decision_summary"],
                "decision_reasons": decision_result["decision_reasons"],
                "failing_dimensions": decision_result["failing_dimensions"],
                "improvement_priorities": decision_result["improvement_priorities"]
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": f"综合审核过程发生错误: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }, ensure_ascii=False, indent=2)


@tool
def validate_review_criteria(
    criteria: Dict[str, Any]
) -> str:
    """
    验证审核标准的有效性
    
    该工具用于验证自定义的审核标准是否符合要求，
    确保审核过程的一致性和可靠性。
    
    Args:
        criteria (Dict[str, Any]): 审核标准配置，包含：
            - pass_threshold: 总体通过阈值
            - dimension_thresholds: 各维度阈值
            - severity_weights: 严重程度权重
    
    Returns:
        str: JSON格式的验证结果
    """
    try:
        validation_results = {
            "is_valid": True,
            "warnings": [],
            "errors": []
        }
        
        # 验证pass_threshold
        if "pass_threshold" in criteria:
            threshold = criteria["pass_threshold"]
            if not isinstance(threshold, (int, float)):
                validation_results["is_valid"] = False
                validation_results["errors"].append("pass_threshold必须是数值类型")
            elif threshold < 0 or threshold > 100:
                validation_results["is_valid"] = False
                validation_results["errors"].append("pass_threshold必须在0-100之间")
            elif threshold < 60:
                validation_results["warnings"].append("pass_threshold设置较低，可能影响文档质量")
        
        # 验证dimension_thresholds
        if "dimension_thresholds" in criteria:
            dim_thresholds = criteria["dimension_thresholds"]
            if not isinstance(dim_thresholds, dict):
                validation_results["is_valid"] = False
                validation_results["errors"].append("dimension_thresholds必须是字典类型")
            else:
                valid_dimensions = [
                    "content_completeness", "technical_accuracy", "logical_coherence",
                    "format_compliance", "language_expression"
                ]
                for dim, threshold in dim_thresholds.items():
                    if dim not in valid_dimensions:
                        validation_results["warnings"].append(f"未知的维度: {dim}")
                    if not isinstance(threshold, (int, float)):
                        validation_results["is_valid"] = False
                        validation_results["errors"].append(f"{dim}的阈值必须是数值类型")
                    elif threshold < 0 or threshold > 100:
                        validation_results["is_valid"] = False
                        validation_results["errors"].append(f"{dim}的阈值必须在0-100之间")
        
        result = {
            "status": "success",
            "validation_results": validation_results,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": f"标准验证过程发生错误: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }, ensure_ascii=False, indent=2)
