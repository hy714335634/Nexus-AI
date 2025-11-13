#!/usr/bin/env python3
"""
Google Scholar搜索工具

该模块提供了通过关键字在Google Scholar上搜索学术文献并提取文献详细信息的功能。
支持根据用户指定的参数获取文献标题、作者、摘要、引用次数、发表年份、期刊等信息。
"""

from strands import tool
from typing import Dict, List, Optional, Any, Union
import requests
import json
import re
import logging
import random
import urllib.parse
from bs4 import BeautifulSoup

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_random_user_agent() -> str:
    """
    生成随机User-Agent头以避免被反爬机制检测
    
    Returns:
        str: 随机的User-Agent字符串
    """
    try:
        from fake_useragent import UserAgent
        ua = UserAgent()
        return ua.random
    except Exception as e:
        logger.warning(f"无法使用fake_useragent: {e}")
        # 备选User-Agent列表
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15'
        ]
        return random.choice(user_agents)

def build_search_url(keywords: str, sort_by: Optional[str] = None, 
                     start_year: Optional[int] = None, end_year: Optional[int] = None) -> str:
    """
    构建Google Scholar搜索URL
    
    Args:
        keywords (str): 搜索关键字或短语
        sort_by (str, optional): 排序方式，可选值：relevance（相关度）或date（日期）
        start_year (int, optional): 筛选文献的起始年份
        end_year (int, optional): 筛选文献的结束年份
        
    Returns:
        str: 完整的Google Scholar搜索URL
    """
    base_url = 'https://scholar.google.com/scholar'
    params = {'q': keywords, 'hl': 'en'}
    
    # 添加排序参数
    if sort_by and sort_by.lower() == 'date':
        params['scisbd'] = '1'  # 按日期排序
    
    # 添加年份范围参数
    if start_year and end_year:
        params['as_ylo'] = str(start_year)  # 起始年份
        params['as_yhi'] = str(end_year)    # 结束年份
    elif start_year:
        params['as_ylo'] = str(start_year)
    elif end_year:
        params['as_yhi'] = str(end_year)
    
    return f"{base_url}?{urllib.parse.urlencode(params)}"

def extract_article_info(article_element) -> Dict[str, Any]:
    """
    从单个文献结果元素中提取详细信息
    
    Args:
        article_element: BeautifulSoup对象，表示单篇文献的HTML元素
        
    Returns:
        Dict[str, Any]: 包含文献详细信息的字典
    """
    article_info = {
        'title': '',
        'authors': [],
        'publication': '',
        'year': None,
        'abstract': '',
        'citations': 0,
        'url': ''
    }
    
    try:
        # 提取标题和链接
        title_element = article_element.find('h3', class_='gs_rt')
        if title_element:
            if title_element.a:
                article_info['title'] = title_element.a.text.strip()
                article_info['url'] = title_element.a.get('href', '')
            else:
                article_info['title'] = title_element.text.strip()
        
        # 提取作者、期刊和年份信息
        pub_info = article_element.find('div', class_='gs_a')
        if pub_info:
            pub_text = pub_info.text
            # 作者通常在第一个 '-' 之前
            if '-' in pub_text:
                authors_text = pub_text.split('-')[0]
                article_info['authors'] = [author.strip() for author in authors_text.split(',') if author.strip()]
            
            # 提取年份 (通常是4位数字)
            year_match = re.search(r'\b(19|20)\d{2}\b', pub_text)
            if year_match:
                article_info['year'] = int(year_match.group(0))
            
            # 提取期刊信息
            if '-' in pub_text and len(pub_text.split('-')) > 1:
                pub_parts = pub_text.split('-')
                if len(pub_parts) > 1:
                    article_info['publication'] = pub_parts[1].split(',')[0].strip()
        
        # 提取摘要
        abstract = article_element.find('div', class_='gs_rs')
        if abstract:
            article_info['abstract'] = abstract.text.strip()
        
        # 提取引用次数
        citation_element = article_element.find('a', text=lambda text: text and 'Cited by' in text)
        if citation_element:
            citation_text = citation_element.text
            citation_match = re.search(r'\d+', citation_text)
            if citation_match:
                article_info['citations'] = int(citation_match.group(0))
    
    except Exception as e:
        logger.error(f"提取文献信息时出错: {e}")
    
    return article_info

