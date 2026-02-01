#!/usr/bin/env python3
"""
工具函数模块
包含User-Agent生成、请求重试、HTML清理等辅助功能
"""

import random
import re
import time
from functools import wraps
from typing import Optional
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

# 预定义的User-Agent列表（备选方案）
DEFAULT_USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36',
]


def get_random_user_agent() -> str:
    """
    生成随机User-Agent
    
    Returns:
        str: 随机的User-Agent字符串
    """
    try:
        # 尝试使用fake-useragent库
        from fake_useragent import UserAgent
        ua = UserAgent()
        return ua.random
    except Exception as e:
        logger.debug(f"fake-useragent库异常，使用备选列表: {e}")
        return random.choice(DEFAULT_USER_AGENTS)


def retry_on_failure(max_retries: int = 3, delay: int = 1, backoff: float = 2.0):
    """
    请求重试装饰器，使用指数退避策略
    
    Args:
        max_retries: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 退避系数
        
    Returns:
        function: 装饰后的函数
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        # 最后一次重试失败，抛出异常
                        logger.error(f"{func.__name__} 在 {max_retries} 次重试后失败: {e}")
                        raise
                    
                    # 计算延迟时间（指数退避）
                    wait_time = delay * (backoff ** attempt)
                    logger.warning(f"{func.__name__} 第 {attempt + 1} 次尝试失败: {e}，{wait_time}秒后重试")
                    time.sleep(wait_time)
            
            return None
        return wrapper
    return decorator


def clean_html(html_text: str) -> str:
    """
    清理HTML标签和特殊字符
    
    Args:
        html_text: 包含HTML标签的文本
        
    Returns:
        str: 清理后的纯文本
    """
    if not html_text:
        return ""
    
    try:
        # 使用BeautifulSoup移除HTML标签
        soup = BeautifulSoup(html_text, 'lxml')
        text = soup.get_text()
        
        # 替换HTML实体
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&amp;', '&')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    except Exception as e:
        logger.warning(f"HTML清理失败: {e}，返回原始文本")
        return html_text


def normalize_url(url: str, base_url: str = "") -> str:
    """
    标准化URL，处理相对路径和协议缺失等问题
    
    Args:
        url: 原始URL
        base_url: 基础URL（用于处理相对路径）
        
    Returns:
        str: 标准化后的URL
    """
    if not url:
        return ""
    
    # 移除前后空白
    url = url.strip()
    
    # 处理相对路径
    if url.startswith('/'):
        if base_url:
            from urllib.parse import urljoin
            return urljoin(base_url, url)
        return url
    
    # 处理缺少协议的URL
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    return url


def truncate_text(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """
    截断文本到指定长度
    
    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 截断后添加的后缀
        
    Returns:
        str: 截断后的文本
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix
