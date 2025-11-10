#!/usr/bin/env python3
"""
文献分析工具

提供对科研文献的多维度分析和评估，包括结构完整性、科学准确性、方法论合理性、引用分析等
"""

import json
import os
import re
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging
from strands import tool

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("literature_analyzer")

# 文献结构部分常量定义
STRUCTURE_COMPONENTS = [
    "title", "abstract", "introduction", "methods", 
    "results", "discussion", "conclusion", "references"
]

# 评估维度定义
EVALUATION_DIMENSIONS = [
    "structure_completeness",  # 结构完整性
    "scientific_accuracy",     # 科学准确性
    "methodology_soundness",   # 方法论合理性
    "reference_quality",       # 引用质量
    "conclusion_validity",     # 结论有效性
    "information_completeness" # 信息完整性
]

@tool
def literature_analyzer(
    content: str, 
    research_id: Optional[str] = None, 
    dimensions: Optional[List[str]] = None,
    detailed_analysis: bool = True
) -> str:
    """
    对科研文献进行多维度分析和评估，包括结构完整性、科学准确性、方法论合理性、引用分析等
    
    Args:
        content (str): 文献内容（必需）
        research_id (Optional[str]): 研究ID，用于指定缓存目录（可选）
        dimensions (Optional[List[str]]): 要评估的维度列表（可选，默认全部维度）
        detailed_analysis (bool): 是否生成详细分析（可选，默认True）
        
    Returns:
        str: 包含多维度评估结果的JSON对象，包括各维度的评分、详细分析和问题清单
    """
    try:
        # 1. 初始化缓存目录
        cache_dir = setup_cache_directory(research_id)
        
        # 2. 如果没有指定维度，则使用所有维度
        if dimensions is None:
            dimensions = EVALUATION_DIMENSIONS
        else:
            # 验证维度是否有效
            for dim in dimensions:
                if dim not in EVALUATION_DIMENSIONS:
                    return json.dumps({
                        "error": f"无效的评估维度: {dim}",
                        "valid_dimensions": EVALUATION_DIMENSIONS
                    }, ensure_ascii=False, indent=2)
        
        # 3. 解析文献内容，提取各部分
        document_sections = parse_document_sections(content)
        
        # 4. 进行多维度评估
        evaluation_results = {}
        
        # 4.1 结构完整性评估
        if "structure_completeness" in dimensions:
            evaluation_results["structure_completeness"] = evaluate_structure_completeness(document_sections)
        
        # 4.2 科学准确性评估
        if "scientific_accuracy" in dimensions:
            evaluation_results["scientific_accuracy"] = evaluate_scientific_accuracy(document_sections)
        
        # 4.3 方法论合理性评估
        if "methodology_soundness" in dimensions:
            evaluation_results["methodology_soundness"] = evaluate_methodology_soundness(document_sections)
        
        # 4.4 引用质量评估
        if "reference_quality" in dimensions:
            evaluation_results["reference_quality"] = evaluate_reference_quality(document_sections)
        
        # 4.5 结论有效性评估
        if "conclusion_validity" in dimensions:
            evaluation_results["conclusion_validity"] = evaluate_conclusion_validity(document_sections)
        
        # 4.6 信息完整性评估（检测潜在的信息不全或幻觉内容）
        if "information_completeness" in dimensions:
            evaluation_results["information_completeness"] = evaluate_information_completeness(document_sections)
        
        # 5. 计算总体评分
        overall_score = calculate_overall_score(evaluation_results)
        
        # 6. 生成最终结果
        result = {
            "overall_assessment": {
                "score": overall_score,
                "level": get_score_level(overall_score),
                "summary": generate_assessment_summary(evaluation_results, overall_score)
            },
            "dimensions": evaluation_results
        }
        
        # 如果不需要详细分析，则移除详细分析部分
        if not detailed_analysis:
            for dimension in result["dimensions"]:
                if "detailed_analysis" in result["dimensions"][dimension]:
                    del result["dimensions"][dimension]["detailed_analysis"]
        
        # 7. 缓存结果
        if research_id:
            cache_results(result, research_id, cache_dir)
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"文献分析过程中发生错误: {str(e)}", exc_info=True)
        return json.dumps({
            "error": f"文献分析失败: {str(e)}",
            "status": "failed"
        }, ensure_ascii=False, indent=2)


def setup_cache_directory(research_id: Optional[str]) -> Path:
    """
    设置缓存目录，统一到 .cache/pmc_literature/<research_id>/feedback/reviewer/<version>/verification/
    若 research_id 为空则使用 .cache/default_literature_analysis
    版本选择规则：
      - 若存在 step5.status，则取 latest_version + 1
      - 否则扫描 feedback/reviewer 下的数字子目录最大值 + 1；未找到则为 1
    """
    if not research_id:
        return Path(".cache/default_literature_analysis")

    safe_id = research_id
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

    status_path = Path(".cache/pmc_literature") / safe_id / "step5.status"
    if version is None and status_path.exists():
        try:
            with open(status_path, "r", encoding="utf-8") as f:
                status = json.load(f)
            latest = int(status.get("latest_version", 0))
            version = latest + 1 if latest >= 0 else 1
        except Exception:
            version = None

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


