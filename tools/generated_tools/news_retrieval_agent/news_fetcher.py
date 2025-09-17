#!/usr/bin/env python3
"""
新闻检索工具模块

提供从多个新闻平台获取新闻、计算热度、生成摘要和管理用户话题的功能
"""

import json
import re
import os
import time
import uuid
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import boto3
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urlparse
from strands import tool


@tool
def fetch_news(topic: str, platforms: List[str] = None, max_results: int = 10) -> str:
    """
    从多个新闻平台获取新闻信息
    
    Args:
        topic (str): 搜索的新闻话题
        platforms (List[str], optional): 新闻平台列表，支持 'baidu', 'sina', 'thepaper'等，默认全部
        max_results (int, optional): 每个平台最大返回结果数，默认10条
        
    Returns:
        str: JSON格式的新闻信息，包含标题、来源、URL、发布时间、阅读量、评论数等
    """
    try:
        if platforms is None:
            platforms = ["baidu", "sina", "thepaper"]
        
        # 验证平台参数
        valid_platforms = ["baidu", "sina", "thepaper", "weibo", "tencent"]
        platforms = [p for p in platforms if p in valid_platforms]
        
        if not platforms:
            return json.dumps({
                "error": "没有指定有效的新闻平台",
                "valid_platforms": valid_platforms
            }, ensure_ascii=False, indent=2)
        
        # 构建结果结构
        results = {
            "topic": topic,
            "search_time": datetime.now().isoformat(),
            "platforms": platforms,
            "news_items": [],
            "total_count": 0,
            "platform_status": {}
        }
        
        # 从各平台获取新闻
        for platform in platforms:
            try:
                platform_news = _fetch_from_platform(platform, topic, max_results)
                results["news_items"].extend(platform_news)
                results["platform_status"][platform] = {
                    "status": "success",
                    "count": len(platform_news)
                }
                results["total_count"] += len(platform_news)
            except Exception as e:
                results["platform_status"][platform] = {
                    "status": "error",
                    "message": str(e)
                }
        
        # 如果没有获取到任何新闻，返回错误信息
        if results["total_count"] == 0:
            available_platforms = [p for p, status in results["platform_status"].items() 
                                  if status["status"] == "success"]
            if available_platforms:
                results["message"] = f"未找到与'{topic}'相关的新闻"
            else:
                results["message"] = "所有平台都无法访问，请稍后再试"
        
        return json.dumps(results, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": f"新闻获取失败: {str(e)}",
            "topic": topic
        }, ensure_ascii=False, indent=2)


def _fetch_from_platform(platform: str, topic: str, max_results: int) -> List[Dict[str, Any]]:
    """从特定平台获取新闻"""
    if platform == "baidu":
        return _fetch_from_baidu(topic, max_results)
    elif platform == "sina":
        return _fetch_from_sina(topic, max_results)
    elif platform == "thepaper":
        return _fetch_from_thepaper(topic, max_results)
    elif platform == "weibo":
        return _fetch_from_weibo(topic, max_results)
    elif platform == "tencent":
        return _fetch_from_tencent(topic, max_results)
    else:
        raise ValueError(f"不支持的平台: {platform}")


def _fetch_from_baidu(topic: str, max_results: int) -> List[Dict[str, Any]]:
    """从百度新闻获取数据"""
    url = f"https://www.baidu.com/s?rtt=1&bsst=1&cl=2&tn=news&word={quote_plus(topic)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        news_items = []
        
        # 解析百度新闻搜索结果
        result_divs = soup.select('div.result')[:max_results]
        
        for div in result_divs:
            try:
                title_element = div.select_one('h3 a')
                title = title_element.get_text().strip() if title_element else "无标题"
                link = title_element.get('href') if title_element else ""
                
                source_time = div.select_one('div.c-author')
                source = source_time.get_text().split('  ')[0].strip() if source_time else "百度新闻"
                publish_time = source_time.get_text().split('  ')[-1].strip() if source_time else ""
                
                summary_element = div.select_one('div.c-summary')
                summary = summary_element.get_text().strip() if summary_element else ""
                
                # 生成唯一ID
                news_id = str(uuid.uuid4())
                
                # 估算热度 (基于发布时间的新鲜度)
                publish_date = _parse_chinese_date(publish_time)
                freshness_score = _calculate_freshness(publish_date)
                
                news_items.append({
                    "news_id": news_id,
                    "title": title,
                    "url": link,
                    "source": source,
                    "platform": "baidu",
                    "publish_time": publish_time,
                    "publish_date": publish_date.isoformat() if publish_date else None,
                    "summary": summary,
                    "read_count": None,  # 百度不提供阅读量
                    "comment_count": None,  # 百度不提供评论数
                    "estimated_heat": freshness_score
                })
            except Exception as e:
                continue
        
        return news_items
    
    except requests.RequestException as e:
        raise Exception(f"百度新闻请求失败: {str(e)}")


