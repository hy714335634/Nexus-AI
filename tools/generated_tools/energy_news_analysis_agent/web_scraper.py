#!/usr/bin/env python3
"""
Web scraper tool using Playwright for dynamic web page crawling.
Supports JavaScript-rendered pages and anti-scraping measures.
"""

import json
import asyncio
import re
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin, urlparse

from strands import tool

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

try:
    import requests
    from bs4 import BeautifulSoup
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


@tool
def scrape_webpage(
    url: str,
    wait_for_selector: Optional[str] = None,
    scroll_to_bottom: bool = False,
    timeout: int = 30000,
    use_playwright: bool = True
) -> str:
    """
    抓取网页内容，支持动态JavaScript渲染
    
    Args:
        url (str): 目标网页URL
        wait_for_selector (str, optional): 等待特定CSS选择器出现
        scroll_to_bottom (bool): 是否滚动到页面底部（加载懒加载内容）
        timeout (int): 超时时间（毫秒）
        use_playwright (bool): 是否使用Playwright（支持动态网页）
        
    Returns:
        str: JSON格式的抓取结果
    """
    try:
        if use_playwright and PLAYWRIGHT_AVAILABLE:
            # 使用异步Playwright
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(_scrape_with_playwright(
                url, wait_for_selector, scroll_to_bottom, timeout
            ))
            loop.close()
            return result
        elif REQUESTS_AVAILABLE:
            # 降级到requests + BeautifulSoup
            return _scrape_with_requests(url, timeout // 1000)
        else:
            return json.dumps({
                "status": "error",
                "message": "网页抓取库未安装。请安装: pip install playwright requests beautifulsoup4"
            }, ensure_ascii=False)
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "url": url,
            "message": f"抓取失败: {str(e)}"
        }, ensure_ascii=False)


async def _scrape_with_playwright(
    url: str,
    wait_for_selector: Optional[str],
    scroll_to_bottom: bool,
    timeout: int
) -> str:
    """使用Playwright抓取动态网页"""
    try:
        async with async_playwright() as p:
            # 启动浏览器（使用可视化模式进行调试）
            # 选项1: 使用 Playwright 的 Chromium
            # browser = await p.chromium.launch(
            #     headless=False,      # 显示浏览器窗口
            #     slow_mo=500          # 每步操作延迟500ms，便于观察
            # )
            # 选项2: 使用本地 Chrome（取消下面注释）
            browser = await p.chromium.launch(
                headless=False,
                slow_mo=500,
                channel="chrome"  # 使用本地 Chrome
            )
            # 选项3: 使用 Firefox（取消下面注释）
            # browser = await p.firefox.launch(
            #     headless=False,
            #     slow_mo=500
            # )
            
            # 创建新页面
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            page = await context.new_page()
            
            # 设置超时
            page.set_default_timeout(timeout)
            
            # 访问页面
            await page.goto(url, wait_until="domcontentloaded")
            
            # 等待特定选择器
            if wait_for_selector:
                try:
                    await page.wait_for_selector(wait_for_selector, timeout=timeout)
                except PlaywrightTimeout:
                    pass  # 继续执行，即使选择器未出现
            
            # 滚动到底部（加载懒加载内容）
            if scroll_to_bottom:
                await page.evaluate("""
                    async () => {
                        await new Promise((resolve) => {
                            let totalHeight = 0;
                            const distance = 100;
                            const timer = setInterval(() => {
                                const scrollHeight = document.body.scrollHeight;
                                window.scrollBy(0, distance);
                                totalHeight += distance;
                                if (totalHeight >= scrollHeight) {
                                    clearInterval(timer);
                                    resolve();
                                }
                            }, 100);
                        });
                    }
                """)
                await page.wait_for_timeout(1000)
            
            # 提取页面内容
            title = await page.title()
            html_content = await page.content()
            
            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(html_content, 'lxml')
            
            # 移除脚本和样式
            for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
                script.decompose()
            
            # 提取主要内容
            main_content = _extract_main_content(soup)
            
            # 提取链接
            links = _extract_links(soup, url)
            
            # 提取日期
            publish_date = _extract_date(soup, html_content)
            
            # 关闭浏览器
            await browser.close()
            
            result = {
                "status": "success",
                "url": url,
                "title": title,
                "content": main_content,
                "content_length": len(main_content),
                "links": links,
                "publish_date": publish_date,
                "extraction_time": datetime.now().isoformat(),
                "source_domain": urlparse(url).netloc,
                "method": "playwright"
            }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
    except PlaywrightTimeout:
        return json.dumps({
            "status": "error",
            "url": url,
            "message": f"页面加载超时（{timeout}ms）"
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "url": url,
            "message": f"Playwright抓取失败: {str(e)}"
        }, ensure_ascii=False)


