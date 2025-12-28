#!/usr/bin/env python3
"""
FDA API Integration Tools

Provides tools for querying openFDA API endpoints, managing cache,
parsing queries, formatting data, and tracking data sources.
"""

import json
import hashlib
import os
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
from strands import tool


# Cache configuration
CACHE_DIR = ".cache/fda_data_query_agent"
CACHE_EXPIRATION_HOURS = 24


def _get_cache_key(query_type: str, query_params: Dict[str, Any]) -> str:
    """Generate cache key from query parameters"""
    # Normalize and sort parameters for consistent hashing
    normalized = json.dumps(query_params, sort_keys=True)
    hash_value = hashlib.md5(f"{query_type}_{normalized}".encode()).hexdigest()
    return hash_value


def _get_cache_path(query_type: str, cache_key: str) -> Path:
    """Get cache file path"""
    cache_dir = Path(CACHE_DIR) / query_type
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{cache_key}.json"


def _read_cache(cache_path: Path) -> Optional[Dict[str, Any]]:
    """Read from cache if exists and not expired"""
    try:
        if not cache_path.exists():
            return None
        
        with open(cache_path, 'r', encoding='utf-8') as f:
            cached_data = json.load(f)
        
        # Check expiration
        cached_time = cached_data.get("cached_at", 0)
        if time.time() - cached_time > CACHE_EXPIRATION_HOURS * 3600:
            return None
        
        return cached_data
    except Exception:
        return None


def _write_cache(cache_path: Path, data: Dict[str, Any]) -> None:
    """Write data to cache"""
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cached_data = {
            "cached_at": time.time(),
            "data": data
        }
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cached_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Warning: Failed to write cache: {e}")


@tool
def fda_api_query(
    endpoint: str,
    search_params: Optional[Dict[str, Any]] = None,
    limit: int = 10,
    skip: int = 0,
    use_cache: bool = True,
    timeout: int = 30
) -> str:
    """
    Query openFDA API endpoint with search parameters.
    
    This tool provides access to various openFDA API endpoints including:
    - drug/label: Drug product labeling
    - drug/event: Adverse drug events (FAERS)
    - drug/nda: New drug application approvals
    - device/classification: Medical device classifications
    - device/recall: Medical device recalls
    - device/event: Medical device adverse events (MAUDE)
    - food/enforcement: Food enforcement reports
    - food/event: Food adverse events
    
    Args:
        endpoint (str): FDA API endpoint (e.g., "drug/label", "device/recall")
        search_params (Dict[str, Any], optional): Search parameters as key-value pairs
            Example: {"brand_name": "Aspirin", "active_ingredient": "acetylsalicylic acid"}
        limit (int): Maximum number of results to return (default: 10, max: 100)
        skip (int): Number of results to skip for pagination (default: 0)
        use_cache (bool): Whether to use cached results (default: True)
        timeout (int): Request timeout in seconds (default: 30)
        
    Returns:
        str: JSON string containing query results, including:
            - results: List of matching records
            - total: Total number of matching records
            - endpoint: The API endpoint used
            - query_url: Full API request URL
            - cached: Whether results came from cache
            - timestamp: Query timestamp
    """
    try:
        import requests
        
        # Validate endpoint
        valid_endpoints = [
            "drug/label", "drug/event", "drug/nda",
            "device/classification", "device/recall", "device/event",
            "food/enforcement", "food/event"
        ]
        if endpoint not in valid_endpoints:
            return json.dumps({
                "error": f"Invalid endpoint: {endpoint}",
                "valid_endpoints": valid_endpoints
            }, ensure_ascii=False, indent=2)
        
        # Build query parameters
        if search_params is None:
            search_params = {}
        
        # Generate cache key
        cache_key = _get_cache_key(endpoint, {**search_params, "limit": limit, "skip": skip})
        cache_path = _get_cache_path(endpoint, cache_key)
        
        # Check cache
        if use_cache:
            cached_result = _read_cache(cache_path)
            if cached_result:
                result = cached_result["data"]
                result["cached"] = True
                result["cache_age_hours"] = (time.time() - cached_result["cached_at"]) / 3600
                return json.dumps(result, ensure_ascii=False, indent=2)
        
        # Build search query string
        search_parts = []
        for key, value in search_params.items():
            if isinstance(value, str):
                # Escape quotes and build search term
                escaped_value = value.replace('"', '\\"')
                search_parts.append(f'{key}:"{escaped_value}"')
            else:
                search_parts.append(f'{key}:{value}')
        
        search_query = " AND ".join(search_parts) if search_parts else ""
        
        # Build API URL
        base_url = f"https://api.fda.gov/{endpoint}.json"
        params = {
            "limit": min(limit, 100),
            "skip": skip
        }
        if search_query:
            params["search"] = search_query
        
        # Make API request
        response = requests.get(base_url, params=params, timeout=timeout)
        
        # Handle response
        if response.status_code == 200:
            api_data = response.json()
            result = {
                "success": True,
                "endpoint": endpoint,
                "query_url": response.url,
                "total": api_data.get("meta", {}).get("results", {}).get("total", 0),
                "results": api_data.get("results", []),
                "cached": False,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Write to cache
            if use_cache:
                _write_cache(cache_path, result)
            
            return json.dumps(result, ensure_ascii=False, indent=2)
        
        elif response.status_code == 404:
            return json.dumps({
                "success": False,
                "error": "No results found",
                "endpoint": endpoint,
                "search_params": search_params,
                "message": "未找到匹配的记录。建议：1) 检查搜索参数是否正确；2) 尝试使用更通用的关键词；3) 访问FDA官网进行人工查询。"
            }, ensure_ascii=False, indent=2)
        
        elif response.status_code == 400:
            return json.dumps({
                "success": False,
                "error": "Invalid request parameters",
                "endpoint": endpoint,
                "search_params": search_params,
                "status_code": 400,
                "message": "查询参数有误。请检查参数格式是否正确。"
            }, ensure_ascii=False, indent=2)
        
        elif response.status_code == 429:
            return json.dumps({
                "success": False,
                "error": "Rate limit exceeded",
                "status_code": 429,
                "message": "API请求频率超限。请稍后重试，或使用缓存数据。"
            }, ensure_ascii=False, indent=2)
        
        else:
            return json.dumps({
                "success": False,
                "error": f"API request failed with status code {response.status_code}",
                "status_code": response.status_code,
                "response": response.text[:500]
            }, ensure_ascii=False, indent=2)
    
    except requests.exceptions.Timeout:
        return json.dumps({
            "success": False,
            "error": "Request timeout",
            "endpoint": endpoint,
            "timeout": timeout,
            "message": "API请求超时。请稍后重试，或使用缓存数据。"
        }, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "endpoint": endpoint
        }, ensure_ascii=False, indent=2)