def _fetch_from_sina(topic: str, max_results: int) -> List[Dict[str, Any]]:
    """从新浪新闻获取数据"""
    url = f"https://search.sina.com.cn/news?q={quote_plus(topic)}&c=news"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        news_items = []
        
        # 解析新浪新闻搜索结果
        result_divs = soup.select('div.box-result')[:max_results]
        
        for div in result_divs:
            try:
                title_element = div.select_one('h2 a')
                title = title_element.get_text().strip() if title_element else "无标题"
                link = title_element.get('href') if title_element else ""
                
                source_element = div.select_one('span.fgray_time a')
                source = source_element.get_text().strip() if source_element else "新浪新闻"
                
                time_element = div.select_one('span.fgray_time')
                publish_time = time_element.get_text().strip().split('  ')[-1] if time_element else ""
                
                summary_element = div.select_one('p.content')
                summary = summary_element.get_text().strip() if summary_element else ""
                
                # 提取阅读量和评论数（如果有）
                stats_element = div.select_one('div.news-stats')
                read_count_text = stats_element.select_one('.news-stats-read') if stats_element else None
                read_count = _extract_number(read_count_text.get_text()) if read_count_text else None
                
                comment_count_text = stats_element.select_one('.news-stats-comment') if stats_element else None
                comment_count = _extract_number(comment_count_text.get_text()) if comment_count_text else None
                
                # 生成唯一ID
                news_id = str(uuid.uuid4())
                
                # 解析发布日期
                publish_date = _parse_chinese_date(publish_time)
                
                # 计算热度
                heat_score = _calculate_heat_score(
                    read_count=read_count,
                    comment_count=comment_count,
                    publish_date=publish_date
                )
                
                news_items.append({
                    "news_id": news_id,
                    "title": title,
                    "url": link,
                    "source": source,
                    "platform": "sina",
                    "publish_time": publish_time,
                    "publish_date": publish_date.isoformat() if publish_date else None,
                    "summary": summary,
                    "read_count": read_count,
                    "comment_count": comment_count,
                    "estimated_heat": heat_score
                })
            except Exception as e:
                continue
        
        return news_items
    
    except requests.RequestException as e:
        raise Exception(f"新浪新闻请求失败: {str(e)}")


def _fetch_from_thepaper(topic: str, max_results: int) -> List[Dict[str, Any]]:
    """从澎湃新闻获取数据"""
    url = f"https://www.thepaper.cn/searchResult.jsp?keyword={quote_plus(topic)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        news_items = []
        
        # 解析澎湃新闻搜索结果
        result_divs = soup.select('div.news_li')[:max_results]
        
        for div in result_divs:
            try:
                title_element = div.select_one('h2 a')
                title = title_element.get_text().strip() if title_element else "无标题"
                
                # 澎湃新闻链接需要拼接
                link_path = title_element.get('href') if title_element else ""
                link = f"https://www.thepaper.cn/{link_path}" if link_path else ""
                
                source = "澎湃新闻"
                
                time_element = div.select_one('span.news_time')
                publish_time = time_element.get_text().strip() if time_element else ""
                
                summary_element = div.select_one('div.news_txt')
                summary = summary_element.get_text().strip() if summary_element else ""
                
                # 提取阅读量和评论数
                read_count_element = div.select_one('span.trbszan')
                read_count = _extract_number(read_count_element.get_text()) if read_count_element else None
                
                comment_count_element = div.select_one('span.trbsfav')
                comment_count = _extract_number(comment_count_element.get_text()) if comment_count_element else None
                
                # 生成唯一ID
                news_id = str(uuid.uuid4())
                
                # 解析发布日期
                publish_date = _parse_chinese_date(publish_time)
                
                # 计算热度
                heat_score = _calculate_heat_score(
                    read_count=read_count,
                    comment_count=comment_count,
                    publish_date=publish_date
                )
                
                news_items.append({
                    "news_id": news_id,
                    "title": title,
                    "url": link,
                    "source": source,
                    "platform": "thepaper",
                    "publish_time": publish_time,
                    "publish_date": publish_date.isoformat() if publish_date else None,
                    "summary": summary,
                    "read_count": read_count,
                    "comment_count": comment_count,
                    "estimated_heat": heat_score
                })
            except Exception as e:
                continue
        
        return news_items
    
    except requests.RequestException as e:
        raise Exception(f"澎湃新闻请求失败: {str(e)}")


