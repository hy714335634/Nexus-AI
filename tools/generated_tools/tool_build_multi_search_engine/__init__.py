#!/usr/bin/env python3
"""
多搜索引擎工具包
提供统一的搜索接口，支持国内外主流搜索引擎
"""

from .multi_search_engine import search, check_engine_health, filter_and_sort_results

__all__ = ['search', 'check_engine_health', 'filter_and_sort_results']

__version__ = '1.0.0'
__author__ = 'Tool Developer'
__description__ = '通用多搜索引擎访问工具，支持百度、搜狗、360搜索、Google、Bing、DuckDuckGo'
