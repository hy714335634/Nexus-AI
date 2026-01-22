#!/usr/bin/env python3
"""
FDA API集成工具

提供与FDA openFDA API交互的核心工具函数，支持药物、医疗设备、食品、
不良事件和召回数据的查询。所有工具自动处理数据解析、来源标注和错误处理。
"""

import json
import hashlib
import time
from typing import Dict, List, Any, Optional, Union
from urllib.parse import urlencode, quote
from strands import tool

try:
    import requests
except ImportError:
    requests = None


# FDA API基础配置
FDA_API_BASE_URL = "https://api.fda.gov"
FDA_API_TIMEOUT = 10  # 秒
FDA_API_RETRY_TIMES = 3
FDA_API_RETRY_DELAY = 1  # 秒


def _build_fda_url(endpoint: str, params: Dict[str, Any]) -> str:
    """
    构建FDA API完整URL
    
    Args:
        endpoint: API端点路径
        params: 查询参数
        
    Returns:
        完整的API URL
    """
    # 过滤空参数
    filtered_params = {k: v for k, v in params.items() if v is not None and v != ""}
    
    if not filtered_params:
        return f"{FDA_API_BASE_URL}{endpoint}"
    
    # 构建查询字符串
    query_string = urlencode(filtered_params)
    return f"{FDA_API_BASE_URL}{endpoint}?{query_string}"


def _call_fda_api(url: str, retry_times: int = FDA_API_RETRY_TIMES) -> Dict[str, Any]:
    """
    调用FDA API并处理重试
    
    Args:
        url: API URL
        retry_times: 重试次数
        
    Returns:
        API响应数据
        
    Raises:
        Exception: API调用失败
    """
    if not requests:
        raise ImportError("requests库未安装，请安装: pip install requests")
    
    last_error = None
    for attempt in range(retry_times):
        try:
            response = requests.get(
                url,
                headers={
                    "User-Agent": "FDA-Data-Query-Agent/1.0",
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip"
                },
                timeout=FDA_API_TIMEOUT
            )
            
            # 检查HTTP状态码
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return {"meta": {"results": {"total": 0}}, "results": []}
            elif response.status_code == 429:
                # 限流错误，等待更长时间
                if attempt < retry_times - 1:
                    time.sleep(60)
                    continue
                raise Exception("FDA API限流，请稍后重试")
            else:
                raise Exception(f"FDA API返回错误状态码: {response.status_code}")
                
        except requests.exceptions.Timeout:
            last_error = Exception("FDA API请求超时")
            if attempt < retry_times - 1:
                time.sleep(FDA_API_RETRY_DELAY * (2 ** attempt))  # 指数退避
                continue
        except requests.exceptions.ConnectionError:
            last_error = Exception("无法连接到FDA API")
            if attempt < retry_times - 1:
                time.sleep(FDA_API_RETRY_DELAY * (2 ** attempt))
                continue
        except Exception as e:
            last_error = e
            if attempt < retry_times - 1:
                time.sleep(FDA_API_RETRY_DELAY * (2 ** attempt))
                continue
    
    # 所有重试都失败
    raise last_error if last_error else Exception("FDA API调用失败")


