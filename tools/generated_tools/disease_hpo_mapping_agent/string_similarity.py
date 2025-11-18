#!/usr/bin/env python3
"""
字符串相似度计算工具

提供多种算法计算字符串相似度，用于模糊匹配疾病名称
"""

import json
import re
import math
from typing import Dict, List, Any, Optional, Union, Tuple, Set
from collections import Counter
import logging
from strands import tool

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@tool
def calculate_levenshtein_similarity(string1: str, string2: str, case_sensitive: bool = False) -> str:
    """
    计算两个字符串的Levenshtein编辑距离相似度
    
    Args:
        string1 (str): 第一个字符串
        string2 (str): 第二个字符串
        case_sensitive (bool): 是否区分大小写，默认为False
    
    Returns:
        str: JSON格式的相似度计算结果，包含相似度分数（0-1之间，1表示完全相同）
    """
    try:
        if not case_sensitive:
            string1 = string1.lower()
            string2 = string2.lower()
        
        # 计算Levenshtein编辑距离
        distance = _levenshtein_distance(string1, string2)
        
        # 计算相似度
        max_len = max(len(string1), len(string2))
        if max_len == 0:
            similarity = 1.0  # 两个空字符串视为完全相同
        else:
            similarity = 1.0 - distance / max_len
        
        return json.dumps({
            "success": True,
            "string1": string1,
            "string2": string2,
            "algorithm": "levenshtein",
            "case_sensitive": case_sensitive,
            "distance": distance,
            "similarity": similarity
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"计算Levenshtein相似度时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"计算失败: {str(e)}",
            "string1": string1,
            "string2": string2
        }, ensure_ascii=False, indent=2)


@tool
def calculate_jaccard_similarity(string1: str, string2: str, case_sensitive: bool = False, ngram_size: int = 1) -> str:
    """
    计算两个字符串的Jaccard相似系数
    
    Args:
        string1 (str): 第一个字符串
        string2 (str): 第二个字符串
        case_sensitive (bool): 是否区分大小写，默认为False
        ngram_size (int): N-gram大小，默认为1（单个字符）
    
    Returns:
        str: JSON格式的相似度计算结果，包含相似度分数（0-1之间，1表示完全相同）
    """
    try:
        if not case_sensitive:
            string1 = string1.lower()
            string2 = string2.lower()
        
        # 生成N-gram集合
        set1 = set(_get_ngrams(string1, ngram_size))
        set2 = set(_get_ngrams(string2, ngram_size))
        
        # 计算交集和并集
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        # 计算Jaccard相似系数
        similarity = intersection / union if union > 0 else 1.0
        
        return json.dumps({
            "success": True,
            "string1": string1,
            "string2": string2,
            "algorithm": "jaccard",
            "case_sensitive": case_sensitive,
            "ngram_size": ngram_size,
            "intersection_size": intersection,
            "union_size": union,
            "similarity": similarity
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"计算Jaccard相似度时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"计算失败: {str(e)}",
            "string1": string1,
            "string2": string2
        }, ensure_ascii=False, indent=2)


@tool
def calculate_cosine_similarity(string1: str, string2: str, case_sensitive: bool = False, ngram_size: int = 1) -> str:
    """
    计算两个字符串的余弦相似度
    
    Args:
        string1 (str): 第一个字符串
        string2 (str): 第二个字符串
        case_sensitive (bool): 是否区分大小写，默认为False
        ngram_size (int): N-gram大小，默认为1（单个字符）
    
    Returns:
        str: JSON格式的相似度计算结果，包含相似度分数（0-1之间，1表示完全相同）
    """
    try:
        if not case_sensitive:
            string1 = string1.lower()
            string2 = string2.lower()
        
        # 生成N-gram并计算频率向量
        vec1 = Counter(_get_ngrams(string1, ngram_size))
        vec2 = Counter(_get_ngrams(string2, ngram_size))
        
        # 计算点积
        dot_product = sum(vec1[gram] * vec2[gram] for gram in set(vec1).intersection(set(vec2)))
        
        # 计算向量模长
        magnitude1 = math.sqrt(sum(count ** 2 for count in vec1.values()))
        magnitude2 = math.sqrt(sum(count ** 2 for count in vec2.values()))
        
        # 计算余弦相似度
        similarity = dot_product / (magnitude1 * magnitude2) if magnitude1 * magnitude2 > 0 else 1.0
        
        return json.dumps({
            "success": True,
            "string1": string1,
            "string2": string2,
            "algorithm": "cosine",
            "case_sensitive": case_sensitive,
            "ngram_size": ngram_size,
            "dot_product": dot_product,
            "magnitude1": magnitude1,
            "magnitude2": magnitude2,
            "similarity": similarity
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"计算余弦相似度时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"计算失败: {str(e)}",
            "string1": string1,
            "string2": string2
        }, ensure_ascii=False, indent=2)