def _fetch_from_weibo(topic: str, max_results: int) -> List[Dict[str, Any]]:
    """从微博获取数据"""
    url = f"https://s.weibo.com/weibo?q={quote_plus(topic)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        news_items = []
        
        # 解析微博搜索结果
        result_divs = soup.select('div.card-wrap')[:max_results]
        
        for div in result_divs:
            try:
                content_element = div.select_one('p.txt')
                if not content_element:
                    continue
                
                title = content_element.get_text().strip()[:100]  # 限制标题长度
                
                link_element = div.select_one('p.from a')
                link = f"https://weibo.com{link_element.get('href')}" if link_element else ""
                
                source_element = div.select_one('a.name')
                source = source_element.get_text().strip() if source_element else "微博用户"
                
                time_element = div.select_one('p.from')
                publish_time = time_element.get_text().strip().split(' ')[0] if time_element else ""
                
                # 提取转发、评论、点赞数
                actions = div.select('div.card-act ul li')
                forward_count = _extract_number(actions[1].get_text()) if len(actions) > 1 else 0
                comment_count = _extract_number(actions[2].get_text()) if len(actions) > 2 else 0
                like_count = _extract_number(actions[3].get_text()) if len(actions) > 3 else 0
                
                # 生成唯一ID
                news_id = str(uuid.uuid4())
                
                # 解析发布日期
                publish_date = _parse_chinese_date(publish_time)
                
                # 计算热度 (微博特有的热度计算)
                heat_score = _calculate_weibo_heat(
                    forward_count=forward_count,
                    comment_count=comment_count,
                    like_count=like_count,
                    publish_date=publish_date
                )
                
                news_items.append({
                    "news_id": news_id,
                    "title": title,
                    "url": link,
                    "source": source,
                    "platform": "weibo",
                    "publish_time": publish_time,
                    "publish_date": publish_date.isoformat() if publish_date else None,
                    "summary": title,  # 微博内容作为摘要
                    "read_count": None,  # 微博不直接提供阅读量
                    "comment_count": comment_count,
                    "forward_count": forward_count,
                    "like_count": like_count,
                    "estimated_heat": heat_score
                })
            except Exception as e:
                continue
        
        return news_items
    
    except requests.RequestException as e:
        raise Exception(f"微博请求失败: {str(e)}")


def _fetch_from_tencent(topic: str, max_results: int) -> List[Dict[str, Any]]:
    """从腾讯新闻获取数据"""
    url = f"https://www.sogou.com/sogou?query={quote_plus(topic)}+site:qq.com"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        news_items = []
        
        # 解析搜狗搜索结果（腾讯新闻）
        result_divs = soup.select('div.vrwrap')[:max_results]
        
        for div in result_divs:
            try:
                title_element = div.select_one('h3 a')
                title = title_element.get_text().strip() if title_element else "无标题"
                link = title_element.get('href') if title_element else ""
                
                # 检查是否为腾讯新闻链接
                if "qq.com" not in link:
                    continue
                
                summary_element = div.select_one('div.text-layout')
                summary = summary_element.get_text().strip() if summary_element else ""
                
                source = "腾讯新闻"
                
                time_element = div.select_one('div.fz-mid')
                publish_time = time_element.get_text().strip() if time_element else ""
                
                # 生成唯一ID
                news_id = str(uuid.uuid4())
                
                # 解析发布日期
                publish_date = _parse_chinese_date(publish_time)
                
                # 计算热度（基于时间新鲜度）
                heat_score = _calculate_freshness(publish_date)
                
                news_items.append({
                    "news_id": news_id,
                    "title": title,
                    "url": link,
                    "source": source,
                    "platform": "tencent",
                    "publish_time": publish_time,
                    "publish_date": publish_date.isoformat() if publish_date else None,
                    "summary": summary,
                    "read_count": None,
                    "comment_count": None,
                    "estimated_heat": heat_score
                })
            except Exception as e:
                continue
        
        return news_items
    
    except requests.RequestException as e:
        raise Exception(f"腾讯新闻请求失败: {str(e)}")


