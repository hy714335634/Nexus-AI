#!/usr/bin/env python3
"""
OpenFDA API工具集

提供OpenFDA API查询、端点路由、参数构建、数据解析等功能
"""

import json
import requests
import time
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urljoin, urlencode
from datetime import datetime, timedelta
from strands import tool


# OpenFDA API配置
OPENFDA_BASE_URL = "https://api.fda.gov"
OPENFDA_ENDPOINTS = {
    "drug": {
        "event": "/drug/event.json",
        "label": "/drug/label.json",
        "enforcement": "/drug/enforcement.json",
        "ndc": "/drug/ndc.json",
        "drugsfda": "/drug/drugsfda.json"
    },
    "device": {
        "event": "/device/event.json",
        "enforcement": "/device/enforcement.json",
        "classification": "/device/classification.json",
        "recall": "/device/recall.json",
        "510k": "/device/510k.json",
        "pma": "/device/pma.json",
        "registrationlisting": "/device/registrationlisting.json",
        "udi": "/device/udi.json"
    },
    "food": {
        "event": "/food/event.json",
        "enforcement": "/food/enforcement.json"
    }
}

# 速率限制配置
RATE_LIMIT_PER_MINUTE = 240
RATE_LIMIT_PER_DAY = 120000


@tool
def openfda_query(
    query_type: str,
    endpoint: str,
    search_params: Dict[str, Any] = None,
    limit: int = 10,
    skip: int = 0,
    sort: str = None,
    count: str = None,
    timeout: int = 30
) -> str:
    """
    OpenFDA API查询工具 - 执行OpenFDA API查询并返回结构化结果
    
    Args:
        query_type (str): 查询类型 (drug, device, food)
        endpoint (str): API端点 (event, label, enforcement等)
        search_params (Dict[str, Any]): 搜索参数，支持多种字段和运算符
        limit (int): 返回结果数量限制 (1-100)
        skip (int): 跳过的结果数量（分页）
        sort (str): 排序字段和方向，例如 "report_date:desc"
        count (str): 计数字段，用于统计分析
        timeout (int): 请求超时时间（秒）
        
    Returns:
        str: JSON格式的查询结果
    """
    try:
        # 验证参数
        if query_type not in OPENFDA_ENDPOINTS:
            return json.dumps({
                "error": f"不支持的查询类型: {query_type}",
                "supported_types": list(OPENFDA_ENDPOINTS.keys())
            }, ensure_ascii=False, indent=2)
        
        if endpoint not in OPENFDA_ENDPOINTS[query_type]:
            return json.dumps({
                "error": f"不支持的端点: {endpoint}",
                "supported_endpoints": list(OPENFDA_ENDPOINTS[query_type].keys())
            }, ensure_ascii=False, indent=2)
        
        # 验证limit范围
        if limit < 1 or limit > 100:
            limit = min(max(limit, 1), 100)
        
        # 构建完整URL
        endpoint_path = OPENFDA_ENDPOINTS[query_type][endpoint]
        url = urljoin(OPENFDA_BASE_URL, endpoint_path)
        
        # 构建查询参数
        params = {}
        
        # 添加搜索条件
        if search_params:
            search_query = _build_search_query(search_params)
            if search_query:
                params["search"] = search_query
        
        # 添加分页参数
        params["limit"] = limit
        if skip > 0:
            params["skip"] = skip
        
        # 添加排序参数
        if sort:
            params["sort"] = sort
        
        # 添加计数参数
        if count:
            params["count"] = count
        
        # 执行请求（带重试机制）
        max_retries = 3
        retry_delays = [1, 2, 4]  # 指数退避
        
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    url,
                    params=params,
                    headers={
                        "Accept": "application/json",
                        "User-Agent": "OpenFDA-Data-Agent/1.0"
                    },
                    timeout=timeout
                )
                
                # 检查响应状态
                if response.status_code == 200:
                    data = response.json()
                    
                    # 构建结果
                    result = {
                        "status": "success",
                        "query_info": {
                            "query_type": query_type,
                            "endpoint": endpoint,
                            "search_params": search_params,
                            "url": url,
                            "params": params
                        },
                        "meta": data.get("meta", {}),
                        "results": data.get("results", []),
                        "total_count": data.get("meta", {}).get("results", {}).get("total", 0),
                        "returned_count": len(data.get("results", [])),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    return json.dumps(result, ensure_ascii=False, indent=2)
                
                elif response.status_code == 404:
                    return json.dumps({
                        "status": "no_results",
                        "message": "未找到匹配的结果",
                        "query_info": {
                            "query_type": query_type,
                            "endpoint": endpoint,
                            "search_params": search_params
                        },
                        "suggestion": "尝试使用不同的搜索关键词或扩大搜索范围"
                    }, ensure_ascii=False, indent=2)
                
                elif response.status_code == 429:
                    # 速率限制，等待后重试
                    if attempt < max_retries - 1:
                        time.sleep(retry_delays[attempt])
                        continue
                    return json.dumps({
                        "status": "error",
                        "error": "API速率限制",
                        "message": "查询频率过高，已达到OpenFDA API速率限制",
                        "suggestion": "请稍后再试（1分钟后）"
                    }, ensure_ascii=False, indent=2)
                
                elif response.status_code >= 500:
                    # 服务器错误，重试
                    if attempt < max_retries - 1:
                        time.sleep(retry_delays[attempt])
                        continue
                    return json.dumps({
                        "status": "error",
                        "error": f"OpenFDA服务错误: {response.status_code}",
                        "message": "OpenFDA服务暂时不可用",
                        "suggestion": "请稍后再试，或访问https://open.fda.gov检查服务状态"
                    }, ensure_ascii=False, indent=2)
                
                else:
                    # 其他错误
                    error_data = {}
                    try:
                        error_data = response.json()
                    except:
                        error_data = {"text": response.text}
                    
                    return json.dumps({
                        "status": "error",
                        "error": f"API请求失败: {response.status_code}",
                        "error_details": error_data,
                        "query_info": {
                            "query_type": query_type,
                            "endpoint": endpoint,
                            "search_params": search_params
                        }
                    }, ensure_ascii=False, indent=2)
                    
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    time.sleep(retry_delays[attempt])
                    continue
                return json.dumps({
                    "status": "error",
                    "error": "请求超时",
                    "message": f"请求超过{timeout}秒未响应",
                    "suggestion": "请检查网络连接或稍后重试"
                }, ensure_ascii=False, indent=2)
            
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delays[attempt])
                    continue
                return json.dumps({
                    "status": "error",
                    "error": f"网络请求失败: {str(e)}",
                    "suggestion": "请检查网络连接"
                }, ensure_ascii=False, indent=2)
        
        # 所有重试都失败
        return json.dumps({
            "status": "error",
            "error": "查询失败",
            "message": f"已重试{max_retries}次，仍然失败",
            "suggestion": "请检查网络连接或稍后重试"
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": f"未知错误: {str(e)}",
            "query_info": {
                "query_type": query_type,
                "endpoint": endpoint
            }
        }, ensure_ascii=False, indent=2)


