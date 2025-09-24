#!/usr/bin/env python3
"""
医学术语标准化工具

提供医学术语标准化功能，将非正式或不完整的疾病描述标准化为正式疾病名称
"""

import json
import re
import os
import time
import requests
from typing import Dict, List, Any, Optional, Union, Tuple
import logging
from pathlib import Path
from strands import tool

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 缓存目录
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache", "disease_hpo_mapper")
os.makedirs(CACHE_DIR, exist_ok=True)

# 医学术语API端点
UMLS_API_URL = "https://uts-ws.nlm.nih.gov/rest/search/current"
MESH_API_URL = "https://id.nlm.nih.gov/mesh/lookup/descriptor"

# 医学术语字典文件路径
MEDICAL_DICT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "medical_dictionary.json")

# 创建数据目录
os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"), exist_ok=True)

# 加载医学术语字典
def _load_medical_dictionary() -> Dict[str, Dict[str, str]]:
    """加载医学术语字典"""
    if os.path.exists(MEDICAL_DICT_PATH):
        try:
            with open(MEDICAL_DICT_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"加载医学术语字典失败: {str(e)}")
    
    # 如果字典不存在或加载失败，创建一个空字典
    return {"en": {}, "zh": {}}

# 保存医学术语字典
def _save_medical_dictionary(dictionary: Dict[str, Dict[str, str]]) -> None:
    """保存医学术语字典"""
    try:
        with open(MEDICAL_DICT_PATH, 'w', encoding='utf-8') as f:
            json.dump(dictionary, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"保存医学术语字典失败: {str(e)}")

# 初始化医学术语字典
MEDICAL_DICTIONARY = _load_medical_dictionary()


@tool
def standardize_medical_term(term: str, language: str = "auto", include_details: bool = False) -> str:
    """
    将医学术语标准化为正式医学名称
    
    Args:
        term (str): 需要标准化的医学术语或疾病描述
        language (str): 输入术语的语言，可选值：'en'（英文）、'zh'（中文）或'auto'（自动检测）
        include_details (bool): 是否包含详细信息，如定义、同义词等
    
    Returns:
        str: JSON格式的标准化结果，包含标准化的医学术语
    """
    try:
        # 检查缓存
        cache_key = f"standardize_{term}_{language}_{include_details}"
        cache_result = _get_from_cache(cache_key)
        if cache_result:
            return cache_result
        
        # 自动检测语言
        if language == "auto":
            language = _detect_language(term)
        
        # 预处理术语
        cleaned_term = _preprocess_text(term)
        
        # 从字典中查找标准化术语
        standardized_term = _lookup_in_dictionary(cleaned_term, language)
        
        if standardized_term:
            # 如果在字典中找到了标准化术语
            result = {
                "success": True,
                "original_term": term,
                "standardized_term": standardized_term,
                "language": language,
                "source": "dictionary"
            }
            
            if include_details:
                details = _get_term_details(standardized_term["standard_name"], language)
                result["details"] = details
            
            result_json = json.dumps(result, ensure_ascii=False, indent=2)
            _save_to_cache(cache_key, result_json)
            return result_json
        
        # 如果字典中没有找到，尝试API查询
        api_result = _query_medical_api(cleaned_term, language)
        
        if api_result:
            # 如果API查询成功
            # 更新字典
            if language == "en":
                MEDICAL_DICTIONARY["en"][cleaned_term.lower()] = {
                    "standard_name": api_result["standard_name"],
                    "standard_code": api_result.get("standard_code", "")
                }
            else:
                MEDICAL_DICTIONARY["zh"][cleaned_term] = {
                    "standard_name": api_result["standard_name"],
                    "standard_code": api_result.get("standard_code", "")
                }
            
            _save_medical_dictionary(MEDICAL_DICTIONARY)
            
            result = {
                "success": True,
                "original_term": term,
                "standardized_term": {
                    "standard_name": api_result["standard_name"],
                    "standard_code": api_result.get("standard_code", "")
                },
                "language": language,
                "source": "api"
            }
            
            if include_details:
                details = _get_term_details(api_result["standard_name"], language)
                result["details"] = details
            
            result_json = json.dumps(result, ensure_ascii=False, indent=2)
            _save_to_cache(cache_key, result_json)
            return result_json
        
        # 如果API查询也失败，尝试模糊匹配
        fuzzy_match = _fuzzy_match_term(cleaned_term, language)
        
        if fuzzy_match:
            result = {
                "success": True,
                "original_term": term,
                "standardized_term": {
                    "standard_name": fuzzy_match["standard_name"],
                    "standard_code": fuzzy_match.get("standard_code", ""),
                    "confidence": fuzzy_match["confidence"]
                },
                "language": language,
                "source": "fuzzy_match"
            }
            
            if include_details:
                details = _get_term_details(fuzzy_match["standard_name"], language)
                result["details"] = details
            
            result_json = json.dumps(result, ensure_ascii=False, indent=2)
            _save_to_cache(cache_key, result_json)
            return result_json
        
        # 如果所有方法都失败
        return json.dumps({
            "success": False,
            "original_term": term,
            "language": language,
            "error": "无法标准化该医学术语",
            "suggestions": _get_suggestions(cleaned_term, language)
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"标准化医学术语时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"标准化失败: {str(e)}",
            "original_term": term
        }, ensure_ascii=False, indent=2)