def _extract_number(text: Optional[str]) -> Optional[int]:
    """从文本中提取数字"""
    if not text:
        return None
    
    match = re.search(r'\d+', text)
    if match:
        return int(match.group())
    return None


def _parse_chinese_date(date_str: Optional[str]) -> Optional[datetime]:
    """解析中文日期格式"""
    if not date_str:
        return None
    
    now = datetime.now()
    
    # 处理"今天"、"昨天"等相对日期
    if "今天" in date_str:
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif "昨天" in date_str:
        return (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 处理"X分钟前"、"X小时前"
    minutes_match = re.search(r'(\d+)\s*分钟前', date_str)
    if minutes_match:
        minutes = int(minutes_match.group(1))
        return now - timedelta(minutes=minutes)
    
    hours_match = re.search(r'(\d+)\s*小时前', date_str)
    if hours_match:
        hours = int(hours_match.group(1))
        return now - timedelta(hours=hours)
    
    # 处理"X天前"
    days_match = re.search(r'(\d+)\s*天前', date_str)
    if days_match:
        days = int(days_match.group(1))
        return now - timedelta(days=days)
    
    # 处理标准日期格式
    try:
        # 尝试解析"YYYY-MM-DD HH:MM:SS"格式
        date_formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%Y年%m月%d日 %H:%M",
            "%Y年%m月%d日",
            "%m月%d日 %H:%M",
            "%m-%d %H:%M"
        ]
        
        for fmt in date_formats:
            try:
                # 对于不包含年份的格式，添加当前年份
                if "%Y" not in fmt and re.search(r'\d+月\d+日', date_str):
                    date_str = f"{now.year}年{date_str}"
                elif "%Y" not in fmt and re.search(r'\d+-\d+', date_str):
                    date_str = f"{now.year}-{date_str}"
                
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
    except Exception:
        pass
    
    return None


def _calculate_heat_score(read_count: Optional[int] = None, 
                         comment_count: Optional[int] = None,
                         publish_date: Optional[datetime] = None) -> float:
    """计算新闻热度分数"""
    score = 0.0
    
    # 基于阅读量的分数
    if read_count is not None:
        # 阅读量对数变换，避免极值影响
        score += min(50, max(0, 10 * (read_count / 1000)))
    
    # 基于评论数的分数（评论互动更有价值）
    if comment_count is not None:
        score += min(30, max(0, 15 * (comment_count / 100)))
    
    # 基于时间新鲜度的分数
    time_score = _calculate_freshness(publish_date)
    score += time_score
    
    # 如果没有任何数据，给一个默认分数
    if score == 0:
        score = 10.0
    
    return round(score, 2)


def _calculate_freshness(publish_date: Optional[datetime]) -> float:
    """计算基于发布时间的新鲜度分数"""
    if not publish_date:
        return 10.0  # 默认分数
    
    now = datetime.now()
    hours_diff = (now - publish_date).total_seconds() / 3600
    
    # 24小时内的新闻获得较高分数
    if hours_diff <= 24:
        return 20.0 * (1 - hours_diff / 24)
    # 一周内的新闻获得中等分数
    elif hours_diff <= 168:  # 7*24
        return 10.0 * (1 - (hours_diff - 24) / 144)
    # 更旧的新闻获得较低分数
    else:
        return max(0, 5.0 * (1 - (hours_diff - 168) / 672))  # 最多考虑一个月


def _calculate_weibo_heat(forward_count: int = 0, 
                         comment_count: int = 0,
                         like_count: int = 0,
                         publish_date: Optional[datetime] = None) -> float:
    """计算微博特有的热度分数"""
    score = 0.0
    
    # 转发比评论和点赞更有价值
    score += min(40, max(0, 10 * (forward_count / 100)))
    score += min(30, max(0, 8 * (comment_count / 100)))
    score += min(20, max(0, 5 * (like_count / 100)))
    
    # 基于时间新鲜度的分数
    time_score = _calculate_freshness(publish_date)
    score += time_score
    
    # 如果没有任何数据，给一个默认分数
    if score == 0:
        score = 10.0
    
    return round(score, 2)