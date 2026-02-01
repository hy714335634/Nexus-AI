#!/usr/bin/env python3
"""
各搜索引擎的适配器模块
实现统一的搜索接口，支持百度、搜狗、360搜索、Google、Bing、DuckDuckGo
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import urllib.parse
import logging

logger = logging.getLogger(__name__)


def _search_baidu(query: str, num_results: int, timeout: int) -> List[Dict]:
    """
    百度搜索适配器
    
    Args:
        query: 搜索关键词
        num_results: 结果数量
        timeout: 超时时间（秒）
        
    Returns:
        list: 搜索结果列表
    """
    from .utils import get_random_user_agent, retry_on_failure
    from .exceptions import EngineUnavailableError, ParseError
    
    @retry_on_failure(max_retries=2, delay=1)
    def _do_search():
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://www.baidu.com/s?wd={encoded_query}&rn={num_results}"
            
            headers = {
                'User-Agent': get_random_user_agent(),
                'Referer': 'https://www.baidu.com',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9',
            }
            
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'lxml')
            results = []
            
            # 百度搜索结果的多种可能选择器
            selectors = [
                '.result.c-container',
                '.result',
                '#content_left .result'
            ]
            
            items = []
            for selector in selectors:
                items = soup.select(selector)
                if items:
                    break
            
            for item in items[:num_results]:
                try:
                    # 提取标题
                    title_elem = item.select_one('h3.t a, h3 a, .c-title a')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    url_link = title_elem.get('href', '')
                    
                    # 提取摘要
                    snippet_elem = item.select_one('.c-abstract, .c-span9, .c-span-last')
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''
                    
                    if title and url_link:
                        results.append({
                            'title': title,
                            'url': url_link,
                            'snippet': snippet
                        })
                except Exception as e:
                    logger.debug(f"解析百度单个结果失败: {e}")
                    continue
            
            if not results:
                logger.warning("百度搜索未返回任何结果")
            
            return results
            
        except requests.RequestException as e:
            raise EngineUnavailableError('baidu', f"网络请求失败: {str(e)}")
        except Exception as e:
            raise ParseError('baidu', f"解析失败: {str(e)}")
    
    return _do_search()


def _search_sogou(query: str, num_results: int, timeout: int) -> List[Dict]:
    """
    搜狗搜索适配器
    
    Args:
        query: 搜索关键词
        num_results: 结果数量
        timeout: 超时时间（秒）
        
    Returns:
        list: 搜索结果列表
    """
    from .utils import get_random_user_agent, retry_on_failure
    from .exceptions import EngineUnavailableError, ParseError
    
    @retry_on_failure(max_retries=2, delay=1)
    def _do_search():
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://www.sogou.com/web?query={encoded_query}&num={num_results}"
            
            headers = {
                'User-Agent': get_random_user_agent(),
                'Referer': 'https://www.sogou.com',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9',
            }
            
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            results = []
            
            # 搜狗搜索结果选择器
            for item in soup.select('.vrwrap, .rb')[:num_results]:
                try:
                    # 提取标题
                    title_elem = item.select_one('h3 a, .pt a')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    url_link = title_elem.get('href', '')
                    
                    # 提取摘要
                    snippet_elem = item.select_one('.str-text, .str_info')
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''
                    
                    if title and url_link:
                        results.append({
                            'title': title,
                            'url': url_link,
                            'snippet': snippet
                        })
                except Exception as e:
                    logger.debug(f"解析搜狗单个结果失败: {e}")
                    continue
            
            return results
            
        except requests.RequestException as e:
            raise EngineUnavailableError('sogou', f"网络请求失败: {str(e)}")
        except Exception as e:
            raise ParseError('sogou', f"解析失败: {str(e)}")
    
    return _do_search()


def _search_so360(query: str, num_results: int, timeout: int) -> List[Dict]:
    """
    360搜索适配器
    
    Args:
        query: 搜索关键词
        num_results: 结果数量
        timeout: 超时时间（秒）
        
    Returns:
        list: 搜索结果列表
    """
    from .utils import get_random_user_agent, retry_on_failure
    from .exceptions import EngineUnavailableError, ParseError
    
    @retry_on_failure(max_retries=2, delay=1)
    def _do_search():
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://www.so.com/s?q={encoded_query}&pn=1"
            
            headers = {
                'User-Agent': get_random_user_agent(),
                'Referer': 'https://www.so.com',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9',
            }
            
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            results = []
            
            # 360搜索结果选择器
            for item in soup.select('.result')[:num_results]:
                try:
                    # 提取标题
                    title_elem = item.select_one('h3 a, .res-title a')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    url_link = title_elem.get('href', '')
                    
                    # 提取摘要
                    snippet_elem = item.select_one('.res-desc, .res-rich')
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''
                    
                    if title and url_link:
                        results.append({
                            'title': title,
                            'url': url_link,
                            'snippet': snippet
                        })
                except Exception as e:
                    logger.debug(f"解析360搜索单个结果失败: {e}")
                    continue
            
            return results
            
        except requests.RequestException as e:
            raise EngineUnavailableError('so360', f"网络请求失败: {str(e)}")
        except Exception as e:
            raise ParseError('so360', f"解析失败: {str(e)}")
    
    return _do_search()


def _search_google(query: str, num_results: int, timeout: int) -> List[Dict]:
    """
    Google搜索适配器
    
    Args:
        query: 搜索关键词
        num_results: 结果数量
        timeout: 超时时间（秒）
        
    Returns:
        list: 搜索结果列表
    """
    from .utils import get_random_user_agent, retry_on_failure
    from .exceptions import EngineUnavailableError, ParseError
    
    @retry_on_failure(max_retries=2, delay=1)
    def _do_search():
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://www.google.com/search?q={encoded_query}&num={num_results}"
            
            headers = {
                'User-Agent': get_random_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.google.com/'
            }
            
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            results = []
            
            # Google搜索结果选择器
            for item in soup.select('.g, div.g')[:num_results]:
                try:
                    # 提取标题
                    title_elem = item.select_one('h3')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    
                    # 提取URL
                    link_elem = item.select_one('a')
                    url_link = link_elem.get('href', '') if link_elem else ''
                    
                    # 提取摘要
                    snippet_elem = item.select_one('.VwiC3b, .s, .st')
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''
                    
                    if title and url_link:
                        results.append({
                            'title': title,
                            'url': url_link,
                            'snippet': snippet
                        })
                except Exception as e:
                    logger.debug(f"解析Google单个结果失败: {e}")
                    continue
            
            return results
            
        except requests.RequestException as e:
            raise EngineUnavailableError('google', f"网络请求失败: {str(e)}")
        except Exception as e:
            raise ParseError('google', f"解析失败: {str(e)}")
    
    return _do_search()


def _search_bing(query: str, num_results: int, timeout: int) -> List[Dict]:
    """
    Bing搜索适配器
    
    Args:
        query: 搜索关键词
        num_results: 结果数量
        timeout: 超时时间（秒）
        
    Returns:
        list: 搜索结果列表
    """
    from .utils import get_random_user_agent, retry_on_failure
    from .exceptions import EngineUnavailableError, ParseError
    
    @retry_on_failure(max_retries=2, delay=1)
    def _do_search():
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://www.bing.com/search?q={encoded_query}&count={num_results}"
            
            headers = {
                'User-Agent': get_random_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            results = []
            
            # Bing搜索结果选择器
            for item in soup.select('.b_algo')[:num_results]:
                try:
                    # 提取标题
                    title_elem = item.select_one('h2 a')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    url_link = title_elem.get('href', '')
                    
                    # 提取摘要
                    snippet_elem = item.select_one('.b_caption p, .b_caption')
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''
                    
                    if title and url_link:
                        results.append({
                            'title': title,
                            'url': url_link,
                            'snippet': snippet
                        })
                except Exception as e:
                    logger.debug(f"解析Bing单个结果失败: {e}")
                    continue
            
            return results
            
        except requests.RequestException as e:
            raise EngineUnavailableError('bing', f"网络请求失败: {str(e)}")
        except Exception as e:
            raise ParseError('bing', f"解析失败: {str(e)}")
    
    return _do_search()


def _search_duckduckgo(query: str, num_results: int, timeout: int) -> List[Dict]:
    """
    DuckDuckGo搜索适配器
    
    Args:
        query: 搜索关键词
        num_results: 结果数量
        timeout: 超时时间（秒）
        
    Returns:
        list: 搜索结果列表
    """
    from .utils import get_random_user_agent, retry_on_failure
    from .exceptions import EngineUnavailableError, ParseError
    
    @retry_on_failure(max_retries=2, delay=1)
    def _do_search():
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://duckduckgo.com/html/?q={encoded_query}"
            
            headers = {
                'User-Agent': get_random_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            results = []
            
            # DuckDuckGo搜索结果选择器
            for item in soup.select('.result, .results_links')[:num_results]:
                try:
                    # 提取标题
                    title_elem = item.select_one('.result__a, h2 a')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    url_link = title_elem.get('href', '')
                    
                    # 提取摘要
                    snippet_elem = item.select_one('.result__snippet, .result__body')
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''
                    
                    if title and url_link:
                        results.append({
                            'title': title,
                            'url': url_link,
                            'snippet': snippet
                        })
                except Exception as e:
                    logger.debug(f"解析DuckDuckGo单个结果失败: {e}")
                    continue
            
            return results
            
        except requests.RequestException as e:
            raise EngineUnavailableError('duckduckgo', f"网络请求失败: {str(e)}")
        except Exception as e:
            raise ParseError('duckduckgo', f"解析失败: {str(e)}")
    
    return _do_search()


# 搜索引擎映射表
ENGINE_ADAPTERS = {
    'baidu': _search_baidu,
    'sogou': _search_sogou,
    'so360': _search_so360,
    'google': _search_google,
    'bing': _search_bing,
    'duckduckgo': _search_duckduckgo
}