@tool
def openfda_endpoint_router(
    query_intent: str,
    keywords: List[str] = None,
    query_context: Dict[str, Any] = None
) -> str:
    """
    OpenFDA端点路由工具 - 根据查询意图智能选择合适的API端点
    
    Args:
        query_intent (str): 查询意图描述（自然语言）
        keywords (List[str]): 关键词列表
        query_context (Dict[str, Any]): 查询上下文信息
        
    Returns:
        str: JSON格式的路由决策结果
    """
    try:
        query_intent_lower = query_intent.lower()
        keywords_lower = [k.lower() for k in (keywords or [])]
        
        # 初始化路由结果
        routing_result = {
            "query_intent": query_intent,
            "keywords": keywords,
            "recommendations": []
        }
        
        # 药物相关路由
        drug_keywords = ["药物", "drug", "medication", "medicine", "pharmaceutical", 
                        "阿司匹林", "aspirin", "处方药", "prescription"]
        if any(kw in query_intent_lower for kw in drug_keywords) or \
           any(kw in keywords_lower for kw in drug_keywords):
            
            # 判断具体端点
            if any(word in query_intent_lower for word in ["不良", "adverse", "副作用", "side effect", "反应", "event"]):
                routing_result["recommendations"].append({
                    "query_type": "drug",
                    "endpoint": "event",
                    "confidence": 0.95,
                    "reason": "查询涉及药物不良事件/副作用",
                    "description": "药物不良事件报告数据库"
                })
            
            if any(word in query_intent_lower for word in ["标签", "label", "说明书", "成分", "ingredient"]):
                routing_result["recommendations"].append({
                    "query_type": "drug",
                    "endpoint": "label",
                    "confidence": 0.90,
                    "reason": "查询涉及药物标签/说明书信息",
                    "description": "药物标签和说明书数据"
                })
            
            if any(word in query_intent_lower for word in ["召回", "recall", "enforcement", "撤回"]):
                routing_result["recommendations"].append({
                    "query_type": "drug",
                    "endpoint": "enforcement",
                    "confidence": 0.92,
                    "reason": "查询涉及药物召回信息",
                    "description": "药物召回和执法行动数据"
                })
            
            # 如果没有具体端点匹配，默认推荐event
            if not routing_result["recommendations"]:
                routing_result["recommendations"].append({
                    "query_type": "drug",
                    "endpoint": "event",
                    "confidence": 0.75,
                    "reason": "药物相关查询，默认推荐不良事件数据",
                    "description": "药物不良事件报告数据库"
                })
        
        # 医疗设备相关路由
        device_keywords = ["设备", "device", "器械", "medical device", "仪器", "equipment"]
        if any(kw in query_intent_lower for kw in device_keywords) or \
           any(kw in keywords_lower for kw in device_keywords):
            
            if any(word in query_intent_lower for word in ["不良", "adverse", "事故", "malfunction", "event"]):
                routing_result["recommendations"].append({
                    "query_type": "device",
                    "endpoint": "event",
                    "confidence": 0.93,
                    "reason": "查询涉及医疗设备不良事件",
                    "description": "医疗设备不良事件报告数据"
                })
            
            if any(word in query_intent_lower for word in ["召回", "recall", "enforcement"]):
                routing_result["recommendations"].append({
                    "query_type": "device",
                    "endpoint": "enforcement",
                    "confidence": 0.91,
                    "reason": "查询涉及医疗设备召回",
                    "description": "医疗设备召回和执法行动数据"
                })
            
            if any(word in query_intent_lower for word in ["分类", "classification", "类别"]):
                routing_result["recommendations"].append({
                    "query_type": "device",
                    "endpoint": "classification",
                    "confidence": 0.88,
                    "reason": "查询涉及医疗设备分类",
                    "description": "医疗设备分类信息"
                })
            
            if not routing_result["recommendations"]:
                routing_result["recommendations"].append({
                    "query_type": "device",
                    "endpoint": "event",
                    "confidence": 0.75,
                    "reason": "设备相关查询，默认推荐不良事件数据",
                    "description": "医疗设备不良事件报告数据"
                })
        
        # 食品相关路由
        food_keywords = ["食品", "food", "dietary supplement", "营养品", "保健品"]
        if any(kw in query_intent_lower for kw in food_keywords) or \
           any(kw in keywords_lower for kw in food_keywords):
            
            if any(word in query_intent_lower for word in ["不良", "adverse", "event", "反应"]):
                routing_result["recommendations"].append({
                    "query_type": "food",
                    "endpoint": "event",
                    "confidence": 0.90,
                    "reason": "查询涉及食品不良事件",
                    "description": "食品不良事件报告数据"
                })
            
            if any(word in query_intent_lower for word in ["召回", "recall", "enforcement"]):
                routing_result["recommendations"].append({
                    "query_type": "food",
                    "endpoint": "enforcement",
                    "confidence": 0.89,
                    "reason": "查询涉及食品召回",
                    "description": "食品召回和执法行动数据"
                })
            
            if not routing_result["recommendations"]:
                routing_result["recommendations"].append({
                    "query_type": "food",
                    "endpoint": "event",
                    "confidence": 0.75,
                    "reason": "食品相关查询，默认推荐不良事件数据",
                    "description": "食品不良事件报告数据"
                })
        
        # 按置信度排序
        routing_result["recommendations"].sort(key=lambda x: x["confidence"], reverse=True)
        
        # 添加状态信息
        if routing_result["recommendations"]:
            routing_result["status"] = "success"
            routing_result["primary_recommendation"] = routing_result["recommendations"][0]
        else:
            routing_result["status"] = "no_match"
            routing_result["message"] = "无法确定查询类型，请提供更多信息"
            routing_result["suggestion"] = "请明确指定是查询药物(drug)、医疗设备(device)还是食品(food)数据"
        
        return json.dumps(routing_result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": f"路由失败: {str(e)}",
            "query_intent": query_intent
        }, ensure_ascii=False, indent=2)


