#!/usr/bin/env python3
"""
HTTP客户端工具模板

提供API调用、认证管理、数据同步等功能
"""

import json
import requests
import time
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin, urlparse
from strands import tool


@tool
def api_client(url: str, method: str = "GET", headers: Dict[str, str] = None, 
               data: Dict[str, Any] = None, timeout: int = 30) -> str:
    """
    API客户端工具
    
    Args:
        url (str): API端点URL
        method (str): HTTP方法 (GET, POST, PUT, DELETE)
        headers (Dict[str, str]): 请求头
        data (Dict[str, Any]): 请求数据
        timeout (int): 超时时间（秒）
        
    Returns:
        str: JSON格式的响应结果
    """
    try:
        if headers is None:
            headers = {"Content-Type": "application/json"}
        
        if data is None:
            data = {}
        
        # 发送请求
        response = requests.request(
            method=method.upper(),
            url=url,
            headers=headers,
            json=data if method.upper() in ["POST", "PUT", "PATCH"] else None,
            params=data if method.upper() == "GET" else None,
            timeout=timeout
        )
        
        # 构建响应结果
        result = {
            "status_code": response.status_code,
            "url": url,
            "method": method.upper(),
            "headers": dict(response.headers),
            "success": response.status_code < 400
        }
        
        # 尝试解析响应内容
        try:
            if response.headers.get("content-type", "").startswith("application/json"):
                result["data"] = response.json()
            else:
                result["data"] = response.text
        except:
            result["data"] = response.text
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except requests.exceptions.Timeout:
        return json.dumps({
            "error": "请求超时",
            "url": url,
            "timeout": timeout
        }, ensure_ascii=False, indent=2)
    except requests.exceptions.RequestException as e:
        return json.dumps({
            "error": f"请求失败: {str(e)}",
            "url": url
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "error": f"未知错误: {str(e)}",
            "url": url
        }, ensure_ascii=False, indent=2)


@tool
def auth_manager(auth_type: str, credentials: Dict[str, str]) -> str:
    """
    认证管理工具
    
    Args:
        auth_type (str): 认证类型 (bearer, basic, api_key, oauth2)
        credentials (Dict[str, str]): 认证凭据
        
    Returns:
        str: JSON格式的认证信息
    """
    try:
        result = {"auth_type": auth_type, "headers": {}}
        
        if auth_type == "bearer":
            token = credentials.get("token")
            if not token:
                raise ValueError("Bearer认证需要token字段")
            result["headers"]["Authorization"] = f"Bearer {token}"
            
        elif auth_type == "basic":
            username = credentials.get("username")
            password = credentials.get("password")
            if not username or not password:
                raise ValueError("Basic认证需要username和password字段")
            import base64
            auth_string = f"{username}:{password}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()
            result["headers"]["Authorization"] = f"Basic {encoded_auth}"
            
        elif auth_type == "api_key":
            key_name = credentials.get("key_name", "X-API-Key")
            key_value = credentials.get("key_value")
            if not key_value:
                raise ValueError("API Key认证需要key_value字段")
            result["headers"][key_name] = key_value
            
        elif auth_type == "oauth2":
            token = credentials.get("access_token")
            if not token:
                raise ValueError("OAuth2认证需要access_token字段")
            result["headers"]["Authorization"] = f"Bearer {token}"
            
        else:
            raise ValueError(f"不支持的认证类型: {auth_type}")
        
        result["success"] = True
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "auth_type": auth_type
        }, ensure_ascii=False, indent=2)


@tool
def data_sync(source_url: str, target_url: str, sync_type: str = "full", 
              headers: Dict[str, str] = None) -> str:
    """
    数据同步工具
    
    Args:
        source_url (str): 源数据URL
        target_url (str): 目标数据URL
        sync_type (str): 同步类型 (full, incremental)
        headers (Dict[str, str]): 请求头
        
    Returns:
        str: JSON格式的同步结果
    """
    try:
        if headers is None:
            headers = {"Content-Type": "application/json"}
        
        # 获取源数据
        source_response = requests.get(source_url, headers=headers, timeout=30)
        if source_response.status_code != 200:
            raise Exception(f"获取源数据失败: {source_response.status_code}")
        
        source_data = source_response.json()
        
        # 发送到目标
        target_response = requests.post(
            target_url,
            headers=headers,
            json=source_data,
            timeout=30
        )
        
        result = {
            "sync_type": sync_type,
            "source_url": source_url,
            "target_url": target_url,
            "source_status": source_response.status_code,
            "target_status": target_response.status_code,
            "success": target_response.status_code < 400,
            "data_size": len(str(source_data))
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": f"数据同步失败: {str(e)}",
            "source_url": source_url,
            "target_url": target_url
        }, ensure_ascii=False, indent=2)


@tool
def webhook_sender(webhook_url: str, payload: Dict[str, Any], 
                  event_type: str = "notification") -> str:
    """
    Webhook发送工具
    
    Args:
        webhook_url (str): Webhook URL
        payload (Dict[str, Any]): 发送的数据
        event_type (str): 事件类型
        
    Returns:
        str: JSON格式的发送结果
    """
    try:
        # 添加事件类型到payload
        payload["event_type"] = event_type
        payload["timestamp"] = int(time.time())
        
        # 发送webhook
        response = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        result = {
            "webhook_url": webhook_url,
            "event_type": event_type,
            "status_code": response.status_code,
            "success": response.status_code < 400,
            "response": response.text if response.status_code < 400 else None
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": f"Webhook发送失败: {str(e)}",
            "webhook_url": webhook_url,
            "event_type": event_type
        }, ensure_ascii=False, indent=2)