@tool
def batch_standardize_terms(terms: List[str], language: str = "auto", include_details: bool = False) -> str:
    """
    批量标准化医学术语
    
    Args:
        terms (List[str]): 需要标准化的医学术语列表
        language (str): 输入术语的语言，可选值：'en'（英文）、'zh'（中文）或'auto'（自动检测）
        include_details (bool): 是否包含详细信息，如定义、同义词等
    
    Returns:
        str: JSON格式的批量标准化结果
    """
    try:
        results = []
        
        for term in terms:
            # 对每个术语进行标准化
            result = _standardize_medical_term_internal(term, language, include_details)
            results.append(result)
        
        return json.dumps({
            "success": True,
            "count": len(results),
            "results": results
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"批量标准化医学术语时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"批量标准化失败: {str(e)}",
            "terms": terms
        }, ensure_ascii=False, indent=2)


@tool
def extract_medical_terms(text: str, language: str = "auto") -> str:
    """
    从文本中提取医学术语
    
    Args:
        text (str): 输入文本
        language (str): 文本语言，可选值：'en'（英文）、'zh'（中文）或'auto'（自动检测）
    
    Returns:
        str: JSON格式的提取结果，包含提取的医学术语列表
    """
    try:
        # 检查缓存
        cache_key = f"extract_{text[:50]}_{language}"
        cache_result = _get_from_cache(cache_key)
        if cache_result:
            return cache_result
        
        # 自动检测语言
        if language == "auto":
            language = _detect_language(text)
        
        # 预处理文本
        cleaned_text = _preprocess_text(text)
        
        # 提取医学术语
        terms = []
        
        if language == "zh":
            # 中文医学术语提取
            terms = _extract_chinese_medical_terms(cleaned_text)
        else:
            # 英文医学术语提取
            terms = _extract_english_medical_terms(cleaned_text)
        
        # 标准化提取的术语
        standardized_terms = []
        for term in terms:
            try:
                result = _standardize_medical_term_internal(term, language, False)
                if result.get("success"):
                    standardized_terms.append({
                        "original_term": term,
                        "standardized_term": result.get("standardized_term", {}).get("standard_name", term),
                        "confidence": result.get("standardized_term", {}).get("confidence", 1.0) if "confidence" in result.get("standardized_term", {}) else 1.0,
                        "source": result.get("source", "unknown")
                    })
                else:
                    standardized_terms.append({
                        "original_term": term,
                        "standardized_term": term,
                        "confidence": 0.5,
                        "source": "original"
                    })
            except Exception as e:
                logger.warning(f"标准化术语 '{term}' 时出错: {str(e)}")
                standardized_terms.append({
                    "original_term": term,
                    "standardized_term": term,
                    "confidence": 0.5,
                    "source": "original"
                })
        
        # 按置信度排序
        standardized_terms.sort(key=lambda x: x["confidence"], reverse=True)
        
        result = {
            "success": True,
            "language": language,
            "original_text": text,
            "extracted_terms_count": len(terms),
            "extracted_terms": terms,
            "standardized_terms": standardized_terms
        }
        
        result_json = json.dumps(result, ensure_ascii=False, indent=2)
        _save_to_cache(cache_key, result_json)
        return result_json
        
    except Exception as e:
        logger.error(f"提取医学术语时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"提取失败: {str(e)}",
            "text": text[:100] + "..." if len(text) > 100 else text
        }, ensure_ascii=False, indent=2)