@tool
def openfda_search_builder(
    field_conditions: List[Dict[str, Any]],
    logic_operator: str = "AND"
) -> str:
    """
    OpenFDA搜索参数构建工具 - 构建符合OpenFDA API规范的搜索查询字符串
    
    Args:
        field_conditions (List[Dict[str, Any]]): 字段条件列表，每个条件包含field、operator、value
        logic_operator (str): 逻辑运算符 (AND, OR)
        
    Returns:
        str: JSON格式的搜索参数构建结果
    """
    try:
        if not field_conditions:
            return json.dumps({
                "status": "error",
                "error": "字段条件列表不能为空"
            }, ensure_ascii=False, indent=2)
        
        search_parts = []
        
        for condition in field_conditions:
            field = condition.get("field")
            operator = condition.get("operator", ":")  # 默认精确匹配
            value = condition.get("value")
            
            if not field or value is None:
                continue
            
            # 处理不同的运算符
            if operator == ":":  # 精确匹配
                if isinstance(value, str):
                    # 对于字符串，需要加引号
                    search_parts.append(f'{field}:"{value}"')
                else:
                    search_parts.append(f'{field}:{value}')
            
            elif operator == "range":  # 范围查询
                start = condition.get("start")
                end = condition.get("end")
                if start and end:
                    search_parts.append(f'{field}:[{start}+TO+{end}]')
                elif start:
                    search_parts.append(f'{field}:[{start}+TO+*]')
                elif end:
                    search_parts.append(f'{field}:[*+TO+{end}]')
            
            elif operator == "exists":  # 字段存在
                search_parts.append(f'_exists_:{field}')
            
            elif operator == "missing":  # 字段缺失
                search_parts.append(f'_missing_:{field}')
        
        if not search_parts:
            return json.dumps({
                "status": "error",
                "error": "未能构建有效的搜索条件"
            }, ensure_ascii=False, indent=2)
        
        # 使用逻辑运算符连接
        logic_op = "+AND+" if logic_operator.upper() == "AND" else "+OR+"
        search_query = logic_op.join(search_parts)
        
        result = {
            "status": "success",
            "search_query": search_query,
            "field_conditions": field_conditions,
            "logic_operator": logic_operator,
            "parts_count": len(search_parts)
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": f"搜索参数构建失败: {str(e)}",
            "field_conditions": field_conditions
        }, ensure_ascii=False, indent=2)