def parse_search_results(html_content: str, top_n: int) -> List[Dict[str, Any]]:
    """
    从Google Scholar搜索结果页面中解析文献信息
    
    Args:
        html_content (str): Google Scholar搜索结果页面的HTML内容
        top_n (int): 需要提取的结果数量
        
    Returns:
        List[Dict[str, Any]]: 包含文献信息的字典列表
    """
    results = []
    
    try:
        soup = BeautifulSoup(html_content, 'lxml')
        # 查找所有文章元素
        articles = soup.find_all('div', class_='gs_r gs_or gs_scl')
        
        # 限制结果数量
        articles = articles[:top_n] if top_n > 0 else articles
        
        # 提取每篇文章的信息
        for article in articles:
            article_info = extract_article_info(article)
            results.append(article_info)
            
    except Exception as e:
        logger.error(f"解析搜索结果时出错: {e}")
    
    return results

@tool
def search_google_scholar(keywords: str, top_n: int = 10, sort_by: Optional[str] = None, 
                          start_year: Optional[int] = None, end_year: Optional[int] = None) -> str:
    """
    根据关键字在Google Scholar上进行搜索并返回学术文献信息
    
    Args:
        keywords (str): 搜索关键字或短语，多个关键字可以用空格分隔
        top_n (int): 返回结果的数量限制，默认为10
        sort_by (str, optional): 结果排序方式，可选值：relevance（相关度）或date（日期）
        start_year (int, optional): 筛选文献的起始年份
        end_year (int, optional): 筛选文献的结束年份
        
    Returns:
        str: 包含学术文献信息的JSON字符串，格式如下：
        {
            "status": "success",
            "results_count": 5,
            "results": [
                {
                    "title": "文献标题",
                    "authors": ["作者1", "作者2"],
                    "publication": "期刊名称",
                    "year": 2023,
                    "abstract": "文献摘要内容...",
                    "citations": 42,
                    "url": "https://..."
                },
                ...
            ]
        }
        
        如果发生错误，返回格式为：
        {
            "status": "error",
            "message": "错误信息"
        }
    """
    # 参数验证
    if not keywords or not keywords.strip():
        return json.dumps({
            'status': 'error',
            'message': '搜索关键字不能为空'
        }, ensure_ascii=False)
    
    # 尝试转换数值参数
    try:
        top_n = int(top_n) if top_n is not None else 10
        start_year = int(start_year) if start_year is not None else None
        end_year = int(end_year) if end_year is not None else None
    except ValueError:
        return json.dumps({
            'status': 'error',
            'message': '参数类型错误: top_n、start_year和end_year必须是整数'
        }, ensure_ascii=False)
    
    # 验证排序参数
    if sort_by and sort_by.lower() not in ['relevance', 'date']:
        return json.dumps({
            'status': 'error',
            'message': '排序参数sort_by必须是"relevance"或"date"'
        }, ensure_ascii=False)
    
    try:
        # 构建搜索URL
        search_url = build_search_url(keywords, sort_by, start_year, end_year)
        logger.info(f"搜索URL: {search_url}")
        
        # 设置请求头
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://scholar.google.com/'
        }
        
        # 发送请求
        response = requests.get(search_url, headers=headers, timeout=10)
        
        # 检查响应状态
        if response.status_code != 200:
            return json.dumps({
                'status': 'error',
                'message': f'请求失败，状态码: {response.status_code}'
            }, ensure_ascii=False)
        
        # 解析搜索结果
        results = parse_search_results(response.text, top_n)
        
        # 构建返回结果
        return json.dumps({
            'status': 'success',
            'results_count': len(results),
            'results': results
        }, ensure_ascii=False, indent=2)
        
    except requests.RequestException as e:
        logger.error(f"网络请求错误: {e}")
        return json.dumps({
            'status': 'error',
            'message': f'网络请求错误: {str(e)}'
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"搜索过程中出现错误: {e}")
        return json.dumps({
            'status': 'error',
            'message': f'搜索过程中出现错误: {str(e)}'
        }, ensure_ascii=False)