def _annotate_source(data: Dict[str, Any], data_type: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    为数据自动注入来源标注
    
    Args:
        data: 原始数据
        data_type: 数据类型（drugs/devices/food/adverse_events/recalls）
        query_params: 查询参数
        
    Returns:
        标注后的数据
    """
    # 构建FDA官方链接
    base_urls = {
        "drugs": "https://open.fda.gov/apis/drug/",
        "devices": "https://open.fda.gov/apis/device/",
        "food": "https://open.fda.gov/apis/food/",
        "adverse_events": "https://open.fda.gov/apis/drug/event/",
        "recalls": "https://open.fda.gov/apis/"
    }
    
    source_info = {
        "source": "FDA openFDA API",
        "data_type": data_type,
        "api_url": base_urls.get(data_type, "https://open.fda.gov/apis/"),
        "query_timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "query_params": query_params
    }
    
    # 为结果数组中的每个项目添加来源信息
    if "results" in data and isinstance(data["results"], list):
        for item in data["results"]:
            if isinstance(item, dict):
                item["_fda_source"] = source_info.copy()
                
                # 添加具体记录的官方链接
                if data_type == "drugs":
                    if "application_number" in item:
                        item["_fda_source"]["official_link"] = f"https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&ApplNo={item['application_number']}"
                elif data_type == "devices":
                    if "k_number" in item:
                        item["_fda_source"]["official_link"] = f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID={item['k_number']}"
                elif data_type in ["adverse_events", "recalls"]:
                    if "report_number" in item or "recall_number" in item:
                        item["_fda_source"]["official_link"] = "https://www.fda.gov/safety/recalls-market-withdrawals-safety-alerts"
    
    # 在顶层添加来源元数据
    data["_metadata"] = {
        "source": source_info,
        "retrieved_at": source_info["query_timestamp"],
        "total_results": data.get("meta", {}).get("results", {}).get("total", 0)
    }
    
    return data


@tool
def query_fda_drugs(
    search_term: str,
    search_field: str = "openfda.brand_name",
    limit: int = 10,
    skip: int = 0,
    sort_field: Optional[str] = None,
    sort_order: str = "desc"
) -> str:
    """
    查询FDA药物批准信息、标签、NDC代码等数据
    
    此工具调用FDA openFDA Drug API，支持按品牌名、通用名、活性成分、
    制造商、NDC代码、申请号等多种方式查询药物信息。
    
    Args:
        search_term (str): 搜索词，如药品名称、活性成分等
        search_field (str): 搜索字段，可选值:
            - openfda.brand_name: 品牌名（商品名）
            - openfda.generic_name: 通用名
            - openfda.substance_name: 活性成分
            - openfda.manufacturer_name: 制造商
            - openfda.product_ndc: NDC代码
            - application_number: 申请号
        limit (int): 返回结果数量限制，默认10，最大100
        skip (int): 跳过的结果数量，用于分页
        sort_field (Optional[str]): 排序字段，如"receivedate"
        sort_order (str): 排序顺序，"asc"或"desc"
        
    Returns:
        str: JSON格式的查询结果，包含药物数据和来源标注
        
    Example:
        >>> result = query_fda_drugs("aspirin", "openfda.brand_name", limit=5)
        >>> data = json.loads(result)
        >>> print(data["results"][0]["openfda"]["brand_name"])
    """
    try:
        # 验证和清理参数
        limit = min(max(1, limit), 100)
        skip = max(0, skip)
        
        # 构建查询参数
        search_query = f'{search_field}:"{search_term}"'
        params = {
            "search": search_query,
            "limit": limit,
            "skip": skip
        }
        
        # 添加排序参数
        if sort_field:
            params["sort"] = f"{sort_field}:{sort_order}"
        
        # 构建URL
        url = _build_fda_url("/drug/label.json", params)
        
        # 调用API
        response_data = _call_fda_api(url)
        
        # 标注来源
        annotated_data = _annotate_source(response_data, "drugs", params)
        
        # 构建返回结果
        result = {
            "status": "success",
            "query_type": "drugs",
            "search_term": search_term,
            "search_field": search_field,
            "total_results": annotated_data.get("meta", {}).get("results", {}).get("total", 0),
            "returned_count": len(annotated_data.get("results", [])),
            "data": annotated_data,
            "from_cache": False
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "status": "error",
            "query_type": "drugs",
            "search_term": search_term,
            "error_type": type(e).__name__,
            "error_message": str(e),
            "suggestions": [
                "检查药品名称拼写是否正确",
                "尝试使用通用名而非商品名",
                "使用更简单的搜索词",
                "稍后重试（可能是API临时故障）"
            ]
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)


@tool
def query_fda_devices(
    search_term: str,
    search_field: str = "device_name",
    limit: int = 10,
    skip: int = 0,
    device_class: Optional[str] = None
) -> str:
    """
    查询FDA医疗设备分类、批准、510(k)/PMA信息等
    
    此工具调用FDA openFDA Device API，支持按设备名称、制造商、
    产品代码、510(k)号等查询医疗设备信息。
    
    Args:
        search_term (str): 搜索词，如设备名称、制造商等
        search_field (str): 搜索字段，可选值:
            - device_name: 设备名称
            - openfda.device_name: openFDA设备名称
            - applicant: 申请人/制造商
            - product_code: 产品代码
            - k_number: 510(k)号
        limit (int): 返回结果数量限制，默认10，最大100
        skip (int): 跳过的结果数量，用于分页
        device_class (Optional[str]): 设备分类过滤，可选值: "1", "2", "3"
        
    Returns:
        str: JSON格式的查询结果，包含设备数据和来源标注
        
    Example:
        >>> result = query_fda_devices("pacemaker", "device_name", limit=5)
        >>> data = json.loads(result)
        >>> print(data["results"][0]["device_name"])
    """
    try:
        # 验证和清理参数
        limit = min(max(1, limit), 100)
        skip = max(0, skip)
        
        # 构建查询参数
        search_query = f'{search_field}:"{search_term}"'
        
        # 添加设备分类过滤
        if device_class and device_class in ["1", "2", "3"]:
            search_query += f' AND device_class:"{device_class}"'
        
        params = {
            "search": search_query,
            "limit": limit,
            "skip": skip
        }
        
        # 构建URL（使用510k端点）
        url = _build_fda_url("/device/510k.json", params)
        
        # 调用API
        response_data = _call_fda_api(url)
        
        # 标注来源
        annotated_data = _annotate_source(response_data, "devices", params)
        
        # 构建返回结果
        result = {
            "status": "success",
            "query_type": "devices",
            "search_term": search_term,
            "search_field": search_field,
            "device_class": device_class,
            "total_results": annotated_data.get("meta", {}).get("results", {}).get("total", 0),
            "returned_count": len(annotated_data.get("results", [])),
            "data": annotated_data,
            "from_cache": False
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "status": "error",
            "query_type": "devices",
            "search_term": search_term,
            "error_type": type(e).__name__,
            "error_message": str(e),
            "suggestions": [
                "检查设备名称拼写是否正确",
                "尝试使用设备的通用名称",
                "提供制造商名称以缩小搜索范围",
                "稍后重试（可能是API临时故障）"
            ]
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)


@tool
def query_fda_food(
    search_term: str,
    search_field: str = "product_description",
    data_type: str = "recall",
    limit: int = 10,
    skip: int = 0,
    recall_class: Optional[str] = None
) -> str:
    """
    查询FDA食品召回、执法行动、不良事件等数据
    
    此工具调用FDA openFDA Food API，支持查询食品召回信息、
    执法行动和不良事件报告。
    
    Args:
        search_term (str): 搜索词，如产品名称、公司名等
        search_field (str): 搜索字段，可选值:
            - product_description: 产品描述
            - recalling_firm: 召回公司
            - recall_number: 召回编号
            - reason_for_recall: 召回原因
        data_type (str): 数据类型，可选值:
            - recall: 召回信息（默认）
            - enforcement: 执法行动
            - event: 不良事件
        limit (int): 返回结果数量限制，默认10，最大100
        skip (int): 跳过的结果数量，用于分页
        recall_class (Optional[str]): 召回级别过滤，可选值: "Class I", "Class II", "Class III"
        
    Returns:
        str: JSON格式的查询结果，包含食品数据和来源标注
        
    Example:
        >>> result = query_fda_food("salmonella", "reason_for_recall", limit=5)
        >>> data = json.loads(result)
        >>> print(data["results"][0]["product_description"])
    """
    try:
        # 验证和清理参数
        limit = min(max(1, limit), 100)
        skip = max(0, skip)
        
        # 构建查询参数
        search_query = f'{search_field}:"{search_term}"'
        
        # 添加召回级别过滤
        if recall_class and data_type == "recall":
            search_query += f' AND classification:"{recall_class}"'
        
        params = {
            "search": search_query,
            "limit": limit,
            "skip": skip
        }
        
        # 根据数据类型选择端点
        endpoint_map = {
            "recall": "/food/recall.json",
            "enforcement": "/food/enforcement.json",
            "event": "/food/event.json"
        }
        endpoint = endpoint_map.get(data_type, "/food/recall.json")
        
        # 构建URL
        url = _build_fda_url(endpoint, params)
        
        # 调用API
        response_data = _call_fda_api(url)
        
        # 标注来源
        annotated_data = _annotate_source(response_data, "food", params)
        
        # 构建返回结果
        result = {
            "status": "success",
            "query_type": "food",
            "data_type": data_type,
            "search_term": search_term,
            "search_field": search_field,
            "recall_class": recall_class,
            "total_results": annotated_data.get("meta", {}).get("results", {}).get("total", 0),
            "returned_count": len(annotated_data.get("results", [])),
            "data": annotated_data,
            "from_cache": False
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "status": "error",
            "query_type": "food",
            "data_type": data_type,
            "search_term": search_term,
            "error_type": type(e).__name__,
            "error_message": str(e),
            "suggestions": [
                "检查产品名称或召回原因的拼写",
                "尝试使用更通用的搜索词",
                "检查召回级别是否正确（Class I/II/III）",
                "稍后重试（可能是API临时故障）"
            ]
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)


@tool
def query_fda_adverse_events(
    search_term: str,
    search_field: str = "patient.drug.openfda.brand_name",
    product_type: str = "drug",
    limit: int = 10,
    skip: int = 0,
    serious_only: bool = False,
    date_range: Optional[str] = None
) -> str:
    """
    查询FDA药物或设备的不良事件报告数据
    
    此工具调用FDA openFDA Adverse Events API，支持查询药物和
    医疗设备相关的不良事件报告。
    
    Args:
        search_term (str): 搜索词，如产品名称
        search_field (str): 搜索字段，可选值:
            - patient.drug.openfda.brand_name: 药品品牌名
            - patient.drug.openfda.generic_name: 药品通用名
            - patient.drug.medicinalproduct: 药品名称
            - device.brand_name: 设备品牌名
            - device.generic_name: 设备通用名
        product_type (str): 产品类型，可选值: "drug" 或 "device"
        limit (int): 返回结果数量限制，默认10，最大100
        skip (int): 跳过的结果数量，用于分页
        serious_only (bool): 是否仅返回严重不良事件，默认False
        date_range (Optional[str]): 日期范围过滤，格式: "20200101:20231231"
        
    Returns:
        str: JSON格式的查询结果，包含不良事件数据和来源标注
        
    Example:
        >>> result = query_fda_adverse_events("aspirin", serious_only=True, limit=5)
        >>> data = json.loads(result)
        >>> print(data["results"][0]["patient"]["reaction"])
    """
    try:
        # 验证和清理参数
        limit = min(max(1, limit), 100)
        skip = max(0, skip)
        
        # 构建查询参数
        search_query = f'{search_field}:"{search_term}"'
        
        # 添加严重性过滤
        if serious_only:
            search_query += ' AND serious:"1"'
        
        # 添加日期范围过滤
        if date_range:
            search_query += f' AND receivedate:[{date_range}]'
        
        params = {
            "search": search_query,
            "limit": limit,
            "skip": skip
        }
        
        # 根据产品类型选择端点
        endpoint = "/drug/event.json" if product_type == "drug" else "/device/event.json"
        
        # 构建URL
        url = _build_fda_url(endpoint, params)
        
        # 调用API
        response_data = _call_fda_api(url)
        
        # 标注来源
        annotated_data = _annotate_source(response_data, "adverse_events", params)
        
        # 构建返回结果
        result = {
            "status": "success",
            "query_type": "adverse_events",
            "product_type": product_type,
            "search_term": search_term,
            "search_field": search_field,
            "serious_only": serious_only,
            "date_range": date_range,
            "total_results": annotated_data.get("meta", {}).get("results", {}).get("total", 0),
            "returned_count": len(annotated_data.get("results", [])),
            "data": annotated_data,
            "from_cache": False
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "status": "error",
            "query_type": "adverse_events",
            "product_type": product_type,
            "search_term": search_term,
            "error_type": type(e).__name__,
            "error_message": str(e),
            "suggestions": [
                "检查产品名称是否正确",
                "尝试使用更通用的产品名称",
                "检查日期范围格式（应为YYYYMMDD:YYYYMMDD）",
                "稍后重试（可能是API临时故障）"
            ]
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)


@tool
def query_fda_recalls(
    search_term: str,
    search_field: str = "product_description",
    product_type: str = "drug",
    limit: int = 10,
    skip: int = 0,
    recall_status: Optional[str] = None,
    recall_class: Optional[str] = None
) -> str:
    """
    查询FDA召回信息（药物、设备、食品）
    
    此工具调用FDA openFDA Recall API，支持查询药物、医疗设备
    和食品的召回信息。
    
    Args:
        search_term (str): 搜索词，如产品名称、公司名等
        search_field (str): 搜索字段，可选值:
            - product_description: 产品描述
            - recalling_firm: 召回公司
            - recall_number: 召回编号
            - reason_for_recall: 召回原因
        product_type (str): 产品类型，可选值: "drug", "device", "food"
        limit (int): 返回结果数量限制，默认10，最大100
        skip (int): 跳过的结果数量，用于分页
        recall_status (Optional[str]): 召回状态过滤，可选值:
            - "Ongoing": 进行中
            - "Completed": 已完成
            - "Terminated": 已终止
        recall_class (Optional[str]): 召回级别过滤，可选值: "Class I", "Class II", "Class III"
        
    Returns:
        str: JSON格式的查询结果，包含召回数据和来源标注
        
    Example:
        >>> result = query_fda_recalls("insulin", "product_description", product_type="drug", limit=5)
        >>> data = json.loads(result)
        >>> print(data["results"][0]["recall_number"])
    """
    try:
        # 验证和清理参数
        limit = min(max(1, limit), 100)
        skip = max(0, skip)
        
        # 构建查询参数
        search_query = f'{search_field}:"{search_term}"'
        
        # 添加召回状态过滤
        if recall_status:
            search_query += f' AND status:"{recall_status}"'
        
        # 添加召回级别过滤
        if recall_class:
            search_query += f' AND classification:"{recall_class}"'
        
        params = {
            "search": search_query,
            "limit": limit,
            "skip": skip
        }
        
        # 根据产品类型选择端点
        endpoint_map = {
            "drug": "/drug/enforcement.json",
            "device": "/device/recall.json",
            "food": "/food/enforcement.json"
        }
        endpoint = endpoint_map.get(product_type, "/drug/enforcement.json")
        
        # 构建URL
        url = _build_fda_url(endpoint, params)
        
        # 调用API
        response_data = _call_fda_api(url)
        
        # 标注来源
        annotated_data = _annotate_source(response_data, "recalls", params)
        
        # 构建返回结果
        result = {
            "status": "success",
            "query_type": "recalls",
            "product_type": product_type,
            "search_term": search_term,
            "search_field": search_field,
            "recall_status": recall_status,
            "recall_class": recall_class,
            "total_results": annotated_data.get("meta", {}).get("results", {}).get("total", 0),
            "returned_count": len(annotated_data.get("results", [])),
            "data": annotated_data,
            "from_cache": False
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "status": "error",
            "query_type": "recalls",
            "product_type": product_type,
            "search_term": search_term,
            "error_type": type(e).__name__,
            "error_message": str(e),
            "suggestions": [
                "检查产品名称或召回编号是否正确",
                "尝试使用更通用的搜索词",
                "检查召回级别和状态是否正确",
                "稍后重试（可能是API临时故障）"
            ]
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)


@tool
def search_fda_comprehensive(
    search_term: str,
    search_types: List[str] = None,
    limit_per_type: int = 5,
    include_adverse_events: bool = True,
    include_recalls: bool = True
) -> str:
    """
    综合搜索FDA数据（跨多个数据类型）
    
    此工具执行跨多个FDA数据类型的综合搜索，适用于用户不确定
    数据类型或需要全面信息的场景。
    
    Args:
        search_term (str): 搜索词，如产品名称
        search_types (List[str]): 要搜索的数据类型列表，可选值:
            - "drugs": 药物
            - "devices": 医疗设备
            - "food": 食品
            如果不提供，则搜索所有类型
        limit_per_type (int): 每种类型返回的结果数量，默认5
        include_adverse_events (bool): 是否包含不良事件数据，默认True
        include_recalls (bool): 是否包含召回数据，默认True
        
    Returns:
        str: JSON格式的综合查询结果，包含各类型数据和来源标注
        
    Example:
        >>> result = search_fda_comprehensive("aspirin", search_types=["drugs"], limit_per_type=3)
        >>> data = json.loads(result)
        >>> print(data["drugs"]["total_results"])
    """
    try:
        # 默认搜索所有类型
        if not search_types:
            search_types = ["drugs", "devices", "food"]
        
        # 验证参数
        limit_per_type = min(max(1, limit_per_type), 20)
        
        # 存储各类型的查询结果
        comprehensive_results = {
            "status": "success",
            "search_term": search_term,
            "search_types": search_types,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "results": {}
        }
        
        # 查询药物数据
        if "drugs" in search_types:
            try:
                drugs_result = query_fda_drugs(search_term, limit=limit_per_type)
                drugs_data = json.loads(drugs_result)
                comprehensive_results["results"]["drugs"] = drugs_data
                
                # 如果需要，查询药物相关的不良事件
                if include_adverse_events and drugs_data.get("status") == "success":
                    ae_result = query_fda_adverse_events(
                        search_term,
                        product_type="drug",
                        limit=limit_per_type
                    )
                    ae_data = json.loads(ae_result)
                    comprehensive_results["results"]["drugs_adverse_events"] = ae_data
                
                # 如果需要，查询药物召回
                if include_recalls and drugs_data.get("status") == "success":
                    recall_result = query_fda_recalls(
                        search_term,
                        product_type="drug",
                        limit=limit_per_type
                    )
                    recall_data = json.loads(recall_result)
                    comprehensive_results["results"]["drugs_recalls"] = recall_data
            except Exception as e:
                comprehensive_results["results"]["drugs"] = {
                    "status": "error",
                    "error_message": str(e)
                }
        
        # 查询设备数据
        if "devices" in search_types:
            try:
                devices_result = query_fda_devices(search_term, limit=limit_per_type)
                devices_data = json.loads(devices_result)
                comprehensive_results["results"]["devices"] = devices_data
                
                # 如果需要，查询设备相关的不良事件
                if include_adverse_events and devices_data.get("status") == "success":
                    ae_result = query_fda_adverse_events(
                        search_term,
                        search_field="device.brand_name",
                        product_type="device",
                        limit=limit_per_type
                    )
                    ae_data = json.loads(ae_result)
                    comprehensive_results["results"]["devices_adverse_events"] = ae_data
                
                # 如果需要，查询设备召回
                if include_recalls and devices_data.get("status") == "success":
                    recall_result = query_fda_recalls(
                        search_term,
                        product_type="device",
                        limit=limit_per_type
                    )
                    recall_data = json.loads(recall_result)
                    comprehensive_results["results"]["devices_recalls"] = recall_data
            except Exception as e:
                comprehensive_results["results"]["devices"] = {
                    "status": "error",
                    "error_message": str(e)
                }
        
        # 查询食品数据
        if "food" in search_types:
            try:
                food_result = query_fda_food(search_term, limit=limit_per_type)
                food_data = json.loads(food_result)
                comprehensive_results["results"]["food"] = food_data
            except Exception as e:
                comprehensive_results["results"]["food"] = {
                    "status": "error",
                    "error_message": str(e)
                }
        
        # 统计成功和失败的查询
        success_count = sum(1 for r in comprehensive_results["results"].values() 
                          if isinstance(r, dict) and r.get("status") == "success")
        total_count = len(comprehensive_results["results"])
        
        comprehensive_results["summary"] = {
            "total_queries": total_count,
            "successful_queries": success_count,
            "failed_queries": total_count - success_count
        }
        
        return json.dumps(comprehensive_results, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "status": "error",
            "query_type": "comprehensive",
            "search_term": search_term,
            "error_type": type(e).__name__,
            "error_message": str(e),
            "suggestions": [
                "检查搜索词是否正确",
                "尝试指定具体的数据类型（drugs/devices/food）",
                "稍后重试（可能是API临时故障）"
            ]
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)


@tool
def get_fda_api_stats() -> str:
    """
    获取FDA API统计信息和健康状态
    
    此工具用于检查FDA API的可用性和响应性能。
    
    Returns:
        str: JSON格式的API统计信息
        
    Example:
        >>> result = get_fda_api_stats()
        >>> data = json.loads(result)
        >>> print(data["api_status"])
    """
    try:
        # 测试各个端点的可用性
        endpoints = {
            "drugs": "/drug/label.json?limit=1",
            "devices": "/device/510k.json?limit=1",
            "food": "/food/recall.json?limit=1",
            "drug_events": "/drug/event.json?limit=1"
        }
        
        endpoint_status = {}
        for name, endpoint in endpoints.items():
            try:
                start_time = time.time()
                url = f"{FDA_API_BASE_URL}{endpoint}"
                response = requests.get(url, timeout=5)
                response_time = time.time() - start_time
                
                endpoint_status[name] = {
                    "status": "available" if response.status_code == 200 else "error",
                    "status_code": response.status_code,
                    "response_time_ms": round(response_time * 1000, 2)
                }
            except Exception as e:
                endpoint_status[name] = {
                    "status": "unavailable",
                    "error": str(e)
                }
        
        # 判断整体状态
        available_count = sum(1 for s in endpoint_status.values() if s.get("status") == "available")
        total_count = len(endpoint_status)
        
        overall_status = "healthy" if available_count == total_count else \
                        "degraded" if available_count > 0 else "unavailable"
        
        result = {
            "status": "success",
            "api_status": overall_status,
            "base_url": FDA_API_BASE_URL,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "endpoints": endpoint_status,
            "summary": {
                "total_endpoints": total_count,
                "available_endpoints": available_count,
                "unavailable_endpoints": total_count - available_count
            }
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e)
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)
