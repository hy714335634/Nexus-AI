#!/usr/bin/env python3
"""
Search engine tools using SerpAPI for comprehensive web search.
Supports general web search, news search, and academic search.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import quote_plus

from strands import tool

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


@tool
def serpapi_search(
    query: str,
    api_key: str,
    num_results: int = 10,
    time_range: str = "w",  # d=day, w=week, m=month, y=year
    language: str = "zh-cn",
    country: str = "cn"
) -> str:
    """
    使用SerpAPI进行Google搜索
    
    Args:
        query: 搜索查询词
        api_key: SerpAPI API密钥
        num_results: 返回结果数量（默认10）
        time_range: 时间范围（d=天, w=周, m=月, y=年）
        language: 搜索语言（默认zh-cn）
        country: 搜索国家（默认cn）
        
    Returns:
        str: JSON格式的搜索结果
    """
    try:
        if not REQUESTS_AVAILABLE:
            return json.dumps({
                "status": "error",
                "message": "requests库未安装。请安装: pip install requests"
            }, ensure_ascii=False)
        
        url = "https://serpapi.com/search"
        params = {
            "q": query,
            "api_key": api_key,
            "num": num_results,
            "tbs": f"qdr:{time_range}",
            "hl": language,
            "gl": country,
            "engine": "google"
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # 提取有机搜索结果
        organic_results = data.get("organic_results", [])
        
        results = []
        for item in organic_results:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "displayed_link": item.get("displayed_link", ""),
                "date": item.get("date", ""),
                "source": "SerpAPI Google Search"
            })
        
        return json.dumps({
            "status": "success",
            "query": query,
            "total_results": len(results),
            "results": results,
            "search_time": datetime.now().isoformat(),
            "source": "SerpAPI Google Search"
        }, ensure_ascii=False, indent=2)
        
    except requests.exceptions.Timeout:
        return json.dumps({
            "status": "error",
            "query": query,
            "message": "SerpAPI请求超时"
        }, ensure_ascii=False)
    except requests.exceptions.RequestException as e:
        return json.dumps({
            "status": "error",
            "query": query,
            "message": f"SerpAPI请求失败: {str(e)}"
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "query": query,
            "message": f"搜索失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def bing_web_search(
    query: str,
    count: int = 10,
    market: str = "zh-CN",
    freshness: Optional[str] = None
) -> str:
    """
    使用Bing Search API进行网页搜索（已废弃，请使用serpapi_search）
    
    Args:
        query (str): 搜索查询词
        count (int): 返回结果数量（1-50）
        market (str): 市场地区代码（zh-CN, en-US等）
        freshness (str, optional): 结果时效性（Day, Week, Month）
        
    Returns:
        str: JSON格式的搜索结果
    """
    return json.dumps({
        "status": "error",
        "message": "此工具已废弃，请使用 serpapi_search"
    }, ensure_ascii=False)


@tool
def serpapi_news_search(
    query: str,
    api_key: str,
    num_results: int = 10,
    time_range: str = "w",
    language: str = "zh-cn",
    country: str = "cn"
) -> str:
    """
    使用SerpAPI进行Google新闻搜索
    
    Args:
        query: 搜索查询词
        api_key: SerpAPI API密钥
        num_results: 返回结果数量（默认10）
        time_range: 时间范围（d=天, w=周, m=月, y=年）
        language: 搜索语言（默认zh-cn）
        country: 搜索国家（默认cn）
        
    Returns:
        str: JSON格式的新闻搜索结果
    """
    try:
        if not REQUESTS_AVAILABLE:
            return json.dumps({
                "status": "error",
                "message": "requests库未安装。请安装: pip install requests"
            }, ensure_ascii=False)
        
        url = "https://serpapi.com/search"
        params = {
            "q": query,
            "api_key": api_key,
            "num": num_results,
            "tbs": f"qdr:{time_range}",
            "hl": language,
            "gl": country,
            "engine": "google",
            "tbm": "nws"  # 新闻搜索
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # 提取新闻结果
        news_results = data.get("news_results", [])
        
        results = []
        for item in news_results:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "date": item.get("date", ""),
                "source": item.get("source", ""),
                "displayed_link": item.get("link", ""),
            })
        
        return json.dumps({
            "status": "success",
            "query": query,
            "total_results": len(results),
            "results": results,
            "search_time": datetime.now().isoformat(),
            "source": "SerpAPI Google News Search"
        }, ensure_ascii=False, indent=2)
        
    except requests.exceptions.Timeout:
        return json.dumps({
            "status": "error",
            "query": query,
            "message": "SerpAPI请求超时"
        }, ensure_ascii=False)
    except requests.exceptions.RequestException as e:
        return json.dumps({
            "status": "error",
            "query": query,
            "message": f"SerpAPI请求失败: {str(e)}"
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "query": query,
            "message": f"搜索失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def multi_keyword_search(
    keywords: List[str],
    api_key: str,
    search_type: str = "web",
    count_per_keyword: int = 5,
    time_range: str = "w"
) -> str:
    """
    多关键词批量搜索（使用SerpAPI）
    
    Args:
        keywords: 关键词列表
        api_key: SerpAPI API密钥
        search_type: 搜索类型（web, news）
        count_per_keyword: 每个关键词的结果数量
        time_range: 时间范围（d=天, w=周, m=月, y=年）
        
    Returns:
        str: JSON格式的批量搜索结果
    """
    try:
        all_results = {
            "keywords": keywords,
            "search_type": search_type,
            "count_per_keyword": count_per_keyword,
            "search_time": datetime.now().isoformat(),
            "results": []
        }
        
        for keyword in keywords:
            try:
                if search_type == "news":
                    result_json = serpapi_news_search(
                        query=keyword,
                        api_key=api_key,
                        num_results=count_per_keyword,
                        time_range=time_range
                    )
                else:
                    result_json = serpapi_search(
                        query=keyword,
                        api_key=api_key,
                        num_results=count_per_keyword,
                        time_range=time_range
                    )
                
                result = json.loads(result_json)
                all_results["results"].append({
                    "keyword": keyword,
                    "status": result["status"],
                    "data": result
                })
                
            except Exception as e:
                all_results["results"].append({
                    "keyword": keyword,
                    "status": "error",
                    "message": str(e)
                })
        
        return json.dumps(all_results, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"批量搜索失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def search_energy_news(
    topic: str,
    api_key: str,
    time_range: str = "w",
    max_results: int = 20,
    include_sources: Optional[List[str]] = None
) -> str:
    """
    搜索能源行业新闻（使用SerpAPI）
    
    Args:
        topic: 搜索主题（如"新能源汽车"、"储能技术"等）
        api_key: SerpAPI API密钥
        time_range: 时间范围（d=天, w=周, m=月, y=年）
        max_results: 最大结果数量
        include_sources: 指定新闻来源
        
    Returns:
        str: JSON格式的能源新闻搜索结果
    """
    try:
        # 构建能源领域相关的搜索查询
        energy_keywords = [
            f"{topic} 能源",
            f"{topic} 新能源",
            f"{topic} 政策",
            f"{topic} 行业动态"
        ]
        
        # 如果指定了新闻来源，添加到查询中
        if include_sources:
            energy_keywords = [f"{kw} site:{source}" for kw in energy_keywords for source in include_sources]
        
        # 批量搜索
        results_json = multi_keyword_search(
            keywords=energy_keywords,
            api_key=api_key,
            search_type="news",
            count_per_keyword=max_results // len(energy_keywords),
            time_range=time_range
        )
        results = json.loads(results_json)
        
        # 合并并去重
        all_articles = []
        seen_urls = set()
        
        for keyword_result in results.get("results", []):
            if keyword_result["status"] == "success":
                for article in keyword_result["data"].get("results", []):
                    url = article.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_articles.append(article)
        
        # 按日期排序
        all_articles.sort(key=lambda x: x.get("date", ""), reverse=True)
        
        # 限制结果数量
        all_articles = all_articles[:max_results]
        
        return json.dumps({
            "status": "success",
            "topic": topic,
            "time_range": time_range,
            "total_results": len(all_articles),
            "articles": all_articles,
            "search_time": datetime.now().isoformat(),
            "source": "SerpAPI Google News Search"
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "topic": topic,
            "message": f"能源新闻搜索失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def search_with_filters(
    query: str,
    api_key: str,
    search_type: str = "web",
    time_filter: Optional[str] = None,
    site_filter: Optional[str] = None,
    file_type: Optional[str] = None,
    language: str = "zh-cn",
    count: int = 10
) -> str:
    """
    带高级过滤器的搜索（使用SerpAPI）
    
    Args:
        query: 搜索查询词
        api_key: SerpAPI API密钥
        search_type: 搜索类型（web, news）
        time_filter: 时间过滤器（d=天, w=周, m=月, y=年）
        site_filter: 网站过滤器（如"gov.cn"）
        file_type: 文件类型过滤器（如"pdf"）
        language: 语言代码（默认zh-cn）
        count: 结果数量
        
    Returns:
        str: JSON格式的搜索结果
    """
    try:
        # 构建高级查询
        advanced_query = query
        
        if site_filter:
            advanced_query += f" site:{site_filter}"
        
        if file_type:
            advanced_query += f" filetype:{file_type}"
        
        # 转换时间过滤器格式
        time_range_map = {
            "Day": "d",
            "Week": "w",
            "Month": "m",
            "Year": "y"
        }
        time_range = time_range_map.get(time_filter, "w") if time_filter else "w"
        
        # 执行搜索
        if search_type == "news":
            result_json = serpapi_news_search(
                query=advanced_query,
                api_key=api_key,
                num_results=count,
                time_range=time_range,
                language=language
            )
        else:
            result_json = serpapi_search(
                query=advanced_query,
                api_key=api_key,
                num_results=count,
                time_range=time_range,
                language=language
            )
        
        result = json.loads(result_json)
        
        # 添加过滤器信息
        if result["status"] == "success":
            result["filters"] = {
                "time_filter": time_filter,
                "site_filter": site_filter,
                "file_type": file_type,
                "language": language
            }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "query": query,
            "message": f"高级搜索失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def search_government_sources(
    topic: str,
    api_key: str,
    government_domains: Optional[List[str]] = None,
    time_range: str = "m",
    max_results: int = 10
) -> str:
    """
    搜索政府官方来源（使用SerpAPI）
    
    Args:
        topic: 搜索主题
        api_key: SerpAPI API密钥
        government_domains: 政府域名列表
        time_range: 时间范围（d=天, w=周, m=月, y=年）
        max_results: 最大结果数量
        
    Returns:
        str: JSON格式的政府来源搜索结果
    """
    try:
        # 默认政府域名
        if not government_domains:
            government_domains = [
                "gov.cn",
                "nea.gov.cn",  # 国家能源局
                "ndrc.gov.cn",  # 国家发改委
                "mee.gov.cn",  # 生态环境部
                "miit.gov.cn"  # 工信部
            ]
        
        all_results = []
        
        for domain in government_domains:
            try:
                result_json = search_with_filters(
                    query=topic,
                    api_key=api_key,
                    search_type="web",
                    time_filter=time_range,
                    site_filter=domain,
                    language="zh-cn",
                    count=max_results // len(government_domains)
                )
                result = json.loads(result_json)
                
                if result["status"] == "success":
                    for item in result.get("results", []):
                        item["government_source"] = domain
                        all_results.append(item)
                        
            except Exception as e:
                continue
        
        # 按日期排序
        all_results.sort(key=lambda x: x.get("date", ""), reverse=True)
        
        return json.dumps({
            "status": "success",
            "topic": topic,
            "government_domains": government_domains,
            "total_results": len(all_results),
            "results": all_results,
            "search_time": datetime.now().isoformat(),
            "source": "SerpAPI Google Search"
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "topic": topic,
            "message": f"政府来源搜索失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def search_academic_papers(
    topic: str,
    api_key: str,
    academic_sites: Optional[List[str]] = None,
    max_results: int = 10
) -> str:
    """
    搜索学术论文和研究报告（使用SerpAPI）
    
    Args:
        topic: 搜索主题
        api_key: SerpAPI API密钥
        academic_sites: 学术网站列表
        max_results: 最大结果数量
        
    Returns:
        str: JSON格式的学术搜索结果
    """
    try:
        # 默认学术网站
        if not academic_sites:
            academic_sites = [
                "scholar.google.com",
                "arxiv.org",
                "researchgate.net",
                "ieee.org",
                "cnki.net"
            ]
        
        # 构建学术查询
        academic_query = f"{topic} (论文 OR paper OR research OR 研究)"
        
        all_results = []
        
        for site in academic_sites:
            try:
                result_json = search_with_filters(
                    query=academic_query,
                    api_key=api_key,
                    search_type="web",
                    site_filter=site,
                    language="zh-cn",
                    count=max_results // len(academic_sites)
                )
                result = json.loads(result_json)
                
                if result["status"] == "success":
                    for item in result.get("results", []):
                        item["academic_source"] = site
                        all_results.append(item)
                        
            except Exception as e:
                continue
        
        return json.dumps({
            "status": "success",
            "topic": topic,
            "academic_sites": academic_sites,
            "total_results": len(all_results),
            "results": all_results,
            "search_time": datetime.now().isoformat(),
            "source": "SerpAPI Google Search"
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "topic": topic,
            "message": f"学术搜索失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def comprehensive_energy_search(
    topic: str,
    api_key: str,
    include_news: bool = True,
    include_government: bool = True,
    include_academic: bool = True,
    time_range: str = "m",
    max_results_per_type: int = 10
) -> str:
    """
    综合能源信息搜索（新闻+政府+学术，使用SerpAPI）
    
    Args:
        topic: 搜索主题
        api_key: SerpAPI API密钥
        include_news: 是否包含新闻
        include_government: 是否包含政府来源
        include_academic: 是否包含学术来源
        time_range: 时间范围（d=天, w=周, m=月, y=年）
        max_results_per_type: 每种类型的最大结果数
        
    Returns:
        str: JSON格式的综合搜索结果
    """
    try:
        comprehensive_results = {
            "topic": topic,
            "time_range": time_range,
            "search_time": datetime.now().isoformat(),
            "results": {
                "news": [],
                "government": [],
                "academic": []
            },
            "summary": {
                "total_news": 0,
                "total_government": 0,
                "total_academic": 0,
                "total_all": 0
            }
        }
        
        # 搜索新闻
        if include_news:
            news_json = search_energy_news(
                topic=topic,
                api_key=api_key,
                time_range=time_range,
                max_results=max_results_per_type
            )
            news_result = json.loads(news_json)
            if news_result["status"] == "success":
                comprehensive_results["results"]["news"] = news_result.get("articles", [])
                comprehensive_results["summary"]["total_news"] = len(news_result.get("articles", []))
        
        # 搜索政府来源
        if include_government:
            gov_json = search_government_sources(
                topic=topic,
                api_key=api_key,
                time_range=time_range,
                max_results=max_results_per_type
            )
            gov_result = json.loads(gov_json)
            if gov_result["status"] == "success":
                comprehensive_results["results"]["government"] = gov_result.get("results", [])
                comprehensive_results["summary"]["total_government"] = len(gov_result.get("results", []))
        
        # 搜索学术来源
        if include_academic:
            academic_json = search_academic_papers(
                topic=topic,
                api_key=api_key,
                max_results=max_results_per_type
            )
            academic_result = json.loads(academic_json)
            if academic_result["status"] == "success":
                comprehensive_results["results"]["academic"] = academic_result.get("results", [])
                comprehensive_results["summary"]["total_academic"] = len(academic_result.get("results", []))
        
        # 计算总数
        comprehensive_results["summary"]["total_all"] = (
            comprehensive_results["summary"]["total_news"] +
            comprehensive_results["summary"]["total_government"] +
            comprehensive_results["summary"]["total_academic"]
        )
        
        return json.dumps(comprehensive_results, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "topic": topic,
            "message": f"综合搜索失败: {str(e)}"
        }, ensure_ascii=False)


if __name__ == "__main__":
    # 测试工具
    print("🧪 测试搜索引擎工具...")
    
    # 需要提供 SerpAPI API Key 进行测试
    api_key = os.getenv("SERPAPI_API_KEY", "")
    if api_key:
        # 测试网页搜索
        web_result = serpapi_search("新能源汽车", api_key=api_key, num_results=5)
        print("🔍 网页搜索:", json.loads(web_result)["status"])
        
        # 测试新闻搜索
        news_result = serpapi_news_search("储能技术", api_key=api_key, num_results=5)
        print("📰 新闻搜索:", json.loads(news_result)["status"])
        
        # 测试能源新闻搜索
        energy_result = search_energy_news("氢能", api_key=api_key, time_range="w", max_results=10)
        print("⚡ 能源新闻搜索:", json.loads(energy_result)["status"])
    else:
        print("⚠️ 未设置 SERPAPI_API_KEY 环境变量，跳过测试")
    
    print("✅ 工具测试完成！")