@tool
def openfda_result_parser(
    raw_results: str,
    extract_fields: List[str] = None,
    max_items: int = 10
) -> str:
    """
    OpenFDA结果解析工具 - 解析和提取OpenFDA API响应中的关键信息
    
    Args:
        raw_results (str): 原始API响应（JSON字符串）
        extract_fields (List[str]): 要提取的字段列表
        max_items (int): 最大处理项数
        
    Returns:
        str: JSON格式的解析结果
    """
    try:
        # 解析JSON
        data = json.loads(raw_results)
        
        if data.get("status") == "error":
            return raw_results  # 直接返回错误信息
        
        results = data.get("results", [])
        
        if not results:
            return json.dumps({
                "status": "no_results",
                "message": "没有结果需要解析",
                "total_count": 0
            }, ensure_ascii=False, indent=2)
        
        # 限制处理数量
        results = results[:max_items]
        
        parsed_items = []
        
        for item in results:
            parsed_item = {}
            
            if extract_fields:
                # 提取指定字段
                for field in extract_fields:
                    parsed_item[field] = _extract_nested_field(item, field)
            else:
                # 自动提取关键字段（根据数据类型）
                parsed_item = _auto_extract_key_fields(item, data.get("query_info", {}))
            
            parsed_items.append(parsed_item)
        
        result = {
            "status": "success",
            "parsed_count": len(parsed_items),
            "total_available": data.get("total_count", len(results)),
            "items": parsed_items,
            "query_info": data.get("query_info", {}),
            "timestamp": data.get("timestamp", datetime.utcnow().isoformat())
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except json.JSONDecodeError as e:
        return json.dumps({
            "status": "error",
            "error": f"JSON解析失败: {str(e)}",
            "suggestion": "请确保输入的是有效的JSON字符串"
        }, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": f"结果解析失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def openfda_result_formatter(
    parsed_results: str,
    format_type: str = "summary"
) -> str:
    """
    OpenFDA结果格式化工具 - 将解析后的结果格式化为用户友好的文本
    
    Args:
        parsed_results (str): 解析后的结果（JSON字符串）
        format_type (str): 格式化类型 (summary, detailed, table)
        
    Returns:
        str: 格式化后的文本
    """
    try:
        data = json.loads(parsed_results)
        
        if data.get("status") == "error":
            return data.get("error", "未知错误")
        
        if data.get("status") == "no_results":
            return "未找到匹配的结果"
        
        items = data.get("items", [])
        query_info = data.get("query_info", {})
        
        if not items:
            return "没有结果需要格式化"
        
        # 根据格式类型生成输出
        if format_type == "summary":
            output = _format_summary(items, query_info, data)
        elif format_type == "detailed":
            output = _format_detailed(items, query_info, data)
        elif format_type == "table":
            output = _format_table(items, query_info, data)
        else:
            output = _format_summary(items, query_info, data)
        
        return output
        
    except json.JSONDecodeError as e:
        return f"格式化失败：JSON解析错误 - {str(e)}"
    
    except Exception as e:
        return f"格式化失败：{str(e)}"


# ========== 辅助函数 ==========

def _build_search_query(search_params: Dict[str, Any]) -> str:
    """构建搜索查询字符串"""
    parts = []
    
    for key, value in search_params.items():
        if value is None:
            continue
        
        if isinstance(value, dict):
            # 处理范围查询
            if "start" in value or "end" in value:
                start = value.get("start", "*")
                end = value.get("end", "*")
                parts.append(f'{key}:[{start}+TO+{end}]')
        elif isinstance(value, list):
            # OR条件
            or_parts = [f'{key}:"{v}"' if isinstance(v, str) else f'{key}:{v}' for v in value]
            parts.append(f'({"+OR+".join(or_parts)})')
        else:
            # 简单条件
            if isinstance(value, str):
                parts.append(f'{key}:"{value}"')
            else:
                parts.append(f'{key}:{value}')
    
    return "+AND+".join(parts)


def _extract_nested_field(item: Dict, field_path: str) -> Any:
    """提取嵌套字段值"""
    parts = field_path.split(".")
    value = item
    
    for part in parts:
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return None
    
    return value


def _auto_extract_key_fields(item: Dict, query_info: Dict) -> Dict:
    """自动提取关键字段"""
    query_type = query_info.get("query_type", "")
    endpoint = query_info.get("endpoint", "")
    
    extracted = {}
    
    # 药物不良事件
    if query_type == "drug" and endpoint == "event":
        extracted["patient_age"] = item.get("patient", {}).get("patientonsetage")
        extracted["patient_sex"] = item.get("patient", {}).get("patientsex")
        extracted["serious"] = item.get("serious")
        extracted["receivedate"] = item.get("receivedate")
        
        # 提取药物信息
        drugs = item.get("patient", {}).get("drug", [])
        if drugs:
            drug = drugs[0]
            extracted["drug_name"] = drug.get("medicinalproduct")
            extracted["drug_indication"] = drug.get("drugindication")
        
        # 提取反应信息
        reactions = item.get("patient", {}).get("reaction", [])
        if reactions:
            extracted["reactions"] = [r.get("reactionmeddrapt") for r in reactions[:3]]
    
    # 药物标签
    elif query_type == "drug" and endpoint == "label":
        extracted["brand_name"] = item.get("openfda", {}).get("brand_name", [None])[0]
        extracted["generic_name"] = item.get("openfda", {}).get("generic_name", [None])[0]
        extracted["manufacturer_name"] = item.get("openfda", {}).get("manufacturer_name", [None])[0]
        extracted["purpose"] = item.get("purpose")
        extracted["warnings"] = item.get("warnings")
    
    # 召回信息
    elif endpoint == "enforcement":
        extracted["product_description"] = item.get("product_description")
        extracted["reason_for_recall"] = item.get("reason_for_recall")
        extracted["recall_initiation_date"] = item.get("recall_initiation_date")
        extracted["classification"] = item.get("classification")
        extracted["status"] = item.get("status")
        extracted["recalling_firm"] = item.get("recalling_firm")
    
    # 医疗设备事件
    elif query_type == "device" and endpoint == "event":
        extracted["date_received"] = item.get("date_received")
        extracted["event_type"] = item.get("event_type")
        extracted["device_name"] = item.get("device", [{}])[0].get("brand_name") if item.get("device") else None
        extracted["manufacturer"] = item.get("device", [{}])[0].get("manufacturer_d_name") if item.get("device") else None
        extracted["event_description"] = item.get("mdr_text", [{}])[0].get("text") if item.get("mdr_text") else None
    
    # 如果没有提取到任何字段，返回原始数据的子集
    if not extracted:
        extracted = {k: v for k, v in list(item.items())[:5]}
    
    return extracted


def _format_summary(items: List[Dict], query_info: Dict, data: Dict) -> str:
    """格式化为摘要格式"""
    lines = []
    
    # 标题
    query_type = query_info.get("query_type", "").upper()
    endpoint = query_info.get("endpoint", "").upper()
    lines.append(f"=== OpenFDA {query_type} {endpoint} 查询结果 ===\n")
    
    # 统计信息
    lines.append(f"总计找到: {data.get('total_available', 0)} 条记录")
    lines.append(f"当前显示: {data.get('parsed_count', 0)} 条记录\n")
    
    # 结果列表
    for i, item in enumerate(items, 1):
        lines.append(f"--- 记录 {i} ---")
        for key, value in item.items():
            if value is not None:
                if isinstance(value, list):
                    lines.append(f"{key}: {', '.join(str(v) for v in value)}")
                else:
                    lines.append(f"{key}: {value}")
        lines.append("")
    
    return "\n".join(lines)


def _format_detailed(items: List[Dict], query_info: Dict, data: Dict) -> str:
    """格式化为详细格式"""
    lines = []
    
    # 标题和查询信息
    lines.append("=" * 60)
    lines.append(f"OpenFDA 查询结果详情")
    lines.append("=" * 60)
    lines.append(f"\n查询类型: {query_info.get('query_type', 'N/A')}")
    lines.append(f"API端点: {query_info.get('endpoint', 'N/A')}")
    lines.append(f"查询时间: {data.get('timestamp', 'N/A')}")
    lines.append(f"\n总结果数: {data.get('total_available', 0)}")
    lines.append(f"当前显示: {data.get('parsed_count', 0)}\n")
    lines.append("=" * 60)
    
    # 详细结果
    for i, item in enumerate(items, 1):
        lines.append(f"\n【记录 {i}】")
        lines.append("-" * 60)
        
        for key, value in item.items():
            if value is not None:
                if isinstance(value, list):
                    lines.append(f"\n{key}:")
                    for v in value:
                        lines.append(f"  • {v}")
                elif isinstance(value, dict):
                    lines.append(f"\n{key}:")
                    for k, v in value.items():
                        lines.append(f"  {k}: {v}")
                else:
                    # 处理长文本
                    value_str = str(value)
                    if len(value_str) > 100:
                        lines.append(f"\n{key}:")
                        lines.append(f"  {value_str[:100]}...")
                    else:
                        lines.append(f"{key}: {value_str}")
    
    lines.append("\n" + "=" * 60)
    
    return "\n".join(lines)


def _format_table(items: List[Dict], query_info: Dict, data: Dict) -> str:
    """格式化为表格格式"""
    if not items:
        return "没有数据"
    
    # 获取所有字段
    all_keys = set()
    for item in items:
        all_keys.update(item.keys())
    
    keys = sorted(list(all_keys))
    
    # 计算列宽
    col_widths = {}
    for key in keys:
        col_widths[key] = max(len(key), 20)  # 最小20字符
    
    lines = []
    
    # 标题
    lines.append(f"OpenFDA {query_info.get('query_type', '')} {query_info.get('endpoint', '')} 结果")
    lines.append(f"共 {data.get('total_available', 0)} 条，显示 {data.get('parsed_count', 0)} 条\n")
    
    # 表头
    header = " | ".join(key.ljust(col_widths[key]) for key in keys)
    lines.append(header)
    lines.append("-" * len(header))
    
    # 数据行
    for item in items:
        row_values = []
        for key in keys:
            value = item.get(key)
            if value is None:
                value_str = "N/A"
            elif isinstance(value, list):
                value_str = ", ".join(str(v) for v in value[:2])
                if len(value) > 2:
                    value_str += "..."
            else:
                value_str = str(value)
            
            # 截断过长的值
            if len(value_str) > col_widths[key]:
                value_str = value_str[:col_widths[key]-3] + "..."
            
            row_values.append(value_str.ljust(col_widths[key]))
        
        lines.append(" | ".join(row_values))
    
    return "\n".join(lines)