@tool
def calculate_jaro_winkler_similarity(string1: str, string2: str, case_sensitive: bool = False, scaling_factor: float = 0.1) -> str:
    """
    计算两个字符串的Jaro-Winkler相似度
    
    Args:
        string1 (str): 第一个字符串
        string2 (str): 第二个字符串
        case_sensitive (bool): 是否区分大小写，默认为False
        scaling_factor (float): 缩放因子，默认为0.1，范围[0, 0.25]
    
    Returns:
        str: JSON格式的相似度计算结果，包含相似度分数（0-1之间，1表示完全相同）
    """
    try:
        if not case_sensitive:
            string1 = string1.lower()
            string2 = string2.lower()
        
        # 确保缩放因子在有效范围内
        scaling_factor = max(0.0, min(0.25, scaling_factor))
        
        # 计算Jaro相似度
        jaro_similarity = _jaro_similarity(string1, string2)
        
        # 计算共同前缀长度
        prefix_len = 0
        max_prefix_len = min(4, min(len(string1), len(string2)))
        for i in range(max_prefix_len):
            if string1[i] == string2[i]:
                prefix_len += 1
            else:
                break
        
        # 计算Jaro-Winkler相似度
        jaro_winkler_similarity = jaro_similarity + (prefix_len * scaling_factor * (1 - jaro_similarity))
        
        return json.dumps({
            "success": True,
            "string1": string1,
            "string2": string2,
            "algorithm": "jaro_winkler",
            "case_sensitive": case_sensitive,
            "scaling_factor": scaling_factor,
            "jaro_similarity": jaro_similarity,
            "common_prefix_length": prefix_len,
            "similarity": jaro_winkler_similarity
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"计算Jaro-Winkler相似度时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"计算失败: {str(e)}",
            "string1": string1,
            "string2": string2
        }, ensure_ascii=False, indent=2)


@tool
def calculate_multi_algorithm_similarity(string1: str, string2: str, case_sensitive: bool = False) -> str:
    """
    使用多种算法计算两个字符串的相似度并返回综合评分
    
    Args:
        string1 (str): 第一个字符串
        string2 (str): 第二个字符串
        case_sensitive (bool): 是否区分大小写，默认为False
    
    Returns:
        str: JSON格式的相似度计算结果，包含多种算法的相似度分数和综合评分
    """
    try:
        if not case_sensitive:
            string1 = string1.lower()
            string2 = string2.lower()
        
        # 计算各种相似度
        levenshtein_similarity = _levenshtein_similarity(string1, string2)
        jaccard_similarity = _jaccard_similarity(string1, string2)
        cosine_similarity = _cosine_similarity(string1, string2)
        jaro_winkler_similarity = _jaro_winkler_similarity(string1, string2)
        
        # 计算综合评分（加权平均）
        weights = {
            "levenshtein": 0.3,
            "jaccard": 0.2,
            "cosine": 0.2,
            "jaro_winkler": 0.3
        }
        
        combined_score = (
            weights["levenshtein"] * levenshtein_similarity +
            weights["jaccard"] * jaccard_similarity +
            weights["cosine"] * cosine_similarity +
            weights["jaro_winkler"] * jaro_winkler_similarity
        )
        
        return json.dumps({
            "success": True,
            "string1": string1,
            "string2": string2,
            "case_sensitive": case_sensitive,
            "algorithms": {
                "levenshtein": {
                    "similarity": levenshtein_similarity,
                    "weight": weights["levenshtein"]
                },
                "jaccard": {
                    "similarity": jaccard_similarity,
                    "weight": weights["jaccard"]
                },
                "cosine": {
                    "similarity": cosine_similarity,
                    "weight": weights["cosine"]
                },
                "jaro_winkler": {
                    "similarity": jaro_winkler_similarity,
                    "weight": weights["jaro_winkler"]
                }
            },
            "combined_score": combined_score
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"计算多算法相似度时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"计算失败: {str(e)}",
            "string1": string1,
            "string2": string2
        }, ensure_ascii=False, indent=2)


