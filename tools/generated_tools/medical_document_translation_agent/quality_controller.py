#!/usr/bin/env python3
"""
quality_controller.py - 医学翻译质量控制工具

该工具提供了医学翻译质量控制功能，包括术语一致性检查、
缩写处理、不确定翻译标注和质量报告生成等功能。
"""

import os
import json
import re
import hashlib
import datetime
from typing import Dict, List, Any, Optional, Union, Tuple, Set
from pathlib import Path
import difflib

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    raise ImportError("请安装boto3库: pip install boto3")

from strands import tool


# 默认缓存目录
DEFAULT_CACHE_DIR = os.path.join(".cache", "medical_translator", "quality")

# 质量评估维度
QUALITY_DIMENSIONS = [
    "terminology_accuracy",    # 术语准确性
    "terminology_consistency", # 术语一致性
    "grammar_correctness",     # 语法正确性
    "style_consistency",       # 风格一致性
    "completeness",            # 完整性
    "readability",             # 可读性
    "context_appropriateness", # 上下文适当性
    "abbreviation_handling"    # 缩写处理
]


@tool
def check_terminology_consistency(source_text: str, 
                                 translated_text: str, 
                                 glossary_name: str,
                                 source_lang: str,
                                 target_lang: str,
                                 cache_dir: Optional[str] = None) -> str:
    """
    检查翻译中术语的一致性
    
    Args:
        source_text (str): 源文本
        translated_text (str): 翻译文本
        glossary_name (str): 词库名称
        source_lang (str): 源语言代码
        target_lang (str): 目标语言代码
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的一致性检查结果
    """
    try:
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        os.makedirs(cache_dir, exist_ok=True)
        
        # 加载词库
        glossary_dir = os.path.join(".cache", "medical_translator", "glossaries")
        glossary_file = os.path.join(glossary_dir, f"{glossary_name}.json")
        
        if not os.path.exists(glossary_file):
            return json.dumps({
                "success": False,
                "error": f"词库不存在: {glossary_name}"
            }, ensure_ascii=False)
        
        with open(glossary_file, 'r', encoding='utf-8') as f:
            glossary_data = json.load(f)
        
        if "terms" not in glossary_data:
            return json.dumps({
                "success": False,
                "error": f"词库格式无效: {glossary_name}"
            }, ensure_ascii=False)
        
        # 源语言术语匹配
        source_terms = {}
        source_field = "source_term"
        target_field = "target_term"
        
        # 按长度排序术语，优先匹配长术语
        sorted_terms = sorted(
            glossary_data["terms"],
            key=lambda x: len(x.get(source_field, "")),
            reverse=True
        )
        
        # 在源文本中匹配术语
        for term in sorted_terms:
            source = term.get(source_field, "")
            target = term.get(target_field, "")
            
            if not source or not target:
                continue
            
            # 使用正则表达式匹配术语
            pattern = r'\b' + re.escape(source) + r'\b'
            for match in re.finditer(pattern, source_text):
                start, end = match.span()
                
                # 记录匹配到的术语
                if source not in source_terms:
                    source_terms[source] = {
                        "term_id": term.get("term_id"),
                        "source": source,
                        "target": target,
                        "positions": [],
                        "category": term.get("category", "未分类")
                    }
                
                source_terms[source]["positions"].append({
                    "start": start,
                    "end": end
                })
        
        # 检查翻译文本中的术语一致性
        inconsistencies = []
        
        for source, term_info in source_terms.items():
            target = term_info["target"]
            
            # 检查目标术语是否在翻译文本中出现
            pattern = r'\b' + re.escape(target) + r'\b'
            matches = list(re.finditer(pattern, translated_text))
            
            # 如果源文本中出现的次数与翻译文本中出现的次数不一致
            if len(matches) != len(term_info["positions"]):
                inconsistencies.append({
                    "term_id": term_info["term_id"],
                    "source_term": source,
                    "target_term": target,
                    "source_occurrences": len(term_info["positions"]),
                    "target_occurrences": len(matches),
                    "category": term_info["category"],
                    "type": "occurrence_mismatch"
                })
            
            # 查找可能的不一致翻译
            if len(matches) > 0:
                # 获取翻译文本中所有可能的术语翻译
                possible_translations = set()
                for position in term_info["positions"]:
                    # 尝试在翻译文本中找到对应位置的翻译
                    # 这是一个简化的方法，实际应用中可能需要更复杂的对齐算法
                    start_ratio = position["start"] / len(source_text)
                    end_ratio = position["end"] / len(source_text)
                    
                    approx_start = int(start_ratio * len(translated_text))
                    approx_end = int(end_ratio * len(translated_text))
                    
                    # 在近似位置附近搜索
                    window_size = 50  # 搜索窗口大小
                    search_start = max(0, approx_start - window_size)
                    search_end = min(len(translated_text), approx_end + window_size)
                    
                    search_text = translated_text[search_start:search_end]
                    
                    # 在搜索窗口中查找可能的翻译
                    for word in re.findall(r'\b\w+\b', search_text):
                        if word != target and len(word) > 1:
                            possible_translations.add(word)
        
        # 生成一致性报告
        consistency_score = 1.0
        if inconsistencies:
            # 根据不一致数量计算一致性得分
            consistency_score = max(0.0, 1.0 - (len(inconsistencies) / max(1, len(source_terms))))
        
        report = {
            "success": True,
            "glossary_name": glossary_name,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "total_terms": len(source_terms),
            "inconsistent_terms": len(inconsistencies),
            "consistency_score": round(consistency_score, 2),
            "inconsistencies": inconsistencies
        }
        
        return json.dumps(report, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"检查术语一致性时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def check_abbreviation_handling(source_text: str, 
                               translated_text: str,
                               source_lang: str,
                               target_lang: str,
                               domain: str = "general",
                               cache_dir: Optional[str] = None) -> str:
    """
    检查翻译中对医学缩写的处理
    
    Args:
        source_text (str): 源文本
        translated_text (str): 翻译文本
        source_lang (str): 源语言代码
        target_lang (str): 目标语言代码
        domain (str): 医学领域
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的缩写处理检查结果
    """
    try:
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        os.makedirs(cache_dir, exist_ok=True)
        
        # 查找源文本中的缩写
        abbreviations = _find_medical_abbreviations(source_text, source_lang, domain)
        
        # 检查翻译文本中的缩写处理
        handling_issues = []
        
        for abbr in abbreviations:
            abbr_text = abbr["abbreviation"]
            expansion = abbr["expansion"]
            
            # 检查缩写是否在翻译文本中保留
            abbr_in_translation = abbr_text in translated_text
            
            # 检查全称是否在翻译文本中
            expansion_in_translation = False
            if expansion:
                # 如果目标语言是英语，直接检查英文全称
                if target_lang == "en":
                    expansion_in_translation = expansion in translated_text
                else:
                    # 对于其他语言，使用AI翻译获取全称的翻译
                    translated_expansion = _translate_term(expansion, "en", target_lang, domain)
                    if translated_expansion:
                        expansion_in_translation = translated_expansion in translated_text
            
            # 如果缩写和全称都不在翻译中，记录问题
            if not abbr_in_translation and not expansion_in_translation:
                handling_issues.append({
                    "abbreviation": abbr_text,
                    "expansion": expansion,
                    "issue": "abbreviation_missing",
                    "description": "缩写及其全称在翻译中均未出现"
                })
            # 如果源语言是英语且目标语言不是英语，但英文缩写在翻译中保留
            elif source_lang == "en" and target_lang != "en" and abbr_in_translation and not expansion_in_translation:
                handling_issues.append({
                    "abbreviation": abbr_text,
                    "expansion": expansion,
                    "issue": "abbreviation_not_translated",
                    "description": "英文缩写在非英语翻译中未被翻译或解释"
                })
        
        # 计算缩写处理得分
        abbreviation_score = 1.0
        if abbreviations:
            abbreviation_score = max(0.0, 1.0 - (len(handling_issues) / len(abbreviations)))
        
        report = {
            "success": True,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "domain": domain,
            "total_abbreviations": len(abbreviations),
            "handling_issues": len(handling_issues),
            "abbreviation_score": round(abbreviation_score, 2),
            "abbreviations": abbreviations,
            "issues": handling_issues
        }
        
        return json.dumps(report, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"检查缩写处理时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def identify_uncertain_translations(source_text: str, 
                                   translated_text: str,
                                   source_lang: str,
                                   target_lang: str,
                                   domain: str = "general",
                                   confidence_threshold: float = 0.7,
                                   cache_dir: Optional[str] = None) -> str:
    """
    识别翻译中的不确定部分并提供备选方案
    
    Args:
        source_text (str): 源文本
        translated_text (str): 翻译文本
        source_lang (str): 源语言代码
        target_lang (str): 目标语言代码
        domain (str): 医学领域
        confidence_threshold (float): 置信度阈值
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的不确定翻译识别结果
    """
    try:
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        os.makedirs(cache_dir, exist_ok=True)
        
        # 分割文本为句子
        source_sentences = _split_into_sentences(source_text, source_lang)
        translated_sentences = _split_into_sentences(translated_text, target_lang)
        
        # 如果句子数量不匹配，进行简单的长度比例对齐
        if len(source_sentences) != len(translated_sentences):
            # 使用简单的长度比例对齐
            source_sentences, translated_sentences = _align_sentences(
                source_sentences, translated_sentences, source_text, translated_text
            )
        
        # 识别不确定翻译
        uncertain_translations = []
        
        for i, (source_sent, translated_sent) in enumerate(zip(source_sentences, translated_sentences)):
            # 使用AI评估翻译质量和置信度
            assessment = _assess_translation_quality(source_sent, translated_sent, source_lang, target_lang, domain)
            
            if assessment["confidence"] < confidence_threshold:
                # 生成备选翻译
                alternatives = _generate_alternative_translations(source_sent, source_lang, target_lang, domain)
                
                uncertain_translations.append({
                    "index": i,
                    "source_sentence": source_sent,
                    "translated_sentence": translated_sent,
                    "confidence": assessment["confidence"],
                    "issues": assessment.get("issues", []),
                    "alternatives": alternatives
                })
        
        # 计算整体置信度
        overall_confidence = 1.0
        if source_sentences:
            uncertain_count = len(uncertain_translations)
            overall_confidence = max(0.0, 1.0 - (uncertain_count / len(source_sentences)))
        
        report = {
            "success": True,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "domain": domain,
            "total_sentences": len(source_sentences),
            "uncertain_sentences": len(uncertain_translations),
            "overall_confidence": round(overall_confidence, 2),
            "uncertain_translations": uncertain_translations
        }
        
        return json.dumps(report, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"识别不确定翻译时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def generate_quality_report(source_text: str, 
                           translated_text: str,
                           source_lang: str,
                           target_lang: str,
                           glossary_name: Optional[str] = None,
                           domain: str = "general",
                           cache_dir: Optional[str] = None) -> str:
    """
    生成全面的翻译质量报告
    
    Args:
        source_text (str): 源文本
        translated_text (str): 翻译文本
        source_lang (str): 源语言代码
        target_lang (str): 目标语言代码
        glossary_name (Optional[str]): 词库名称（可选）
        domain (str): 医学领域
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的质量报告
    """
    try:
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        os.makedirs(cache_dir, exist_ok=True)
        
        # 创建报告ID
        report_id = hashlib.md5(f"{source_text}:{translated_text}:{datetime.datetime.now().isoformat()}".encode()).hexdigest()
        
        # 检查缓存
        cache_file = os.path.join(cache_dir, f"report_{report_id}.json")
        
        # 基本统计
        source_chars = len(source_text)
        translated_chars = len(translated_text)
        source_words = len(re.findall(r'\b\w+\b', source_text))
        translated_words = len(re.findall(r'\b\w+\b', translated_text))
        
        source_sentences = _split_into_sentences(source_text, source_lang)
        translated_sentences = _split_into_sentences(translated_text, target_lang)
        
        # 术语一致性检查
        terminology_consistency = {}
        if glossary_name:
            consistency_result = json.loads(check_terminology_consistency(
                source_text, translated_text, glossary_name, source_lang, target_lang, cache_dir
            ))
            
            if consistency_result.get("success", False):
                terminology_consistency = {
                    "consistency_score": consistency_result.get("consistency_score", 0.0),
                    "total_terms": consistency_result.get("total_terms", 0),
                    "inconsistent_terms": consistency_result.get("inconsistent_terms", 0),
                    "inconsistencies": consistency_result.get("inconsistencies", [])
                }
        
        # 缩写处理检查
        abbreviation_handling = {}
        abbreviation_result = json.loads(check_abbreviation_handling(
            source_text, translated_text, source_lang, target_lang, domain, cache_dir
        ))
        
        if abbreviation_result.get("success", False):
            abbreviation_handling = {
                "abbreviation_score": abbreviation_result.get("abbreviation_score", 0.0),
                "total_abbreviations": abbreviation_result.get("total_abbreviations", 0),
                "handling_issues": abbreviation_result.get("handling_issues", 0),
                "issues": abbreviation_result.get("issues", [])
            }
        
        # 不确定翻译识别
        uncertain_translations = {}
        uncertain_result = json.loads(identify_uncertain_translations(
            source_text, translated_text, source_lang, target_lang, domain, 0.7, cache_dir
        ))
        
        if uncertain_result.get("success", False):
            uncertain_translations = {
                "overall_confidence": uncertain_result.get("overall_confidence", 0.0),
                "total_sentences": uncertain_result.get("total_sentences", 0),
                "uncertain_sentences": uncertain_result.get("uncertain_sentences", 0),
                "uncertain_translations": uncertain_result.get("uncertain_translations", [])
            }
        
        # 使用AI评估其他质量维度
        quality_dimensions = _assess_quality_dimensions(source_text, translated_text, source_lang, target_lang, domain)
        
        # 计算整体质量得分
        scores = [
            terminology_consistency.get("consistency_score", 0.0),
            abbreviation_handling.get("abbreviation_score", 0.0),
            uncertain_translations.get("overall_confidence", 0.0)
        ]
        
        for dimension, score in quality_dimensions.items():
            scores.append(score)
        
        overall_score = sum(scores) / len(scores) if scores else 0.0
        
        # 生成质量报告
        report = {
            "success": True,
            "report_id": report_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "source_lang": source_lang,
            "target_lang": target_lang,
            "domain": domain,
            "statistics": {
                "source_chars": source_chars,
                "translated_chars": translated_chars,
                "source_words": source_words,
                "translated_words": translated_words,
                "source_sentences": len(source_sentences),
                "translated_sentences": len(translated_sentences),
                "char_ratio": round(translated_chars / source_chars, 2) if source_chars > 0 else 0,
                "word_ratio": round(translated_words / source_words, 2) if source_words > 0 else 0
            },
            "quality_scores": {
                "overall_score": round(overall_score, 2),
                "terminology_consistency": round(terminology_consistency.get("consistency_score", 0.0), 2),
                "abbreviation_handling": round(abbreviation_handling.get("abbreviation_score", 0.0), 2),
                "translation_confidence": round(uncertain_translations.get("overall_confidence", 0.0), 2),
                **{dim: round(score, 2) for dim, score in quality_dimensions.items()}
            },
            "terminology_consistency": terminology_consistency,
            "abbreviation_handling": abbreviation_handling,
            "uncertain_translations": uncertain_translations,
            "improvement_suggestions": _generate_improvement_suggestions(
                terminology_consistency,
                abbreviation_handling,
                uncertain_translations,
                quality_dimensions
            )
        }
        
        # 缓存报告
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return json.dumps(report, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"生成质量报告时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def compare_translations(source_text: str, 
                        translation1: str, 
                        translation2: str,
                        source_lang: str,
                        target_lang: str,
                        domain: str = "general",
                        cache_dir: Optional[str] = None) -> str:
    """
    比较两个翻译版本的质量
    
    Args:
        source_text (str): 源文本
        translation1 (str): 第一个翻译版本
        translation2 (str): 第二个翻译版本
        source_lang (str): 源语言代码
        target_lang (str): 目标语言代码
        domain (str): 医学领域
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的比较结果
    """
    try:
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        os.makedirs(cache_dir, exist_ok=True)
        
        # 生成两个翻译的质量报告
        report1_json = generate_quality_report(
            source_text, translation1, source_lang, target_lang, None, domain, cache_dir
        )
        
        report2_json = generate_quality_report(
            source_text, translation2, source_lang, target_lang, None, domain, cache_dir
        )
        
        report1 = json.loads(report1_json)
        report2 = json.loads(report2_json)
        
        # 比较质量得分
        if "success" not in report1 or not report1["success"] or "success" not in report2 or not report2["success"]:
            return json.dumps({
                "success": False,
                "error": "生成质量报告失败"
            }, ensure_ascii=False)
        
        # 提取质量得分
        scores1 = report1["quality_scores"]
        scores2 = report2["quality_scores"]
        
        # 比较各维度得分
        score_comparison = {}
        for dimension in scores1.keys():
            if dimension in scores2:
                score1 = scores1[dimension]
                score2 = scores2[dimension]
                difference = score2 - score1
                
                score_comparison[dimension] = {
                    "translation1_score": score1,
                    "translation2_score": score2,
                    "difference": round(difference, 2),
                    "better_translation": "translation2" if difference > 0 else "translation1" if difference < 0 else "equal"
                }
        
        # 计算整体优劣
        better_dimensions1 = sum(1 for dim in score_comparison.values() if dim["better_translation"] == "translation1")
        better_dimensions2 = sum(1 for dim in score_comparison.values() if dim["better_translation"] == "translation2")
        equal_dimensions = sum(1 for dim in score_comparison.values() if dim["better_translation"] == "equal")
        
        overall_better = "translation2" if better_dimensions2 > better_dimensions1 else "translation1" if better_dimensions1 > better_dimensions2 else "equal"
        
        # 找出差异最大的句子
        source_sentences = _split_into_sentences(source_text, source_lang)
        sentences1 = _split_into_sentences(translation1, target_lang)
        sentences2 = _split_into_sentences(translation2, target_lang)
        
        # 确保句子数量一致，如果不一致则进行对齐
        if len(sentences1) != len(source_sentences) or len(sentences2) != len(source_sentences):
            sentences1, _ = _align_sentences(sentences1, source_sentences, translation1, source_text)
            sentences2, _ = _align_sentences(sentences2, source_sentences, translation2, source_text)
        
        # 找出差异最大的句子
        sentence_differences = []
        for i, (src, s1, s2) in enumerate(zip(source_sentences, sentences1, sentences2)):
            if s1 != s2:
                # 计算差异程度
                similarity = difflib.SequenceMatcher(None, s1, s2).ratio()
                difference = 1.0 - similarity
                
                sentence_differences.append({
                    "index": i,
                    "source": src,
                    "translation1": s1,
                    "translation2": s2,
                    "difference_score": round(difference, 2)
                })
        
        # 按差异程度排序
        sentence_differences.sort(key=lambda x: x["difference_score"], reverse=True)
        
        # 生成比较报告
        comparison_report = {
            "success": True,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "domain": domain,
            "overall_comparison": {
                "better_translation": overall_better,
                "translation1_better_dimensions": better_dimensions1,
                "translation2_better_dimensions": better_dimensions2,
                "equal_dimensions": equal_dimensions,
                "translation1_overall_score": scores1.get("overall_score", 0.0),
                "translation2_overall_score": scores2.get("overall_score", 0.0),
                "score_difference": round(scores2.get("overall_score", 0.0) - scores1.get("overall_score", 0.0), 2)
            },
            "dimension_comparison": score_comparison,
            "sentence_differences": sentence_differences[:10],  # 只返回差异最大的10个句子
            "total_different_sentences": len(sentence_differences),
            "recommendation": _generate_comparison_recommendation(
                overall_better,
                better_dimensions1,
                better_dimensions2,
                score_comparison
            )
        }
        
        return json.dumps(comparison_report, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"比较翻译时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def annotate_translation_issues(source_text: str, 
                               translated_text: str,
                               source_lang: str,
                               target_lang: str,
                               glossary_name: Optional[str] = None,
                               domain: str = "general",
                               cache_dir: Optional[str] = None) -> str:
    """
    为翻译文本添加问题标注
    
    Args:
        source_text (str): 源文本
        translated_text (str): 翻译文本
        source_lang (str): 源语言代码
        target_lang (str): 目标语言代码
        glossary_name (Optional[str]): 词库名称（可选）
        domain (str): 医学领域
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的标注结果
    """
    try:
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        os.makedirs(cache_dir, exist_ok=True)
        
        # 分割文本为句子
        source_sentences = _split_into_sentences(source_text, source_lang)
        translated_sentences = _split_into_sentences(translated_text, target_lang)
        
        # 如果句子数量不匹配，进行简单的长度比例对齐
        if len(source_sentences) != len(translated_sentences):
            source_sentences, translated_sentences = _align_sentences(
                source_sentences, translated_sentences, source_text, translated_text
            )
        
        # 收集所有问题
        all_issues = []
        
        # 检查术语一致性
        if glossary_name:
            consistency_result = json.loads(check_terminology_consistency(
                source_text, translated_text, glossary_name, source_lang, target_lang, cache_dir
            ))
            
            if consistency_result.get("success", False) and "inconsistencies" in consistency_result:
                for issue in consistency_result["inconsistencies"]:
                    all_issues.append({
                        "type": "terminology_inconsistency",
                        "source_term": issue.get("source_term", ""),
                        "target_term": issue.get("target_term", ""),
                        "description": f"术语'{issue.get('source_term', '')}'的翻译不一致",
                        "severity": "high"
                    })
        
        # 检查缩写处理
        abbreviation_result = json.loads(check_abbreviation_handling(
            source_text, translated_text, source_lang, target_lang, domain, cache_dir
        ))
        
        if abbreviation_result.get("success", False) and "issues" in abbreviation_result:
            for issue in abbreviation_result["issues"]:
                all_issues.append({
                    "type": "abbreviation_issue",
                    "abbreviation": issue.get("abbreviation", ""),
                    "expansion": issue.get("expansion", ""),
                    "description": issue.get("description", "缩写处理问题"),
                    "severity": "medium"
                })
        
        # 检查不确定翻译
        uncertain_result = json.loads(identify_uncertain_translations(
            source_text, translated_text, source_lang, target_lang, domain, 0.7, cache_dir
        ))
        
        if uncertain_result.get("success", False) and "uncertain_translations" in uncertain_result:
            for uncertain in uncertain_result["uncertain_translations"]:
                index = uncertain.get("index", 0)
                if 0 <= index < len(translated_sentences):
                    all_issues.append({
                        "type": "uncertain_translation",
                        "sentence_index": index,
                        "source_sentence": uncertain.get("source_sentence", ""),
                        "translated_sentence": uncertain.get("translated_sentence", ""),
                        "confidence": uncertain.get("confidence", 0.0),
                        "description": f"翻译置信度低: {uncertain.get('confidence', 0.0)}",
                        "alternatives": uncertain.get("alternatives", []),
                        "severity": "medium"
                    })
        
        # 逐句检查其他问题
        for i, (source_sent, translated_sent) in enumerate(zip(source_sentences, translated_sentences)):
            # 检查长度异常
            src_length = len(source_sent)
            tgt_length = len(translated_sent)
            
            # 如果翻译比源文本短很多或长很多
            if src_length > 0 and (tgt_length / src_length < 0.5 or tgt_length / src_length > 2.0):
                all_issues.append({
                    "type": "length_issue",
                    "sentence_index": i,
                    "source_sentence": source_sent,
                    "translated_sentence": translated_sent,
                    "source_length": src_length,
                    "translated_length": tgt_length,
                    "ratio": round(tgt_length / src_length, 2) if src_length > 0 else 0,
                    "description": "翻译长度异常",
                    "severity": "low"
                })
            
            # 使用AI检查其他问题
            other_issues = _check_sentence_issues(source_sent, translated_sent, source_lang, target_lang, domain)
            
            for issue in other_issues:
                issue["sentence_index"] = i
                issue["source_sentence"] = source_sent
                issue["translated_sentence"] = translated_sent
                all_issues.append(issue)
        
        # 创建标注结果
        annotated_result = {
            "success": True,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "domain": domain,
            "total_sentences": len(source_sentences),
            "total_issues": len(all_issues),
            "issues_by_type": {},
            "issues_by_severity": {
                "high": 0,
                "medium": 0,
                "low": 0
            },
            "all_issues": all_issues,
            "annotated_text": _generate_annotated_text(translated_text, all_issues)
        }
        
        # 统计问题类型
        for issue in all_issues:
            issue_type = issue.get("type", "other")
            severity = issue.get("severity", "medium")
            
            if issue_type not in annotated_result["issues_by_type"]:
                annotated_result["issues_by_type"][issue_type] = 0
            
            annotated_result["issues_by_type"][issue_type] += 1
            annotated_result["issues_by_severity"][severity] += 1
        
        return json.dumps(annotated_result, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"标注翻译问题时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def get_quality_report(report_id: str, cache_dir: Optional[str] = None) -> str:
    """
    获取已生成的质量报告
    
    Args:
        report_id (str): 报告ID
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的质量报告
    """
    try:
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        
        # 构建报告文件路径
        report_file = os.path.join(cache_dir, f"report_{report_id}.json")
        
        if not os.path.exists(report_file):
            return json.dumps({
                "success": False,
                "error": f"报告不存在: {report_id}"
            }, ensure_ascii=False)
        
        # 读取报告
        with open(report_file, 'r', encoding='utf-8') as f:
            report = json.load(f)
        
        return json.dumps(report, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"获取质量报告时出错: {str(e)}"
        }, ensure_ascii=False)


