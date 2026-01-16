"""
生命科学新闻采集工具模块

该模块提供多源数据采集功能，支持：
- SerpAPI Google Search集成
- 医疗资讯网站HTML解析（静态和动态）
- Playwright浏览器自动化
- 并发采集和错误处理
- URL去重和深度遍历
"""

import json
import asyncio
import hashlib
import re
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from urllib.parse import urljoin, urlparse
import aiohttp
from bs4 import BeautifulSoup
from strands import tool


# ============================================================================
# SerpAPI Google Search 工具
# ============================================================================

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
    import requests
    
    try:
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
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "displayed_link": item.get("displayed_link", ""),
                "date": item.get("date", ""),
                "source": "SerpAPI Google Search"
            })
        
        return json.dumps({
            "success": True,
            "query": query,
            "total_results": len(results),
            "results": results,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except requests.exceptions.Timeout:
        return json.dumps({
            "success": False,
            "error": "SerpAPI请求超时",
            "query": query
        }, ensure_ascii=False, indent=2)
    except requests.exceptions.RequestException as e:
        return json.dumps({
            "success": False,
            "error": f"SerpAPI请求失败: {str(e)}",
            "query": query
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"SerpAPI搜索异常: {str(e)}",
            "query": query
        }, ensure_ascii=False, indent=2)


# ============================================================================
# HTTP 静态网页采集工具
# ============================================================================

@tool
async def fetch_webpage_content(
    url: str,
    timeout: int = 30,
    headers: Optional[Dict[str, str]] = None
) -> str:
    """
    使用aiohttp获取网页内容（适用于静态网页）
    
    Args:
        url: 网页URL
        timeout: 超时时间（秒）
        headers: 自定义请求头
    
    Returns:
        str: JSON格式的网页内容
    """
    default_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive"
    }
    
    if headers:
        default_headers.update(headers)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=timeout),
                headers=default_headers,
                ssl=False
            ) as response:
                response.raise_for_status()
                html_content = await response.text()
                
                return json.dumps({
                    "success": True,
                    "url": url,
                    "status_code": response.status,
                    "content_length": len(html_content),
                    "html": html_content,
                    "timestamp": datetime.now().isoformat()
                }, ensure_ascii=False)
                
    except asyncio.TimeoutError:
        return json.dumps({
            "success": False,
            "url": url,
            "error": "请求超时"
        }, ensure_ascii=False)
    except aiohttp.ClientError as e:
        return json.dumps({
            "success": False,
            "url": url,
            "error": f"HTTP请求失败: {str(e)}"
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "success": False,
            "url": url,
            "error": f"网页获取异常: {str(e)}"
        }, ensure_ascii=False)


# ============================================================================
# Playwright 动态网页采集工具
# ============================================================================