@tool
def find_best_match(query: str, candidates: List[str], algorithm: str = "combined", case_sensitive: bool = False, threshold: float = 0.7) -> str:
    """
    在候选字符串列表中找到与查询字符串最相似的匹配项
    
    Args:
        query (str): 查询字符串
        candidates (List[str]): 候选字符串列表
        algorithm (str): 相似度算法，可选值：'levenshtein'、'jaccard'、'cosine'、'jaro_winkler'或'combined'
        case_sensitive (bool): 是否区分大小写，默认为False
        threshold (float): 相似度阈值，默认为0.7，低于此值的匹配将被过滤
    
    Returns:
        str: JSON格式的匹配结果，包含最佳匹配和相似度分数
    """
    try:
        if not candidates:
            return json.dumps({
                "success": False,
                "error": "候选字符串列表为空",
                "query": query
            }, ensure_ascii=False, indent=2)
        
        if not case_sensitive:
            query = query.lower()
            candidates = [c.lower() for c in candidates]
        
        # 计算每个候选项的相似度
        similarities = []
        
        for candidate in candidates:
            if algorithm == "levenshtein":
                similarity = _levenshtein_similarity(query, candidate)
            elif algorithm == "jaccard":
                similarity = _jaccard_similarity(query, candidate)
            elif algorithm == "cosine":
                similarity = _cosine_similarity(query, candidate)
            elif algorithm == "jaro_winkler":
                similarity = _jaro_winkler_similarity(query, candidate)
            elif algorithm == "combined":
                # 使用多算法综合评分
                levenshtein_sim = _levenshtein_similarity(query, candidate)
                jaccard_sim = _jaccard_similarity(query, candidate)
                cosine_sim = _cosine_similarity(query, candidate)
                jaro_winkler_sim = _jaro_winkler_similarity(query, candidate)
                
                weights = {
                    "levenshtein": 0.3,
                    "jaccard": 0.2,
                    "cosine": 0.2,
                    "jaro_winkler": 0.3
                }
                
                similarity = (
                    weights["levenshtein"] * levenshtein_sim +
                    weights["jaccard"] * jaccard_sim +
                    weights["cosine"] * cosine_sim +
                    weights["jaro_winkler"] * jaro_winkler_sim
                )
            else:
                raise ValueError(f"不支持的算法: {algorithm}")
            
            similarities.append({
                "candidate": candidate,
                "similarity": similarity
            })
        
        # 按相似度降序排序
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        
        # 过滤低于阈值的匹配
        filtered_similarities = [s for s in similarities if s["similarity"] >= threshold]
        
        # 构建结果
        result = {
            "success": True,
            "query": query,
            "algorithm": algorithm,
            "case_sensitive": case_sensitive,
            "threshold": threshold,
            "matches_count": len(filtered_similarities),
            "total_candidates": len(candidates)
        }
        
        if filtered_similarities:
            result["best_match"] = filtered_similarities[0]["candidate"]
            result["best_match_similarity"] = filtered_similarities[0]["similarity"]
            result["all_matches"] = filtered_similarities
        else:
            result["best_match"] = None
            result["best_match_similarity"] = 0.0
            result["all_matches"] = []
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"查找最佳匹配时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"查找失败: {str(e)}",
            "query": query
        }, ensure_ascii=False, indent=2)


@tool
def calculate_token_based_similarity(string1: str, string2: str, case_sensitive: bool = False, tokenizer: str = "word") -> str:
    """
    基于分词的字符串相似度计算
    
    Args:
        string1 (str): 第一个字符串
        string2 (str): 第二个字符串
        case_sensitive (bool): 是否区分大小写，默认为False
        tokenizer (str): 分词方式，可选值：'word'（按单词分词）、'char'（按字符分词）
    
    Returns:
        str: JSON格式的相似度计算结果，包含相似度分数
    """
    try:
        if not case_sensitive:
            string1 = string1.lower()
            string2 = string2.lower()
        
        # 分词
        if tokenizer == "word":
            tokens1 = _tokenize_words(string1)
            tokens2 = _tokenize_words(string2)
        elif tokenizer == "char":
            tokens1 = list(string1)
            tokens2 = list(string2)
        else:
            raise ValueError(f"不支持的分词方式: {tokenizer}")
        
        # 计算Jaccard相似度
        set1 = set(tokens1)
        set2 = set(tokens2)
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        jaccard_similarity = intersection / union if union > 0 else 1.0
        
        # 计算余弦相似度
        vec1 = Counter(tokens1)
        vec2 = Counter(tokens2)
        
        dot_product = sum(vec1[token] * vec2[token] for token in set(vec1).intersection(set(vec2)))
        
        magnitude1 = math.sqrt(sum(count ** 2 for count in vec1.values()))
        magnitude2 = math.sqrt(sum(count ** 2 for count in vec2.values()))
        
        cosine_similarity = dot_product / (magnitude1 * magnitude2) if magnitude1 * magnitude2 > 0 else 1.0
        
        # 计算Dice系数
        dice_coefficient = (2 * intersection) / (len(set1) + len(set2)) if (len(set1) + len(set2)) > 0 else 1.0
        
        # 计算综合评分
        combined_score = (jaccard_similarity + cosine_similarity + dice_coefficient) / 3
        
        return json.dumps({
            "success": True,
            "string1": string1,
            "string2": string2,
            "tokenizer": tokenizer,
            "case_sensitive": case_sensitive,
            "token_count1": len(tokens1),
            "token_count2": len(tokens2),
            "unique_tokens1": len(set1),
            "unique_tokens2": len(set2),
            "common_tokens": intersection,
            "jaccard_similarity": jaccard_similarity,
            "cosine_similarity": cosine_similarity,
            "dice_coefficient": dice_coefficient,
            "combined_score": combined_score
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"计算基于分词的相似度时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"计算失败: {str(e)}",
            "string1": string1,
            "string2": string2
        }, ensure_ascii=False, indent=2)