@tool
def fda_drug_search(
    brand_name: Optional[str] = None,
    generic_name: Optional[str] = None,
    active_ingredient: Optional[str] = None,
    manufacturer: Optional[str] = None,
    limit: int = 10,
    use_cache: bool = True
) -> str:
    """
    Search FDA drug database with flexible parameters.
    
    Searches drug/label endpoint for drug product labeling information.
    
    Args:
        brand_name (str, optional): Brand/trade name of the drug
        generic_name (str, optional): Generic name of the drug
        active_ingredient (str, optional): Active ingredient name
        manufacturer (str, optional): Manufacturer name
        limit (int): Maximum number of results (default: 10)
        use_cache (bool): Whether to use cached results (default: True)
        
    Returns:
        str: JSON string containing drug information including:
            - Product name and manufacturer
            - Active ingredients
            - Indications and usage
            - Warnings and precautions
            - Adverse reactions
            - Data source information
    """
    try:
        # Build search parameters
        search_params = {}
        if brand_name:
            search_params["openfda.brand_name"] = brand_name
        if generic_name:
            search_params["openfda.generic_name"] = generic_name
        if active_ingredient:
            search_params["openfda.substance_name"] = active_ingredient
        if manufacturer:
            search_params["openfda.manufacturer_name"] = manufacturer
        
        if not search_params:
            return json.dumps({
                "error": "At least one search parameter is required",
                "available_params": ["brand_name", "generic_name", "active_ingredient", "manufacturer"]
            }, ensure_ascii=False, indent=2)
        
        # Query API
        result_str = fda_api_query(
            endpoint="drug/label",
            search_params=search_params,
            limit=limit,
            use_cache=use_cache
        )
        
        result = json.loads(result_str)
        
        if not result.get("success"):
            return result_str
        
        # Format drug information
        formatted_results = []
        for item in result.get("results", []):
            openfda = item.get("openfda", {})
            formatted_item = {
                "brand_name": openfda.get("brand_name", ["N/A"])[0],
                "generic_name": openfda.get("generic_name", ["N/A"])[0],
                "manufacturer": openfda.get("manufacturer_name", ["N/A"])[0],
                "active_ingredients": openfda.get("substance_name", []),
                "indications": item.get("indications_and_usage", ["N/A"])[0][:500] if item.get("indications_and_usage") else "N/A",
                "warnings": item.get("warnings", ["N/A"])[0][:500] if item.get("warnings") else "N/A",
                "adverse_reactions": item.get("adverse_reactions", ["N/A"])[0][:500] if item.get("adverse_reactions") else "N/A",
                "dosage": item.get("dosage_and_administration", ["N/A"])[0][:500] if item.get("dosage_and_administration") else "N/A"
            }
            formatted_results.append(formatted_item)
        
        return json.dumps({
            "success": True,
            "query_type": "drug_search",
            "search_params": search_params,
            "total": result.get("total", 0),
            "results": formatted_results,
            "data_source": {
                "api_endpoint": "https://api.fda.gov/drug/label.json",
                "query_url": result.get("query_url"),
                "timestamp": result.get("timestamp")
            },
            "cached": result.get("cached", False)
        }, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Drug search failed: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def fda_device_search(
    device_name: Optional[str] = None,
    device_class: Optional[str] = None,
    manufacturer: Optional[str] = None,
    search_type: str = "classification",
    limit: int = 10,
    use_cache: bool = True
) -> str:
    """
    Search FDA medical device database.
    
    Args:
        device_name (str, optional): Device name or description
        device_class (str, optional): Device class (1, 2, or 3)
        manufacturer (str, optional): Manufacturer name
        search_type (str): Type of device data to search
            - "classification": Device classifications (default)
            - "recall": Device recalls
            - "event": Adverse events (MAUDE)
        limit (int): Maximum number of results (default: 10)
        use_cache (bool): Whether to use cached results (default: True)
        
    Returns:
        str: JSON string containing device information
    """
    try:
        # Validate search type
        valid_types = ["classification", "recall", "event"]
        if search_type not in valid_types:
            return json.dumps({
                "error": f"Invalid search_type: {search_type}",
                "valid_types": valid_types
            }, ensure_ascii=False, indent=2)
        
        # Build search parameters
        search_params = {}
        if search_type == "classification":
            if device_name:
                search_params["device_name"] = device_name
            if device_class:
                search_params["device_class"] = device_class
        elif search_type == "recall":
            if device_name:
                search_params["product_description"] = device_name
            if manufacturer:
                search_params["firm_fei_number"] = manufacturer
        elif search_type == "event":
            if device_name:
                search_params["device.generic_name"] = device_name
            if manufacturer:
                search_params["device.manufacturer_d_name"] = manufacturer
        
        if not search_params:
            return json.dumps({
                "error": "At least one search parameter is required",
                "available_params": ["device_name", "device_class", "manufacturer"]
            }, ensure_ascii=False, indent=2)
        
        # Query API
        endpoint_map = {
            "classification": "device/classification",
            "recall": "device/recall",
            "event": "device/event"
        }
        
        result_str = fda_api_query(
            endpoint=endpoint_map[search_type],
            search_params=search_params,
            limit=limit,
            use_cache=use_cache
        )
        
        result = json.loads(result_str)
        
        if not result.get("success"):
            return result_str
        
        # Format device information
        formatted_results = []
        for item in result.get("results", []):
            if search_type == "classification":
                formatted_item = {
                    "device_name": item.get("device_name", "N/A"),
                    "device_class": item.get("device_class", "N/A"),
                    "medical_specialty": item.get("medical_specialty_description", "N/A"),
                    "regulation_number": item.get("regulation_number", "N/A"),
                    "product_code": item.get("product_code", "N/A")
                }
            elif search_type == "recall":
                formatted_item = {
                    "product_description": item.get("product_description", "N/A"),
                    "recall_reason": item.get("reason_for_recall", "N/A"),
                    "recall_date": item.get("recall_initiation_date", "N/A"),
                    "firm_name": item.get("recalling_firm", "N/A"),
                    "classification": item.get("classification", "N/A")
                }
            else:  # event
                device_info = item.get("device", [{}])[0] if item.get("device") else {}
                formatted_item = {
                    "device_name": device_info.get("generic_name", "N/A"),
                    "manufacturer": device_info.get("manufacturer_d_name", "N/A"),
                    "event_type": item.get("event_type", "N/A"),
                    "date_received": item.get("date_received", "N/A"),
                    "device_problem": device_info.get("device_problem_codes", [])
                }
            
            formatted_results.append(formatted_item)
        
        return json.dumps({
            "success": True,
            "query_type": f"device_{search_type}",
            "search_params": search_params,
            "total": result.get("total", 0),
            "results": formatted_results,
            "data_source": {
                "api_endpoint": f"https://api.fda.gov/{endpoint_map[search_type]}.json",
                "query_url": result.get("query_url"),
                "timestamp": result.get("timestamp")
            },
            "cached": result.get("cached", False)
        }, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Device search failed: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def fda_food_search(
    product_name: Optional[str] = None,
    manufacturer: Optional[str] = None,
    search_type: str = "enforcement",
    limit: int = 10,
    use_cache: bool = True
) -> str:
    """
    Search FDA food database for enforcement actions and adverse events.
    
    Args:
        product_name (str, optional): Food product name or description
        manufacturer (str, optional): Manufacturer or distributor name
        search_type (str): Type of food data to search
            - "enforcement": Food enforcement reports (recalls, market withdrawals)
            - "event": Food adverse events
        limit (int): Maximum number of results (default: 10)
        use_cache (bool): Whether to use cached results (default: True)
        
    Returns:
        str: JSON string containing food safety information
    """
    try:
        # Validate search type
        valid_types = ["enforcement", "event"]
        if search_type not in valid_types:
            return json.dumps({
                "error": f"Invalid search_type: {search_type}",
                "valid_types": valid_types
            }, ensure_ascii=False, indent=2)
        
        # Build search parameters
        search_params = {}
        if search_type == "enforcement":
            if product_name:
                search_params["product_description"] = product_name
            if manufacturer:
                search_params["recalling_firm"] = manufacturer
        elif search_type == "event":
            if product_name:
                search_params["products.name_brand"] = product_name
        
        if not search_params:
            return json.dumps({
                "error": "At least one search parameter is required",
                "available_params": ["product_name", "manufacturer"]
            }, ensure_ascii=False, indent=2)
        
        # Query API
        endpoint_map = {
            "enforcement": "food/enforcement",
            "event": "food/event"
        }
        
        result_str = fda_api_query(
            endpoint=endpoint_map[search_type],
            search_params=search_params,
            limit=limit,
            use_cache=use_cache
        )
        
        result = json.loads(result_str)
        
        if not result.get("success"):
            return result_str
        
        # Format food information
        formatted_results = []
        for item in result.get("results", []):
            if search_type == "enforcement":
                formatted_item = {
                    "product_description": item.get("product_description", "N/A"),
                    "reason_for_recall": item.get("reason_for_recall", "N/A"),
                    "recall_date": item.get("recall_initiation_date", "N/A"),
                    "firm_name": item.get("recalling_firm", "N/A"),
                    "classification": item.get("classification", "N/A"),
                    "status": item.get("status", "N/A")
                }
            else:  # event
                products = item.get("products", [])
                formatted_item = {
                    "product_name": products[0].get("name_brand", "N/A") if products else "N/A",
                    "event_date": item.get("date_created", "N/A"),
                    "reactions": item.get("consumer.age", "N/A"),
                    "outcomes": item.get("outcomes", [])
                }
            
            formatted_results.append(formatted_item)
        
        return json.dumps({
            "success": True,
            "query_type": f"food_{search_type}",
            "search_params": search_params,
            "total": result.get("total", 0),
            "results": formatted_results,
            "data_source": {
                "api_endpoint": f"https://api.fda.gov/{endpoint_map[search_type]}.json",
                "query_url": result.get("query_url"),
                "timestamp": result.get("timestamp")
            },
            "cached": result.get("cached", False)
        }, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Food search failed: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def fda_adverse_events_search(
    product_name: str,
    product_type: str = "drug",
    date_range: Optional[Dict[str, str]] = None,
    limit: int = 10,
    use_cache: bool = True
) -> str:
    """
    Search FDA adverse events database for drugs, devices, or foods.
    
    Args:
        product_name (str): Product name to search for
        product_type (str): Type of product - "drug", "device", or "food"
        date_range (Dict[str, str], optional): Date range filter
            Example: {"start": "20230101", "end": "20231231"}
        limit (int): Maximum number of results (default: 10)
        use_cache (bool): Whether to use cached results (default: True)
        
    Returns:
        str: JSON string containing adverse event information
    """
    try:
        # Validate product type
        valid_types = ["drug", "device", "food"]
        if product_type not in valid_types:
            return json.dumps({
                "error": f"Invalid product_type: {product_type}",
                "valid_types": valid_types
            }, ensure_ascii=False, indent=2)
        
        # Build search parameters
        search_params = {}
        if product_type == "drug":
            search_params["patient.drug.medicinalproduct"] = product_name
        elif product_type == "device":
            search_params["device.generic_name"] = product_name
        elif product_type == "food":
            search_params["products.name_brand"] = product_name
        
        # Add date range if provided
        if date_range:
            start_date = date_range.get("start")
            end_date = date_range.get("end")
            if start_date and end_date:
                search_params["receivedate"] = f"[{start_date} TO {end_date}]"
        
        # Query API
        endpoint = f"{product_type}/event"
        result_str = fda_api_query(
            endpoint=endpoint,
            search_params=search_params,
            limit=limit,
            use_cache=use_cache
        )
        
        result = json.loads(result_str)
        
        if not result.get("success"):
            return result_str
        
        # Format adverse event information
        formatted_results = []
        for item in result.get("results", []):
            if product_type == "drug":
                reactions = item.get("patient", {}).get("reaction", [])
                formatted_item = {
                    "product_name": product_name,
                    "report_date": item.get("receivedate", "N/A"),
                    "serious": item.get("serious", "N/A"),
                    "reactions": [r.get("reactionmeddrapt", "N/A") for r in reactions[:5]],
                    "patient_age": item.get("patient", {}).get("patientonsetage", "N/A"),
                    "patient_sex": item.get("patient", {}).get("patientsex", "N/A")
                }
            elif product_type == "device":
                formatted_item = {
                    "device_name": product_name,
                    "event_date": item.get("date_received", "N/A"),
                    "event_type": item.get("event_type", "N/A"),
                    "device_problems": item.get("device", [{}])[0].get("device_problem_codes", [])[:3] if item.get("device") else [],
                    "patient_problems": item.get("patient", [{}])[0].get("patient_problems", [])[:3] if item.get("patient") else []
                }
            else:  # food
                formatted_item = {
                    "product_name": product_name,
                    "event_date": item.get("date_created", "N/A"),
                    "reactions": item.get("reactions", [])[:5],
                    "outcomes": item.get("outcomes", [])
                }
            
            formatted_results.append(formatted_item)
        
        return json.dumps({
            "success": True,
            "query_type": f"{product_type}_adverse_events",
            "product_name": product_name,
            "total": result.get("total", 0),
            "results": formatted_results,
            "data_source": {
                "api_endpoint": f"https://api.fda.gov/{endpoint}.json",
                "query_url": result.get("query_url"),
                "timestamp": result.get("timestamp")
            },
            "cached": result.get("cached", False)
        }, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Adverse events search failed: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def fda_recall_search(
    product_name: str,
    product_type: str = "drug",
    classification: Optional[str] = None,
    limit: int = 10,
    use_cache: bool = True
) -> str:
    """
    Search FDA recall database for drugs, devices, or foods.
    
    Args:
        product_name (str): Product name to search for
        product_type (str): Type of product - "drug", "device", or "food"
        classification (str, optional): Recall classification (Class I, II, or III)
        limit (int): Maximum number of results (default: 10)
        use_cache (bool): Whether to use cached results (default: True)
        
    Returns:
        str: JSON string containing recall information
    """
    try:
        # Validate product type
        valid_types = ["drug", "device", "food"]
        if product_type not in valid_types:
            return json.dumps({
                "error": f"Invalid product_type: {product_type}",
                "valid_types": valid_types
            }, ensure_ascii=False, indent=2)
        
        # Build search parameters
        search_params = {"product_description": product_name}
        if classification:
            search_params["classification"] = classification
        
        # Query API
        endpoint = f"{product_type}/enforcement" if product_type == "food" else f"{product_type}/recall"
        
        result_str = fda_api_query(
            endpoint=endpoint,
            search_params=search_params,
            limit=limit,
            use_cache=use_cache
        )
        
        result = json.loads(result_str)
        
        if not result.get("success"):
            return result_str
        
        # Format recall information
        formatted_results = []
        for item in result.get("results", []):
            formatted_item = {
                "product_description": item.get("product_description", "N/A"),
                "reason_for_recall": item.get("reason_for_recall", "N/A"),
                "recall_date": item.get("recall_initiation_date", "N/A"),
                "firm_name": item.get("recalling_firm", "N/A"),
                "classification": item.get("classification", "N/A"),
                "status": item.get("status", "N/A"),
                "distribution_pattern": item.get("distribution_pattern", "N/A")
            }
            formatted_results.append(formatted_item)
        
        return json.dumps({
            "success": True,
            "query_type": f"{product_type}_recall",
            "product_name": product_name,
            "total": result.get("total", 0),
            "results": formatted_results,
            "data_source": {
                "api_endpoint": f"https://api.fda.gov/{endpoint}.json",
                "query_url": result.get("query_url"),
                "timestamp": result.get("timestamp")
            },
            "cached": result.get("cached", False)
        }, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Recall search failed: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def fda_nda_search(
    application_number: Optional[str] = None,
    sponsor_name: Optional[str] = None,
    brand_name: Optional[str] = None,
    limit: int = 10,
    use_cache: bool = True
) -> str:
    """
    Search FDA New Drug Application (NDA) approvals database.
    
    Args:
        application_number (str, optional): NDA application number
        sponsor_name (str, optional): Sponsor/company name
        brand_name (str, optional): Brand name of the drug
        limit (int): Maximum number of results (default: 10)
        use_cache (bool): Whether to use cached results (default: True)
        
    Returns:
        str: JSON string containing NDA approval information
    """
    try:
        # Build search parameters
        search_params = {}
        if application_number:
            search_params["application_number"] = application_number
        if sponsor_name:
            search_params["sponsor_name"] = sponsor_name
        if brand_name:
            search_params["openfda.brand_name"] = brand_name
        
        if not search_params:
            return json.dumps({
                "error": "At least one search parameter is required",
                "available_params": ["application_number", "sponsor_name", "brand_name"]
            }, ensure_ascii=False, indent=2)
        
        # Query API
        result_str = fda_api_query(
            endpoint="drug/nda",
            search_params=search_params,
            limit=limit,
            use_cache=use_cache
        )
        
        result = json.loads(result_str)
        
        if not result.get("success"):
            return result_str
        
        # Format NDA information
        formatted_results = []
        for item in result.get("results", []):
            openfda = item.get("openfda", {})
            formatted_item = {
                "application_number": item.get("application_number", "N/A"),
                "sponsor_name": item.get("sponsor_name", "N/A"),
                "brand_name": openfda.get("brand_name", ["N/A"])[0],
                "generic_name": openfda.get("generic_name", ["N/A"])[0],
                "approval_date": item.get("submissions", [{}])[0].get("submission_status_date", "N/A") if item.get("submissions") else "N/A",
                "application_type": item.get("application_type", "N/A")
            }
            formatted_results.append(formatted_item)
        
        return json.dumps({
            "success": True,
            "query_type": "nda_approval",
            "search_params": search_params,
            "total": result.get("total", 0),
            "results": formatted_results,
            "data_source": {
                "api_endpoint": "https://api.fda.gov/drug/nda.json",
                "query_url": result.get("query_url"),
                "timestamp": result.get("timestamp")
            },
            "cached": result.get("cached", False)
        }, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"NDA search failed: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def clear_fda_cache(
    query_type: Optional[str] = None,
    older_than_hours: Optional[int] = None
) -> str:
    """
    Clear FDA API cache.
    
    Args:
        query_type (str, optional): Specific query type to clear
            (e.g., "drug/label", "device/recall"). If None, clears all cache.
        older_than_hours (int, optional): Only clear cache older than specified hours.
            If None, clears all cache regardless of age.
        
    Returns:
        str: JSON string containing cache clearing results
    """
    try:
        cache_base = Path(CACHE_DIR)
        if not cache_base.exists():
            return json.dumps({
                "success": True,
                "message": "Cache directory does not exist",
                "cleared_files": 0
            }, ensure_ascii=False, indent=2)
        
        cleared_count = 0
        total_size = 0
        current_time = time.time()
        cutoff_time = current_time - (older_than_hours * 3600) if older_than_hours else 0
        
        # Determine which directories to clear
        if query_type:
            # Clear specific query type
            cache_dirs = [cache_base / query_type.replace("/", "_")]
        else:
            # Clear all query types
            cache_dirs = [d for d in cache_base.iterdir() if d.is_dir()]
        
        # Clear cache files
        for cache_dir in cache_dirs:
            if not cache_dir.exists():
                continue
            
            for cache_file in cache_dir.glob("*.json"):
                try:
                    # Check file age if older_than_hours is specified
                    if older_than_hours:
                        file_mtime = cache_file.stat().st_mtime
                        if file_mtime > cutoff_time:
                            continue
                    
                    # Get file size before deletion
                    file_size = cache_file.stat().st_size
                    total_size += file_size
                    
                    # Delete file
                    cache_file.unlink()
                    cleared_count += 1
                except Exception as e:
                    print(f"Warning: Failed to delete {cache_file}: {e}")
        
        return json.dumps({
            "success": True,
            "cleared_files": cleared_count,
            "total_size_bytes": total_size,
            "query_type": query_type or "all",
            "older_than_hours": older_than_hours
        }, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Cache clearing failed: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def get_cache_stats() -> str:
    """
    Get FDA API cache statistics.
    
    Returns:
        str: JSON string containing cache statistics including:
            - Total cache size
            - Number of cached queries by type
            - Cache hit rate (if available)
            - Oldest and newest cache entries
    """
    try:
        cache_base = Path(CACHE_DIR)
        if not cache_base.exists():
            return json.dumps({
                "success": True,
                "total_files": 0,
                "total_size_bytes": 0,
                "cache_by_type": {}
            }, ensure_ascii=False, indent=2)
        
        stats = {
            "total_files": 0,
            "total_size_bytes": 0,
            "cache_by_type": {},
            "oldest_cache": None,
            "newest_cache": None
        }
        
        oldest_time = None
        newest_time = None
        
        # Scan cache directories
        for cache_dir in cache_base.iterdir():
            if not cache_dir.is_dir():
                continue
            
            query_type = cache_dir.name
            type_files = 0
            type_size = 0
            
            for cache_file in cache_dir.glob("*.json"):
                try:
                    file_stat = cache_file.stat()
                    type_files += 1
                    type_size += file_stat.st_size
                    
                    # Track oldest and newest
                    if oldest_time is None or file_stat.st_mtime < oldest_time:
                        oldest_time = file_stat.st_mtime
                        stats["oldest_cache"] = datetime.fromtimestamp(file_stat.st_mtime).isoformat()
                    
                    if newest_time is None or file_stat.st_mtime > newest_time:
                        newest_time = file_stat.st_mtime
                        stats["newest_cache"] = datetime.fromtimestamp(file_stat.st_mtime).isoformat()
                
                except Exception as e:
                    print(f"Warning: Failed to stat {cache_file}: {e}")
            
            if type_files > 0:
                stats["cache_by_type"][query_type] = {
                    "files": type_files,
                    "size_bytes": type_size
                }
                stats["total_files"] += type_files
                stats["total_size_bytes"] += type_size
        
        stats["success"] = True
        return json.dumps(stats, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to get cache stats: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def format_fda_response(
    raw_response: str,
    format_type: str = "summary"
) -> str:
    """
    Format raw FDA API response into user-friendly format.
    
    Args:
        raw_response (str): Raw JSON response from FDA API query tools
        format_type (str): Format type - "summary", "detailed", or "raw"
            - "summary": Brief summary with key information
            - "detailed": Comprehensive information with all fields
            - "raw": Original API response
        
    Returns:
        str: JSON string containing formatted response
    """
    try:
        response_data = json.loads(raw_response)
        
        if not response_data.get("success"):
            return raw_response
        
        if format_type == "raw":
            return raw_response
        
        query_type = response_data.get("query_type", "unknown")
        results = response_data.get("results", [])
        
        if format_type == "summary":
            # Generate brief summaries
            summaries = []
            for idx, item in enumerate(results, 1):
                if "drug" in query_type:
                    summary = f"{idx}. {item.get('brand_name', 'N/A')} ({item.get('generic_name', 'N/A')}) - {item.get('manufacturer', 'N/A')}"
                elif "device" in query_type:
                    summary = f"{idx}. {item.get('device_name', item.get('product_description', 'N/A'))}"
                elif "food" in query_type:
                    summary = f"{idx}. {item.get('product_name', item.get('product_description', 'N/A'))}"
                else:
                    summary = f"{idx}. {str(item)[:100]}..."
                summaries.append(summary)
            
            return json.dumps({
                "success": True,
                "format": "summary",
                "query_type": query_type,
                "total_results": response_data.get("total", 0),
                "summaries": summaries,
                "data_source": response_data.get("data_source")
            }, ensure_ascii=False, indent=2)
        
        else:  # detailed
            return json.dumps({
                "success": True,
                "format": "detailed",
                "query_type": query_type,
                "total_results": response_data.get("total", 0),
                "results": results,
                "data_source": response_data.get("data_source")
            }, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to format response: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def extract_data_fields(
    fda_response: str,
    fields: List[str]
) -> str:
    """
    Extract specific fields from FDA API response.
    
    Args:
        fda_response (str): JSON response from FDA API query tools
        fields (List[str]): List of field names to extract
            Example: ["brand_name", "manufacturer", "indications"]
        
    Returns:
        str: JSON string containing extracted fields
    """
    try:
        response_data = json.loads(fda_response)
        
        if not response_data.get("success"):
            return fda_response
        
        results = response_data.get("results", [])
        extracted_results = []
        
        for item in results:
            extracted_item = {}
            for field in fields:
                # Handle nested fields with dot notation
                if "." in field:
                    parts = field.split(".")
                    value = item
                    for part in parts:
                        if isinstance(value, dict):
                            value = value.get(part)
                        else:
                            value = None
                            break
                    extracted_item[field] = value
                else:
                    extracted_item[field] = item.get(field)
            
            extracted_results.append(extracted_item)
        
        return json.dumps({
            "success": True,
            "extracted_fields": fields,
            "results": extracted_results,
            "total": len(extracted_results),
            "data_source": response_data.get("data_source")
        }, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to extract fields: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def validate_fda_data(
    fda_response: str
) -> str:
    """
    Validate FDA API response data quality and completeness.
    
    Checks for:
    - Missing required fields
    - Empty or null values
    - Data consistency
    - Completeness score
    
    Args:
        fda_response (str): JSON response from FDA API query tools
        
    Returns:
        str: JSON string containing validation results
    """
    try:
        response_data = json.loads(fda_response)
        
        if not response_data.get("success"):
            return json.dumps({
                "success": False,
                "error": "Cannot validate unsuccessful response"
            }, ensure_ascii=False, indent=2)
        
        results = response_data.get("results", [])
        query_type = response_data.get("query_type", "unknown")
        
        # Define required fields by query type
        required_fields_map = {
            "drug_search": ["brand_name", "generic_name", "manufacturer"],
            "device_classification": ["device_name", "device_class"],
            "device_recall": ["product_description", "reason_for_recall"],
            "food_enforcement": ["product_description", "reason_for_recall"],
            "drug_adverse_events": ["report_date", "reactions"],
            "nda_approval": ["application_number", "sponsor_name"]
        }
        
        required_fields = required_fields_map.get(query_type, [])
        
        # Validate each result
        validation_results = []
        for idx, item in enumerate(results):
            missing_fields = []
            empty_fields = []
            
            for field in required_fields:
                if field not in item:
                    missing_fields.append(field)
                elif item[field] in [None, "", "N/A", []]:
                    empty_fields.append(field)
            
            completeness = 1.0 - (len(missing_fields) + len(empty_fields)) / max(len(required_fields), 1)
            
            validation_results.append({
                "result_index": idx,
                "completeness_score": round(completeness * 100, 2),
                "missing_fields": missing_fields,
                "empty_fields": empty_fields,
                "is_complete": len(missing_fields) == 0 and len(empty_fields) == 0
            })
        
        # Overall statistics
        avg_completeness = sum(v["completeness_score"] for v in validation_results) / max(len(validation_results), 1)
        complete_count = sum(1 for v in validation_results if v["is_complete"])
        
        return json.dumps({
            "success": True,
            "query_type": query_type,
            "total_results": len(results),
            "complete_results": complete_count,
            "average_completeness": round(avg_completeness, 2),
            "validation_results": validation_results,
            "data_quality": "high" if avg_completeness >= 90 else "medium" if avg_completeness >= 70 else "low"
        }, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Validation failed: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def generate_data_source_info(
    fda_response: str
) -> str:
    """
    Generate comprehensive data source information for FDA query results.
    
    Creates DataSource objects with full traceability including:
    - API endpoint
    - Complete request URL
    - Query parameters
    - Timestamp
    - Cache status
    
    Args:
        fda_response (str): JSON response from FDA API query tools
        
    Returns:
        str: JSON string containing data source information
    """
    try:
        response_data = json.loads(fda_response)
        
        if not response_data.get("success"):
            return fda_response
        
        data_source = response_data.get("data_source", {})
        
        source_info = {
            "success": True,
            "data_source": {
                "api_name": "openFDA API",
                "api_endpoint": data_source.get("api_endpoint"),
                "query_url": data_source.get("query_url"),
                "timestamp": data_source.get("timestamp"),
                "cached": response_data.get("cached", False),
                "query_type": response_data.get("query_type"),
                "total_results": response_data.get("total", 0),
                "verification_url": "https://open.fda.gov/apis/",
                "data_freshness": "Real-time" if not response_data.get("cached") else f"Cached (age: {response_data.get('cache_age_hours', 0):.1f} hours)",
                "reliability": "Official FDA data source"
            }
        }
        
        return json.dumps(source_info, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to generate source info: {str(e)}"
        }, ensure_ascii=False, indent=2)