# 辅助函数
def _find_medical_abbreviations(text: str, lang: str, domain: str) -> List[Dict[str, Any]]:
    """
    在文本中查找医学缩写
    
    Args:
        text (str): 文本内容
        lang (str): 语言代码
        domain (str): 医学领域
        
    Returns:
        List[Dict[str, Any]]: 找到的缩写列表
    """
    # 常见英文医学缩写正则表达式
    en_abbr_pattern = r'\b([A-Z]{2,})\b'
    
    # 中文医学缩写通常是英文字母缩写
    zh_abbr_pattern = r'\b([A-Z]{2,})\b'
    
    abbreviations = []
    
    if lang == 'en':
        # 查找英文缩写
        matches = re.finditer(en_abbr_pattern, text)
        for match in matches:
            abbr = match.group(1)
            expansion = _get_abbreviation_expansion(abbr, lang, domain)
            
            if expansion:
                abbreviations.append({
                    "abbreviation": abbr,
                    "expansion": expansion,
                    "position": {
                        "start": match.start(),
                        "end": match.end()
                    }
                })
    
    elif lang == 'zh':
        # 查找中文文本中的英文缩写
        matches = re.finditer(zh_abbr_pattern, text)
        for match in matches:
            abbr = match.group(1)
            expansion = _get_abbreviation_expansion(abbr, 'en', domain)  # 中文文本中的缩写通常是英文缩写
            
            if expansion:
                abbreviations.append({
                    "abbreviation": abbr,
                    "expansion": expansion,
                    "position": {
                        "start": match.start(),
                        "end": match.end()
                    }
                })
    
    return abbreviations