# 辅助函数

def _levenshtein_distance(s1: str, s2: str) -> int:
    """计算Levenshtein编辑距离"""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def _levenshtein_similarity(s1: str, s2: str) -> float:
    """计算基于Levenshtein距离的相似度"""
    if not s1 and not s2:
        return 1.0
    
    distance = _levenshtein_distance(s1, s2)
    max_len = max(len(s1), len(s2))
    
    return 1.0 - (distance / max_len) if max_len > 0 else 1.0


def _get_ngrams(text: str, n: int) -> List[str]:
    """生成文本的N-gram"""
    return [text[i:i+n] for i in range(len(text) - n + 1)] if len(text) >= n else [text]


def _jaccard_similarity(s1: str, s2: str) -> float:
    """计算Jaccard相似系数"""
    if not s1 and not s2:
        return 1.0
    
    set1 = set(s1)
    set2 = set(s2)
    
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    
    return intersection / union if union > 0 else 1.0


def _cosine_similarity(s1: str, s2: str) -> float:
    """计算余弦相似度"""
    if not s1 and not s2:
        return 1.0
    
    vec1 = Counter(s1)
    vec2 = Counter(s2)
    
    dot_product = sum(vec1[char] * vec2[char] for char in set(vec1).intersection(set(vec2)))
    
    magnitude1 = math.sqrt(sum(count ** 2 for count in vec1.values()))
    magnitude2 = math.sqrt(sum(count ** 2 for count in vec2.values()))
    
    return dot_product / (magnitude1 * magnitude2) if magnitude1 * magnitude2 > 0 else 1.0


def _jaro_similarity(s1: str, s2: str) -> float:
    """计算Jaro相似度"""
    if not s1 and not s2:
        return 1.0
    
    if not s1 or not s2:
        return 0.0
    
    # 匹配窗口大小
    match_distance = max(len(s1), len(s2)) // 2 - 1
    match_distance = max(0, match_distance)
    
    # 匹配字符
    s1_matches = [False] * len(s1)
    s2_matches = [False] * len(s2)
    
    matches = 0
    for i in range(len(s1)):
        start = max(0, i - match_distance)
        end = min(i + match_distance + 1, len(s2))
        
        for j in range(start, end):
            if not s2_matches[j] and s1[i] == s2[j]:
                s1_matches[i] = True
                s2_matches[j] = True
                matches += 1
                break
    
    if matches == 0:
        return 0.0
    
    # 计算转置
    transpositions = 0
    j = 0
    for i in range(len(s1)):
        if s1_matches[i]:
            while not s2_matches[j]:
                j += 1
            if s1[i] != s2[j]:
                transpositions += 1
            j += 1
    
    transpositions = transpositions // 2
    
    # 计算Jaro相似度
    return (
        matches / len(s1) +
        matches / len(s2) +
        (matches - transpositions) / matches
    ) / 3.0


def _jaro_winkler_similarity(s1: str, s2: str, scaling_factor: float = 0.1) -> float:
    """计算Jaro-Winkler相似度"""
    jaro_sim = _jaro_similarity(s1, s2)
    
    # 计算共同前缀长度
    prefix_len = 0
    max_prefix_len = min(4, min(len(s1), len(s2)))
    for i in range(max_prefix_len):
        if s1[i] == s2[i]:
            prefix_len += 1
        else:
            break
    
    # 计算Jaro-Winkler相似度
    return jaro_sim + (prefix_len * scaling_factor * (1 - jaro_sim))


def _tokenize_words(text: str) -> List[str]:
    """将文本分词为单词"""
    # 简单的分词实现，实际应用中可能需要更复杂的分词器
    return re.findall(r'\b\w+\b', text)