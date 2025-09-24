#!/usr/bin/env python3
"""
HPO数据库API客户端工具

提供与HPO数据库交互的工具，用于查询疾病对应的HPO ID和相关信息
"""

import json
import requests
import time
import os
import re
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path
import logging
from strands import tool

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# HPO API 端点 - 尝试多个可能的端点
HPO_API_ENDPOINTS = [
    "https://hpo.jax.org/api/hpo",
    "https://hpo.jax.org/api/search", 
    "https://hpo.jax.org/api/autocomplete",
    "https://api.monarchinitiative.org/api/search",
    "http://www.ontobee.org/api/search",
    "https://data.bioontology.org/search"
]

# 主要的HPO API端点
HPO_API_BASE_URL = HPO_API_ENDPOINTS[0]
ONTOBEE_API_URL = "http://www.ontobee.org/api/search"
BIOPORTAL_API_URL = "https://data.bioontology.org/search"

# 缓存目录
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache", "disease_hpo_mapper")
os.makedirs(CACHE_DIR, exist_ok=True)


@tool
def query_hpo_database(disease_name: str, language: str = "en", exact_match: bool = True) -> str:
    """
    查询HPO数据库获取疾病对应的HPO ID和相关信息
    
    Args:
        disease_name (str): 疾病名称（中文或英文）
        language (str): 输入疾病名称的语言，可选值：'en'（英文）或'zh'（中文）
        exact_match (bool): 是否进行精确匹配，如果为False则进行模糊匹配
    
    Returns:
        str: JSON格式的查询结果，包含疾病的HPO ID和相关信息
    """
    try:
        # 检查缓存
        cache_key = f"{disease_name}_{language}_{exact_match}"
        cache_result = _get_from_cache(cache_key)
        if cache_result:
            logger.info(f"返回缓存结果: {disease_name}")
            return cache_result
        
        # 如果输入是中文，尝试翻译为英文（这里简化处理，实际应使用翻译API或字典）
        query_name = disease_name
        if language == "zh":
            english_name = _translate_disease_name(disease_name)
            if english_name:
                query_name = english_name
                logger.info(f"将中文疾病名称 '{disease_name}' 翻译为 '{english_name}'")
        
        # 构建查询参数
        params = {
            "q": query_name,
            "category": "diseases",
            "max_results": 10
        }
        
        # 首先尝试找到可用的API端点
        working_endpoint = _find_working_api_endpoint()
        
        if working_endpoint:
            # 使用可用的API端点
            if "search" in working_endpoint:
                api_url = f"{working_endpoint}?q={query_name}&category=diseases&max_results=10"
            else:
                api_url = f"{working_endpoint}/search?q={query_name}&category=diseases&max_results=10"
            
            try:
                response = requests.get(api_url, timeout=10)
                
                if response.status_code == 200:
                    # 检查响应内容类型
                    content_type = response.headers.get('content-type', '').lower()
                    if 'application/json' in content_type:
                        data = response.json()
                    else:
                        # 如果不是JSON，尝试解析
                        try:
                            data = response.json()
                        except json.JSONDecodeError:
                            # API返回非JSON数据，使用备用策略
                            logger.warning(f"API端点 {working_endpoint} 返回非JSON数据，使用本地知识库")
                            local_result = _get_hpo_data_from_local_knowledge(disease_name, language)
                            result_json = json.dumps(local_result, ensure_ascii=False, indent=2)
                            _save_to_cache(cache_key, result_json)
                            return result_json
                else:
                    # API请求失败，使用备用策略
                    logger.warning(f"API请求失败，状态码: {response.status_code}，使用本地知识库")
                    local_result = _get_hpo_data_from_local_knowledge(disease_name, language)
                    result_json = json.dumps(local_result, ensure_ascii=False, indent=2)
                    _save_to_cache(cache_key, result_json)
                    return result_json
                    
            except Exception as api_error:
                logger.warning(f"API请求异常: {str(api_error)}，使用本地知识库")
                local_result = _get_hpo_data_from_local_knowledge(disease_name, language)
                result_json = json.dumps(local_result, ensure_ascii=False, indent=2)
                _save_to_cache(cache_key, result_json)
                return result_json
        else:
            # 没有可用的API端点，使用本地知识库
            logger.info("没有可用的API端点，使用本地知识库")
            local_result = _get_hpo_data_from_local_knowledge(disease_name, language)
            result_json = json.dumps(local_result, ensure_ascii=False, indent=2)
            _save_to_cache(cache_key, result_json)
            return result_json
        
        # 处理结果
        results = []
        for item in data.get("terms", []):
            # 如果是精确匹配模式，检查名称是否完全匹配
            if exact_match and query_name.lower() != item.get("name", "").lower():
                continue
                
            # 获取详细信息
            details = _get_term_details(item.get("id"))
            
            result_item = {
                "id": item.get("id"),
                "name": {
                    "en": item.get("name"),
                    "zh": _get_chinese_name(item.get("id"), item.get("name"))
                },
                "definition": details.get("definition", ""),
                "synonyms": details.get("synonyms", []),
                "parents": details.get("parents", []),
                "children": details.get("children", []),
                "match_type": "exact" if exact_match else "fuzzy",
                "confidence": 1.0 if exact_match else _calculate_similarity(query_name, item.get("name", ""))
            }
            
            results.append(result_item)
        
        # 如果没有找到结果，尝试模糊匹配
        if not results and exact_match:
            logger.info(f"未找到精确匹配结果，尝试模糊匹配: {query_name}")
            fuzzy_results = _query_hpo_database_internal(disease_name, language, False)
            
            # 如果模糊匹配也没有结果，尝试关键词搜索
            if not fuzzy_results.get("results"):
                logger.info(f"未找到模糊匹配结果，尝试关键词搜索: {query_name}")
                keywords = _extract_keywords(query_name)
                if keywords:
                    keyword_results = []
                    for keyword in keywords:
                        # 直接调用内部函数而不是工具函数
                        keyword_response = _search_hpo_by_keyword_internal(keyword)
                        if keyword_response.get("success") and keyword_response.get("results"):
                            keyword_results.extend(keyword_response.get("results"))
                    
                    if keyword_results:
                        response_data = {
                            "success": True,
                            "query": disease_name,
                            "original_language": language,
                            "results": keyword_results,
                            "match_type": "keyword",
                            "count": len(keyword_results)
                        }
                        result_json = json.dumps(response_data, ensure_ascii=False, indent=2)
                        _save_to_cache(cache_key, result_json)
                        return result_json
            
            return fuzzy_results
        
        response_data = {
            "success": True,
            "query": disease_name,
            "original_language": language,
            "results": results,
            "match_type": "exact" if exact_match else "fuzzy",
            "count": len(results)
        }
        
        result_json = json.dumps(response_data, ensure_ascii=False, indent=2)
        
        # 保存到缓存
        _save_to_cache(cache_key, result_json)
        
        return result_json
        
    except Exception as e:
        logger.error(f"查询HPO数据库时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"查询失败: {str(e)}",
            "query": disease_name
        }, ensure_ascii=False, indent=2)