@tool
def add_to_medical_dictionary(term: str, standard_name: str, language: str, standard_code: str = "") -> str:
    """
    将术语添加到医学术语字典
    
    Args:
        term (str): 原始术语
        standard_name (str): 标准化名称
        language (str): 语言，可选值：'en'（英文）或'zh'（中文）
        standard_code (str): 标准代码（可选）
    
    Returns:
        str: JSON格式的操作结果
    """
    try:
        if language not in ["en", "zh"]:
            return json.dumps({
                "success": False,
                "error": "不支持的语言，只支持'en'或'zh'"
            }, ensure_ascii=False, indent=2)
        
        # 预处理术语
        cleaned_term = _preprocess_text(term)
        
        # 添加到字典
        if language == "en":
            MEDICAL_DICTIONARY["en"][cleaned_term.lower()] = {
                "standard_name": standard_name,
                "standard_code": standard_code
            }
        else:
            MEDICAL_DICTIONARY["zh"][cleaned_term] = {
                "standard_name": standard_name,
                "standard_code": standard_code
            }
        
        # 保存字典
        _save_medical_dictionary(MEDICAL_DICTIONARY)
        
        return json.dumps({
            "success": True,
            "message": f"已将'{term}'添加到医学术语字典",
            "term": term,
            "standard_name": standard_name,
            "language": language,
            "standard_code": standard_code
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"添加术语到字典时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"添加失败: {str(e)}",
            "term": term
        }, ensure_ascii=False, indent=2)


@tool
def manage_medical_dictionary(action: str, language: str = None) -> str:
    """
    管理医学术语字典
    
    Args:
        action (str): 操作类型，可选值：'list'（列出字典）、'count'（统计字典条目数）、'clear'（清空字典）
        language (str): 语言，可选值：'en'（英文）、'zh'（中文）或None（所有语言）
    
    Returns:
        str: JSON格式的操作结果
    """
    try:
        if action == "list":
            # 列出字典内容
            if language:
                if language not in ["en", "zh"]:
                    return json.dumps({
                        "success": False,
                        "error": "不支持的语言，只支持'en'或'zh'"
                    }, ensure_ascii=False, indent=2)
                
                return json.dumps({
                    "success": True,
                    "language": language,
                    "count": len(MEDICAL_DICTIONARY[language]),
                    "dictionary": MEDICAL_DICTIONARY[language]
                }, ensure_ascii=False, indent=2)
            else:
                return json.dumps({
                    "success": True,
                    "en_count": len(MEDICAL_DICTIONARY["en"]),
                    "zh_count": len(MEDICAL_DICTIONARY["zh"]),
                    "dictionary": MEDICAL_DICTIONARY
                }, ensure_ascii=False, indent=2)
                
        elif action == "count":
            # 统计字典条目数
            if language:
                if language not in ["en", "zh"]:
                    return json.dumps({
                        "success": False,
                        "error": "不支持的语言，只支持'en'或'zh'"
                    }, ensure_ascii=False, indent=2)
                
                return json.dumps({
                    "success": True,
                    "language": language,
                    "count": len(MEDICAL_DICTIONARY[language])
                }, ensure_ascii=False, indent=2)
            else:
                return json.dumps({
                    "success": True,
                    "en_count": len(MEDICAL_DICTIONARY["en"]),
                    "zh_count": len(MEDICAL_DICTIONARY["zh"]),
                    "total_count": len(MEDICAL_DICTIONARY["en"]) + len(MEDICAL_DICTIONARY["zh"])
                }, ensure_ascii=False, indent=2)
                
        elif action == "clear":
            # 清空字典
            if language:
                if language not in ["en", "zh"]:
                    return json.dumps({
                        "success": False,
                        "error": "不支持的语言，只支持'en'或'zh'"
                    }, ensure_ascii=False, indent=2)
                
                count = len(MEDICAL_DICTIONARY[language])
                MEDICAL_DICTIONARY[language] = {}
                _save_medical_dictionary(MEDICAL_DICTIONARY)
                
                return json.dumps({
                    "success": True,
                    "language": language,
                    "cleared_count": count,
                    "message": f"已清空{language}语言的医学术语字典"
                }, ensure_ascii=False, indent=2)
            else:
                en_count = len(MEDICAL_DICTIONARY["en"])
                zh_count = len(MEDICAL_DICTIONARY["zh"])
                MEDICAL_DICTIONARY["en"] = {}
                MEDICAL_DICTIONARY["zh"] = {}
                _save_medical_dictionary(MEDICAL_DICTIONARY)
                
                return json.dumps({
                    "success": True,
                    "en_cleared_count": en_count,
                    "zh_cleared_count": zh_count,
                    "total_cleared_count": en_count + zh_count,
                    "message": "已清空所有语言的医学术语字典"
                }, ensure_ascii=False, indent=2)
        else:
            return json.dumps({
                "success": False,
                "error": f"不支持的操作: {action}，只支持'list'、'count'或'clear'"
            }, ensure_ascii=False, indent=2)
            
    except Exception as e:
        logger.error(f"管理医学术语字典时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"操作失败: {str(e)}",
            "action": action
        }, ensure_ascii=False, indent=2)