def _get_abbreviation_expansion(abbr: str, lang: str, domain: str) -> Optional[str]:
    """
    获取缩写的全称
    
    Args:
        abbr (str): 缩写
        lang (str): 语言代码
        domain (str): 医学领域
        
    Returns:
        Optional[str]: 缩写的全称，如果找不到则返回None
    """
    # 常见医学缩写词典
    common_medical_abbreviations = {
        "BP": "Blood Pressure",
        "HR": "Heart Rate",
        "RR": "Respiratory Rate",
        "T": "Temperature",
        "SpO2": "Oxygen Saturation",
        "CBC": "Complete Blood Count",
        "BMP": "Basic Metabolic Panel",
        "CMP": "Comprehensive Metabolic Panel",
        "BUN": "Blood Urea Nitrogen",
        "Cr": "Creatinine",
        "Na": "Sodium",
        "K": "Potassium",
        "Cl": "Chloride",
        "CO2": "Carbon Dioxide",
        "Ca": "Calcium",
        "Mg": "Magnesium",
        "PO4": "Phosphate",
        "Glu": "Glucose",
        "HbA1c": "Hemoglobin A1c",
        "PT": "Prothrombin Time",
        "PTT": "Partial Thromboplastin Time",
        "INR": "International Normalized Ratio",
        "WBC": "White Blood Cell",
        "RBC": "Red Blood Cell",
        "Hgb": "Hemoglobin",
        "Hct": "Hematocrit",
        "MCV": "Mean Corpuscular Volume",
        "MCH": "Mean Corpuscular Hemoglobin",
        "MCHC": "Mean Corpuscular Hemoglobin Concentration",
        "PLT": "Platelet",
        "ESR": "Erythrocyte Sedimentation Rate",
        "CRP": "C-Reactive Protein",
        "LFT": "Liver Function Test",
        "AST": "Aspartate Aminotransferase",
        "ALT": "Alanine Aminotransferase",
        "ALP": "Alkaline Phosphatase",
        "GGT": "Gamma-Glutamyl Transferase",
        "TB": "Total Bilirubin",
        "DB": "Direct Bilirubin",
        "TP": "Total Protein",
        "Alb": "Albumin",
        "BNP": "Brain Natriuretic Peptide",
        "CK": "Creatine Kinase",
        "CK-MB": "Creatine Kinase-MB",
        "LDH": "Lactate Dehydrogenase",
        "Trop": "Troponin",
        "TSH": "Thyroid Stimulating Hormone",
        "T3": "Triiodothyronine",
        "T4": "Thyroxine",
        "FT3": "Free Triiodothyronine",
        "FT4": "Free Thyroxine",
        "PSA": "Prostate Specific Antigen",
        "CEA": "Carcinoembryonic Antigen",
        "AFP": "Alpha-Fetoprotein",
        "CA-125": "Cancer Antigen 125",
        "CA-19-9": "Cancer Antigen 19-9",
        "EKG": "Electrocardiogram",
        "ECG": "Electrocardiogram",
        "ECHO": "Echocardiogram",
        "CT": "Computed Tomography",
        "MRI": "Magnetic Resonance Imaging",
        "US": "Ultrasound",
        "CXR": "Chest X-Ray",
        "KUB": "Kidneys, Ureters, Bladder X-Ray",
        "IVP": "Intravenous Pyelogram",
        "UGI": "Upper Gastrointestinal Series",
        "BE": "Barium Enema",
        "ERCP": "Endoscopic Retrograde Cholangiopancreatography",
        "EGD": "Esophagogastroduodenoscopy",
        "EUS": "Endoscopic Ultrasound",
        "MRCP": "Magnetic Resonance Cholangiopancreatography",
        "PET": "Positron Emission Tomography",
        "PFT": "Pulmonary Function Test",
        "ABG": "Arterial Blood Gas",
        "COPD": "Chronic Obstructive Pulmonary Disease",
        "CHF": "Congestive Heart Failure",
        "CAD": "Coronary Artery Disease",
        "MI": "Myocardial Infarction",
        "CVA": "Cerebrovascular Accident",
        "TIA": "Transient Ischemic Attack",
        "DVT": "Deep Vein Thrombosis",
        "PE": "Pulmonary Embolism",
        "HTN": "Hypertension",
        "DM": "Diabetes Mellitus",
        "CKD": "Chronic Kidney Disease",
        "ESRD": "End-Stage Renal Disease",
        "HD": "Hemodialysis",
        "PD": "Peritoneal Dialysis",
        "RA": "Rheumatoid Arthritis",
        "SLE": "Systemic Lupus Erythematosus",
        "IBD": "Inflammatory Bowel Disease",
        "UC": "Ulcerative Colitis",
        "CD": "Crohn's Disease",
        "GERD": "Gastroesophageal Reflux Disease",
        "PUD": "Peptic Ulcer Disease",
        "UTI": "Urinary Tract Infection",
        "URI": "Upper Respiratory Infection",
        "LRI": "Lower Respiratory Infection",
        "CAP": "Community-Acquired Pneumonia",
        "HAP": "Hospital-Acquired Pneumonia",
        "VAP": "Ventilator-Associated Pneumonia",
        "TB": "Tuberculosis",
        "HIV": "Human Immunodeficiency Virus",
        "AIDS": "Acquired Immunodeficiency Syndrome",
        "HBV": "Hepatitis B Virus",
        "HCV": "Hepatitis C Virus",
        "HSV": "Herpes Simplex Virus",
        "HPV": "Human Papillomavirus",
        "STI": "Sexually Transmitted Infection",
        "PID": "Pelvic Inflammatory Disease",
        "BPH": "Benign Prostatic Hyperplasia",
        "ED": "Erectile Dysfunction",
        "PCOS": "Polycystic Ovary Syndrome",
        "PMS": "Premenstrual Syndrome",
        "OA": "Osteoarthritis",
        "OP": "Osteoporosis",
        "MS": "Multiple Sclerosis",
        "ALS": "Amyotrophic Lateral Sclerosis",
        "AD": "Alzheimer's Disease",
        "PD": "Parkinson's Disease",
        "ADHD": "Attention Deficit Hyperactivity Disorder",
        "OCD": "Obsessive-Compulsive Disorder",
        "PTSD": "Post-Traumatic Stress Disorder",
        "MDD": "Major Depressive Disorder",
        "GAD": "Generalized Anxiety Disorder",
        "BD": "Bipolar Disorder",
        "SCZ": "Schizophrenia"
    }
    
    # 特定领域的缩写词典
    domain_specific_abbreviations = {
        "clinical": {
            "Dx": "Diagnosis",
            "Tx": "Treatment",
            "Hx": "History",
            "PMH": "Past Medical History",
            "FH": "Family History",
            "SH": "Social History",
            "ROS": "Review of Systems",
            "PE": "Physical Examination",
            "VS": "Vital Signs",
            "CC": "Chief Complaint",
            "HPI": "History of Present Illness",
            "A/P": "Assessment and Plan"
        },
        "pharmacology": {
            "PO": "Per Os (by mouth)",
            "IV": "Intravenous",
            "IM": "Intramuscular",
            "SC": "Subcutaneous",
            "SL": "Sublingual",
            "PR": "Per Rectum",
            "PV": "Per Vagina",
            "QD": "Once Daily",
            "BID": "Twice Daily",
            "TID": "Three Times Daily",
            "QID": "Four Times Daily",
            "PRN": "As Needed",
            "STAT": "Immediately",
            "NPO": "Nothing by Mouth",
            "AC": "Before Meals",
            "PC": "After Meals",
            "HS": "At Bedtime"
        }
    }
    
    # 查找缩写全称
    expansion = None
    
    # 先查找特定领域的缩写
    if domain in domain_specific_abbreviations and abbr in domain_specific_abbreviations[domain]:
        expansion = domain_specific_abbreviations[domain][abbr]
    
    # 如果没有找到，查找通用医学缩写
    if not expansion and abbr in common_medical_abbreviations:
        expansion = common_medical_abbreviations[abbr]
    
    return expansion


def _split_into_sentences(text: str, lang: str) -> List[str]:
    """
    将文本分割为句子
    
    Args:
        text (str): 文本内容
        lang (str): 语言代码
        
    Returns:
        List[str]: 句子列表
    """
    if lang == 'zh':
        # 中文句子分隔符
        pattern = r'[。！？…]+|\.{3,}|[.!?]+[\s\n]+'
    else:
        # 英文和其他语言句子分隔符
        pattern = r'(?<=[.!?])\s+'
    
    # 分割文本
    sentences = re.split(pattern, text)
    
    # 过滤空句子
    sentences = [s.strip() for s in sentences if s.strip()]
    
    return sentences


def _align_sentences(sentences1: List[str], sentences2: List[str], text1: str, text2: str) -> Tuple[List[str], List[str]]:
    """
    对齐两组句子
    
    Args:
        sentences1 (List[str]): 第一组句子
        sentences2 (List[str]): 第二组句子
        text1 (str): 第一组句子的原始文本
        text2 (str): 第二组句子的原始文本
        
    Returns:
        Tuple[List[str], List[str]]: 对齐后的两组句子
    """
    # 如果句子数量相同，直接返回
    if len(sentences1) == len(sentences2):
        return sentences1, sentences2
    
    # 使用简单的长度比例对齐
    len1 = len(text1)
    len2 = len(text2)
    
    if len1 == 0 or len2 == 0:
        return sentences1, sentences2
    
    # 确定哪个更长
    if len(sentences1) > len(sentences2):
        longer = sentences1
        shorter = sentences2
        longer_text = text1
        shorter_text = text2
    else:
        longer = sentences2
        shorter = sentences1
        longer_text = text2
        shorter_text = text1
    
    # 计算长度比例
    ratio = len(shorter_text) / len(longer_text)
    
    # 创建对齐结果
    aligned_longer = []
    aligned_shorter = []
    
    # 合并较长的句子列表
    i = 0
    j = 0
    current_chunk = ""
    
    while i < len(longer) and j < len(shorter):
        current_chunk += longer[i]
        i += 1
        
        # 计算当前块的比例
        chunk_ratio = len(current_chunk) / len(longer_text)
        target_ratio = (j + 1) / len(shorter)
        
        if chunk_ratio >= target_ratio * ratio:
            aligned_longer.append(current_chunk)
            aligned_shorter.append(shorter[j])
            current_chunk = ""
            j += 1
    
    # 处理剩余部分
    if current_chunk:
        aligned_longer.append(current_chunk)
    
    while j < len(shorter):
        aligned_shorter.append(shorter[j])
        j += 1
    
    # 确保长度一致
    min_len = min(len(aligned_longer), len(aligned_shorter))
    aligned_longer = aligned_longer[:min_len]
    aligned_shorter = aligned_shorter[:min_len]
    
    # 返回对齐结果
    if len(sentences1) > len(sentences2):
        return aligned_longer, aligned_shorter
    else:
        return aligned_shorter, aligned_longer


def _translate_term(term: str, source_lang: str, target_lang: str, domain: str) -> Optional[str]:
    """
    翻译单个术语
    
    Args:
        term (str): 术语
        source_lang (str): 源语言代码
        target_lang (str): 目标语言代码
        domain (str): 医学领域
        
    Returns:
        Optional[str]: 翻译结果，如果失败则返回None
    """
    try:
        # 创建Bedrock客户端
        bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name='us-west-2'  # 使用适当的区域
        )
        
        # 构建提示词
        prompt = f"""请将以下医学术语从{source_lang}翻译成{target_lang}。只需要提供翻译结果，不要添加任何解释或其他内容。

术语: {term}

这是一个{domain}领域的医学术语。请确保翻译准确、专业。
"""
        
        # 调用Claude模型
        response = bedrock_runtime.invoke_model(
            modelId='anthropic.claude-3-sonnet-20240229-v1:0',
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 100,
                "temperature": 0.1,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })
        )
        
        # 解析响应
        response_body = json.loads(response['body'].read().decode('utf-8'))
        translation = response_body['content'][0]['text']
        
        # 清理翻译结果
        translation = translation.strip()
        
        # 如果翻译结果以"翻译:"开头，移除这个前缀
        prefixes = ["翻译:", "翻译：", "Translation:", "Translated term:"]
        for prefix in prefixes:
            if translation.startswith(prefix):
                translation = translation[len(prefix):].strip()
        
        return translation
    
    except Exception:
        return None


def _assess_translation_quality(source_sent: str, translated_sent: str, source_lang: str, target_lang: str, domain: str) -> Dict[str, Any]:
    """
    评估翻译质量
    
    Args:
        source_sent (str): 源句子
        translated_sent (str): 翻译句子
        source_lang (str): 源语言代码
        target_lang (str): 目标语言代码
        domain (str): 医学领域
        
    Returns:
        Dict[str, Any]: 评估结果
    """
    # 简单启发式评估
    assessment = {
        "confidence": 0.8,  # 默认置信度
        "issues": []
    }
    
    # 检查长度异常
    src_length = len(source_sent)
    tgt_length = len(translated_sent)
    
    if src_length > 0:
        length_ratio = tgt_length / src_length
        
        # 如果翻译比源文本短很多或长很多
        if length_ratio < 0.5:
            assessment["confidence"] -= 0.2
            assessment["issues"].append({
                "type": "length_issue",
                "description": "翻译可能不完整",
                "severity": "high"
            })
        elif length_ratio > 2.0:
            assessment["confidence"] -= 0.1
            assessment["issues"].append({
                "type": "length_issue",
                "description": "翻译可能包含冗余内容",
                "severity": "medium"
            })
    
    # 检查数字是否保持一致
    src_numbers = re.findall(r'\d+(?:\.\d+)?', source_sent)
    tgt_numbers = re.findall(r'\d+(?:\.\d+)?', translated_sent)
    
    if len(src_numbers) != len(tgt_numbers):
        assessment["confidence"] -= 0.15
        assessment["issues"].append({
            "type": "number_issue",
            "description": "数字数量不一致",
            "severity": "high",
            "source_numbers": src_numbers,
            "target_numbers": tgt_numbers
        })
    
    # 确保置信度在有效范围内
    assessment["confidence"] = max(0.0, min(1.0, assessment["confidence"]))
    
    return assessment


def _generate_alternative_translations(source_sent: str, source_lang: str, target_lang: str, domain: str) -> List[str]:
    """
    生成备选翻译
    
    Args:
        source_sent (str): 源句子
        source_lang (str): 源语言代码
        target_lang (str): 目标语言代码
        domain (str): 医学领域
        
    Returns:
        List[str]: 备选翻译列表
    """
    try:
        # 创建Bedrock客户端
        bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name='us-west-2'  # 使用适当的区域
        )
        
        # 构建提示词
        prompt = f"""请为以下{source_lang}医学文本提供3种不同的{target_lang}翻译版本。这是一篇关于{domain}领域的医学文本。
请确保翻译准确、专业，并保持医学术语的一致性。请以编号列表的形式提供这3种翻译版本。

源文本:
{source_sent}

请提供3种不同的翻译版本:
"""
        
        # 调用Claude模型
        response = bedrock_runtime.invoke_model(
            modelId='anthropic.claude-3-sonnet-20240229-v1:0',
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "temperature": 0.7,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })
        )
        
        # 解析响应
        response_body = json.loads(response['body'].read().decode('utf-8'))
        content = response_body['content'][0]['text']
        
        # 提取备选翻译
        alternatives = []
        for line in content.split('\n'):
            # 查找以数字开头的行
            match = re.match(r'^\s*(\d+)[\.、)]\s*(.+)$', line)
            if match:
                alternatives.append(match.group(2).strip())
        
        return alternatives[:3]  # 最多返回3个备选翻译
    
    except Exception:
        # 如果API调用失败，返回空列表
        return []


def _assess_quality_dimensions(source_text: str, translated_text: str, source_lang: str, target_lang: str, domain: str) -> Dict[str, float]:
    """
    评估翻译质量的各个维度
    
    Args:
        source_text (str): 源文本
        translated_text (str): 翻译文本
        source_lang (str): 源语言代码
        target_lang (str): 目标语言代码
        domain (str): 医学领域
        
    Returns:
        Dict[str, float]: 各维度的评分
    """
    # 初始化评分
    scores = {
        "grammar_correctness": 0.9,    # 语法正确性
        "style_consistency": 0.9,      # 风格一致性
        "completeness": 0.9,           # 完整性
        "readability": 0.9,            # 可读性
        "context_appropriateness": 0.9  # 上下文适当性
    }
    
    # 简单启发式评估
    # 完整性：基于文本长度比例
    src_length = len(source_text)
    tgt_length = len(translated_text)
    
    if src_length > 0:
        length_ratio = tgt_length / src_length
        
        # 如果翻译比源文本短很多或长很多
        if length_ratio < 0.5:
            scores["completeness"] = 0.5
        elif length_ratio < 0.7:
            scores["completeness"] = 0.7
        elif length_ratio > 2.0:
            scores["completeness"] = 0.6
        elif length_ratio > 1.5:
            scores["completeness"] = 0.8
    
    # 语法正确性：检查标点符号
    if target_lang == "en":
        # 英文标点检查
        if re.search(r'[，。；：？！]', translated_text):
            scores["grammar_correctness"] = 0.7
    elif target_lang == "zh":
        # 中文标点检查
        if re.search(r'[,.;:?!]', translated_text):
            scores["grammar_correctness"] = 0.8
    
    # 可读性：检查句子长度
    translated_sentences = _split_into_sentences(translated_text, target_lang)
    if translated_sentences:
        avg_sent_length = sum(len(s) for s in translated_sentences) / len(translated_sentences)
        
        if avg_sent_length > 100:
            scores["readability"] = 0.7
        elif avg_sent_length > 50:
            scores["readability"] = 0.8
    
    return scores


def _generate_improvement_suggestions(terminology_consistency: Dict[str, Any], 
                                     abbreviation_handling: Dict[str, Any], 
                                     uncertain_translations: Dict[str, Any],
                                     quality_dimensions: Dict[str, float]) -> List[str]:
    """
    生成改进建议
    
    Args:
        terminology_consistency (Dict[str, Any]): 术语一致性结果
        abbreviation_handling (Dict[str, Any]): 缩写处理结果
        uncertain_translations (Dict[str, Any]): 不确定翻译结果
        quality_dimensions (Dict[str, float]): 质量维度评分
        
    Returns:
        List[str]: 改进建议列表
    """
    suggestions = []
    
    # 术语一致性建议
    if terminology_consistency:
        consistency_score = terminology_consistency.get("consistency_score", 1.0)
        inconsistent_terms = terminology_consistency.get("inconsistent_terms", 0)
        
        if consistency_score < 0.8 and inconsistent_terms > 0:
            suggestions.append(f"提高术语一致性：发现{inconsistent_terms}个术语翻译不一致，建议使用术语表确保一致翻译")
    
    # 缩写处理建议
    if abbreviation_handling:
        abbreviation_score = abbreviation_handling.get("abbreviation_score", 1.0)
        handling_issues = abbreviation_handling.get("handling_issues", 0)
        
        if abbreviation_score < 0.8 and handling_issues > 0:
            suggestions.append(f"改进缩写处理：发现{handling_issues}个缩写处理问题，建议在首次出现时提供全称")
    
    # 不确定翻译建议
    if uncertain_translations:
        overall_confidence = uncertain_translations.get("overall_confidence", 1.0)
        uncertain_sentences = uncertain_translations.get("uncertain_sentences", 0)
        
        if overall_confidence < 0.8 and uncertain_sentences > 0:
            suggestions.append(f"提高翻译准确性：发现{uncertain_sentences}个可能存在问题的句子，建议进行人工审校")
    
    # 质量维度建议
    for dimension, score in quality_dimensions.items():
        if score < 0.8:
            if dimension == "grammar_correctness":
                suggestions.append("提高语法正确性：检查并修正语法错误，特别是标点符号使用")
            elif dimension == "style_consistency":
                suggestions.append("保持风格一致性：统一使用相同的表达方式和术语")
            elif dimension == "completeness":
                suggestions.append("确保翻译完整性：检查是否有遗漏或未翻译的内容")
            elif dimension == "readability":
                suggestions.append("提高可读性：避免过长句子，使用清晰简洁的表达")
            elif dimension == "context_appropriateness":
                suggestions.append("注意上下文适当性：确保翻译符合医学专业语境")
    
    # 如果没有具体建议，添加一个通用建议
    if not suggestions:
        suggestions.append("翻译质量良好，建议进行最后的人工审校以确保专业准确")
    
    return suggestions