@tool
def search_hpo_by_keyword(keyword: str, max_results: int = 10) -> str:
    """
    通过关键词搜索HPO数据库
    
    Args:
        keyword (str): 搜索关键词
        max_results (int): 最大返回结果数量
    
    Returns:
        str: JSON格式的搜索结果
    """
    try:
        # 检查缓存
        cache_key = f"keyword_{keyword}_{max_results}"
        cache_result = _get_from_cache(cache_key)
        if cache_result:
            return cache_result
        
        # 构建查询参数
        params = {
            "q": keyword,
            "category": "diseases",
            "max_results": max_results
        }
        
        # 发送请求
        response = requests.get(f"{HPO_API_BASE_URL}/search", params=params)
        
        if response.status_code != 200:
            return json.dumps({
                "success": False,
                "error": f"API请求失败，状态码: {response.status_code}",
                "query": keyword
            }, ensure_ascii=False, indent=2)
        
        data = response.json()
        
        # 处理结果
        results = []
        for item in data.get("terms", []):
            # 获取详细信息
            details = _get_term_details(item.get("id"))
            
            result_item = {
                "id": item.get("id"),
                "name": {
                    "en": item.get("name"),
                    "zh": _get_chinese_name(item.get("id"), item.get("name"))
                },
                "definition": details.get("definition", ""),
                "synonyms": details.get("synonyms", []),
                "match_type": "keyword",
                "confidence": _calculate_keyword_relevance(keyword, item.get("name", ""), details.get("synonyms", []))
            }
            
            results.append(result_item)
        
        # 按相关度排序
        results.sort(key=lambda x: x["confidence"], reverse=True)
        
        response_data = {
            "success": True,
            "query": keyword,
            "results": results[:max_results],
            "match_type": "keyword",
            "count": len(results[:max_results])
        }
        
        result_json = json.dumps(response_data, ensure_ascii=False, indent=2)
        
        # 保存到缓存
        _save_to_cache(cache_key, result_json)
        
        return result_json
        
    except Exception as e:
        logger.error(f"关键词搜索HPO数据库时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"搜索失败: {str(e)}",
            "query": keyword
        }, ensure_ascii=False, indent=2)


