#!/usr/bin/env python3
"""
搜索引擎客户端工具

提供多搜索引擎集成和API调用功能，支持SerpAPI和直接HTTP请求
"""

import json
import time
import re
import os
import random
from typing import Dict, List, Any, Optional, Union
from urllib.parse import quote_plus, urlparse

import boto3
import requests
from bs4 import BeautifulSoup

from strands import tool


@tool
def serpapi_search(query: str, engine: str = "google", api_key: Optional[str] = None, 
                  params: Optional[Dict[str, Any]] = None) -> str:
    """
    使用SerpAPI搜索信息
    
    Args:
        query: 搜索查询
        engine: 搜索引擎，支持"google"、"bing"、"baidu"、"duckduckgo"
        api_key: SerpAPI API密钥，如果不提供则尝试从环境变量获取
        params: 额外的搜索参数
    
    Returns:
        JSON格式的搜索结果
    """
    try:
        # 获取API密钥
        if not api_key:
            api_key = os.environ.get("SERPAPI_KEY")
            if not api_key:
                return json.dumps({
                    "status": "error",
                    "message": "未提供SerpAPI密钥，请通过参数或环境变量SERPAPI_KEY提供",
                    "results": None
                }, ensure_ascii=False)
        
        # 构建基本参数
        base_params = {
            "q": query,
            "api_key": api_key
        }
        
        # 添加额外参数
        if params:
            base_params.update(params)
        
        # 根据引擎选择API端点
        if engine.lower() == "google":
            url = "https://serpapi.com/search"
            base_params["engine"] = "google"
        elif engine.lower() == "bing":
            url = "https://serpapi.com/search"
            base_params["engine"] = "bing"
        elif engine.lower() == "baidu":
            url = "https://serpapi.com/search"
            base_params["engine"] = "baidu"
        elif engine.lower() == "duckduckgo":
            url = "https://serpapi.com/search"
            base_params["engine"] = "duckduckgo"
        else:
            return json.dumps({
                "status": "error",
                "message": f"不支持的搜索引擎: {engine}",
                "results": None
            }, ensure_ascii=False)
        
        # 发送请求
        response = requests.get(url, params=base_params)
        
        # 检查响应
        if response.status_code != 200:
            return json.dumps({
                "status": "error",
                "message": f"SerpAPI请求失败，状态码: {response.status_code}，响应: {response.text}",
                "results": None
            }, ensure_ascii=False)
        
        # 解析响应
        results = response.json()
        
        # 构建结果
        search_results = {
            "status": "success",
            "message": f"成功使用{engine}搜索: {query}",
            "query": query,
            "engine": engine,
            "search_metadata": {
                "timestamp": time.time(),
                "params": base_params.copy()
            },
            "results": results
        }
        
        # 移除API密钥
        if "api_key" in search_results["search_metadata"]["params"]:
            search_results["search_metadata"]["params"]["api_key"] = "***"
        
        return json.dumps(search_results, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"SerpAPI搜索时发生错误: {str(e)}",
            "query": query,
            "engine": engine,
            "results": None
        }, ensure_ascii=False)