# 辅助函数

def _standardize_medical_term_internal(term: str, language: str = "auto", include_details: bool = False) -> Dict[str, Any]:
    """
    内部函数：将医学术语标准化为正式医学名称（返回字典而不是JSON字符串）
    
    Args:
        term (str): 需要标准化的医学术语或疾病描述
        language (str): 输入术语的语言，可选值：'en'（英文）、'zh'（中文）或'auto'（自动检测）
        include_details (bool): 是否包含详细信息，如定义、同义词等
    
    Returns:
        Dict[str, Any]: 标准化结果字典
    """
    try:
        # 检查缓存
        cache_key = f"standardize_{term}_{language}_{include_details}"
        cache_result = _get_from_cache(cache_key)
        if cache_result:
            return json.loads(cache_result)
        
        # 自动检测语言
        if language == "auto":
            language = _detect_language(term)
        
        # 预处理术语
        cleaned_term = _preprocess_text(term)
        
        # 从字典中查找标准化术语
        standardized_term = _lookup_in_dictionary(cleaned_term, language)
        
        if standardized_term:
            # 如果在字典中找到了标准化术语
            result = {
                "success": True,
                "original_term": term,
                "standardized_term": standardized_term,
                "language": language,
                "source": "dictionary"
            }
            
            if include_details:
                details = _get_term_details(standardized_term["standard_name"], language)
                result["details"] = details
            
            result_json = json.dumps(result, ensure_ascii=False, indent=2)
            _save_to_cache(cache_key, result_json)
            return result
        
        # 如果字典中没有找到，尝试API查询
        api_result = _query_medical_api(cleaned_term, language)
        
        if api_result:
            # 如果API查询成功
            # 更新字典
            if language == "en":
                MEDICAL_DICTIONARY["en"][cleaned_term.lower()] = {
                    "standard_name": api_result["standard_name"],
                    "standard_code": api_result.get("standard_code", "")
                }
            else:
                MEDICAL_DICTIONARY["zh"][cleaned_term] = {
                    "standard_name": api_result["standard_name"],
                    "standard_code": api_result.get("standard_code", "")
                }
            
            _save_medical_dictionary(MEDICAL_DICTIONARY)
            
            result = {
                "success": True,
                "original_term": term,
                "standardized_term": {
                    "standard_name": api_result["standard_name"],
                    "standard_code": api_result.get("standard_code", "")
                },
                "language": language,
                "source": "api"
            }
            
            if include_details:
                details = _get_term_details(api_result["standard_name"], language)
                result["details"] = details
            
            result_json = json.dumps(result, ensure_ascii=False, indent=2)
            _save_to_cache(cache_key, result_json)
            return result
        
        # 如果API查询也失败，尝试模糊匹配
        fuzzy_match = _fuzzy_match_term(cleaned_term, language)
        
        if fuzzy_match:
            result = {
                "success": True,
                "original_term": term,
                "standardized_term": {
                    "standard_name": fuzzy_match["standard_name"],
                    "standard_code": fuzzy_match.get("standard_code", ""),
                    "confidence": fuzzy_match["confidence"]
                },
                "language": language,
                "source": "fuzzy_match"
            }
            
            if include_details:
                details = _get_term_details(fuzzy_match["standard_name"], language)
                result["details"] = details
            
            result_json = json.dumps(result, ensure_ascii=False, indent=2)
            _save_to_cache(cache_key, result_json)
            return result
        
        # 如果所有方法都失败
        return {
            "success": False,
            "original_term": term,
            "language": language,
            "error": "无法标准化该医学术语",
            "suggestions": _get_suggestions(cleaned_term, language)
        }
        
    except Exception as e:
        logger.error(f"标准化医学术语时出错: {str(e)}")
        return {
            "success": False,
            "error": f"标准化失败: {str(e)}",
            "original_term": term
        }