@tool
def standardize_disease_name(disease_description: str, language: str = "auto") -> str:
    """
    将非正式或不完整的疾病描述标准化为正式疾病名称
    
    Args:
        disease_description (str): 疾病描述文本
        language (str): 输入语言，可选值：'en'（英文）、'zh'（中文）或'auto'（自动检测）
    
    Returns:
        str: JSON格式的标准化结果，包含标准化的疾病名称
    """
    try:
        # 检查缓存
        cache_key = f"standardize_{disease_description}_{language}"
        cache_result = _get_from_cache(cache_key)
        if cache_result:
            return cache_result
        
        # 自动检测语言
        if language == "auto":
            language = _detect_language(disease_description)
        
        # 预处理文本
        cleaned_text = _preprocess_text(disease_description)
        
        # 提取关键医学术语
        medical_terms = _extract_medical_terms(cleaned_text, language)
        
        # 查询标准化名称
        standardized_names = []
        for term in medical_terms:
            # 查询HPO数据库
            term_results = json.loads(query_hpo_database(term, language, False))
            
            if term_results.get("success") and term_results.get("results"):
                for result in term_results.get("results"):
                    standardized_name = {
                        "original_term": term,
                        "standardized_name": {
                            "en": result.get("name", {}).get("en", ""),
                            "zh": result.get("name", {}).get("zh", "")
                        },
                        "hpo_id": result.get("id", ""),
                        "confidence": result.get("confidence", 0),
                        "definition": result.get("definition", "")
                    }
                    standardized_names.append(standardized_name)
        
        # 按置信度排序
        standardized_names.sort(key=lambda x: x["confidence"], reverse=True)
        
        # 如果没有找到标准化名称，尝试使用推理匹配
        if not standardized_names:
            inferred_results = _infer_disease_from_description(disease_description, language)
            if inferred_results:
                standardized_names = inferred_results
        
        response_data = {
            "success": True,
            "original_description": disease_description,
            "detected_language": language,
            "standardized_names": standardized_names,
            "count": len(standardized_names)
        }
        
        result_json = json.dumps(response_data, ensure_ascii=False, indent=2)
        
        # 保存到缓存
        _save_to_cache(cache_key, result_json)
        
        return result_json
        
    except Exception as e:
        logger.error(f"标准化疾病名称时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"标准化失败: {str(e)}",
            "original_description": disease_description
        }, ensure_ascii=False, indent=2)


@tool
def calculate_string_similarity(string1: str, string2: str, method: str = "levenshtein") -> str:
    """
    计算两个字符串之间的相似度
    
    Args:
        string1 (str): 第一个字符串
        string2 (str): 第二个字符串
        method (str): 相似度计算方法，可选值：'levenshtein'（编辑距离）、'jaccard'（杰卡德相似度）或'cosine'（余弦相似度）
    
    Returns:
        str: JSON格式的相似度计算结果
    """
    try:
        similarity = 0.0
        
        if method == "levenshtein":
            similarity = _levenshtein_similarity(string1, string2)
        elif method == "jaccard":
            similarity = _jaccard_similarity(string1, string2)
        elif method == "cosine":
            similarity = _cosine_similarity(string1, string2)
        else:
            raise ValueError(f"不支持的相似度计算方法: {method}")
        
        return json.dumps({
            "success": True,
            "string1": string1,
            "string2": string2,
            "method": method,
            "similarity": similarity
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"计算字符串相似度时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"计算失败: {str(e)}",
            "string1": string1,
            "string2": string2
        }, ensure_ascii=False, indent=2)


@tool
def manage_hpo_cache(action: str, key: str = None) -> str:
    """
    管理HPO查询缓存
    
    Args:
        action (str): 缓存操作，可选值：'list'（列出缓存）、'clear'（清除缓存）、'get'（获取特定缓存）或'delete'（删除特定缓存）
        key (str): 缓存键，仅在'get'和'delete'操作时需要
    
    Returns:
        str: JSON格式的操作结果
    """
    try:
        if action == "list":
            cache_files = os.listdir(CACHE_DIR)
            cache_info = []
            
            for file in cache_files:
                if file.endswith(".json"):
                    file_path = os.path.join(CACHE_DIR, file)
                    stats = os.stat(file_path)
                    
                    cache_info.append({
                        "key": file[:-5],  # 移除.json后缀
                        "size": stats.st_size,
                        "created": time.ctime(stats.st_ctime),
                        "last_accessed": time.ctime(stats.st_atime)
                    })
            
            return json.dumps({
                "success": True,
                "action": "list",
                "cache_count": len(cache_info),
                "cache_items": cache_info
            }, ensure_ascii=False, indent=2)
            
        elif action == "clear":
            cache_files = os.listdir(CACHE_DIR)
            deleted_count = 0
            
            for file in cache_files:
                if file.endswith(".json"):
                    os.remove(os.path.join(CACHE_DIR, file))
                    deleted_count += 1
            
            return json.dumps({
                "success": True,
                "action": "clear",
                "deleted_count": deleted_count,
                "message": f"已清除 {deleted_count} 个缓存项"
            }, ensure_ascii=False, indent=2)
            
        elif action == "get":
            if not key:
                return json.dumps({
                    "success": False,
                    "error": "获取缓存需要提供key参数"
                }, ensure_ascii=False, indent=2)
            
            cache_content = _get_from_cache(key, raw=True)
            if cache_content:
                return json.dumps({
                    "success": True,
                    "action": "get",
                    "key": key,
                    "content": cache_content
                }, ensure_ascii=False, indent=2)
            else:
                return json.dumps({
                    "success": False,
                    "action": "get",
                    "key": key,
                    "error": "缓存项不存在"
                }, ensure_ascii=False, indent=2)
                
        elif action == "delete":
            if not key:
                return json.dumps({
                    "success": False,
                    "error": "删除缓存需要提供key参数"
                }, ensure_ascii=False, indent=2)
            
            cache_path = os.path.join(CACHE_DIR, f"{key}.json")
            if os.path.exists(cache_path):
                os.remove(cache_path)
                return json.dumps({
                    "success": True,
                    "action": "delete",
                    "key": key,
                    "message": f"已删除缓存项 {key}"
                }, ensure_ascii=False, indent=2)
            else:
                return json.dumps({
                    "success": False,
                    "action": "delete",
                    "key": key,
                    "error": "缓存项不存在"
                }, ensure_ascii=False, indent=2)
        else:
            return json.dumps({
                "success": False,
                "error": f"不支持的缓存操作: {action}"
            }, ensure_ascii=False, indent=2)
            
    except Exception as e:
        logger.error(f"管理缓存时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"操作失败: {str(e)}",
            "action": action
        }, ensure_ascii=False, indent=2)


# 辅助函数

def _test_api_endpoint(endpoint: str, test_query: str = "diabetes") -> bool:
    """
    测试API端点是否可用
    
    Args:
        endpoint (str): API端点URL
        test_query (str): 测试查询词
    
    Returns:
        bool: API端点是否可用
    """
    try:
        # 构建测试请求
        if "search" in endpoint:
            url = f"{endpoint}?q={test_query}"
        else:
            url = f"{endpoint}/search?q={test_query}"
        
        response = requests.get(url, timeout=10)
        
        # 检查响应状态码
        if response.status_code != 200:
            return False
        
        # 检查响应内容类型
        content_type = response.headers.get('content-type', '').lower()
        if 'application/json' in content_type:
            # 尝试解析JSON
            try:
                data = response.json()
                # 检查是否有有效的数据结构
                return isinstance(data, (dict, list)) and len(str(data)) > 10
            except json.JSONDecodeError:
                return False
        else:
            # 如果不是JSON，检查是否是HTML（说明API不可用）
            content = response.text.lower()
            if '<html' in content or '<!doctype' in content:
                return False
            return True
            
    except Exception as e:
        logger.warning(f"测试API端点 {endpoint} 时出错: {str(e)}")
        return False


def _find_working_api_endpoint() -> Optional[str]:
    """
    查找可用的API端点
    
    Returns:
        Optional[str]: 可用的API端点URL，如果没有找到则返回None
    """
    for endpoint in HPO_API_ENDPOINTS:
        logger.info(f"测试API端点: {endpoint}")
        if _test_api_endpoint(endpoint):
            logger.info(f"找到可用的API端点: {endpoint}")
            return endpoint
        else:
            logger.warning(f"API端点不可用: {endpoint}")
    
    logger.error("所有HPO API端点都不可用")
    return None


def _get_hpo_data_from_local_knowledge(disease_name: str, language: str = "en") -> Dict[str, Any]:
    """
    从本地知识库获取HPO数据（当API不可用时的备用方案）
    
    Args:
        disease_name (str): 疾病名称
        language (str): 语言
    
    Returns:
        Dict[str, Any]: HPO数据
    """
    # 本地HPO知识库（简化版）
    local_hpo_db = {
        "diabetes": {
            "id": "HP:0000819",
            "name": {"en": "Diabetes mellitus", "zh": "糖尿病"},
            "definition": "A metabolic disorder characterized by abnormally high blood glucose levels due to diminished production of insulin or insulin resistance/desensitization.",
            "synonyms": ["Diabetes", "DM", "Type 1 Diabetes", "Type 2 Diabetes"],
            "alternative_ids": [
                {"id": "HP:0000857", "name": "Neonatal diabetes mellitus"},
                {"id": "HP:0100651", "name": "Type 2 diabetes mellitus"},
                {"id": "HP:0004904", "name": "Maturity-onset diabetes of the young"},
                {"id": "HP:0100485", "name": "Type 1 diabetes mellitus"}
            ]
        },
        "高血压": {
            "id": "HP:0000822",
            "name": {"en": "Hypertension", "zh": "高血压"},
            "definition": "The presence of chronic increased pressure in the systemic arterial system.",
            "synonyms": ["High blood pressure", "HTN", "HT"],
            "alternative_ids": []
        },
        "hypertension": {
            "id": "HP:0000822",
            "name": {"en": "Hypertension", "zh": "高血压"},
            "definition": "The presence of chronic increased pressure in the systemic arterial system.",
            "synonyms": ["High blood pressure", "HTN", "HT"],
            "alternative_ids": []
        },
        "糖尿病": {
            "id": "HP:0000819",
            "name": {"en": "Diabetes mellitus", "zh": "糖尿病"},
            "definition": "A metabolic disorder characterized by abnormally high blood glucose levels due to diminished production of insulin or insulin resistance/desensitization.",
            "synonyms": ["Diabetes", "DM", "Type 1 Diabetes", "Type 2 Diabetes"],
            "alternative_ids": [
                {"id": "HP:0000857", "name": "Neonatal diabetes mellitus"},
                {"id": "HP:0100651", "name": "Type 2 diabetes mellitus"},
                {"id": "HP:0004904", "name": "Maturity-onset diabetes of the young"},
                {"id": "HP:0100485", "name": "Type 1 diabetes mellitus"}
            ]
        }
    }
    
    # 查找匹配的疾病
    query_key = disease_name.lower()
    if query_key in local_hpo_db:
        data = local_hpo_db[query_key]
        
        # 构建结果
        results = []
        main_result = {
            "id": data["id"],
            "name": data["name"],
            "definition": data["definition"],
            "synonyms": data["synonyms"],
            "match_type": "exact",
            "confidence": 0.95,
            "source": "local_knowledge"
        }
        results.append(main_result)
        
        # 添加替代ID
        for alt in data.get("alternative_ids", []):
            alt_result = {
                "id": alt["id"],
                "name": {"en": alt["name"], "zh": alt["name"]},
                "definition": f"Alternative form of {data['name']['en']}",
                "synonyms": [],
                "match_type": "alternative",
                "confidence": 0.8,
                "source": "local_knowledge"
            }
            results.append(alt_result)
        
        return {
            "success": True,
            "query": disease_name,
            "original_language": language,
            "results": results,
            "match_type": "local_knowledge",
            "count": len(results),
            "source": "local_knowledge_base"
        }
    
    return {
        "success": False,
        "query": disease_name,
        "error": "疾病名称在本地知识库中未找到",
        "suggestions": ["糖尿病", "高血压", "diabetes", "hypertension"]
    }