@tool
def web_page_extractor(url: str, extract_type: str = "text", 
                      timeout: int = 10) -> str:
    """
    提取网页内容
    
    Args:
        url: 网页URL
        extract_type: 提取类型，支持"text"、"html"、"links"、"all"
        timeout: 请求超时时间(秒)
    
    Returns:
        JSON格式的提取结果
    """
    try:
        # 验证URL
        if not url.startswith(("http://", "https://")):
            return json.dumps({
                "status": "error",
                "message": "URL必须以http://或https://开头",
                "url": url,
                "content": None
            }, ensure_ascii=False)
        
        # 添加请求头，模拟浏览器
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0"
        }
        
        # 发送请求
        response = requests.get(url, headers=headers, timeout=timeout)
        
        # 检查响应
        if response.status_code != 200:
            return json.dumps({
                "status": "error",
                "message": f"请求失败，状态码: {response.status_code}",
                "url": url,
                "content": None
            }, ensure_ascii=False)
        
        # 解析响应
        soup = BeautifulSoup(response.text, "html.parser")
        
        # 根据提取类型返回不同内容
        result = {
            "status": "success",
            "message": f"成功提取网页内容",
            "url": url,
            "extraction_type": extract_type,
            "metadata": {
                "title": soup.title.string if soup.title else "无标题",
                "content_length": len(response.text),
                "content_type": response.headers.get("Content-Type", "未知"),
                "timestamp": time.time()
            }
        }
        
        if extract_type == "text" or extract_type == "all":
            # 移除脚本和样式元素
            for script in soup(["script", "style"]):
                script.extract()
            
            # 获取文本
            text = soup.get_text()
            
            # 处理文本
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = "\n".join(chunk for chunk in chunks if chunk)
            
            result["text_content"] = text[:100000]  # 限制文本长度
            
        if extract_type == "html" or extract_type == "all":
            result["html_content"] = response.text[:100000]  # 限制HTML长度
            
        if extract_type == "links" or extract_type == "all":
            links = []
            for link in soup.find_all("a", href=True):
                href = link["href"]
                # 处理相对URL
                if not href.startswith(("http://", "https://")):
                    base_url = "{0.scheme}://{0.netloc}".format(urlparse(url))
                    if href.startswith("/"):
                        href = base_url + href
                    else:
                        href = base_url + "/" + href
                
                links.append({
                    "text": link.get_text().strip(),
                    "url": href
                })
            
            result["links"] = links[:100]  # 限制链接数量
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"提取网页内容时发生错误: {str(e)}",
            "url": url,
            "content": None
        }, ensure_ascii=False)


@tool
def multi_engine_search(query: str, engines: List[str] = None, 
                       max_results: int = 5, api_key: Optional[str] = None) -> str:
    """
    使用多个搜索引擎进行搜索，自动切换引擎
    
    Args:
        query: 搜索查询
        engines: 要使用的搜索引擎列表，默认为["google", "bing", "duckduckgo"]
        max_results: 每个搜索引擎返回的最大结果数，默认为5
        api_key: SerpAPI API密钥，如果不提供则尝试从环境变量获取
    
    Returns:
        JSON格式的多引擎搜索结果
    """
    try:
        # 设置默认搜索引擎
        if not engines:
            engines = ["google", "bing", "duckduckgo"]
        
        # 获取API密钥
        if not api_key:
            api_key = os.environ.get("SERPAPI_KEY")
        
        # 初始化结果
        all_results = {
            "status": "success",
            "message": f"多引擎搜索: {query}",
            "query": query,
            "search_metadata": {
                "engines": engines,
                "max_results": max_results,
                "timestamp": time.time()
            },
            "engine_results": {}
        }
        
        # 尝试每个搜索引擎
        for engine in engines:
            try:
                # 构建搜索参数
                params = {
                    "num": max_results,
                    "gl": "us",
                    "hl": "en"
                }
                
                # 调用SerpAPI
                if api_key:
                    engine_result_json = serpapi_search(query, engine, api_key, params)
                    engine_result = json.loads(engine_result_json)
                    
                    if engine_result["status"] == "success":
                        all_results["engine_results"][engine] = {
                            "status": "success",
                            "results": engine_result["results"]
                        }
                    else:
                        all_results["engine_results"][engine] = {
                            "status": "error",
                            "message": engine_result["message"]
                        }
                else:
                    # 如果没有API密钥，使用直接HTTP请求
                    search_url = _build_search_url(engine, query)
                    
                    # 添加到结果，但标记为需要HTTP请求
                    all_results["engine_results"][engine] = {
                        "status": "pending",
                        "message": "需要使用web_page_extractor工具获取搜索结果",
                        "search_url": search_url
                    }
            except Exception as e:
                all_results["engine_results"][engine] = {
                    "status": "error",
                    "message": f"搜索引擎 {engine} 出错: {str(e)}"
                }
        
        # 检查是否至少有一个成功的结果
        success_count = sum(1 for engine, result in all_results["engine_results"].items() 
                          if result.get("status") == "success")
        
        if success_count == 0 and api_key:
            all_results["status"] = "warning"
            all_results["message"] = "所有搜索引擎都失败，请检查API密钥或尝试其他搜索引擎"
        elif not api_key:
            all_results["status"] = "pending"
            all_results["message"] = "需要使用web_page_extractor工具获取搜索结果"
        
        return json.dumps(all_results, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"多引擎搜索时发生错误: {str(e)}",
            "query": query,
            "results": None
        }, ensure_ascii=False)


@tool
def aws_bedrock_search(query: str, model_id: str = "us.anthropic.claude-3-7-sonnet-20250219-v1:0", 
                      max_tokens: int = 4096) -> str:
    """
    使用AWS Bedrock进行搜索和信息提取
    
    Args:
        query: 搜索查询
        model_id: Bedrock模型ID，默认为Claude 3.7 Sonnet
        max_tokens: 最大生成token数，默认为4096
    
    Returns:
        JSON格式的搜索和提取结果
    """
    try:
        # 初始化Bedrock客户端
        bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name="us-east-1"
        )
        
        # 构建提示词
        prompt = f"""
        请帮我搜索关于"{query}"的详细信息，并提供以下格式的结构化结果：
        
        1. 公司基本信息：公司全称、成立时间、总部位置、行业领域
        2. 业务概述：主要产品或服务、业务模式、目标市场
        3. 财务信息：年营收(如可获取)、市值(如适用)、盈利状况
        4. 公司规模：员工数量、全球分布(如适用)
        5. 公司历史：重要里程碑、创始人信息、发展历程
        6. 相关链接：官方网站、社交媒体账号
        
        请尽量提供准确、最新的信息，并标明信息来源。如果某些信息无法获取，请说明。
        请以JSON格式返回结果，不要包含任何其他内容。
        """
        
        # 根据模型ID选择请求格式
        if "anthropic.claude" in model_id:
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.1
            }
        else:
            # 默认格式，适用于其他模型
            request_body = {
                "prompt": prompt,
                "max_tokens_to_sample": max_tokens,
                "temperature": 0.1
            }
        
        # 调用Bedrock
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body)
        )
        
        # 解析响应
        response_body = json.loads(response.get("body").read())
        
        # 根据模型ID提取内容
        if "anthropic.claude" in model_id:
            content = response_body.get("content", [{}])[0].get("text", "")
        else:
            content = response_body.get("completion", "")
        
        # 尝试解析JSON内容
        try:
            # 提取JSON部分
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
            if json_match:
                extracted_json = json_match.group(1)
                search_data = json.loads(extracted_json)
            else:
                # 尝试直接解析整个内容
                search_data = json.loads(content)
        except Exception:
            # 如果解析失败，返回原始内容
            search_data = {"raw_content": content}
        
        result = {
            "status": "success",
            "message": f"成功使用AWS Bedrock搜索: {query}",
            "query": query,
            "model_id": model_id,
            "search_metadata": {
                "timestamp": time.time()
            },
            "search_results": search_data
        }
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"AWS Bedrock搜索时发生错误: {str(e)}",
            "query": query,
            "results": None
        }, ensure_ascii=False)


def _build_search_url(engine: str, query: str) -> str:
    """构建搜索引擎URL"""
    encoded_query = quote_plus(query)
    
    if engine.lower() == "google":
        return f"https://www.google.com/search?q={encoded_query}"
    elif engine.lower() == "bing":
        return f"https://www.bing.com/search?q={encoded_query}"
    elif engine.lower() == "baidu":
        return f"https://www.baidu.com/s?wd={encoded_query}"
    elif engine.lower() == "duckduckgo":
        return f"https://duckduckgo.com/?q={encoded_query}"
    else:
        return f"https://www.google.com/search?q={encoded_query}"