def _scrape_with_requests(url: str, timeout: int) -> str:
    """使用requests + BeautifulSoup抓取静态网页"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
        }
        
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        # 移除脚本和样式
        for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
            script.decompose()
        
        # 提取主要内容
        main_content = _extract_main_content(soup)
        
        # 提取链接
        links = _extract_links(soup, url)
        
        # 提取日期
        publish_date = _extract_date(soup, response.text)
        
        # 提取标题
        title = soup.title.string if soup.title else ""
        
        result = {
            "status": "success",
            "url": url,
            "title": title,
            "content": main_content,
            "content_length": len(main_content),
            "links": links,
            "publish_date": publish_date,
            "extraction_time": datetime.now().isoformat(),
            "source_domain": urlparse(url).netloc,
            "method": "requests"
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except requests.Timeout:
        return json.dumps({
            "status": "error",
            "url": url,
            "message": f"请求超时（{timeout}秒）"
        }, ensure_ascii=False)
    except requests.RequestException as e:
        return json.dumps({
            "status": "error",
            "url": url,
            "message": f"网络请求失败: {str(e)}"
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "url": url,
            "message": f"内容提取失败: {str(e)}"
        }, ensure_ascii=False)


def _extract_main_content(soup: BeautifulSoup) -> str:
    """提取网页主要内容"""
    # 尝试提取article、main、content等主要内容区域
    main_content = None
    for selector in ['article', 'main', '[role="main"]', '.content', '#content', '.main-content']:
        main_content = soup.select_one(selector)
        if main_content:
            break
    
    if not main_content:
        main_content = soup.body if soup.body else soup
    
    # 提取文本
    text = main_content.get_text(separator="\n", strip=True)
    
    # 清理文本
    lines = []
    for line in text.split("\n"):
        line = line.strip()
        if line and len(line) > 10:  # 过滤短行
            lines.append(line)
    
    return "\n".join(lines)


def _extract_links(soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
    """提取网页中的链接"""
    links = []
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        text = a_tag.get_text(strip=True)
        
        # 转换相对链接为绝对链接
        absolute_url = urljoin(base_url, href)
        
        # 过滤无效链接
        if absolute_url.startswith(('http://', 'https://')) and text:
            links.append({
                "url": absolute_url,
                "text": text
            })
    
    return links[:50]  # 限制链接数量


def _extract_date(soup: BeautifulSoup, html_content: str) -> Optional[str]:
    """提取文章发布日期"""
    # 尝试多种日期提取策略
    date_patterns = [
        r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?',
        r'\d{4}\.\d{1,2}\.\d{1,2}',
        r'\d{1,2}/\d{1,2}/\d{4}'
    ]
    
    # 从meta标签提取
    for meta_tag in ['article:published_time', 'datePublished', 'publishdate']:
        meta = soup.find('meta', attrs={'property': meta_tag}) or soup.find('meta', attrs={'name': meta_tag})
        if meta and meta.get('content'):
            return meta['content']
    
    # 从time标签提取
    time_tag = soup.find('time')
    if time_tag and time_tag.get('datetime'):
        return time_tag['datetime']
    
    # 从文本中提取
    for pattern in date_patterns:
        match = re.search(pattern, html_content)
        if match:
            return match.group(0)
    
    return None


@tool
def batch_scrape_webpages(
    urls: List[str],
    wait_for_selector: Optional[str] = None,
    max_concurrent: int = 3,
    timeout: int = 30000,
    use_playwright: bool = True
) -> str:
    """
    批量抓取多个网页内容
    
    Args:
        urls (List[str]): 网页URL列表
        wait_for_selector (str, optional): 等待特定CSS选择器出现
        max_concurrent (int): 最大并发数（默认3，避免资源消耗过大）
        timeout (int): 超时时间（毫秒）
        use_playwright (bool): 是否使用Playwright
        
    Returns:
        str: JSON格式的批量抓取结果
    """
    try:
        results = []
        successful = 0
        failed = 0
        
        # 分批处理，避免并发过多
        for i in range(0, len(urls), max_concurrent):
            batch_urls = urls[i:i+max_concurrent]
            
            for url in batch_urls:
                result_json = scrape_webpage(
                    url,
                    wait_for_selector=wait_for_selector,
                    scroll_to_bottom=False,
                    timeout=timeout,
                    use_playwright=use_playwright
                )
                result = json.loads(result_json)
                
                if result["status"] == "success":
                    successful += 1
                else:
                    failed += 1
                
                results.append(result)
                
                # 避免触发速率限制
                time.sleep(2)
        
        return json.dumps({
            "status": "success",
            "total_urls": len(urls),
            "processed_urls": len(results),
            "successful": successful,
            "failed": failed,
            "results": results,
            "extraction_time": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"批量抓取失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def extract_article_list(
    url: str,
    article_selector: str = "article, .news-item, .article-item",
    title_selector: str = "h1, h2, h3, .title",
    link_selector: str = "a",
    date_selector: Optional[str] = None,
    max_articles: int = 20,
    use_playwright: bool = True
) -> str:
    """
    从列表页提取文章列表
    
    Args:
        url (str): 列表页URL
        article_selector (str): 文章容器的CSS选择器
        title_selector (str): 标题的CSS选择器
        link_selector (str): 链接的CSS选择器
        date_selector (str, optional): 日期的CSS选择器
        max_articles (int): 最大提取文章数
        use_playwright (bool): 是否使用Playwright
        
    Returns:
        str: JSON格式的文章列表
    """
    try:
        # 先抓取列表页
        page_result_json = scrape_webpage(url, timeout=30000, use_playwright=use_playwright)
        page_result = json.loads(page_result_json)
        
        if page_result["status"] != "success":
            return json.dumps({
                "status": "error",
                "message": f"列表页抓取失败: {page_result.get('message', 'Unknown error')}"
            }, ensure_ascii=False)
        
        # 解析HTML
        soup = BeautifulSoup(page_result.get("content", ""), 'lxml')
        
        # 提取文章列表
        articles = []
        article_elements = soup.select(article_selector)[:max_articles]
        
        for idx, article_elem in enumerate(article_elements, 1):
            try:
                # 提取标题
                title_elem = article_elem.select_one(title_selector)
                title = title_elem.get_text(strip=True) if title_elem else ""
                
                # 提取链接
                link_elem = article_elem.select_one(link_selector)
                if link_elem and link_elem.get('href'):
                    article_url = urljoin(url, link_elem['href'])
                else:
                    article_url = ""
                
                # 提取日期
                publish_date = None
                if date_selector:
                    date_elem = article_elem.select_one(date_selector)
                    if date_elem:
                        publish_date = date_elem.get_text(strip=True)
                
                if title and article_url:
                    articles.append({
                        "index": idx,
                        "title": title,
                        "url": article_url,
                        "publish_date": publish_date,
                        "source_page": url
                    })
                    
            except Exception as e:
                print(f"提取文章 {idx} 失败: {e}")
                continue
        
        return json.dumps({
            "status": "success",
            "list_url": url,
            "total_articles": len(articles),
            "articles": articles,
            "extraction_time": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "url": url,
            "message": f"文章列表提取失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def scrape_energy_news_sites(
    keywords: str,
    data_sources: Optional[List[str]] = None,
    max_articles_per_source: int = 10
) -> str:
    """
    从能源行业新闻网站抓取内容
    
    Args:
        keywords (str): 搜索关键词
        data_sources (List[str], optional): 数据源列表
        max_articles_per_source (int): 每个数据源最大文章数
        
    Returns:
        str: JSON格式的抓取结果
    """
    try:
        # 默认数据源
        if not data_sources:
            data_sources = [
                "https://energy.bjx.com.cn/nyxny/",  # 北极星能源网
                "https://www.nea.gov.cn/",  # 国家能源局
                "https://www.ndrc.gov.cn/"  # 国家发改委
            ]
        
        all_results = {
            "keywords": keywords,
            "data_sources": data_sources,
            "scraping_time": datetime.now().isoformat(),
            "results": [],
            "summary": {
                "total_sources": len(data_sources),
                "total_articles": 0,
                "successful_sources": 0,
                "failed_sources": 0
            }
        }
        
        # 针对不同数据源使用不同的抓取策略
        for source_url in data_sources:
            try:
                domain = urlparse(source_url).netloc
                
                # 根据域名选择抓取策略
                if "bjx.com.cn" in domain:
                    # 北极星能源网 - 需要Playwright
                    source_result = _scrape_bjx_energy(source_url, keywords, max_articles_per_source)
                elif "nea.gov.cn" in domain:
                    # 国家能源局 - 可用requests
                    source_result = _scrape_nea_gov(source_url, keywords, max_articles_per_source)
                elif "ndrc.gov.cn" in domain:
                    # 国家发改委 - 可用requests
                    source_result = _scrape_ndrc_gov(source_url, keywords, max_articles_per_source)
                else:
                    # 其他来源 - 通用抓取
                    source_result = _scrape_generic_site(source_url, keywords, max_articles_per_source)
                
                if source_result["status"] == "success":
                    all_results["results"].append(source_result)
                    all_results["summary"]["total_articles"] += len(source_result.get("articles", []))
                    all_results["summary"]["successful_sources"] += 1
                else:
                    all_results["results"].append(source_result)
                    all_results["summary"]["failed_sources"] += 1
                
                # 避免触发速率限制
                time.sleep(3)
                
            except Exception as e:
                all_results["results"].append({
                    "status": "error",
                    "source_url": source_url,
                    "message": f"数据源抓取失败: {str(e)}"
                })
                all_results["summary"]["failed_sources"] += 1
        
        return json.dumps(all_results, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"批量抓取失败: {str(e)}"
        }, ensure_ascii=False)


def _scrape_bjx_energy(url: str, keywords: str, max_articles: int) -> Dict[str, Any]:
    """抓取北极星能源网"""
    try:
        # 构建搜索URL
        search_url = f"https://energy.bjx.com.cn/search.aspx?keyword={keywords}"
        
        # 使用Playwright抓取
        result_json = scrape_webpage(
            search_url,
            wait_for_selector=".news-list",
            scroll_to_bottom=True,
            timeout=30000,
            use_playwright=True
        )
        result = json.loads(result_json)
        
        if result["status"] != "success":
            return {
                "status": "error",
                "source_url": url,
                "source_name": "北极星能源网",
                "message": "页面抓取失败"
            }
        
        # 提取文章列表
        articles_json = extract_article_list(
            search_url,
            article_selector=".news-item, .article-item",
            title_selector="h3, .title",
            link_selector="a",
            date_selector=".date, .time",
            max_articles=max_articles,
            use_playwright=False  # 已经抓取过页面，使用缓存
        )
        articles_result = json.loads(articles_json)
        
        return {
            "status": "success",
            "source_url": url,
            "source_name": "北极星能源网",
            "articles": articles_result.get("articles", []),
            "total_articles": len(articles_result.get("articles", []))
        }
        
    except Exception as e:
        return {
            "status": "error",
            "source_url": url,
            "source_name": "北极星能源网",
            "message": f"抓取失败: {str(e)}"
        }


def _scrape_nea_gov(url: str, keywords: str, max_articles: int) -> Dict[str, Any]:
    """抓取国家能源局"""
    try:
        # 国家能源局通常有新闻列表页
        news_url = urljoin(url, "/xwfb/")
        
        result_json = scrape_webpage(news_url, timeout=30000, use_playwright=False)
        result = json.loads(result_json)
        
        if result["status"] != "success":
            return {
                "status": "error",
                "source_url": url,
                "source_name": "国家能源局",
                "message": "页面抓取失败"
            }
        
        # 从内容中过滤包含关键词的文章
        soup = BeautifulSoup(result.get("content", ""), 'lxml')
        articles = []
        
        for a_tag in soup.find_all('a', href=True):
            title = a_tag.get_text(strip=True)
            if keywords in title and len(title) > 10:
                article_url = urljoin(news_url, a_tag['href'])
                articles.append({
                    "title": title,
                    "url": article_url,
                    "source_page": news_url
                })
                
                if len(articles) >= max_articles:
                    break
        
        return {
            "status": "success",
            "source_url": url,
            "source_name": "国家能源局",
            "articles": articles,
            "total_articles": len(articles)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "source_url": url,
            "source_name": "国家能源局",
            "message": f"抓取失败: {str(e)}"
        }


def _scrape_ndrc_gov(url: str, keywords: str, max_articles: int) -> Dict[str, Any]:
    """抓取国家发改委"""
    try:
        # 国家发改委通常有新闻列表页
        news_url = urljoin(url, "/xwzx/")
        
        result_json = scrape_webpage(news_url, timeout=30000, use_playwright=False)
        result = json.loads(result_json)
        
        if result["status"] != "success":
            return {
                "status": "error",
                "source_url": url,
                "source_name": "国家发改委",
                "message": "页面抓取失败"
            }
        
        # 从内容中过滤包含关键词的文章
        soup = BeautifulSoup(result.get("content", ""), 'lxml')
        articles = []
        
        for a_tag in soup.find_all('a', href=True):
            title = a_tag.get_text(strip=True)
            if keywords in title and len(title) > 10:
                article_url = urljoin(news_url, a_tag['href'])
                articles.append({
                    "title": title,
                    "url": article_url,
                    "source_page": news_url
                })
                
                if len(articles) >= max_articles:
                    break
        
        return {
            "status": "success",
            "source_url": url,
            "source_name": "国家发改委",
            "articles": articles,
            "total_articles": len(articles)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "source_url": url,
            "source_name": "国家发改委",
            "message": f"抓取失败: {str(e)}"
        }


def _scrape_generic_site(url: str, keywords: str, max_articles: int) -> Dict[str, Any]:
    """通用网站抓取"""
    try:
        result_json = scrape_webpage(url, timeout=30000, use_playwright=True)
        result = json.loads(result_json)
        
        if result["status"] != "success":
            return {
                "status": "error",
                "source_url": url,
                "source_name": urlparse(url).netloc,
                "message": "页面抓取失败"
            }
        
        # 从链接中过滤包含关键词的文章
        articles = []
        for link in result.get("links", []):
            if keywords in link["text"]:
                articles.append({
                    "title": link["text"],
                    "url": link["url"],
                    "source_page": url
                })
                
                if len(articles) >= max_articles:
                    break
        
        return {
            "status": "success",
            "source_url": url,
            "source_name": urlparse(url).netloc,
            "articles": articles,
            "total_articles": len(articles)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "source_url": url,
            "source_name": urlparse(url).netloc,
            "message": f"抓取失败: {str(e)}"
        }


@tool
def scrape_with_retry(
    url: str,
    max_retries: int = 3,
    retry_delay: int = 5,
    timeout: int = 30000
) -> str:
    """
    带重试机制的网页抓取
    
    Args:
        url (str): 目标网页URL
        max_retries (int): 最大重试次数
        retry_delay (int): 重试延迟（秒）
        timeout (int): 超时时间（毫秒）
        
    Returns:
        str: JSON格式的抓取结果
    """
    for attempt in range(max_retries):
        try:
            result_json = scrape_webpage(url, timeout=timeout, use_playwright=True)
            result = json.loads(result_json)
            
            if result["status"] == "success":
                result["retry_attempts"] = attempt
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            # 如果失败，等待后重试
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))  # 指数退避
                
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
            else:
                return json.dumps({
                    "status": "error",
                    "url": url,
                    "message": f"重试{max_retries}次后仍失败: {str(e)}",
                    "retry_attempts": max_retries
                }, ensure_ascii=False)
    
    return json.dumps({
        "status": "error",
        "url": url,
        "message": f"重试{max_retries}次后仍失败",
        "retry_attempts": max_retries
    }, ensure_ascii=False)


if __name__ == "__main__":
    # 测试工具
    print("🧪 测试网页抓取工具...")
    
    # 测试单页抓取
    test_url = "https://www.nea.gov.cn/"
    result = scrape_webpage(test_url, use_playwright=False)
    print("📄 单页抓取结果:", json.loads(result)["status"])
    
    # 测试文章列表提取
    list_url = "https://energy.bjx.com.cn/nyxny/"
    articles = extract_article_list(list_url)
    print("📋 文章列表提取:", json.loads(articles)["status"])
    
    print("✅ 工具测试完成！")