def _get_from_cache(key: str, raw: bool = False) -> Optional[str]:
    """从缓存中获取数据"""
    cache_path = os.path.join(CACHE_DIR, f"{key}.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if raw:
                    return content
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


def _get_term_details(term_id: str) -> Dict[str, Any]:
    """获取术语详细信息"""
    try:
        # 检查缓存
        cache_key = f"term_details_{term_id}"
        cache_result = _get_from_cache(cache_key)
        if cache_result:
            return json.loads(cache_result)
        
        # 发送请求
        response = requests.get(f"{HPO_API_BASE_URL}/term/{term_id}")
        
        if response.status_code != 200:
            logger.warning(f"获取术语详情失败，状态码: {response.status_code}")
            return {}
        
        data = response.json()
        
        details = {
            "id": data.get("id"),
            "name": data.get("name"),
            "definition": data.get("definition", {}).get("text", ""),
            "synonyms": [s.get("val") for s in data.get("synonyms", [])],
            "parents": [{"id": p.get("id"), "name": p.get("name")} for p in data.get("relations", {}).get("parents", [])],
            "children": [{"id": c.get("id"), "name": c.get("name")} for c in data.get("relations", {}).get("children", [])]
        }
        
        # 保存到缓存
        _save_to_cache(cache_key, json.dumps(details, ensure_ascii=False))
        
        return details
    except Exception as e:
        logger.warning(f"获取术语详情时出错: {str(e)}")
        return {}


def _translate_disease_name(chinese_name: str) -> Optional[str]:
    """将中文疾病名称翻译为英文（简化版）"""
    # 这里应该使用专业的医学术语翻译API或字典
    # 此处为简化实现，实际应用中应使用更复杂的翻译逻辑
    
    # 简单的中英文疾病名称映射
    disease_dict = {
        "糖尿病": "diabetes mellitus",
        "高血压": "hypertension",
        "冠心病": "coronary heart disease",
        "肺炎": "pneumonia",
        "哮喘": "asthma",
        "癌症": "cancer",
        "肝炎": "hepatitis",
        "艾滋病": "AIDS",
        "帕金森病": "Parkinson's disease",
        "阿尔茨海默病": "Alzheimer's disease",
        "抑郁症": "depression",
        "精神分裂症": "schizophrenia",
        "白血病": "leukemia",
        "肺结核": "tuberculosis",
        "脑卒中": "stroke"
    }
    
    # 直接匹配
    if chinese_name in disease_dict:
        return disease_dict[chinese_name]
    
    # 部分匹配
    for zh, en in disease_dict.items():
        if zh in chinese_name:
            return en
    
    # 如果无法翻译，返回原名称
    return chinese_name


def _get_chinese_name(term_id: str, english_name: str) -> str:
    """获取疾病的中文名称（简化版）"""
    # 这里应该查询专业的医学术语翻译API或字典
    # 此处为简化实现，实际应用中应使用更复杂的翻译逻辑
    
    # 简单的英中文疾病名称映射
    disease_dict = {
        "diabetes mellitus": "糖尿病",
        "hypertension": "高血压",
        "coronary heart disease": "冠心病",
        "pneumonia": "肺炎",
        "asthma": "哮喘",
        "cancer": "癌症",
        "hepatitis": "肝炎",
        "AIDS": "艾滋病",
        "Parkinson's disease": "帕金森病",
        "Alzheimer's disease": "阿尔茨海默病",
        "depression": "抑郁症",
        "schizophrenia": "精神分裂症",
        "leukemia": "白血病",
        "tuberculosis": "肺结核",
        "stroke": "脑卒中"
    }
    
    # 直接匹配
    if english_name.lower() in [k.lower() for k in disease_dict.keys()]:
        for k, v in disease_dict.items():
            if k.lower() == english_name.lower():
                return v
    
    # 部分匹配
    for en, zh in disease_dict.items():
        if en.lower() in english_name.lower():
            return zh
    
    # 如果无法翻译，返回空字符串
    return ""


def _calculate_similarity(str1: str, str2: str) -> float:
    """计算两个字符串的相似度"""
    return _levenshtein_similarity(str1.lower(), str2.lower())


def _levenshtein_similarity(s1: str, s2: str) -> float:
    """计算Levenshtein相似度"""
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
            cost = 0 if s1[i-1] == s2[j-1] else 1
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


def _jaccard_similarity(s1: str, s2: str) -> float:
    """计算Jaccard相似度"""
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    
    # 将字符串转换为字符集合
    set1 = set(s1.lower())
    set2 = set(s2.lower())
    
    # 计算交集和并集
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    
    if union == 0:
        return 0.0
    
    return intersection / union


def _cosine_similarity(s1: str, s2: str) -> float:
    """计算余弦相似度"""
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    
    # 将字符串转换为词频向量
    def get_word_freq(s: str) -> Dict[str, int]:
        words = s.lower().split()
        freq = {}
        for word in words:
            freq[word] = freq.get(word, 0) + 1
        return freq
    
    vec1 = get_word_freq(s1)
    vec2 = get_word_freq(s2)
    
    # 计算点积
    dot_product = 0
    for word, count in vec1.items():
        if word in vec2:
            dot_product += count * vec2[word]
    
    # 计算向量模长
    mag1 = sum(count ** 2 for count in vec1.values()) ** 0.5
    mag2 = sum(count ** 2 for count in vec2.values()) ** 0.5
    
    if mag1 * mag2 == 0:
        return 0.0
    
    return dot_product / (mag1 * mag2)


def _calculate_keyword_relevance(keyword: str, name: str, synonyms: List[str]) -> float:
    """计算关键词与疾病名称及同义词的相关度"""
    # 计算与名称的相似度
    name_similarity = _levenshtein_similarity(keyword.lower(), name.lower())
    
    # 计算与同义词的最大相似度
    synonym_similarity = 0.0
    for synonym in synonyms:
        similarity = _levenshtein_similarity(keyword.lower(), synonym.lower())
        synonym_similarity = max(synonym_similarity, similarity)
    
    # 返回最大相似度
    return max(name_similarity, synonym_similarity)


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


def _extract_keywords(text: str) -> List[str]:
    """从文本中提取关键词"""
    words = text.split()
    # 过滤短词
    keywords = [word for word in words if len(word) > 3]
    return keywords


def _extract_medical_terms(text: str, language: str) -> List[str]:
    """从文本中提取医学术语"""
    # 简单的实现，实际应使用医学NER模型
    if language == "zh":
        # 中文医学术语提取逻辑
        terms = []
        # 常见中文疾病后缀
        suffixes = ["病", "症", "炎", "癌"]
        words = list(text)
        
        i = 0
        while i < len(words):
            # 查找以医学后缀结尾的词组
            for j in range(i + 1, min(i + 10, len(words) + 1)):
                if j < len(words) and words[j] in suffixes:
                    term = ''.join(words[i:j+1])
                    terms.append(term)
                    i = j + 1
                    break
            else:
                i += 1
        
        return terms
    else:
        # 英文医学术语提取逻辑
        terms = []
        words = text.split()
        
        # 常见英文疾病后缀
        suffixes = ["disease", "syndrome", "disorder", "itis", "osis", "pathy"]
        
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


def _query_hpo_database_internal(disease_name: str, language: str = "en", exact_match: bool = True) -> Dict[str, Any]:
    """
    内部函数：查询HPO数据库（不通过工具装饰器）
    """
    try:
        # 检查缓存
        cache_key = f"{disease_name}_{language}_{exact_match}"
        cache_result = _get_from_cache(cache_key)
        if cache_result:
            return json.loads(cache_result)
        
        # 如果输入是中文，尝试翻译为英文
        query_name = disease_name
        if language == "zh":
            english_name = _translate_disease_name(disease_name)
            if english_name:
                query_name = english_name
                logger.info(f"将中文疾病名称 '{disease_name}' 翻译为 '{english_name}'")
        
        # 构建查询参数
        params = {
            "q": query_name,
            "category": "diseases",
            "max_results": 10
        }
        
        # 发送请求
        response = requests.get(f"{HPO_API_BASE_URL}/search", params=params)
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"API请求失败，状态码: {response.status_code}",
                "query": query_name
            }
        
        data = response.json()
        
        # 处理结果
        results = []
        for item in data.get("terms", []):
            # 如果是精确匹配模式，检查名称是否完全匹配
            if exact_match and query_name.lower() != item.get("name", "").lower():
                continue
                
            # 获取详细信息
            details = _get_term_details(item.get("id"))
            
            result_item = {
                "id": item.get("id"),
                "name": {
                    "en": item.get("name"),
                    "zh": _get_chinese_name(item.get("id"), item.get("name"))
                },
                "definition": details.get("definition", ""),
                "synonyms": details.get("synonyms", []),
                "parents": details.get("parents", []),
                "children": details.get("children", []),
                "match_type": "exact" if exact_match else "fuzzy",
                "confidence": 1.0 if exact_match else _calculate_similarity(query_name, item.get("name", ""))
            }
            
            results.append(result_item)
        
        response_data = {
            "success": True,
            "query": disease_name,
            "original_language": language,
            "results": results,
            "match_type": "exact" if exact_match else "fuzzy",
            "count": len(results)
        }
        
        result_json = json.dumps(response_data, ensure_ascii=False, indent=2)
        
        # 保存到缓存
        _save_to_cache(cache_key, result_json)
        
        return response_data
        
    except Exception as e:
        logger.error(f"查询HPO数据库时出错: {str(e)}")
        return {
            "success": False,
            "error": f"查询失败: {str(e)}",
            "query": disease_name
        }


