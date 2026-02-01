#!/usr/bin/env python3
"""
网络环境检测和搜索引擎选择策略模块
"""

import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# 搜索引擎测试URL
ENGINE_TEST_URLS = {
    'baidu': 'https://www.baidu.com',
    'sogou': 'https://www.sogou.com',
    'so360': 'https://www.so.com',
    'google': 'https://www.google.com',
    'bing': 'https://www.bing.com',
    'duckduckgo': 'https://duckduckgo.com'
}

# 国内和海外搜索引擎分类
CHINA_ENGINES = ['baidu', 'sogou', 'so360']
OVERSEAS_ENGINES = ['google', 'bing', 'duckduckgo']


def _check_engine_availability(engine: str, timeout: int = 5) -> Dict:
    """
    检查单个搜索引擎的可用性
    
    Args:
        engine: 搜索引擎名称
        timeout: 检查超时时间（秒）
        
    Returns:
        dict: 包含可用性和响应时间的字典
    """
    if engine not in ENGINE_TEST_URLS:
        return {
            'engine': engine,
            'available': False,
            'response_time_ms': -1,
            'error': f'未知的搜索引擎: {engine}'
        }
    
    try:
        from .utils import get_random_user_agent
        
        start_time = time.time()
        headers = {'User-Agent': get_random_user_agent()}
        
        response = requests.head(
            ENGINE_TEST_URLS[engine], 
            headers=headers,
            timeout=timeout,
            allow_redirects=True
        )
        
        response_time = int((time.time() - start_time) * 1000)
        
        return {
            'engine': engine,
            'available': response.status_code < 400,
            'response_time_ms': response_time,
            'error': None
        }
    except requests.Timeout:
        return {
            'engine': engine,
            'available': False,
            'response_time_ms': -1,
            'error': 'Connection timeout'
        }
    except requests.ConnectionError as e:
        return {
            'engine': engine,
            'available': False,
            'response_time_ms': -1,
            'error': f'Connection error: {str(e)}'
        }
    except Exception as e:
        return {
            'engine': engine,
            'available': False,
            'response_time_ms': -1,
            'error': str(e)
        }


def _detect_best_engine(region: str = 'auto', language: str = 'auto', 
                       timeout: int = 3) -> str:
    """
    自动检测最佳搜索引擎
    
    Args:
        region: 地区提示（china/overseas/auto）
        language: 语言偏好（zh-CN/en-US/auto）
        timeout: 检测超时时间（秒）
        
    Returns:
        str: 推荐的搜索引擎名称
    """
    # 根据明确的地区提示直接返回
    if region == 'china':
        logger.info("根据地区提示选择国内搜索引擎: baidu")
        return 'baidu'
    elif region == 'overseas':
        logger.info("根据地区提示选择海外搜索引擎: google")
        return 'google'
    
    # 自动检测
    logger.info("开始自动检测最佳搜索引擎...")
    
    # 确定要检测的引擎列表
    if language == 'zh-CN':
        # 优先检测国内引擎
        engines_to_check = CHINA_ENGINES + OVERSEAS_ENGINES
    elif language == 'en-US':
        # 优先检测海外引擎
        engines_to_check = OVERSEAS_ENGINES + CHINA_ENGINES
    else:
        # 全部检测
        engines_to_check = CHINA_ENGINES + OVERSEAS_ENGINES
    
    # 并发检测所有引擎
    available_engines = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(_check_engine_availability, engine, timeout): engine 
            for engine in engines_to_check
        }
        
        for future in as_completed(futures):
            try:
                result = future.result()
                if result['available']:
                    available_engines.append(result)
                    logger.debug(f"引擎 {result['engine']} 可用，响应时间: {result['response_time_ms']}ms")
                else:
                    logger.debug(f"引擎 {result['engine']} 不可用: {result['error']}")
            except Exception as e:
                logger.error(f"检测引擎时发生异常: {e}")
    
    # 如果没有可用的引擎，返回默认值
    if not available_engines:
        logger.warning("所有搜索引擎都不可用，使用默认引擎: baidu")
        return 'baidu'
    
    # 按响应时间排序
    available_engines.sort(key=lambda x: x['response_time_ms'])
    
    # 根据语言偏好选择引擎
    if language == 'zh-CN':
        # 优先选择国内引擎
        for engine_info in available_engines:
            if engine_info['engine'] in CHINA_ENGINES:
                logger.info(f"根据语言偏好选择国内引擎: {engine_info['engine']}")
                return engine_info['engine']
    elif language == 'en-US':
        # 优先选择海外引擎
        for engine_info in available_engines:
            if engine_info['engine'] in OVERSEAS_ENGINES:
                logger.info(f"根据语言偏好选择海外引擎: {engine_info['engine']}")
                return engine_info['engine']
    
    # 返回响应最快的引擎
    best_engine = available_engines[0]['engine']
    logger.info(f"选择响应最快的引擎: {best_engine} ({available_engines[0]['response_time_ms']}ms)")
    return best_engine


def batch_check_engines(engines: Optional[List[str]] = None, 
                       check_timeout: int = 5) -> List[Dict]:
    """
    批量检查搜索引擎可用性
    
    Args:
        engines: 需要检查的引擎列表，为None时检查所有引擎
        check_timeout: 每个引擎的检查超时时间（秒）
        
    Returns:
        list: 包含各引擎健康状态的列表
    """
    if engines is None:
        engines = list(ENGINE_TEST_URLS.keys())
    
    results = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(_check_engine_availability, engine, check_timeout): engine 
            for engine in engines
        }
        
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                engine = futures[future]
                logger.error(f"检查引擎 {engine} 时发生异常: {e}")
                results.append({
                    'engine': engine,
                    'available': False,
                    'response_time_ms': -1,
                    'error': str(e)
                })
    
    return results
