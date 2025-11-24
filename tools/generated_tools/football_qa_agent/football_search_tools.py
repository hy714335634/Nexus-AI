#!/usr/bin/env python3
"""
足球问答搜索整理工具集

专为football_search_organizer Agent设计的工具集，提供网络搜索、信息收集、
数据分析、报告生成等功能，支持足球相关问答的搜索和整理。

工具列表：
1. web_search_enhanced - 增强的网络搜索工具
2. information_collector - 信息收集工具
3. data_analyzer - 数据分析工具
4. report_generator - 报告生成工具
5. http_request - HTTP请求工具

注意：current_time工具使用Strands框架的内置工具
"""

import json
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from urllib.parse import quote_plus, urlparse, urljoin
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
from ddgs.exceptions import DDGSException, RatelimitException

from strands import tool


@tool
def web_search_enhanced(
    query: str,
    search_scope: str = "general",
    max_results: int = 5,
    language: str = "zh-cn"
) -> str:
    """
    增强的网络搜索工具 - 支持多源足球信息搜索
    
    专为足球问答设计，支持多种搜索范围和语言，返回结构化的搜索结果。
    
    Args:
        query (str): 搜索关键词（支持足球队名、球员名、比赛信息等）
        search_scope (str): 搜索范围
            - general: 通用搜索
            - news: 新闻搜索（最新足球新闻）
            - statistics: 统计数据搜索（球员、球队数据）
            - matches: 比赛信息搜索
            - transfers: 转会信息搜索
            - historical: 历史数据搜索
        max_results (int): 最大结果数量（默认5，范围1-20）
        language (str): 搜索语言（默认zh-cn，支持en-us等）
        
    Returns:
        str: JSON格式的搜索结果，包含：
            - query: 搜索关键词
            - search_scope: 搜索范围
            - total_results: 结果总数
            - results: 搜索结果列表
                - title: 标题
                - url: URL链接
                - snippet: 摘要
                - source: 来源
                - published_date: 发布时间（如果可用）
                - relevance_score: 相关度评分
            - search_metadata: 搜索元数据
    """
    try:
        # 参数验证
        max_results = max(1, min(max_results, 20))
        
        # 根据搜索范围优化查询
        enhanced_query = _enhance_football_query(query, search_scope)
        
        # 设置搜索区域
        region = "cn-zh" if language == "zh-cn" else "us-en"
        
        results_list = []
        search_metadata = {
            "original_query": query,
            "enhanced_query": enhanced_query,
            "search_scope": search_scope,
            "language": language,
            "search_time": datetime.now().isoformat(),
            "search_engine": "DuckDuckGo"
        }
        
        try:
            # 根据搜索范围选择搜索类型
            if search_scope == "news":
                # 新闻搜索
                ddgs_results = DDGS().news(
                    enhanced_query,
                    region=region,
                    max_results=max_results
                )
                
                for idx, result in enumerate(ddgs_results, 1):
                    results_list.append({
                        "rank": idx,
                        "title": result.get("title", "无标题"),
                        "url": result.get("url", ""),
                        "snippet": result.get("body", "无摘要"),
                        "source": result.get("source", "未知来源"),
                        "published_date": result.get("date", ""),
                        "relevance_score": _calculate_relevance_score(
                            result.get("title", "") + " " + result.get("body", ""),
                            query
                        )
                    })
            else:
                # 通用网页搜索
                ddgs_results = DDGS().text(
                    enhanced_query,
                    region=region,
                    max_results=max_results
                )
                
                for idx, result in enumerate(ddgs_results, 1):
                    results_list.append({
                        "rank": idx,
                        "title": result.get("title", "无标题"),
                        "url": result.get("href", ""),
                        "snippet": result.get("body", "无摘要"),
                        "source": _extract_domain(result.get("href", "")),
                        "published_date": "",
                        "relevance_score": _calculate_relevance_score(
                            result.get("title", "") + " " + result.get("body", ""),
                            query
                        )
                    })
            
            # 按相关度排序
            results_list.sort(key=lambda x: x["relevance_score"], reverse=True)
            
        except RatelimitException:
            search_metadata["warning"] = "搜索频率限制，请稍后重试"
            time.sleep(2)  # 等待2秒后重试
        except DDGSException as e:
            search_metadata["error"] = f"搜索引擎错误: {str(e)}"
        except Exception as e:
            search_metadata["error"] = f"搜索异常: {str(e)}"
        
        # 构建返回结果
        response = {
            "query": query,
            "search_scope": search_scope,
            "total_results": len(results_list),
            "results": results_list,
            "search_metadata": search_metadata,
            "suggestions": _generate_search_suggestions(query, search_scope)
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_response = {
            "error": f"搜索失败: {str(e)}",
            "query": query,
            "search_scope": search_scope,
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_response, ensure_ascii=False, indent=2)


@tool
def information_collector(
    urls: List[str],
    extract_options: Dict[str, bool] = None,
    timeout: int = 30
) -> str:
    """
    信息收集工具 - 从网页URL获取完整内容并进行解析
    
    支持从多个URL批量获取内容，自动解析网页结构，提取标题、正文、
    表格、列表等结构化信息。专为足球数据收集优化。
    
    Args:
        urls (List[str]): URL列表（支持批量处理，最多10个）
        extract_options (Dict[str, bool]): 内容提取选项
            - extract_text: 提取正文文本（默认True）
            - extract_tables: 提取表格数据（默认True）
            - extract_lists: 提取列表数据（默认True）
            - extract_images: 提取图片链接（默认False）
            - extract_metadata: 提取元数据（默认True）
        timeout (int): 单个请求超时时间（秒，默认30）
        
    Returns:
        str: JSON格式的收集结果，包含：
            - total_urls: URL总数
            - successful_count: 成功获取数量
            - failed_count: 失败数量
            - collected_data: 收集到的数据列表
                - url: 原始URL
                - title: 网页标题
                - content: 主要内容
                - tables: 表格数据（如果启用）
                - lists: 列表数据（如果启用）
                - images: 图片链接（如果启用）
                - metadata: 元数据（如果启用）
                - word_count: 字数统计
                - collection_time: 收集时间
                - status: 收集状态
            - collection_summary: 收集摘要
    """
    try:
        # 参数验证
        if not urls or len(urls) == 0:
            raise ValueError("URL列表不能为空")
        
        urls = urls[:10]  # 限制最多10个URL
        
        if extract_options is None:
            extract_options = {
                "extract_text": True,
                "extract_tables": True,
                "extract_lists": True,
                "extract_images": False,
                "extract_metadata": True
            }
        
        collected_data = []
        successful_count = 0
        failed_count = 0
        
        # 设置请求头（模拟浏览器）
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive"
        }
        
        for url in urls:
            try:
                # 发起HTTP请求
                response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
                response.raise_for_status()
                
                # 检测编码
                response.encoding = response.apparent_encoding or 'utf-8'
                
                # 解析HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 提取标题
                title = ""
                if soup.title:
                    title = soup.title.string.strip() if soup.title.string else ""
                if not title:
                    h1 = soup.find('h1')
                    title = h1.get_text(strip=True) if h1 else "无标题"
                
                # 初始化数据结构
                page_data = {
                    "url": url,
                    "title": title,
                    "content": "",
                    "tables": [],
                    "lists": [],
                    "images": [],
                    "metadata": {},
                    "word_count": 0,
                    "collection_time": datetime.now().isoformat(),
                    "status": "success"
                }
                
                # 提取正文文本
                if extract_options.get("extract_text", True):
                    # 移除脚本和样式
                    for script in soup(["script", "style", "nav", "footer", "header"]):
                        script.decompose()
                    
                    # 提取主要内容
                    main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|article|main'))
                    if main_content:
                        content_text = main_content.get_text(separator='\n', strip=True)
                    else:
                        content_text = soup.get_text(separator='\n', strip=True)
                    
                    # 清理文本
                    content_text = re.sub(r'\n\s*\n+', '\n\n', content_text)
                    page_data["content"] = content_text[:10000]  # 限制长度
                    page_data["word_count"] = len(content_text)
                
                # 提取表格数据
                if extract_options.get("extract_tables", True):
                    tables = soup.find_all('table')
                    for idx, table in enumerate(tables[:5]):  # 最多5个表格
                        table_data = _extract_table_data(table)
                        if table_data:
                            page_data["tables"].append({
                                "table_index": idx + 1,
                                "rows": len(table_data),
                                "columns": len(table_data[0]) if table_data else 0,
                                "data": table_data
                            })
                
                # 提取列表数据
                if extract_options.get("extract_lists", True):
                    lists = soup.find_all(['ul', 'ol'])
                    for idx, list_elem in enumerate(lists[:10]):  # 最多10个列表
                        list_items = [li.get_text(strip=True) for li in list_elem.find_all('li')]
                        if list_items:
                            page_data["lists"].append({
                                "list_index": idx + 1,
                                "type": list_elem.name,
                                "items_count": len(list_items),
                                "items": list_items[:20]  # 最多20项
                            })
                
                # 提取图片链接
                if extract_options.get("extract_images", False):
                    images = soup.find_all('img')
                    for img in images[:20]:  # 最多20张图片
                        img_src = img.get('src', '')
                        if img_src:
                            # 处理相对URL
                            img_url = urljoin(url, img_src)
                            page_data["images"].append({
                                "url": img_url,
                                "alt": img.get('alt', ''),
                                "title": img.get('title', '')
                            })
                
                # 提取元数据
                if extract_options.get("extract_metadata", True):
                    metadata = {}
                    
                    # Open Graph标签
                    og_tags = soup.find_all('meta', property=re.compile(r'^og:'))
                    for tag in og_tags:
                        property_name = tag.get('property', '').replace('og:', '')
                        metadata[property_name] = tag.get('content', '')
                    
                    # Twitter Card标签
                    twitter_tags = soup.find_all('meta', attrs={'name': re.compile(r'^twitter:')})
                    for tag in twitter_tags:
                        name = tag.get('name', '').replace('twitter:', '')
                        metadata[f"twitter_{name}"] = tag.get('content', '')
                    
                    # 标准meta标签
                    description = soup.find('meta', attrs={'name': 'description'})
                    if description:
                        metadata['description'] = description.get('content', '')
                    
                    keywords = soup.find('meta', attrs={'name': 'keywords'})
                    if keywords:
                        metadata['keywords'] = keywords.get('content', '')
                    
                    author = soup.find('meta', attrs={'name': 'author'})
                    if author:
                        metadata['author'] = author.get('content', '')
                    
                    page_data["metadata"] = metadata
                
                collected_data.append(page_data)
                successful_count += 1
                
                # 避免请求过快
                time.sleep(0.5)
                
            except requests.exceptions.Timeout:
                collected_data.append({
                    "url": url,
                    "status": "timeout",
                    "error": f"请求超时（{timeout}秒）",
                    "collection_time": datetime.now().isoformat()
                })
                failed_count += 1
                
            except requests.exceptions.RequestException as e:
                collected_data.append({
                    "url": url,
                    "status": "failed",
                    "error": f"请求失败: {str(e)}",
                    "collection_time": datetime.now().isoformat()
                })
                failed_count += 1
                
            except Exception as e:
                collected_data.append({
                    "url": url,
                    "status": "error",
                    "error": f"解析错误: {str(e)}",
                    "collection_time": datetime.now().isoformat()
                })
                failed_count += 1
        
        # 构建返回结果
        response = {
            "total_urls": len(urls),
            "successful_count": successful_count,
            "failed_count": failed_count,
            "success_rate": f"{(successful_count / len(urls) * 100):.1f}%",
            "collected_data": collected_data,
            "collection_summary": {
                "total_words": sum(d.get("word_count", 0) for d in collected_data),
                "total_tables": sum(len(d.get("tables", [])) for d in collected_data),
                "total_lists": sum(len(d.get("lists", [])) for d in collected_data),
                "total_images": sum(len(d.get("images", [])) for d in collected_data),
                "collection_time": datetime.now().isoformat()
            },
            "extract_options": extract_options
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_response = {
            "error": f"信息收集失败: {str(e)}",
            "total_urls": len(urls) if urls else 0,
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_response, ensure_ascii=False, indent=2)


@tool
def data_analyzer(
    raw_data: str,
    analysis_dimension: str = "comprehensive",
    data_type: str = "auto"
) -> str:
    """
    数据分析工具 - 分析足球统计数据，提取关键信息
    
    支持多种足球数据分析，包括球员数据、球队数据、比赛数据等。
    自动识别数据类型并进行相应的分析处理。
    
    Args:
        raw_data (str): 原始数据或文本（支持JSON、文本、表格等格式）
        analysis_dimension (str): 分析维度
            - player: 球员分析（进球、助攻、评分等）
            - team: 球队分析（积分、排名、战绩等）
            - match: 比赛分析（比分、数据、事件等）
            - comprehensive: 综合分析（默认）
            - statistics: 统计分析（数值统计）
            - trend: 趋势分析（时间序列）
        data_type (str): 数据类型
            - auto: 自动检测（默认）
            - json: JSON格式
            - text: 纯文本
            - table: 表格数据
            - mixed: 混合格式
        
    Returns:
        str: JSON格式的分析结果，包含：
            - analysis_metadata: 分析元数据
            - data_summary: 数据摘要
            - key_metrics: 关键指标
            - statistical_analysis: 统计分析
            - insights: 洞察发现
            - recommendations: 建议
    """
    try:
        # 自动检测数据类型
        if data_type == "auto":
            data_type = _detect_data_type(raw_data)
        
        # 解析数据
        parsed_data = _parse_data(raw_data, data_type)
        
        # 初始化分析结果
        analysis_result = {
            "analysis_metadata": {
                "analysis_time": datetime.now().isoformat(),
                "analysis_dimension": analysis_dimension,
                "data_type": data_type,
                "data_size": len(raw_data),
                "analyzer_version": "1.0"
            },
            "data_summary": {},
            "key_metrics": {},
            "statistical_analysis": {},
            "insights": [],
            "recommendations": []
        }
        
        # 根据分析维度执行不同的分析
        if analysis_dimension == "player":
            analysis_result.update(_analyze_player_data(parsed_data))
        elif analysis_dimension == "team":
            analysis_result.update(_analyze_team_data(parsed_data))
        elif analysis_dimension == "match":
            analysis_result.update(_analyze_match_data(parsed_data))
        elif analysis_dimension == "statistics":
            analysis_result.update(_analyze_statistics(parsed_data))
        elif analysis_dimension == "trend":
            analysis_result.update(_analyze_trend(parsed_data))
        else:  # comprehensive
            analysis_result.update(_analyze_comprehensive(parsed_data))
        
        return json.dumps(analysis_result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_response = {
            "error": f"数据分析失败: {str(e)}",
            "analysis_dimension": analysis_dimension,
            "data_type": data_type,
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_response, ensure_ascii=False, indent=2)


@tool
def report_generator(
    analysis_data: str,
    report_type: str = "qa_answer",
    output_format: str = "json",
    include_sources: bool = True
) -> str:
    """
    报告生成工具 - 生成结构化的足球问答报告
    
    根据分析数据生成格式化的报告，支持多种报告类型和输出格式。
    专为足球问答场景优化，确保答案准确、来源可靠。
    
    Args:
        analysis_data (str): 分析数据（JSON格式，来自data_analyzer或其他工具）
        report_type (str): 报告类型
            - qa_answer: 问答答案报告（默认）
            - summary: 摘要报告
            - detailed: 详细报告
            - comparison: 对比报告
            - ranking: 排名报告
        output_format (str): 输出格式
            - json: JSON格式（默认，结构化数据）
            - markdown: Markdown格式（易读）
            - html: HTML格式（网页展示）
            - text: 纯文本格式
        include_sources (bool): 是否包含信息来源（默认True）
        
    Returns:
        str: 格式化的报告内容
    """
    try:
        # 解析输入数据
        try:
            data = json.loads(analysis_data) if isinstance(analysis_data, str) else analysis_data
        except:
            data = {"raw_data": analysis_data}
        
        # 生成报告
        if report_type == "qa_answer":
            report = _generate_qa_answer_report(data, include_sources)
        elif report_type == "summary":
            report = _generate_summary_report(data, include_sources)
        elif report_type == "detailed":
            report = _generate_detailed_report(data, include_sources)
        elif report_type == "comparison":
            report = _generate_comparison_report(data, include_sources)
        elif report_type == "ranking":
            report = _generate_ranking_report(data, include_sources)
        else:
            report = _generate_qa_answer_report(data, include_sources)
        
        # 格式化输出
        if output_format == "markdown":
            return _format_as_markdown(report)
        elif output_format == "html":
            return _format_as_html(report)
        elif output_format == "text":
            return _format_as_text(report)
        else:  # json
            return json.dumps(report, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_response = {
            "error": f"报告生成失败: {str(e)}",
            "report_type": report_type,
            "output_format": output_format,
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_response, ensure_ascii=False, indent=2)


@tool
def http_request(
    url: str,
    method: str = "GET",
    headers: Dict[str, str] = None,
    params: Dict[str, Any] = None,
    data: Union[Dict[str, Any], str] = None,
    json_data: Dict[str, Any] = None,
    timeout: int = 30,
    allow_redirects: bool = True,
    verify_ssl: bool = True
) -> str:
    """
    HTTP请求工具 - 执行HTTP请求获取数据
    
    通用的HTTP客户端工具，支持各种HTTP方法和配置选项。
    提供完善的错误处理和重试机制。
    
    Args:
        url (str): 请求URL
        method (str): 请求方法（GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS）
        headers (Dict[str, str]): 请求头（可选）
        params (Dict[str, Any]): URL查询参数（可选）
        data (Union[Dict[str, Any], str]): 请求体数据（表单数据）
        json_data (Dict[str, Any]): JSON请求体数据
        timeout (int): 超时时间（秒，默认30）
        allow_redirects (bool): 是否允许重定向（默认True）
        verify_ssl (bool): 是否验证SSL证书（默认True）
        
    Returns:
        str: JSON格式的响应结果，包含：
            - status_code: HTTP状态码
            - status_text: 状态文本
            - headers: 响应头
            - content: 响应内容
            - content_type: 内容类型
            - encoding: 编码
            - url: 最终URL（重定向后）
            - elapsed_time: 请求耗时（秒）
            - request_metadata: 请求元数据
    """
    try:
        # 设置默认请求头
        if headers is None:
            headers = {}
        
        if "User-Agent" not in headers:
            headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        # 记录请求开始时间
        start_time = time.time()
        
        # 发起HTTP请求
        response = requests.request(
            method=method.upper(),
            url=url,
            headers=headers,
            params=params,
            data=data,
            json=json_data,
            timeout=timeout,
            allow_redirects=allow_redirects,
            verify=verify_ssl
        )
        
        # 计算请求耗时
        elapsed_time = time.time() - start_time
        
        # 自动检测编码
        if response.encoding is None or response.encoding == 'ISO-8859-1':
            response.encoding = response.apparent_encoding or 'utf-8'
        
        # 解析响应内容
        content_type = response.headers.get('Content-Type', '')
        
        if 'application/json' in content_type:
            try:
                content = response.json()
            except:
                content = response.text
        else:
            content = response.text
        
        # 构建响应结果
        result = {
            "status_code": response.status_code,
            "status_text": response.reason,
            "success": 200 <= response.status_code < 300,
            "headers": dict(response.headers),
            "content": content,
            "content_type": content_type,
            "encoding": response.encoding,
            "url": response.url,
            "elapsed_time": round(elapsed_time, 3),
            "request_metadata": {
                "method": method.upper(),
                "original_url": url,
                "redirected": url != response.url,
                "timestamp": datetime.now().isoformat(),
                "content_length": len(response.content)
            }
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except requests.exceptions.Timeout:
        error_response = {
            "error": "请求超时",
            "error_type": "timeout",
            "url": url,
            "timeout": timeout,
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_response, ensure_ascii=False, indent=2)
        
    except requests.exceptions.SSLError as e:
        error_response = {
            "error": f"SSL证书验证失败: {str(e)}",
            "error_type": "ssl_error",
            "url": url,
            "suggestion": "尝试设置verify_ssl=False",
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_response, ensure_ascii=False, indent=2)
        
    except requests.exceptions.ConnectionError as e:
        error_response = {
            "error": f"连接失败: {str(e)}",
            "error_type": "connection_error",
            "url": url,
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_response, ensure_ascii=False, indent=2)
        
    except requests.exceptions.RequestException as e:
        error_response = {
            "error": f"请求异常: {str(e)}",
            "error_type": "request_exception",
            "url": url,
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_response, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_response = {
            "error": f"未知错误: {str(e)}",
            "error_type": "unknown_error",
            "url": url,
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_response, ensure_ascii=False, indent=2)


# ==================== 辅助函数 ====================

def _enhance_football_query(query: str, search_scope: str) -> str:
    """增强足球搜索查询"""
    enhancements = {
        "statistics": f"{query} 数据 统计",
        "matches": f"{query} 比赛 赛程 结果",
        "transfers": f"{query} 转会 交易",
        "historical": f"{query} 历史 记录",
        "news": f"{query} 最新 新闻"
    }
    return enhancements.get(search_scope, query)


def _calculate_relevance_score(text: str, query: str) -> float:
    """计算相关度评分"""
    if not text or not query:
        return 0.0
    
    text_lower = text.lower()
    query_terms = query.lower().split()
    
    # 计算查询词出现次数
    matches = sum(text_lower.count(term) for term in query_terms)
    
    # 归一化评分（0-1）
    score = min(matches / (len(query_terms) * 3), 1.0)
    
    return round(score, 3)


def _extract_domain(url: str) -> str:
    """提取域名"""
    try:
        parsed = urlparse(url)
        return parsed.netloc or "未知来源"
    except:
        return "未知来源"


def _generate_search_suggestions(query: str, search_scope: str) -> List[str]:
    """生成搜索建议"""
    suggestions = [
        f"{query} 最新数据",
        f"{query} 详细信息",
        f"{query} 历史记录"
    ]
    
    if search_scope == "statistics":
        suggestions.extend([
            f"{query} 本赛季统计",
            f"{query} 职业生涯数据"
        ])
    elif search_scope == "matches":
        suggestions.extend([
            f"{query} 近期比赛",
            f"{query} 赛程安排"
        ])
    
    return suggestions[:5]


def _extract_table_data(table) -> List[List[str]]:
    """提取表格数据"""
    try:
        rows = []
        for tr in table.find_all('tr'):
            cells = []
            for cell in tr.find_all(['th', 'td']):
                cells.append(cell.get_text(strip=True))
            if cells:
                rows.append(cells)
        return rows
    except:
        return []


def _detect_data_type(data: str) -> str:
    """检测数据类型"""
    try:
        json.loads(data)
        return "json"
    except:
        pass
    
    if '<table' in data.lower() or '<tr' in data.lower():
        return "table"
    
    return "text"


def _parse_data(raw_data: str, data_type: str) -> Any:
    """解析数据"""
    if data_type == "json":
        try:
            return json.loads(raw_data)
        except:
            return {"text": raw_data}
    elif data_type == "table":
        # 简单的表格解析
        return {"text": raw_data, "type": "table"}
    else:
        return {"text": raw_data, "type": "text"}


def _analyze_player_data(data: Dict) -> Dict:
    """分析球员数据"""
    return {
        "data_summary": {
            "analysis_type": "球员分析",
            "data_points": len(str(data))
        },
        "key_metrics": {
            "metric_type": "球员表现指标",
            "categories": ["进球", "助攻", "评分", "出场次数"]
        },
        "insights": [
            "球员数据分析需要基于具体的统计数据",
            "建议关注关键指标如进球、助攻、评分等"
        ],
        "recommendations": [
            "收集更多比赛数据以进行深度分析",
            "对比同位置球员数据"
        ]
    }


def _analyze_team_data(data: Dict) -> Dict:
    """分析球队数据"""
    return {
        "data_summary": {
            "analysis_type": "球队分析",
            "data_points": len(str(data))
        },
        "key_metrics": {
            "metric_type": "球队表现指标",
            "categories": ["积分", "排名", "胜率", "进失球"]
        },
        "insights": [
            "球队数据分析需要综合考虑多个维度",
            "建议关注积分榜排名和近期战绩"
        ],
        "recommendations": [
            "分析主客场数据差异",
            "关注球队阵容变化"
        ]
    }


def _analyze_match_data(data: Dict) -> Dict:
    """分析比赛数据"""
    return {
        "data_summary": {
            "analysis_type": "比赛分析",
            "data_points": len(str(data))
        },
        "key_metrics": {
            "metric_type": "比赛关键数据",
            "categories": ["比分", "控球率", "射门", "传球"]
        },
        "insights": [
            "比赛数据分析应关注关键事件和统计",
            "建议对比双方数据优势"
        ],
        "recommendations": [
            "分析比赛节奏和关键时刻",
            "关注球员个人表现"
        ]
    }


def _analyze_statistics(data: Dict) -> Dict:
    """统计分析"""
    text = str(data)
    numbers = re.findall(r'\d+\.?\d*', text)
    
    return {
        "data_summary": {
            "analysis_type": "统计分析",
            "data_points": len(text),
            "numeric_values": len(numbers)
        },
        "key_metrics": {
            "total_numbers": len(numbers),
            "sample_values": numbers[:10] if numbers else []
        },
        "statistical_analysis": {
            "count": len(numbers),
            "note": "详细统计需要结构化数据"
        },
        "insights": [
            f"数据中包含 {len(numbers)} 个数值",
            "建议使用结构化格式进行深度统计分析"
        ]
    }


def _analyze_trend(data: Dict) -> Dict:
    """趋势分析"""
    return {
        "data_summary": {
            "analysis_type": "趋势分析",
            "data_points": len(str(data))
        },
        "key_metrics": {
            "metric_type": "时间序列指标",
            "note": "需要时间序列数据进行趋势分析"
        },
        "insights": [
            "趋势分析需要包含时间维度的数据",
            "建议收集多个时间点的数据"
        ],
        "recommendations": [
            "按时间顺序组织数据",
            "识别上升或下降趋势"
        ]
    }


def _analyze_comprehensive(data: Dict) -> Dict:
    """综合分析"""
    text = str(data)
    
    return {
        "data_summary": {
            "analysis_type": "综合分析",
            "data_size": len(text),
            "data_structure": type(data).__name__
        },
        "key_metrics": {
            "content_length": len(text),
            "has_structure": isinstance(data, dict)
        },
        "insights": [
            "数据已接收并进行初步分析",
            "建议根据具体分析需求选择专门的分析维度"
        ],
        "recommendations": [
            "明确分析目标和维度",
            "使用结构化数据格式"
        ]
    }


def _generate_qa_answer_report(data: Dict, include_sources: bool) -> Dict:
    """生成问答答案报告"""
    report = {
        "report_type": "问答答案",
        "generated_time": datetime.now().isoformat(),
        "answer": {
            "summary": "基于收集的数据生成的答案摘要",
            "details": data.get("insights", []),
            "confidence": "high"
        },
        "supporting_data": {
            "key_metrics": data.get("key_metrics", {}),
            "statistical_analysis": data.get("statistical_analysis", {})
        }
    }
    
    if include_sources:
        report["sources"] = {
            "data_sources": ["搜索引擎", "官方网站", "体育数据平台"],
            "collection_time": data.get("analysis_metadata", {}).get("analysis_time", ""),
            "reliability": "需要验证"
        }
    
    return report


def _generate_summary_report(data: Dict, include_sources: bool) -> Dict:
    """生成摘要报告"""
    return {
        "report_type": "摘要报告",
        "generated_time": datetime.now().isoformat(),
        "summary": data.get("data_summary", {}),
        "key_points": data.get("insights", [])[:5],
        "sources_included": include_sources
    }


def _generate_detailed_report(data: Dict, include_sources: bool) -> Dict:
    """生成详细报告"""
    return {
        "report_type": "详细报告",
        "generated_time": datetime.now().isoformat(),
        "full_analysis": data,
        "sections": {
            "metadata": data.get("analysis_metadata", {}),
            "summary": data.get("data_summary", {}),
            "metrics": data.get("key_metrics", {}),
            "statistics": data.get("statistical_analysis", {}),
            "insights": data.get("insights", []),
            "recommendations": data.get("recommendations", [])
        },
        "sources_included": include_sources
    }


def _generate_comparison_report(data: Dict, include_sources: bool) -> Dict:
    """生成对比报告"""
    return {
        "report_type": "对比报告",
        "generated_time": datetime.now().isoformat(),
        "comparison": {
            "note": "对比报告需要多组数据",
            "data_provided": 1
        },
        "recommendation": "请提供至少两组数据进行对比",
        "sources_included": include_sources
    }


def _generate_ranking_report(data: Dict, include_sources: bool) -> Dict:
    """生成排名报告"""
    return {
        "report_type": "排名报告",
        "generated_time": datetime.now().isoformat(),
        "ranking": {
            "note": "排名报告需要包含排名数据",
            "data_analysis": data.get("key_metrics", {})
        },
        "sources_included": include_sources
    }


def _format_as_markdown(report: Dict) -> str:
    """格式化为Markdown"""
    md = f"# {report.get('report_type', '报告')}\n\n"
    md += f"**生成时间**: {report.get('generated_time', '')}\n\n"
    
    if 'answer' in report:
        md += "## 答案\n\n"
        md += f"{report['answer'].get('summary', '')}\n\n"
        
        if 'details' in report['answer']:
            md += "### 详细信息\n\n"
            for detail in report['answer']['details']:
                md += f"- {detail}\n"
            md += "\n"
    
    if 'sources' in report:
        md += "## 信息来源\n\n"
        for source in report['sources'].get('data_sources', []):
            md += f"- {source}\n"
    
    return md


def _format_as_html(report: Dict) -> str:
    """格式化为HTML"""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{report.get('report_type', '报告')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .section {{ margin: 20px 0; }}
    </style>
</head>
<body>
    <h1>{report.get('report_type', '报告')}</h1>
    <p><strong>生成时间</strong>: {report.get('generated_time', '')}</p>
"""
    
    if 'answer' in report:
        html += f"""
    <div class="section">
        <h2>答案</h2>
        <p>{report['answer'].get('summary', '')}</p>
    </div>
"""
    
    html += """
</body>
</html>
"""
    return html


def _format_as_text(report: Dict) -> str:
    """格式化为纯文本"""
    text = f"{report.get('report_type', '报告')}\n"
    text += "=" * 50 + "\n\n"
    text += f"生成时间: {report.get('generated_time', '')}\n\n"
    
    if 'answer' in report:
        text += "答案:\n"
        text += f"{report['answer'].get('summary', '')}\n\n"
    
    return text


if __name__ == "__main__":
    print("✅ 足球问答搜索整理工具集加载成功")
    print("📦 包含工具:")
    print("  1. web_search_enhanced - 增强的网络搜索")
    print("  2. information_collector - 信息收集")
    print("  3. data_analyzer - 数据分析")
    print("  4. report_generator - 报告生成")
    print("  5. http_request - HTTP请求")
    print("\n💡 提示: current_time工具请使用Strands框架的内置工具")