def _search_hpo_by_keyword_internal(keyword: str, max_results: int = 10) -> Dict[str, Any]:
    """
    内部函数：通过关键词搜索HPO数据库（不通过工具装饰器）
    """
    try:
        # 检查缓存
        cache_key = f"keyword_{keyword}_{max_results}"
        cache_result = _get_from_cache(cache_key)
        if cache_result:
            return json.loads(cache_result)
        
        # 构建查询参数
        params = {
            "q": keyword,
            "category": "diseases",
            "max_results": max_results
        }
        
        # 发送请求
        response = requests.get(f"{HPO_API_BASE_URL}/search", params=params)
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"API请求失败，状态码: {response.status_code}",
                "query": keyword
            }
        
        data = response.json()
        
        # 处理结果
        results = []
        for item in data.get("terms", []):
            # 获取详细信息
            details = _get_term_details(item.get("id"))
            
            result_item = {
                "id": item.get("id"),
                "name": {
                    "en": item.get("name"),
                    "zh": _get_chinese_name(item.get("id"), item.get("name"))
                },
                "definition": details.get("definition", ""),
                "synonyms": details.get("synonyms", []),
                "match_type": "keyword",
                "confidence": _calculate_keyword_relevance(keyword, item.get("name", ""), details.get("synonyms", []))
            }
            
            results.append(result_item)
        
        # 按相关度排序
        results.sort(key=lambda x: x["confidence"], reverse=True)
        
        response_data = {
            "success": True,
            "query": keyword,
            "results": results[:max_results],
            "match_type": "keyword",
            "count": len(results[:max_results])
        }
        
        result_json = json.dumps(response_data, ensure_ascii=False, indent=2)
        
        # 保存到缓存
        _save_to_cache(cache_key, result_json)
        
        return response_data
        
    except Exception as e:
        logger.error(f"关键词搜索HPO数据库时出错: {str(e)}")
        return {
            "success": False,
            "error": f"搜索失败: {str(e)}",
            "query": keyword
        }


def _infer_disease_from_description(description: str, language: str) -> List[Dict[str, Any]]:
    """从描述中推断疾病"""
    # 这里应该使用更复杂的推理逻辑，如医学知识图谱或专业模型
    # 此处为简化实现
    
    # 提取关键词
    keywords = _extract_keywords(description)
    
    results = []
    for keyword in keywords:
        # 搜索相关疾病
        keyword_response = _search_hpo_by_keyword_internal(keyword)
        if keyword_response.get("success") and keyword_response.get("results"):
            for result in keyword_response.get("results"):
                inferred_result = {
                    "original_term": keyword,
                    "standardized_name": {
                        "en": result.get("name", {}).get("en", ""),
                        "zh": result.get("name", {}).get("zh", "")
                    },
                    "hpo_id": result.get("id", ""),
                    "confidence": result.get("confidence", 0) * 0.8,  # 降低推理结果的置信度
                    "definition": result.get("definition", ""),
                    "inference_method": "keyword_based"
                }
                results.append(inferred_result)
    
    # 按置信度排序
    results.sort(key=lambda x: x["confidence"], reverse=True)
    
    return results[:5]  # 只返回前5个结果