def _get_from_cache(key: str) -> Optional[str]:
    """从缓存中获取数据"""
    cache_path = os.path.join(CACHE_DIR, f"{key}.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # 验证JSON格式
                json.loads(content)
                return content
        except Exception as e:
            logger.warning(f"读取缓存失败: {str(e)}")
    return None


def _save_to_cache(key: str, content: str) -> None:
    """保存数据到缓存"""
    try:
        cache_path = os.path.join(CACHE_DIR, f"{key}.json")
        with open(cache_path, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        logger.warning(f"保存缓存失败: {str(e)}")


def _detect_language(text: str) -> str:
    """检测文本语言"""
    # 简单的语言检测逻辑
    chinese_pattern = re.compile(r'[\u4e00-\u9fff]')
    if chinese_pattern.search(text):
        return "zh"
    return "en"


def _preprocess_text(text: str) -> str:
    """预处理文本"""
    # 移除多余空格
    text = re.sub(r'\s+', ' ', text)
    # 移除标点符号
    text = re.sub(r'[^\w\s]', ' ', text)
    # 规范化空白
    text = ' '.join(text.split())
    return text


def _lookup_in_dictionary(term: str, language: str) -> Optional[Dict[str, str]]:
    """在字典中查找标准化术语"""
    if language == "en":
        return MEDICAL_DICTIONARY["en"].get(term.lower())
    else:
        return MEDICAL_DICTIONARY["zh"].get(term)


def _query_medical_api(term: str, language: str) -> Optional[Dict[str, str]]:
    """查询医学术语API"""
    try:
        # 这里应该使用实际的医学术语API
        # 此处为简化实现，实际应用中应使用专业的医学术语API
        
        # 模拟API查询
        # 在实际应用中，应该替换为真实的API调用
        
        # 英文常见疾病映射
        en_disease_map = {
            "diabetes": {"standard_name": "Diabetes Mellitus", "standard_code": "UMLS:C0011849"},
            "hypertension": {"standard_name": "Hypertension", "standard_code": "UMLS:C0020538"},
            "heart disease": {"standard_name": "Heart Disease", "standard_code": "UMLS:C0018799"},
            "cancer": {"standard_name": "Neoplasms", "standard_code": "UMLS:C0027651"},
            "asthma": {"standard_name": "Asthma", "standard_code": "UMLS:C0004096"},
            "alzheimer": {"standard_name": "Alzheimer's Disease", "standard_code": "UMLS:C0002395"},
            "parkinson": {"standard_name": "Parkinson Disease", "standard_code": "UMLS:C0030567"},
            "stroke": {"standard_name": "Cerebrovascular Accident", "standard_code": "UMLS:C0038454"},
            "pneumonia": {"standard_name": "Pneumonia", "standard_code": "UMLS:C0032285"},
            "flu": {"standard_name": "Influenza", "standard_code": "UMLS:C0021400"}
        }
        
        # 中文常见疾病映射
        zh_disease_map = {
            "糖尿病": {"standard_name": "糖尿病", "standard_code": "UMLS:C0011849"},
            "高血压": {"standard_name": "高血压", "standard_code": "UMLS:C0020538"},
            "心脏病": {"standard_name": "心脏病", "standard_code": "UMLS:C0018799"},
            "癌症": {"standard_name": "肿瘤", "standard_code": "UMLS:C0027651"},
            "哮喘": {"standard_name": "哮喘", "standard_code": "UMLS:C0004096"},
            "阿尔茨海默": {"standard_name": "阿尔茨海默病", "standard_code": "UMLS:C0002395"},
            "帕金森": {"standard_name": "帕金森病", "standard_code": "UMLS:C0030567"},
            "中风": {"standard_name": "脑卒中", "standard_code": "UMLS:C0038454"},
            "肺炎": {"standard_name": "肺炎", "standard_code": "UMLS:C0032285"},
            "流感": {"standard_name": "流行性感冒", "standard_code": "UMLS:C0021400"}
        }
        
        # 根据语言选择疾病映射
        disease_map = en_disease_map if language == "en" else zh_disease_map
        
        # 精确匹配
        if term.lower() in [k.lower() for k in disease_map.keys()]:
            for k, v in disease_map.items():
                if k.lower() == term.lower():
                    return v
        
        # 部分匹配
        for k, v in disease_map.items():
            if term.lower() in k.lower() or k.lower() in term.lower():
                return v
        
        return None
        
    except Exception as e:
        logger.warning(f"查询医学术语API时出错: {str(e)}")
        return None


def _get_term_details(term: str, language: str) -> Dict[str, Any]:
    """获取术语的详细信息"""
    try:
        # 这里应该查询专业的医学术语数据库
        # 此处为简化实现，实际应用中应使用专业的医学术语数据库
        
        # 英文疾病详情
        en_details = {
            "Diabetes Mellitus": {
                "definition": "A metabolic disorder characterized by high blood sugar levels over a prolonged period.",
                "synonyms": ["Diabetes", "DM", "Type 1 Diabetes", "Type 2 Diabetes"],
                "category": "Endocrine disorders"
            },
            "Hypertension": {
                "definition": "A long-term medical condition in which the blood pressure in the arteries is persistently elevated.",
                "synonyms": ["High blood pressure", "HTN", "HT"],
                "category": "Cardiovascular disorders"
            },
            "Heart Disease": {
                "definition": "A class of diseases that involve the heart or blood vessels.",
                "synonyms": ["Cardiovascular disease", "Coronary artery disease", "Coronary heart disease"],
                "category": "Cardiovascular disorders"
            },
            "Neoplasms": {
                "definition": "An abnormal growth of tissue which may be benign or malignant.",
                "synonyms": ["Cancer", "Tumor", "Malignancy"],
                "category": "Oncology"
            },
            "Asthma": {
                "definition": "A common long-term inflammatory disease of the airways of the lungs.",
                "synonyms": ["Bronchial asthma", "Reactive airway disease"],
                "category": "Respiratory disorders"
            },
            "Alzheimer's Disease": {
                "definition": "A chronic neurodegenerative disease that usually starts slowly and worsens over time.",
                "synonyms": ["Alzheimer disease", "Senile dementia"],
                "category": "Neurological disorders"
            },
            "Parkinson Disease": {
                "definition": "A long-term degenerative disorder of the central nervous system that mainly affects the motor system.",
                "synonyms": ["Parkinson's disease", "PD", "Parkinsonism"],
                "category": "Neurological disorders"
            },
            "Cerebrovascular Accident": {
                "definition": "The sudden death of brain cells due to lack of oxygen, caused by blockage of blood flow or rupture of an artery to the brain.",
                "synonyms": ["Stroke", "Brain attack", "CVA"],
                "category": "Neurological disorders"
            },
            "Pneumonia": {
                "definition": "Inflammation of the tissue in one or both lungs, usually due to infection.",
                "synonyms": ["Pneumonitis", "Bronchopneumonia"],
                "category": "Respiratory disorders"
            },
            "Influenza": {
                "definition": "A contagious respiratory illness caused by influenza viruses.",
                "synonyms": ["Flu", "Grippe", "Seasonal influenza"],
                "category": "Infectious diseases"
            }
        }
        
        # 中文疾病详情
        zh_details = {
            "糖尿病": {
                "definition": "一种以血糖水平长期偏高为特征的代谢性疾病。",
                "synonyms": ["消渴症", "高血糖", "1型糖尿病", "2型糖尿病"],
                "category": "内分泌疾病"
            },
            "高血压": {
                "definition": "一种长期的医疗状况，其特征是动脉中的血压持续升高。",
                "synonyms": ["血压高", "高血压病", "原发性高血压"],
                "category": "心血管疾病"
            },
            "心脏病": {
                "definition": "涉及心脏或血管的一类疾病。",
                "synonyms": ["心血管疾病", "冠状动脉疾病", "冠心病"],
                "category": "心血管疾病"
            },
            "肿瘤": {
                "definition": "组织的异常生长，可能是良性的或恶性的。",
                "synonyms": ["癌症", "瘤", "恶性肿瘤"],
                "category": "肿瘤学"
            },
            "哮喘": {
                "definition": "一种常见的肺部气道长期炎症性疾病。",
                "synonyms": ["支气管哮喘", "气喘", "过敏性哮喘"],
                "category": "呼吸系统疾病"
            },
            "阿尔茨海默病": {
                "definition": "一种慢性神经退行性疾病，通常起病缓慢，随时间恶化。",
                "synonyms": ["老年痴呆", "阿兹海默病", "老年性痴呆"],
                "category": "神经系统疾病"
            },
            "帕金森病": {
                "definition": "一种主要影响运动系统的中枢神经系统的长期退行性疾病。",
                "synonyms": ["震颤麻痹", "帕金森综合征", "帕金森氏病"],
                "category": "神经系统疾病"
            },
            "脑卒中": {
                "definition": "由于缺氧导致的脑细胞突然死亡，原因是脑部动脉血流阻塞或破裂。",
                "synonyms": ["中风", "脑血管意外", "脑梗塞"],
                "category": "神经系统疾病"
            },
            "肺炎": {
                "definition": "一种或两种肺部组织的炎症，通常由感染引起。",
                "synonyms": ["肺部感染", "支气管肺炎", "肺部炎症"],
                "category": "呼吸系统疾病"
            },
            "流行性感冒": {
                "definition": "由流感病毒引起的一种传染性呼吸道疾病。",
                "synonyms": ["流感", "感冒", "季节性流感"],
                "category": "传染病"
            }
        }
        
        # 根据语言选择疾病详情
        details_map = en_details if language == "en" else zh_details
        
        # 查找详情
        if term in details_map:
            return details_map[term]
        
        # 如果找不到详情，返回空结构
        return {
            "definition": "",
            "synonyms": [],
            "category": ""
        }
        
    except Exception as e:
        logger.warning(f"获取术语详情时出错: {str(e)}")
        return {
            "definition": "",
            "synonyms": [],
            "category": ""
        }


def _fuzzy_match_term(term: str, language: str) -> Optional[Dict[str, Any]]:
    """模糊匹配术语"""
    try:
        best_match = None
        best_similarity = 0
        
        # 根据语言选择字典
        dictionary = MEDICAL_DICTIONARY["en"] if language == "en" else MEDICAL_DICTIONARY["zh"]
        
        # 计算与字典中每个术语的相似度
        for dict_term, dict_value in dictionary.items():
            similarity = _calculate_similarity(term, dict_term)
            if similarity > best_similarity and similarity > 0.7:  # 设置相似度阈值
                best_similarity = similarity
                best_match = {
                    "standard_name": dict_value["standard_name"],
                    "standard_code": dict_value.get("standard_code", ""),
                    "confidence": similarity
                }
        
        return best_match
        
    except Exception as e:
        logger.warning(f"模糊匹配术语时出错: {str(e)}")
        return None


def _calculate_similarity(s1: str, s2: str) -> float:
    """计算两个字符串的相似度"""
    # 使用Levenshtein距离计算相似度
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    
    # 计算编辑距离
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if s1[i-1].lower() == s2[j-1].lower() else 1
            dp[i][j] = min(
                dp[i-1][j] + 1,      # 删除
                dp[i][j-1] + 1,      # 插入
                dp[i-1][j-1] + cost  # 替换
            )
    
    # 计算相似度
    max_len = max(m, n)
    if max_len == 0:
        return 1.0
    
    return 1.0 - dp[m][n] / max_len


def _get_suggestions(term: str, language: str) -> List[Dict[str, Any]]:
    """获取术语的建议列表"""
    try:
        suggestions = []
        
        # 根据语言选择字典
        dictionary = MEDICAL_DICTIONARY["en"] if language == "en" else MEDICAL_DICTIONARY["zh"]
        
        # 计算与字典中每个术语的相似度
        similarities = []
        for dict_term, dict_value in dictionary.items():
            similarity = _calculate_similarity(term, dict_term)
            if similarity > 0.5:  # 设置相似度阈值
                similarities.append({
                    "term": dict_term,
                    "standard_name": dict_value["standard_name"],
                    "standard_code": dict_value.get("standard_code", ""),
                    "similarity": similarity
                })
        
        # 按相似度排序
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        
        # 返回前5个建议
        for item in similarities[:5]:
            suggestions.append({
                "suggested_term": item["term"],
                "standard_name": item["standard_name"],
                "standard_code": item["standard_code"],
                "similarity": item["similarity"]
            })
        
        return suggestions
        
    except Exception as e:
        logger.warning(f"获取术语建议时出错: {str(e)}")
        return []


def _extract_chinese_medical_terms(text: str) -> List[str]:
    """从中文文本中提取医学术语"""
    terms = []
    
    # 常见中文疾病后缀
    suffixes = ["病", "症", "炎", "癌", "瘤"]
    
    # 分词（简化版）
    words = []
    current_word = ""
    for char in text:
        if re.match(r'[\u4e00-\u9fff]', char):
            current_word += char
        else:
            if current_word:
                words.append(current_word)
                current_word = ""
            if char.strip():
                words.append(char)
    if current_word:
        words.append(current_word)
    
    # 提取疾病术语
    i = 0
    while i < len(words):
        # 查找以医学后缀结尾的词组
        for j in range(i + 1, min(i + 10, len(words) + 1)):
            if j < len(words):
                word = words[j]
                if len(word) == 1 and word in suffixes:
                    term = ''.join(words[i:j+1])
                    terms.append(term)
                    i = j + 1
                    break
                elif any(word.endswith(suffix) for suffix in suffixes):
                    term = ''.join(words[i:j+1])
                    terms.append(term)
                    i = j + 1
                    break
        else:
            i += 1
    
    return terms


def _extract_english_medical_terms(text: str) -> List[str]:
    """从英文文本中提取医学术语"""
    terms = []
    
    # 常见英文疾病后缀
    suffixes = ["disease", "syndrome", "disorder", "itis", "osis", "pathy"]
    
    # 分词
    words = text.split()
    
    # 提取疾病术语
    i = 0
    while i < len(words):
        # 查找以医学后缀结尾的词组
        for j in range(i, min(i + 5, len(words))):
            for suffix in suffixes:
                if words[j].lower().endswith(suffix):
                    term = ' '.join(words[i:j+1])
                    terms.append(term)
                    i = j + 1
                    break
            else:
                continue
            break
        else:
            i += 1
    
    return terms