def cache_results(results: Dict[str, Any], research_id: str, cache_dir: Path) -> None:
    """
    缓存分析结果
    
    Args:
        results: 分析结果
        research_id: 研究ID
        cache_dir: 缓存目录
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    cache_file = cache_dir / f"analysis_results_{timestamp}.json"
    
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # 更新最新分析结果的链接
    latest_file = cache_dir / "latest_analysis.json"
    with open(latest_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


def parse_document_sections(content: str) -> Dict[str, str]:
    """
    解析文档内容，提取各部分
    
    Args:
        content: 文档内容
        
    Returns:
        Dict[str, str]: 文档各部分内容
    """
    sections = {}
    
    # 提取标题（假设文档第一行是标题）
    lines = content.strip().split('\n')
    if lines:
        sections["title"] = lines[0].strip()
    
    # 尝试识别常见的文档部分
    section_patterns = {
        "abstract": r'(?i)(abstract|summary)[\s]*?[\n:]+(.*?)(?=\n\s*(?:introduction|keywords|background|1\.|$))',
        "introduction": r'(?i)(introduction|background)[\s]*?[\n:]+(.*?)(?=\n\s*(?:methods|materials and methods|methodology|2\.|$))',
        "methods": r'(?i)(methods|materials and methods|methodology|experimental procedure)[\s]*?[\n:]+(.*?)(?=\n\s*(?:results|findings|3\.|$))',
        "results": r'(?i)(results|findings)[\s]*?[\n:]+(.*?)(?=\n\s*(?:discussion|interpretation|4\.|$))',
        "discussion": r'(?i)(discussion|interpretation)[\s]*?[\n:]+(.*?)(?=\n\s*(?:conclusion|summary|5\.|$))',
        "conclusion": r'(?i)(conclusion|summary|concluding remarks)[\s]*?[\n:]+(.*?)(?=\n\s*(?:references|bibliography|acknowledgements|6\.|$))',
        "references": r'(?i)(references|bibliography|cited works)[\s]*?[\n:]+(.*?)(?=$)'
    }
    
    for section, pattern in section_patterns.items():
        match = re.search(pattern, content, re.DOTALL)
        if match:
            sections[section] = match.group(2).strip()
        else:
            sections[section] = ""
    
    return sections


def evaluate_structure_completeness(document_sections: Dict[str, str]) -> Dict[str, Any]:
    """
    评估文献结构的完整性
    
    Args:
        document_sections: 文档各部分内容
        
    Returns:
        Dict[str, Any]: 结构完整性评估结果
    """
    missing_sections = []
    weak_sections = []
    
    # 检查每个关键部分是否存在且内容充实
    for section in STRUCTURE_COMPONENTS:
        if section not in document_sections or not document_sections[section]:
            missing_sections.append(section)
        elif len(document_sections[section].split()) < 50 and section != "title":
            weak_sections.append(section)
    
    # 计算结构完整性评分
    total_sections = len(STRUCTURE_COMPONENTS)
    present_sections = total_sections - len(missing_sections)
    strong_sections = present_sections - len(weak_sections)
    
    # 评分计算：强部分 + 0.5 * 弱部分
    score = (strong_sections + 0.5 * len(weak_sections)) / total_sections * 100
    
    return {
        "score": round(score, 1),
        "level": get_score_level(score),
        "missing_sections": missing_sections,
        "weak_sections": weak_sections,
        "detailed_analysis": {
            "section_analysis": {
                section: {
                    "present": section in document_sections and bool(document_sections[section]),
                    "length": len(document_sections.get(section, "").split()),
                    "quality": "strong" if section in document_sections and len(document_sections[section].split()) >= 50 else "weak"
                } for section in STRUCTURE_COMPONENTS
            },
            "recommendations": generate_structure_recommendations(missing_sections, weak_sections)
        }
    }


def evaluate_scientific_accuracy(document_sections: Dict[str, str]) -> Dict[str, Any]:
    """
    评估文献的科学准确性
    
    Args:
        document_sections: 文档各部分内容
        
    Returns:
        Dict[str, Any]: 科学准确性评估结果
    """
    # 初始化问题列表
    accuracy_issues = []
    
    # 检查方法和结果部分的一致性
    methods_content = document_sections.get("methods", "")
    results_content = document_sections.get("results", "")
    
    # 提取方法中提到的关键技术、实验或分析方法
    methods_keywords = extract_methods_keywords(methods_content)
    
    # 检查结果中是否反映了这些方法
    methods_reflected_in_results = check_methods_reflected_in_results(methods_keywords, results_content)
    
    # 检查结论是否过度解读结果
    conclusion_content = document_sections.get("conclusion", "")
    overinterpretation_issues = check_conclusion_overinterpretation(results_content, conclusion_content)
    
    # 收集所有问题
    accuracy_issues.extend(methods_reflected_in_results["issues"])
    accuracy_issues.extend(overinterpretation_issues)
    
    # 基于问题数量和严重性计算评分
    base_score = 100
    deduction_per_issue = 10
    score = max(0, base_score - len(accuracy_issues) * deduction_per_issue)
    
    return {
        "score": round(score, 1),
        "level": get_score_level(score),
        "issues": accuracy_issues,
        "detailed_analysis": {
            "methods_keywords": methods_keywords,
            "methods_results_consistency": methods_reflected_in_results["consistency_rate"],
            "overinterpretation_detected": len(overinterpretation_issues) > 0,
            "recommendations": generate_scientific_accuracy_recommendations(accuracy_issues)
        }
    }


def evaluate_methodology_soundness(document_sections: Dict[str, str]) -> Dict[str, Any]:
    """
    评估文献的方法论合理性
    
    Args:
        document_sections: 文档各部分内容
        
    Returns:
        Dict[str, Any]: 方法论合理性评估结果
    """
    methods_content = document_sections.get("methods", "")
    
    # 初始化问题列表
    methodology_issues = []
    
    # 检查方法描述的详细程度
    if len(methods_content.split()) < 100:
        methodology_issues.append("方法描述过于简略，缺乏足够的细节")
    
    # 检查是否包含关键方法学要素
    methodology_elements = {
        "sample_description": check_contains_pattern(methods_content, r'(?i)(sample|participant|subject|specimen|data\s*set)'),
        "procedure_description": check_contains_pattern(methods_content, r'(?i)(procedure|protocol|step|process|technique)'),
        "analysis_description": check_contains_pattern(methods_content, r'(?i)(analysis|statistical|calculation|computation|evaluation)'),
        "controls_mentioned": check_contains_pattern(methods_content, r'(?i)(control|comparison|baseline|reference|placebo)'),
        "limitations_acknowledged": check_contains_pattern(document_sections.get("discussion", ""), r'(?i)(limitation|constraint|weakness|drawback|caveat)')
    }
    
    # 添加缺失的方法学要素到问题列表
    for element, present in methodology_elements.items():
        if not present:
            readable_element = element.replace("_", " ").capitalize()
            methodology_issues.append(f"缺少{readable_element}")
    
    # 计算方法论合理性评分
    base_score = 100
    deduction_per_issue = 15
    score = max(0, base_score - len(methodology_issues) * deduction_per_issue)
    
    return {
        "score": round(score, 1),
        "level": get_score_level(score),
        "issues": methodology_issues,
        "detailed_analysis": {
            "methodology_elements": methodology_elements,
            "method_length": len(methods_content.split()),
            "recommendations": generate_methodology_recommendations(methodology_issues, methodology_elements)
        }
    }


def evaluate_reference_quality(document_sections: Dict[str, str]) -> Dict[str, Any]:
    """
    评估文献引用的质量和相关性
    
    Args:
        document_sections: 文档各部分内容
        
    Returns:
        Dict[str, Any]: 引用质量评估结果
    """
    references_content = document_sections.get("references", "")
    main_content = ' '.join([
        document_sections.get("introduction", ""),
        document_sections.get("methods", ""),
        document_sections.get("results", ""),
        document_sections.get("discussion", "")
    ])
    
    # 提取引用
    references = extract_references(references_content)
    
    # 检查引用数量
    reference_count = len(references)
    
    # 提取正文中的引用标记
    citation_marks = extract_citation_marks(main_content)
    
    # 计算引用覆盖率（正文中的引用标记数量与引用列表数量的比率）
    citation_coverage = min(1.0, len(citation_marks) / max(1, reference_count)) * 100 if reference_count > 0 else 0
    
    # 初始化问题列表
    reference_issues = []
    
    # 检查引用数量是否合理
    if reference_count < 5:
        reference_issues.append("引用数量过少，可能缺乏充分的文献支持")
    
    # 检查引用覆盖率
    if citation_coverage < 50:
        reference_issues.append("正文中的引用标记与参考文献列表不匹配，可能存在未引用的参考文献")
    
    # 检查参考文献格式一致性
    format_consistency = check_reference_format_consistency(references)
    if not format_consistency["consistent"]:
        reference_issues.append("参考文献格式不一致")
    
    # 计算引用质量评分
    base_score = 100
    deduction_per_issue = 20
    score = max(0, base_score - len(reference_issues) * deduction_per_issue)
    
    return {
        "score": round(score, 1),
        "level": get_score_level(score),
        "issues": reference_issues,
        "detailed_analysis": {
            "reference_count": reference_count,
            "citation_marks_count": len(citation_marks),
            "citation_coverage_percentage": round(citation_coverage, 1),
            "format_consistency": format_consistency["consistency_rate"],
            "recommendations": generate_reference_recommendations(reference_issues, reference_count, citation_coverage)
        }
    }


def evaluate_conclusion_validity(document_sections: Dict[str, str]) -> Dict[str, Any]:
    """
    评估结论是否由结果充分支持
    
    Args:
        document_sections: 文档各部分内容
        
    Returns:
        Dict[str, Any]: 结论有效性评估结果
    """
    results_content = document_sections.get("results", "")
    conclusion_content = document_sections.get("conclusion", "")
    
    # 初始化问题列表
    validity_issues = []
    
    # 提取结果中的关键发现
    key_findings = extract_key_findings(results_content)
    
    # 检查结论是否基于这些发现
    conclusion_alignment = check_conclusion_alignment(key_findings, conclusion_content)
    
    # 检查结论是否包含未在结果中提及的内容
    unsupported_claims = check_unsupported_claims(results_content, conclusion_content)
    
    # 收集所有问题
    validity_issues.extend(conclusion_alignment["issues"])
    validity_issues.extend(unsupported_claims)
    
    # 计算结论有效性评分
    base_score = 100
    deduction_per_issue = 15
    score = max(0, base_score - len(validity_issues) * deduction_per_issue)
    
    return {
        "score": round(score, 1),
        "level": get_score_level(score),
        "issues": validity_issues,
        "detailed_analysis": {
            "key_findings": key_findings,
            "conclusion_alignment_rate": conclusion_alignment["alignment_rate"],
            "unsupported_claims_detected": len(unsupported_claims) > 0,
            "recommendations": generate_conclusion_validity_recommendations(validity_issues)
        }
    }


def evaluate_information_completeness(document_sections: Dict[str, str]) -> Dict[str, Any]:
    """
    评估文献的信息完整性，检测潜在的信息不全或幻觉内容
    
    Args:
        document_sections: 文档各部分内容
        
    Returns:
        Dict[str, Any]: 信息完整性评估结果
    """
    # 初始化问题列表
    completeness_issues = []
    
    # 检查关键部分是否包含足够的信息
    information_gaps = check_information_gaps(document_sections)
    completeness_issues.extend(information_gaps)
    
    # 检查潜在的幻觉内容（自相矛盾的陈述）
    hallucinations = check_potential_hallucinations(document_sections)
    completeness_issues.extend(hallucinations)
    
    # 检查数据呈现的完整性
    data_presentation_issues = check_data_presentation(document_sections)
    completeness_issues.extend(data_presentation_issues)
    
    # 计算信息完整性评分
    base_score = 100
    deduction_per_issue = 10
    score = max(0, base_score - len(completeness_issues) * deduction_per_issue)
    
    return {
        "score": round(score, 1),
        "level": get_score_level(score),
        "issues": completeness_issues,
        "detailed_analysis": {
            "information_gaps_detected": len(information_gaps) > 0,
            "hallucinations_detected": len(hallucinations) > 0,
            "data_presentation_issues": len(data_presentation_issues) > 0,
            "recommendations": generate_information_completeness_recommendations(completeness_issues)
        }
    }


def calculate_overall_score(evaluation_results: Dict[str, Dict[str, Any]]) -> float:
    """
    计算总体评分
    
    Args:
        evaluation_results: 各维度的评估结果
        
    Returns:
        float: 总体评分
    """
    # 各维度权重
    weights = {
        "structure_completeness": 0.15,
        "scientific_accuracy": 0.25,
        "methodology_soundness": 0.25,
        "reference_quality": 0.15,
        "conclusion_validity": 0.15,
        "information_completeness": 0.05
    }
    
    # 计算加权平均分
    total_weight = 0
    weighted_sum = 0
    
    for dimension, result in evaluation_results.items():
        if dimension in weights:
            weight = weights[dimension]
            score = result["score"]
            weighted_sum += score * weight
            total_weight += weight
    
    # 避免除零错误
    if total_weight == 0:
        return 0
    
    return round(weighted_sum / total_weight, 1)


def get_score_level(score: float) -> str:
    """
    根据评分获取评级
    
    Args:
        score: 评分
        
    Returns:
        str: 评级
    """
    if score >= 90:
        return "优秀"
    elif score >= 80:
        return "良好"
    elif score >= 70:
        return "一般"
    elif score >= 60:
        return "及格"
    else:
        return "不及格"


def generate_assessment_summary(evaluation_results: Dict[str, Dict[str, Any]], overall_score: float) -> str:
    """
    生成评估总结
    
    Args:
        evaluation_results: 各维度的评估结果
        overall_score: 总体评分
        
    Returns:
        str: 评估总结
    """
    # 获取评级
    level = get_score_level(overall_score)
    
    # 找出最高和最低评分的维度
    dimensions = list(evaluation_results.keys())
    if not dimensions:
        return "无法生成评估总结，缺少评估维度。"
    
    strongest_dimension = max(dimensions, key=lambda d: evaluation_results[d]["score"])
    weakest_dimension = min(dimensions, key=lambda d: evaluation_results[d]["score"])
    
    # 生成总结
    summary = f"文献整体评级为{level}（{overall_score}分）。"
    summary += f"最强的方面是{get_dimension_name(strongest_dimension)}（{evaluation_results[strongest_dimension]['score']}分），"
    summary += f"最弱的方面是{get_dimension_name(weakest_dimension)}（{evaluation_results[weakest_dimension]['score']}分）。"
    
    # 添加总体建议
    if overall_score < 70:
        summary += "建议对文献进行实质性修改，特别关注薄弱环节。"
    elif overall_score < 80:
        summary += "文献需要一定程度的改进，尤其是薄弱环节。"
    elif overall_score < 90:
        summary += "文献质量良好，但仍有提升空间。"
    else:
        summary += "文献质量优秀，只需少量微调。"
    
    return summary


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


# 辅助函数
def check_contains_pattern(text: str, pattern: str) -> bool:
    """
    检查文本是否包含指定模式
    
    Args:
        text: 要检查的文本
        pattern: 正则表达式模式
        
    Returns:
        bool: 是否包含指定模式
    """
    return bool(re.search(pattern, text))


def extract_methods_keywords(methods_content: str) -> List[str]:
    """
    提取方法中提到的关键技术、实验或分析方法
    
    Args:
        methods_content: 方法部分内容
        
    Returns:
        List[str]: 关键方法列表
    """
    # 提取可能的方法关键词
    method_patterns = [
        r'(?i)(used|performed|conducted|applied|implemented)\s+([a-z\s]+(?:analysis|assay|test|method|technique|approach|procedure|protocol))',
        r'(?i)([a-z\s]+(?:analysis|assay|test|method|technique|approach|procedure|protocol))\s+(?:was|were)\s+(?:used|performed|conducted|applied|implemented)',
        r'(?i)(?:using|via|through|by)\s+([a-z\s]+(?:analysis|assay|test|method|technique|approach|procedure|protocol))'
    ]
    
    methods = []
    for pattern in method_patterns:
        matches = re.findall(pattern, methods_content)
        for match in matches:
            if isinstance(match, tuple):
                # 如果匹配结果是元组，取第二个元素（捕获组）
                method = match[1].strip()
            else:
                method = match.strip()
            
            if method and len(method.split()) <= 5:  # 限制关键词长度
                methods.append(method)
    
    # 去重
    return list(set(methods))


def check_methods_reflected_in_results(methods_keywords: List[str], results_content: str) -> Dict[str, Any]:
    """
    检查方法中提到的关键词是否在结果中有所反映
    
    Args:
        methods_keywords: 方法关键词列表
        results_content: 结果部分内容
        
    Returns:
        Dict[str, Any]: 检查结果
    """
    issues = []
    reflected_count = 0
    
    for keyword in methods_keywords:
        # 检查关键词或其变体是否在结果中出现
        if re.search(rf'\b{re.escape(keyword)}s?\b', results_content, re.IGNORECASE):
            reflected_count += 1
        else:
            issues.append(f"方法中提到的'{keyword}'在结果部分没有明确反映")
    
    # 计算一致性比率
    consistency_rate = reflected_count / len(methods_keywords) * 100 if methods_keywords else 100
    
    return {
        "issues": issues,
        "consistency_rate": round(consistency_rate, 1)
    }


def check_conclusion_overinterpretation(results_content: str, conclusion_content: str) -> List[str]:
    """
    检查结论是否过度解读结果
    
    Args:
        results_content: 结果部分内容
        conclusion_content: 结论部分内容
        
    Returns:
        List[str]: 过度解读问题列表
    """
    issues = []
    
    # 检查结论中是否包含过度自信的表述
    overconfidence_patterns = [
        r'(?i)\b(prove|proves|proven|definitively|conclusively|without\s+doubt|absolute|absolutely)\b',
        r'(?i)\b(all|every|always|never|completely|totally)\b'
    ]
    
    for pattern in overconfidence_patterns:
        matches = re.findall(pattern, conclusion_content)
        if matches:
            unique_matches = set(matches)
            issues.append(f"结论中包含过度自信的表述: {', '.join(unique_matches)}")
            break
    
    # 检查结论中是否包含未在结果中支持的因果关系
    causality_in_conclusion = re.search(r'(?i)\b(cause|causes|caused|causing|lead\s+to|leads\s+to|resulting\s+in|result\s+in|due\s+to)\b', conclusion_content)
    if causality_in_conclusion and not re.search(r'(?i)\b(cause|causes|caused|causing|lead\s+to|leads\s+to|resulting\s+in|result\s+in|due\s+to)\b', results_content):
        issues.append("结论中包含因果关系的陈述，但结果部分没有提供足够的因果证据")
    
    return issues


def extract_references(references_content: str) -> List[str]:
    """
    从参考文献部分提取单独的引用
    
    Args:
        references_content: 参考文献部分内容
        
    Returns:
        List[str]: 引用列表
    """
    # 尝试按常见的引用分隔符分割
    references = []
    
    # 按编号模式分割
    numbered_refs = re.split(r'\n\s*\d+\.\s+', '\n' + references_content)
    if len(numbered_refs) > 1:
        references = [ref.strip() for ref in numbered_refs[1:] if ref.strip()]
    else:
        # 按换行符分割
        references = [ref.strip() for ref in references_content.split('\n') if ref.strip()]
    
    return references


def extract_citation_marks(content: str) -> List[str]:
    """
    从正文中提取引用标记
    
    Args:
        content: 正文内容
        
    Returns:
        List[str]: 引用标记列表
    """
    # 匹配常见的引用标记模式
    patterns = [
        r'\[\d+(?:,\s*\d+)*\]',  # [1] 或 [1,2,3]
        r'\(\d+(?:,\s*\d+)*\)',  # (1) 或 (1,2,3)
        r'\[(?:[A-Za-z]+(?:\s+et\s+al\.)?(?:,\s*\d{4})?(?:;)?)+\]',  # [Smith et al., 2020] 或 [Smith, 2020; Jones, 2019]
        r'\((?:[A-Za-z]+(?:\s+et\s+al\.)?(?:,\s*\d{4})?(?:;)?)+\)'   # (Smith et al., 2020) 或 (Smith, 2020; Jones, 2019)
    ]
    
    citation_marks = []
    for pattern in patterns:
        matches = re.findall(pattern, content)
        citation_marks.extend(matches)
    
    return citation_marks


def check_reference_format_consistency(references: List[str]) -> Dict[str, Any]:
    """
    检查参考文献格式的一致性
    
    Args:
        references: 参考文献列表
        
    Returns:
        Dict[str, Any]: 一致性检查结果
    """
    if not references or len(references) < 2:
        return {"consistent": True, "consistency_rate": 100.0}
    
    # 检查作者格式一致性
    author_formats = []
    for ref in references:
        # 尝试提取作者部分
        author_match = re.match(r'^([^\.]+)\.', ref)
        if author_match:
            author_formats.append(author_match.group(1))
    
    # 检查年份格式一致性
    year_formats = []
    for ref in references:
        # 尝试提取年份部分
        year_matches = re.findall(r'(?:19|20)\d{2}', ref)
        if year_matches:
            for year in year_matches:
                position = ref.find(year)
                before_char = ref[position-1] if position > 0 else ""
                after_char = ref[position+4] if position+4 < len(ref) else ""
                year_formats.append(f"{before_char}{year}{after_char}")
    
    # 计算一致性
    author_consistency = len(set([f.count(',') for f in author_formats])) <= 1 if author_formats else True
    year_consistency = len(set(year_formats)) <= 1 if year_formats else True
    
    # 综合评估
    consistent = author_consistency and year_consistency
    consistency_rate = 100.0 if consistent else 50.0
    
    return {
        "consistent": consistent,
        "consistency_rate": consistency_rate
    }


def extract_key_findings(results_content: str) -> List[str]:
    """
    从结果部分提取关键发现
    
    Args:
        results_content: 结果部分内容
        
    Returns:
        List[str]: 关键发现列表
    """
    # 尝试识别结果中的关键发现
    finding_patterns = [
        r'(?i)(?:we|our|this\s+study)\s+(?:found|observed|discovered|identified|showed|demonstrated)\s+([^\.]+)',
        r'(?i)(?:results|findings|data)\s+(?:showed|demonstrated|indicated|suggested|revealed)\s+([^\.]+)',
        r'(?i)(?:significantly|notably|importantly|interestingly|remarkably)\s+([^\.]+)'
    ]
    
    findings = []
    for pattern in finding_patterns:
        matches = re.findall(pattern, results_content)
        findings.extend([match.strip() for match in matches if match.strip()])
    
    # 如果没有找到明确的发现表述，则提取关键句子
    if not findings:
        sentences = re.split(r'[.!?]', results_content)
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence.split()) >= 5 and len(sentence.split()) <= 30:
                findings.append(sentence)
    
    # 限制数量
    return findings[:5]


def check_conclusion_alignment(key_findings: List[str], conclusion_content: str) -> Dict[str, Any]:
    """
    检查结论是否与关键发现一致
    
    Args:
        key_findings: 关键发现列表
        conclusion_content: 结论部分内容
        
    Returns:
        Dict[str, Any]: 一致性检查结果
    """
    issues = []
    aligned_count = 0
    
    for finding in key_findings:
        # 提取发现中的关键词
        words = re.findall(r'\b[a-zA-Z]{4,}\b', finding)
        significant_words = [word for word in words if len(word) >= 4]
        
        # 检查关键词是否在结论中出现
        if significant_words:
            aligned = False
            for word in significant_words:
                if re.search(rf'\b{re.escape(word)}\b', conclusion_content, re.IGNORECASE):
                    aligned = True
                    break
            
            if aligned:
                aligned_count += 1
            else:
                issues.append(f"结果中的发现 '{finding}' 在结论部分没有明确反映")
    
    # 计算一致性比率
    alignment_rate = aligned_count / len(key_findings) * 100 if key_findings else 100
    
    return {
        "issues": issues,
        "alignment_rate": round(alignment_rate, 1)
    }


def check_unsupported_claims(results_content: str, conclusion_content: str) -> List[str]:
    """
    检查结论中是否包含未在结果中支持的主张
    
    Args:
        results_content: 结果部分内容
        conclusion_content: 结论部分内容
        
    Returns:
        List[str]: 未支持的主张列表
    """
    issues = []
    
    # 提取结论中的主要主张
    conclusion_sentences = re.split(r'[.!?]', conclusion_content)
    for sentence in conclusion_sentences:
        sentence = sentence.strip()
        if not sentence or len(sentence.split()) < 5:
            continue
        
        # 提取主张中的关键词
        words = re.findall(r'\b[a-zA-Z]{5,}\b', sentence)
        significant_words = [word for word in words if len(word) >= 5 and word.lower() not in ["these", "those", "their", "which", "where", "there", "about", "study"]]
        
        # 检查关键词是否在结果中出现
        unsupported = True
        for word in significant_words[:3]:  # 只检查前三个关键词
            if re.search(rf'\b{re.escape(word)}\b', results_content, re.IGNORECASE):
                unsupported = False
                break
        
        if unsupported and significant_words:
            issues.append(f"结论中的主张 '{sentence}' 可能缺乏结果部分的直接支持")
    
    return issues


def check_information_gaps(document_sections: Dict[str, str]) -> List[str]:
    """
    检查文档中的信息缺口
    
    Args:
        document_sections: 文档各部分内容
        
    Returns:
        List[str]: 信息缺口列表
    """
    issues = []
    
    # 检查方法部分是否缺少关键信息
    methods_content = document_sections.get("methods", "")
    if methods_content:
        if not re.search(r'(?i)(?:sample|participant|subject|data)\s+(?:size|number|count)', methods_content):
            issues.append("方法部分缺少样本量信息")
        
        if not re.search(r'(?i)(?:statistical|analysis|test|significance|p-value)', methods_content):
            issues.append("方法部分缺少统计分析方法信息")
    
    # 检查结果部分是否缺少关键信息
    results_content = document_sections.get("results", "")
    if results_content:
        if not re.search(r'(?i)(?:p|p-value|significance|significant|alpha)\s*(?:<|=|>)\s*0\.\d+', results_content):
            issues.append("结果部分缺少统计显著性信息")
        
        if not re.search(r'(?i)(?:table|figure|chart|graph|plot|diagram)', results_content) and not re.search(r'(?i)(?:mean|average|median|std|standard deviation|variance)', results_content):
            issues.append("结果部分缺少数据呈现（表格、图表或统计量）")
    
    return issues


def check_potential_hallucinations(document_sections: Dict[str, str]) -> List[str]:
    """
    检查潜在的幻觉内容（自相矛盾的陈述）
    
    Args:
        document_sections: 文档各部分内容
        
    Returns:
        List[str]: 潜在幻觉内容列表
    """
    issues = []
    
    # 合并所有内容
    full_content = ' '.join([section for section in document_sections.values()])
    
    # 检查数字不一致
    number_patterns = [
        (r'(?i)(?:n\s*=\s*)(\d+)', "样本量"),
        (r'(?i)(?:p\s*(?:<|=|>)\s*)(0\.\d+)', "p值"),
        (r'(?i)(?:age\s*(?:=|:)\s*)(\d+(?:\.\d+)?)', "年龄")
    ]
    
    for pattern, desc in number_patterns:
        matches = re.findall(pattern, full_content)
        if len(matches) >= 2 and len(set(matches)) >= 2:
            issues.append(f"文档中存在{desc}不一致的情况: {', '.join(set(matches))}")
    
    # 检查矛盾的结论陈述
    contradiction_pairs = [
        (r'(?i)(?:increase|increased|increasing|higher|greater|more)', r'(?i)(?:decrease|decreased|decreasing|lower|lesser|less)'),
        (r'(?i)(?:significant|significantly)', r'(?i)(?:not significant|insignificant)'),
        (r'(?i)(?:positive|positively)', r'(?i)(?:negative|negatively)'),
        (r'(?i)(?:confirm|confirmed|confirms)', r'(?i)(?:reject|rejected|rejects)')
    ]
    
    conclusion_content = document_sections.get("conclusion", "")
    for positive, negative in contradiction_pairs:
        if re.search(positive, conclusion_content) and re.search(negative, conclusion_content):
            issues.append(f"结论部分可能包含矛盾的陈述（同时使用了相反的表述）")
            break
    
    return issues


def check_data_presentation(document_sections: Dict[str, str]) -> List[str]:
    """
    检查数据呈现的完整性
    
    Args:
        document_sections: 文档各部分内容
        
    Returns:
        List[str]: 数据呈现问题列表
    """
    issues = []
    
    results_content = document_sections.get("results", "")
    
    # 检查是否提到了表格或图表但没有提供
    table_figure_mentions = re.findall(r'(?i)(?:table|figure|fig\.)(?:\s+)(\d+)', results_content)
    if table_figure_mentions and not re.search(r'(?i)(?:see|shown|presented|displayed|illustrated)\s+(?:in|on|by)', results_content):
        issues.append("结果部分提到了表格或图表，但可能没有实际提供或引用不明确")
    
    # 检查数据是否有单位
    if re.search(r'(?i)(?:measured|measurement|value|level|concentration)', results_content) and not re.search(r'(?i)(?:mg|kg|ml|cm|mm|g|l|mol|μ|µ|%|percent)', results_content):
        issues.append("结果部分可能缺少测量单位")
    
    # 检查是否提供了变异性指标
    if re.search(r'(?i)(?:mean|average)', results_content) and not re.search(r'(?i)(?:standard deviation|std|SD|standard error|SE|confidence interval|CI)', results_content):
        issues.append("结果部分提供了均值但可能缺少变异性指标（如标准差）")
    
    return issues


# 生成建议函数
def generate_structure_recommendations(missing_sections: List[str], weak_sections: List[str]) -> List[str]:
    """
    生成结构完整性建议
    
    Args:
        missing_sections: 缺失的部分
        weak_sections: 薄弱的部分
        
    Returns:
        List[str]: 建议列表
    """
    recommendations = []
    
    if missing_sections:
        recommendations.append(f"添加缺失的部分: {', '.join(missing_sections)}")
    
    if weak_sections:
        recommendations.append(f"增强薄弱的部分: {', '.join(weak_sections)}")
    
    if not missing_sections and not weak_sections:
        recommendations.append("文献结构完整，保持良好的结构组织")
    
    return recommendations


def generate_scientific_accuracy_recommendations(issues: List[str]) -> List[str]:
    """
    生成科学准确性建议
    
    Args:
        issues: 问题列表
        
    Returns:
        List[str]: 建议列表
    """
    if not issues:
        return ["文献科学准确性良好，保持这种水平"]
    
    recommendations = []
    
    if any("方法中提到" in issue for issue in issues):
        recommendations.append("确保方法部分提到的所有技术和分析在结果部分都有相应的呈现")
    
    if any("过度自信" in issue for issue in issues):
        recommendations.append("避免在结论中使用过度自信的表述，如'证明'、'绝对'等词语")
    
    if any("因果关系" in issue for issue in issues):
        recommendations.append("确保所有因果关系陈述都有充分的实验证据支持，或改用相关性描述")
    
    return recommendations


def generate_methodology_recommendations(issues: List[str], methodology_elements: Dict[str, bool]) -> List[str]:
    """
    生成方法论建议
    
    Args:
        issues: 问题列表
        methodology_elements: 方法学要素
        
    Returns:
        List[str]: 建议列表
    """
    recommendations = []
    
    if "方法描述过于简略" in issues:
        recommendations.append("扩展方法描述，提供更多细节，确保其他研究者能够复现研究")
    
    for element, present in methodology_elements.items():
        if not present:
            readable_element = element.replace("_", " ").capitalize()
            recommendations.append(f"添加{readable_element}的详细描述")
    
    if not issues:
        recommendations.append("方法论描述合理，可考虑添加更多细节以增强可复现性")
    
    return recommendations


def generate_reference_recommendations(issues: List[str], reference_count: int, citation_coverage: float) -> List[str]:
    """
    生成引用质量建议
    
    Args:
        issues: 问题列表
        reference_count: 引用数量
        citation_coverage: 引用覆盖率
        
    Returns:
        List[str]: 建议列表
    """
    recommendations = []
    
    if reference_count < 5:
        recommendations.append("增加参考文献数量，确保充分支持研究背景和讨论")
    
    if citation_coverage < 50:
        recommendations.append("确保正文中的所有引用标记都在参考文献列表中有对应条目，反之亦然")
    
    if any("格式不一致" in issue for issue in issues):
        recommendations.append("统一参考文献格式，遵循一种标准的引用格式（如APA、MLA、Chicago等）")
    
    if not issues:
        recommendations.append("引用质量良好，保持这种水平")
    
    return recommendations


def generate_conclusion_validity_recommendations(issues: List[str]) -> List[str]:
    """
    生成结论有效性建议
    
    Args:
        issues: 问题列表
        
    Returns:
        List[str]: 建议列表
    """
    recommendations = []
    
    if any("没有明确反映" in issue for issue in issues):
        recommendations.append("确保结论中的所有要点都基于结果部分的具体发现")
    
    if any("缺乏结果部分的直接支持" in issue for issue in issues):
        recommendations.append("移除或修改结论中没有直接数据支持的主张")
    
    if not issues:
        recommendations.append("结论有效性良好，与研究结果保持一致")
    
    return recommendations


def generate_information_completeness_recommendations(issues: List[str]) -> List[str]:
    """
    生成信息完整性建议
    
    Args:
        issues: 问题列表
        
    Returns:
        List[str]: 建议列表
    """
    recommendations = []
    
    if any("方法部分缺少" in issue for issue in issues):
        recommendations.append("补充方法部分的关键信息，特别是样本量和统计分析方法")
    
    if any("结果部分缺少" in issue for issue in issues):
        recommendations.append("增强结果部分的数据呈现，添加统计显著性信息和适当的表格或图表")
    
    if any("不一致" in issue for issue in issues):
        recommendations.append("检查并修正文档中的数据不一致问题")
    
    if any("矛盾的陈述" in issue for issue in issues):
        recommendations.append("解决结论部分的矛盾陈述，确保论点一致")
    
    if not issues:
        recommendations.append("信息完整性良好，数据呈现清晰")
    
    return recommendations