def _generate_comparison_recommendation(overall_better: str, better_dimensions1: int, better_dimensions2: int, score_comparison: Dict[str, Any]) -> str:
    """
    生成翻译比较建议
    
    Args:
        overall_better (str): 总体更好的翻译
        better_dimensions1 (int): 第一个翻译更好的维度数
        better_dimensions2 (int): 第二个翻译更好的维度数
        score_comparison (Dict[str, Any]): 各维度得分比较
        
    Returns:
        str: 比较建议
    """
    if overall_better == "equal":
        return "两个翻译版本质量相近，建议结合两者优点进行整合"
    
    if overall_better == "translation1":
        recommendation = f"总体而言，翻译版本1质量更好，在{better_dimensions1}个维度上表现优于版本2"
        
        # 找出版本1的优势维度
        strengths = [dim for dim, comp in score_comparison.items() if comp["better_translation"] == "translation1"]
        if strengths:
            recommendation += f"，特别是在{', '.join(strengths)}方面"
        
        # 找出版本2的优势维度
        strengths2 = [dim for dim, comp in score_comparison.items() if comp["better_translation"] == "translation2"]
        if strengths2:
            recommendation += f"。但版本2在{', '.join(strengths2)}方面表现更好，建议参考这些方面的翻译"
        
        return recommendation
    else:
        recommendation = f"总体而言，翻译版本2质量更好，在{better_dimensions2}个维度上表现优于版本1"
        
        # 找出版本2的优势维度
        strengths = [dim for dim, comp in score_comparison.items() if comp["better_translation"] == "translation2"]
        if strengths:
            recommendation += f"，特别是在{', '.join(strengths)}方面"
        
        # 找出版本1的优势维度
        strengths1 = [dim for dim, comp in score_comparison.items() if comp["better_translation"] == "translation1"]
        if strengths1:
            recommendation += f"。但版本1在{', '.join(strengths1)}方面表现更好，建议参考这些方面的翻译"
        
        return recommendation


def _check_sentence_issues(source_sent: str, translated_sent: str, source_lang: str, target_lang: str, domain: str) -> List[Dict[str, Any]]:
    """
    检查句子翻译中的问题
    
    Args:
        source_sent (str): 源句子
        translated_sent (str): 翻译句子
        source_lang (str): 源语言代码
        target_lang (str): 目标语言代码
        domain (str): 医学领域
        
    Returns:
        List[Dict[str, Any]]: 问题列表
    """
    issues = []
    
    # 检查数字是否保持一致
    src_numbers = re.findall(r'\d+(?:\.\d+)?', source_sent)
    tgt_numbers = re.findall(r'\d+(?:\.\d+)?', translated_sent)
    
    if len(src_numbers) != len(tgt_numbers):
        issues.append({
            "type": "number_issue",
            "description": "数字数量不一致",
            "severity": "high",
            "source_numbers": src_numbers,
            "target_numbers": tgt_numbers
        })
    elif src_numbers and tgt_numbers:
        # 检查数字是否一一对应
        for src_num, tgt_num in zip(src_numbers, tgt_numbers):
            if src_num != tgt_num:
                issues.append({
                    "type": "number_value_issue",
                    "description": f"数字值不一致: {src_num} -> {tgt_num}",
                    "severity": "high",
                    "source_number": src_num,
                    "target_number": tgt_num
                })
    
    # 检查单位是否正确翻译
    common_units = {
        "mg": ["mg", "毫克"],
        "g": ["g", "克"],
        "kg": ["kg", "公斤"],
        "ml": ["ml", "毫升"],
        "l": ["l", "升"],
        "mmol": ["mmol", "毫摩尔"],
        "cm": ["cm", "厘米"],
        "mm": ["mm", "毫米"],
        "m": ["m", "米"]
    }
    
    for unit, translations in common_units.items():
        if re.search(r'\d+\s*' + re.escape(unit) + r'\b', source_sent):
            # 检查单位是否在翻译中正确出现
            unit_found = False
            for trans_unit in translations:
                if trans_unit in translated_sent:
                    unit_found = True
                    break
            
            if not unit_found:
                issues.append({
                    "type": "unit_issue",
                    "description": f"单位可能未正确翻译: {unit}",
                    "severity": "medium",
                    "unit": unit
                })
    
    return issues


def _generate_annotated_text(text: str, issues: List[Dict[str, Any]]) -> str:
    """
    生成带标注的文本
    
    Args:
        text (str): 原始文本
        issues (List[Dict[str, Any]]): 问题列表
        
    Returns:
        str: 带标注的文本
    """
    # 按句子索引组织问题
    issues_by_sentence = {}
    for issue in issues:
        if "sentence_index" in issue:
            idx = issue["sentence_index"]
            if idx not in issues_by_sentence:
                issues_by_sentence[idx] = []
            issues_by_sentence[idx].append(issue)
    
    # 分割文本为句子
    sentences = _split_into_sentences(text, "auto")
    
    # 为每个句子添加标注
    annotated_sentences = []
    for i, sentence in enumerate(sentences):
        if i in issues_by_sentence:
            # 添加句子
            annotated_sentences.append(sentence)
            
            # 添加问题标注
            for issue in issues_by_sentence[i]:
                issue_type = issue.get("type", "unknown")
                description = issue.get("description", "未知问题")
                severity = issue.get("severity", "medium")
                
                annotated_sentences.append(f"[问题: {issue_type}] {description} [严重程度: {severity}]")
        else:
            annotated_sentences.append(sentence)
    
    # 处理不是按句子组织的问题
    other_issues = [issue for issue in issues if "sentence_index" not in issue]
    if other_issues:
        annotated_sentences.append("\n其他问题:")
        for issue in other_issues:
            issue_type = issue.get("type", "unknown")
            description = issue.get("description", "未知问题")
            severity = issue.get("severity", "medium")
            
            if issue_type == "terminology_inconsistency":
                source_term = issue.get("source_term", "")
                target_term = issue.get("target_term", "")
                annotated_sentences.append(f"[术语不一致] 源术语: {source_term}, 目标术语: {target_term} [严重程度: {severity}]")
            elif issue_type == "abbreviation_issue":
                abbr = issue.get("abbreviation", "")
                expansion = issue.get("expansion", "")
                annotated_sentences.append(f"[缩写问题] 缩写: {abbr}, 全称: {expansion} [严重程度: {severity}]")
            else:
                annotated_sentences.append(f"[问题: {issue_type}] {description} [严重程度: {severity}]")
    
    return "\n".join(annotated_sentences)