@tool
def fetch_dynamic_webpage(
    url: str,
    wait_for_selector: Optional[str] = None,
    scroll_to_bottom: bool = False,
    timeout: int = 30000,
    wait_time: int = 2000
) -> str:
    """
    使用Playwright获取动态网页内容（支持JavaScript渲染）
    
    Args:
        url: 网页URL
        wait_for_selector: 等待特定CSS选择器出现
        scroll_to_bottom: 是否滚动到页面底部（加载懒加载内容）
        timeout: 超时时间（毫秒）
        wait_time: 页面加载后等待时间（毫秒）
    
    Returns:
        str: JSON格式的网页内容
    """
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            page = context.new_page()
            
            # 设置超时
            page.set_default_timeout(timeout)
            
            # 导航到URL
            page.goto(url, wait_until="networkidle")
            
            # 等待特定选择器
            if wait_for_selector:
                page.wait_for_selector(wait_for_selector, timeout=timeout)
            
            # 滚动到底部
            if scroll_to_bottom:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(wait_time)
            
            # 等待额外时间确保内容加载
            page.wait_for_timeout(wait_time)
            
            # 获取HTML内容
            html_content = page.content()
            
            browser.close()
            
            return json.dumps({
                "success": True,
                "url": url,
                "content_length": len(html_content),
                "html": html_content,
                "method": "playwright",
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False)
            
    except Exception as e:
        return json.dumps({
            "success": False,
            "url": url,
            "error": f"Playwright采集失败: {str(e)}",
            "method": "playwright"
        }, ensure_ascii=False)


# ============================================================================
# HTML 内容解析工具
# ============================================================================

@tool
def parse_article_content(
    html: str,
    url: str,
    title_selectors: List[str],
    content_selectors: List[str],
    date_selectors: Optional[List[str]] = None,
    link_selectors: Optional[List[str]] = None
) -> str:
    """
    从HTML中解析文章内容
    
    Args:
        html: HTML内容
        url: 网页URL
        title_selectors: 标题CSS选择器列表（按优先级）
        content_selectors: 正文CSS选择器列表（按优先级）
        date_selectors: 日期CSS选择器列表（可选）
        link_selectors: 链接CSS选择器列表（可选）
    
    Returns:
        str: JSON格式的解析结果
    """
    try:
        soup = BeautifulSoup(html, "lxml")
        
        # 提取标题
        title = ""
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get_text(strip=True)
                break
        
        # 提取正文
        content = ""
        for selector in content_selectors:
            element = soup.select_one(selector)
            if element:
                # 清理HTML标签，保留文本
                content = element.get_text(separator="\n", strip=True)
                break
        
        # 提取日期
        date = ""
        if date_selectors:
            for selector in date_selectors:
                element = soup.select_one(selector)
                if element:
                    date = element.get_text(strip=True)
                    break
        
        # 提取链接
        links = []
        if link_selectors:
            for selector in link_selectors:
                elements = soup.select(selector)
                for elem in elements:
                    href = elem.get("href", "")
                    if href:
                        # 转换相对URL为绝对URL
                        absolute_url = urljoin(url, href)
                        links.append({
                            "text": elem.get_text(strip=True),
                            "url": absolute_url
                        })
        
        return json.dumps({
            "success": True,
            "url": url,
            "title": title,
            "content": content,
            "date": date,
            "links": links,
            "content_length": len(content),
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "url": url,
            "error": f"HTML解析失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def extract_article_list(
    html: str,
    url: str,
    article_container_selector: str,
    title_selector: str,
    link_selector: str,
    date_selector: Optional[str] = None,
    snippet_selector: Optional[str] = None,
    max_articles: int = 50
) -> str:
    """
    从列表页提取文章列表
    
    Args:
        html: HTML内容
        url: 列表页URL
        article_container_selector: 文章容器CSS选择器
        title_selector: 标题CSS选择器（相对于容器）
        link_selector: 链接CSS选择器（相对于容器）
        date_selector: 日期CSS选择器（相对于容器，可选）
        snippet_selector: 摘要CSS选择器（相对于容器，可选）
        max_articles: 最大提取文章数
    
    Returns:
        str: JSON格式的文章列表
    """
    try:
        soup = BeautifulSoup(html, "lxml")
        
        # 查找所有文章容器
        containers = soup.select(article_container_selector)
        
        articles = []
        for container in containers[:max_articles]:
            # 提取标题
            title_elem = container.select_one(title_selector)
            title = title_elem.get_text(strip=True) if title_elem else ""
            
            # 提取链接
            link_elem = container.select_one(link_selector)
            link = ""
            if link_elem:
                link = link_elem.get("href", "")
                if link:
                    link = urljoin(url, link)
            
            # 提取日期
            date = ""
            if date_selector:
                date_elem = container.select_one(date_selector)
                if date_elem:
                    date = date_elem.get_text(strip=True)
            
            # 提取摘要
            snippet = ""
            if snippet_selector:
                snippet_elem = container.select_one(snippet_selector)
                if snippet_elem:
                    snippet = snippet_elem.get_text(strip=True)
            
            if title and link:
                articles.append({
                    "title": title,
                    "link": link,
                    "date": date,
                    "snippet": snippet,
                    "source_url": url
                })
        
        return json.dumps({
            "success": True,
            "source_url": url,
            "total_articles": len(articles),
            "articles": articles,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "source_url": url,
            "error": f"文章列表提取失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


# ============================================================================
# URL管理工具
# ============================================================================

@tool
def deduplicate_urls(
    urls: List[str],
    normalize: bool = True
) -> str:
    """
    URL去重工具
    
    Args:
        urls: URL列表
        normalize: 是否规范化URL（移除查询参数和片段）
    
    Returns:
        str: JSON格式的去重结果
    """
    try:
        seen_urls: Set[str] = set()
        unique_urls = []
        duplicates = []
        
        for url in urls:
            # 规范化URL
            normalized_url = url
            if normalize:
                parsed = urlparse(url)
                # 移除查询参数和片段
                normalized_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            
            # 去重
            if normalized_url not in seen_urls:
                seen_urls.add(normalized_url)
                unique_urls.append(url)
            else:
                duplicates.append(url)
        
        return json.dumps({
            "success": True,
            "original_count": len(urls),
            "unique_count": len(unique_urls),
            "duplicate_count": len(duplicates),
            "unique_urls": unique_urls,
            "duplicates": duplicates,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"URL去重失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def filter_urls_by_domain(
    urls: List[str],
    allowed_domains: Optional[List[str]] = None,
    blocked_domains: Optional[List[str]] = None
) -> str:
    """
    根据域名过滤URL
    
    Args:
        urls: URL列表
        allowed_domains: 允许的域名列表（白名单）
        blocked_domains: 禁止的域名列表（黑名单）
    
    Returns:
        str: JSON格式的过滤结果
    """
    try:
        filtered_urls = []
        removed_urls = []
        
        for url in urls:
            parsed = urlparse(url)
            domain = parsed.netloc
            
            # 黑名单检查
            if blocked_domains and any(blocked in domain for blocked in blocked_domains):
                removed_urls.append({"url": url, "reason": "blocked_domain"})
                continue
            
            # 白名单检查
            if allowed_domains and not any(allowed in domain for allowed in allowed_domains):
                removed_urls.append({"url": url, "reason": "not_in_whitelist"})
                continue
            
            filtered_urls.append(url)
        
        return json.dumps({
            "success": True,
            "original_count": len(urls),
            "filtered_count": len(filtered_urls),
            "removed_count": len(removed_urls),
            "filtered_urls": filtered_urls,
            "removed_urls": removed_urls,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"URL过滤失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


# ============================================================================
# 批量并发采集工具
# ============================================================================

@tool
async def batch_fetch_webpages(
    urls: List[str],
    max_concurrent: int = 5,
    timeout: int = 30,
    use_playwright: bool = False,
    retry_count: int = 2
) -> str:
    """
    批量并发采集网页
    
    Args:
        urls: URL列表
        max_concurrent: 最大并发数（默认5）
        timeout: 超时时间（秒）
        use_playwright: 是否使用Playwright（默认False）
        retry_count: 失败重试次数（默认2）
    
    Returns:
        str: JSON格式的批量采集结果
    """
    results = []
    failed_urls = []
    
    async def fetch_with_retry(url: str) -> Dict[str, Any]:
        """带重试的单个URL采集"""
        for attempt in range(retry_count + 1):
            try:
                if use_playwright:
                    # 使用Playwright（同步转异步）
                    result_json = fetch_dynamic_webpage(url, timeout=timeout * 1000)
                    result = json.loads(result_json)
                else:
                    # 使用aiohttp
                    result_json = await fetch_webpage_content(url, timeout=timeout)
                    result = json.loads(result_json)
                
                if result.get("success"):
                    return result
                else:
                    if attempt < retry_count:
                        await asyncio.sleep(2 ** attempt)  # 指数退避
                    else:
                        return result
                        
            except Exception as e:
                if attempt < retry_count:
                    await asyncio.sleep(2 ** attempt)
                else:
                    return {
                        "success": False,
                        "url": url,
                        "error": f"重试{retry_count}次后仍失败: {str(e)}"
                    }
        
        return {"success": False, "url": url, "error": "未知错误"}
    
    # 使用信号量控制并发
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def fetch_with_semaphore(url: str):
        async with semaphore:
            return await fetch_with_retry(url)
    
    # 并发执行
    tasks = [fetch_with_semaphore(url) for url in urls]
    results = await asyncio.gather(*tasks)
    
    # 分类成功和失败
    successful_results = [r for r in results if r.get("success")]
    failed_results = [r for r in results if not r.get("success")]
    
    return json.dumps({
        "success": True,
        "total_urls": len(urls),
        "successful_count": len(successful_results),
        "failed_count": len(failed_results),
        "successful_results": successful_results,
        "failed_results": failed_results,
        "timestamp": datetime.now().isoformat()
    }, ensure_ascii=False, indent=2)


# ============================================================================
# 深度遍历采集工具
# ============================================================================

@tool
async def deep_crawl_website(
    start_url: str,
    max_depth: int = 2,
    max_pages: int = 50,
    allowed_domains: Optional[List[str]] = None,
    article_patterns: Optional[List[str]] = None,
    timeout: int = 30
) -> str:
    """
    深度遍历网站，自动发现和采集详情页
    
    Args:
        start_url: 起始URL
        max_depth: 最大遍历深度（默认2）
        max_pages: 最大采集页面数（默认50）
        allowed_domains: 允许的域名列表（默认只允许起始URL的域名）
        article_patterns: 文章URL模式列表（正则表达式）
        timeout: 超时时间（秒）
    
    Returns:
        str: JSON格式的遍历结果
    """
    try:
        # 初始化
        visited_urls: Set[str] = set()
        url_queue: List[tuple[str, int]] = [(start_url, 0)]  # (url, depth)
        collected_pages = []
        
        # 确定允许的域名
        if not allowed_domains:
            parsed = urlparse(start_url)
            allowed_domains = [parsed.netloc]
        
        # 编译文章URL模式
        article_regex_list = []
        if article_patterns:
            article_regex_list = [re.compile(pattern) for pattern in article_patterns]
        
        async with aiohttp.ClientSession() as session:
            while url_queue and len(collected_pages) < max_pages:
                current_url, current_depth = url_queue.pop(0)
                
                # 跳过已访问的URL
                if current_url in visited_urls:
                    continue
                
                visited_urls.add(current_url)
                
                # 检查域名
                parsed = urlparse(current_url)
                if not any(domain in parsed.netloc for domain in allowed_domains):
                    continue
                
                # 获取页面内容
                try:
                    async with session.get(
                        current_url,
                        timeout=aiohttp.ClientTimeout(total=timeout),
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                        },
                        ssl=False
                    ) as response:
                        if response.status != 200:
                            continue
                        
                        html = await response.text()
                        soup = BeautifulSoup(html, "lxml")
                        
                        # 判断是否为文章页
                        is_article = False
                        if article_regex_list:
                            is_article = any(regex.search(current_url) for regex in article_regex_list)
                        
                        # 收集页面
                        collected_pages.append({
                            "url": current_url,
                            "depth": current_depth,
                            "is_article": is_article,
                            "html": html,
                            "title": soup.title.string if soup.title else ""
                        })
                        
                        # 如果未达到最大深度，提取链接继续遍历
                        if current_depth < max_depth:
                            for link in soup.find_all("a", href=True):
                                href = link["href"]
                                absolute_url = urljoin(current_url, href)
                                
                                # 跳过已访问和外部链接
                                if absolute_url not in visited_urls:
                                    parsed_link = urlparse(absolute_url)
                                    if any(domain in parsed_link.netloc for domain in allowed_domains):
                                        url_queue.append((absolute_url, current_depth + 1))
                
                except Exception as e:
                    # 单个页面失败不影响整体
                    continue
                
                # 避免过快请求
                await asyncio.sleep(0.5)
        
        return json.dumps({
            "success": True,
            "start_url": start_url,
            "total_collected": len(collected_pages),
            "total_visited": len(visited_urls),
            "max_depth_reached": max([p["depth"] for p in collected_pages]) if collected_pages else 0,
            "collected_pages": collected_pages,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "start_url": start_url,
            "error": f"深度遍历失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


# ============================================================================
# 文本清洗工具
# ============================================================================

@tool
def clean_article_text(
    text: str,
    remove_extra_whitespace: bool = True,
    remove_html_entities: bool = True,
    remove_special_chars: bool = False
) -> str:
    """
    清洗文章文本
    
    Args:
        text: 原始文本
        remove_extra_whitespace: 移除多余空格和换行
        remove_html_entities: 移除HTML实体
        remove_special_chars: 移除特殊字符
    
    Returns:
        str: JSON格式的清洗结果
    """
    try:
        import html as html_lib
        
        cleaned_text = text
        
        # 移除HTML实体
        if remove_html_entities:
            cleaned_text = html_lib.unescape(cleaned_text)
        
        # 移除多余空格和换行
        if remove_extra_whitespace:
            # 替换多个空格为单个空格
            cleaned_text = re.sub(r' +', ' ', cleaned_text)
            # 替换多个换行为最多两个换行
            cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
            # 移除行首行尾空格
            cleaned_text = '\n'.join(line.strip() for line in cleaned_text.split('\n'))
        
        # 移除特殊字符（保留中英文、数字、标点）
        if remove_special_chars:
            cleaned_text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s\.,!?;:，。！？；：、\-\(\)\[\]（）【】]', '', cleaned_text)
        
        return json.dumps({
            "success": True,
            "original_length": len(text),
            "cleaned_length": len(cleaned_text),
            "cleaned_text": cleaned_text,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"文本清洗失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


# ============================================================================
# 数据源配置加载工具
# ============================================================================

@tool
def load_data_source_config(
    config_path: str = "agents/generated_agents/lifescience_news_collector/lifescience_news_sources.yaml"
) -> str:
    """
    加载数据源配置文件
    
    Args:
        config_path: 配置文件路径
    
    Returns:
        str: JSON格式的配置内容
    """
    try:
        import yaml
        from pathlib import Path
        
        config_file = Path(config_path)
        
        if not config_file.exists():
            return json.dumps({
                "success": False,
                "error": f"配置文件不存在: {config_path}"
            }, ensure_ascii=False, indent=2)
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        return json.dumps({
            "success": True,
            "config_path": config_path,
            "config": config,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"配置加载失败: {str(e)}"
        }, ensure_ascii=False, indent=2)
