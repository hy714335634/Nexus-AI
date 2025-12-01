"""
药物反馈收集工具集

本模块提供药物反馈收集Agent所需的专业工具，包括：
1. 网络搜索和内容提取
2. 情感分析和主题分类
3. 数据去重和质量过滤
4. 结果聚合和统计分析
5. 缓存管理

技术栈：
- Python 3.13+
- Strands Framework (@tool装饰器)
- DuckDuckGo搜索引擎
- BeautifulSoup4 (HTML解析)
- boto3 (AWS服务集成)

作者：Nexus-AI Tools Developer
创建时间：2025-11-29
"""

import json
import hashlib
import re
import os
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter
import time

from strands import tool

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    import requests
except ImportError:
    requests = None


# ============================================================================
# 缓存管理
# ============================================================================

def _get_cache_dir() -> Path:
    """获取缓存目录路径"""
    cache_dir = Path(".cache/drug_feedback_collector")
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _get_cache_key(drug_name: str) -> str:
    """生成缓存键"""
    return hashlib.md5(drug_name.lower().strip().encode()).hexdigest()


def _load_cache(drug_name: str) -> Optional[Dict[str, Any]]:
    """加载缓存数据"""
    try:
        cache_file = _get_cache_dir() / f"{_get_cache_key(drug_name)}.json"
        if not cache_file.exists():
            return None
        
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        # 检查缓存是否过期（1小时）
        cache_time = datetime.fromisoformat(cache_data.get('timestamp', '2000-01-01T00:00:00'))
        if datetime.now() - cache_time > timedelta(hours=1):
            return None
        
        return cache_data
    except Exception as e:
        print(f"加载缓存失败: {str(e)}")
        return None


def _save_cache(drug_name: str, data: Dict[str, Any]) -> None:
    """保存缓存数据"""
    try:
        cache_file = _get_cache_dir() / f"{_get_cache_key(drug_name)}.json"
        cache_data = {
            'drug_name': drug_name,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存缓存失败: {str(e)}")


# ============================================================================
# 工具函数
# ============================================================================

@tool
def search_drug_feedback(
    drug_name: str,
    search_sources: List[str] = ["web", "news", "forums"],
    max_results_per_source: int = 10,
    use_cache: bool = True
) -> str:
    """
    搜索药物相关的反馈信息
    
    从多个来源搜索药物相关的用户反馈、评论、新闻等信息。
    
    Args:
        drug_name: 药物名称
        search_sources: 搜索来源列表，可选值：web（网页）、news（新闻）、forums（论坛）
        max_results_per_source: 每个来源的最大结果数量
        use_cache: 是否使用缓存
    
    Returns:
        str: JSON格式的搜索结果，包含标题、URL、摘要等信息
    """
    start_time = time.time()
    
    try:
        # 验证药物名称
        if not drug_name or not drug_name.strip():
            return json.dumps({
                "status": "error",
                "message": "药物名称不能为空",
                "error_code": "INVALID_INPUT"
            }, ensure_ascii=False)
        
        drug_name = drug_name.strip()
        
        # 检查缓存
        if use_cache:
            cached_data = _load_cache(drug_name)
            if cached_data:
                return json.dumps({
                    "status": "success",
                    "message": "从缓存加载数据",
                    "drug_name": drug_name,
                    "from_cache": True,
                    "results": cached_data['data'],
                    "execution_time": time.time() - start_time
                }, ensure_ascii=False)
        
        # 检查依赖
        if DDGS is None:
            return json.dumps({
                "status": "error",
                "message": "缺少 duckduckgo-search 依赖库",
                "error_code": "MISSING_DEPENDENCY"
            }, ensure_ascii=False)
        
        all_results = {}
        
        # 搜索网页
        if "web" in search_sources:
            try:
                web_query = f"{drug_name} 用户反馈 评价 副作用"
                web_results = []
                with DDGS() as ddgs:
                    for result in ddgs.text(web_query, max_results=max_results_per_source):
                        web_results.append({
                            "title": result.get("title", ""),
                            "url": result.get("href", ""),
                            "snippet": result.get("body", ""),
                            "source_type": "web"
                        })
                all_results["web"] = web_results
            except Exception as e:
                all_results["web"] = {"error": str(e)}
        
        # 搜索新闻
        if "news" in search_sources:
            try:
                news_query = f"{drug_name} 新闻 报道"
                news_results = []
                with DDGS() as ddgs:
                    for result in ddgs.news(news_query, max_results=max_results_per_source):
                        news_results.append({
                            "title": result.get("title", ""),
                            "url": result.get("url", ""),
                            "snippet": result.get("body", ""),
                            "date": result.get("date", ""),
                            "source": result.get("source", ""),
                            "source_type": "news"
                        })
                all_results["news"] = news_results
            except Exception as e:
                all_results["news"] = {"error": str(e)}
        
        # 搜索论坛讨论
        if "forums" in search_sources:
            try:
                forum_query = f"{drug_name} 论坛 讨论 患者经验"
                forum_results = []
                with DDGS() as ddgs:
                    for result in ddgs.text(forum_query, max_results=max_results_per_source):
                        # 过滤论坛相关的结果
                        url = result.get("href", "")
                        if any(keyword in url.lower() for keyword in ["forum", "bbs", "community", "discuss"]):
                            forum_results.append({
                                "title": result.get("title", ""),
                                "url": url,
                                "snippet": result.get("body", ""),
                                "source_type": "forum"
                            })
                all_results["forums"] = forum_results
            except Exception as e:
                all_results["forums"] = {"error": str(e)}
        
        # 保存缓存
        if use_cache:
            _save_cache(drug_name, all_results)
        
        return json.dumps({
            "status": "success",
            "drug_name": drug_name,
            "from_cache": False,
            "results": all_results,
            "total_results": sum(len(v) if isinstance(v, list) else 0 for v in all_results.values()),
            "execution_time": time.time() - start_time
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"搜索失败: {str(e)}",
            "error_code": "SEARCH_ERROR",
            "execution_time": time.time() - start_time
        }, ensure_ascii=False)


@tool
def extract_page_content(
    url: str,
    extract_type: str = "text",
    timeout: int = 30
) -> str:
    """
    提取网页内容
    
    从指定URL提取文本内容或HTML结构。
    
    Args:
        url: 网页URL
        extract_type: 提取类型，可选值：text（纯文本）、html（HTML结构）、all（全部）
        timeout: 请求超时时间（秒）
    
    Returns:
        str: JSON格式的提取结果
    """
    start_time = time.time()
    
    try:
        # 检查依赖
        if requests is None or BeautifulSoup is None:
            return json.dumps({
                "status": "error",
                "message": "缺少 requests 或 beautifulsoup4 依赖库",
                "error_code": "MISSING_DEPENDENCY"
            }, ensure_ascii=False)
        
        # 验证URL
        if not url or not url.startswith(('http://', 'https://')):
            return json.dumps({
                "status": "error",
                "message": "无效的URL",
                "error_code": "INVALID_URL"
            }, ensure_ascii=False)
        
        # 发送请求
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        # 解析HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 移除脚本和样式标签
        for script in soup(['script', 'style', 'nav', 'footer', 'header']):
            script.decompose()
        
        result = {
            "url": url,
            "status_code": response.status_code,
            "content_type": response.headers.get('content-type', '')
        }
        
        if extract_type in ["text", "all"]:
            # 提取纯文本
            text = soup.get_text(separator=' ', strip=True)
            # 清理多余空格
            text = re.sub(r'\s+', ' ', text)
            result["text"] = text
            result["text_length"] = len(text)
        
        if extract_type in ["html", "all"]:
            # 提取结构化HTML
            result["title"] = soup.title.string if soup.title else ""
            
            # 提取段落
            paragraphs = [p.get_text(strip=True) for p in soup.find_all('p') if p.get_text(strip=True)]
            result["paragraphs"] = paragraphs[:20]  # 限制数量
            
            # 提取链接
            links = [{"text": a.get_text(strip=True), "href": a.get('href', '')} 
                    for a in soup.find_all('a', href=True)[:20]]
            result["links"] = links
        
        return json.dumps({
            "status": "success",
            "result": result,
            "execution_time": time.time() - start_time
        }, ensure_ascii=False)
        
    except requests.Timeout:
        return json.dumps({
            "status": "error",
            "message": "请求超时",
            "error_code": "TIMEOUT",
            "execution_time": time.time() - start_time
        }, ensure_ascii=False)
    except requests.RequestException as e:
        return json.dumps({
            "status": "error",
            "message": f"网络请求失败: {str(e)}",
            "error_code": "REQUEST_ERROR",
            "execution_time": time.time() - start_time
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"内容提取失败: {str(e)}",
            "error_code": "EXTRACTION_ERROR",
            "execution_time": time.time() - start_time
        }, ensure_ascii=False)


@tool
def analyze_sentiment(
    text: str,
    language: str = "auto"
) -> str:
    """
    分析文本情感倾向
    
    对药物反馈文本进行情感分析，识别正面、负面或中性情感。
    
    Args:
        text: 要分析的文本内容
        language: 语言类型，可选值：auto（自动检测）、zh（中文）、en（英文）
    
    Returns:
        str: JSON格式的情感分析结果
    """
    start_time = time.time()
    
    try:
        if not text or not text.strip():
            return json.dumps({
                "status": "error",
                "message": "文本不能为空",
                "error_code": "INVALID_INPUT"
            }, ensure_ascii=False)
        
        text = text.strip()
        
        # 定义情感关键词
        positive_keywords = {
            'zh': ['有效', '好', '改善', '缓解', '治愈', '满意', '推荐', '不错', '优秀', '显著'],
            'en': ['effective', 'good', 'improved', 'relief', 'cured', 'satisfied', 'recommend', 'excellent', 'significant']
        }
        
        negative_keywords = {
            'zh': ['无效', '副作用', '不良反应', '恶化', '失望', '不推荐', '糟糕', '严重', '危险', '过敏'],
            'en': ['ineffective', 'side effect', 'adverse', 'worse', 'disappointed', 'not recommend', 'terrible', 'severe', 'dangerous', 'allergic']
        }
        
        # 自动检测语言
        if language == "auto":
            # 简单的语言检测：检查中文字符
            if re.search(r'[\u4e00-\u9fff]', text):
                language = "zh"
            else:
                language = "en"
        
        # 统计关键词
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_keywords.get(language, []) if word.lower() in text_lower)
        negative_count = sum(1 for word in negative_keywords.get(language, []) if word.lower() in text_lower)
        
        # 计算情感得分
        total_count = positive_count + negative_count
        if total_count == 0:
            sentiment = "neutral"
            confidence = 0.5
        else:
            if positive_count > negative_count:
                sentiment = "positive"
                confidence = min(0.5 + (positive_count / (total_count * 2)), 0.95)
            elif negative_count > positive_count:
                sentiment = "negative"
                confidence = min(0.5 + (negative_count / (total_count * 2)), 0.95)
            else:
                sentiment = "neutral"
                confidence = 0.5
        
        return json.dumps({
            "status": "success",
            "sentiment": sentiment,
            "confidence": round(confidence, 2),
            "positive_signals": positive_count,
            "negative_signals": negative_count,
            "language": language,
            "text_length": len(text),
            "execution_time": time.time() - start_time
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"情感分析失败: {str(e)}",
            "error_code": "ANALYSIS_ERROR",
            "execution_time": time.time() - start_time
        }, ensure_ascii=False)


@tool
def classify_feedback_topic(
    text: str,
    drug_name: str
) -> str:
    """
    分类反馈主题
    
    将药物反馈分类为不同的主题类别（疗效、副作用、价格等）。
    
    Args:
        text: 反馈文本
        drug_name: 药物名称
    
    Returns:
        str: JSON格式的主题分类结果
    """
    start_time = time.time()
    
    try:
        if not text or not text.strip():
            return json.dumps({
                "status": "error",
                "message": "文本不能为空",
                "error_code": "INVALID_INPUT"
            }, ensure_ascii=False)
        
        text = text.strip().lower()
        
        # 定义主题关键词
        topic_keywords = {
            "efficacy": {
                "keywords": ['疗效', '效果', '有效', '治疗', 'effective', 'efficacy', 'treatment', 'cure', 'relief'],
                "weight": 0
            },
            "side_effects": {
                "keywords": ['副作用', '不良反应', '过敏', '头晕', '恶心', 'side effect', 'adverse', 'reaction', 'allergy', 'nausea'],
                "weight": 0
            },
            "price": {
                "keywords": ['价格', '费用', '贵', '便宜', '报销', 'price', 'cost', 'expensive', 'cheap', 'reimbursement'],
                "weight": 0
            },
            "usage": {
                "keywords": ['用法', '剂量', '服用', '使用方法', 'dosage', 'usage', 'administration', 'take'],
                "weight": 0
            },
            "availability": {
                "keywords": ['购买', '哪里买', '有货', '缺货', 'buy', 'purchase', 'available', 'stock'],
                "weight": 0
            },
            "comparison": {
                "keywords": ['对比', '比较', '替代', '其他药', 'compare', 'alternative', 'versus', 'instead'],
                "weight": 0
            }
        }
        
        # 计算每个主题的权重
        for topic, info in topic_keywords.items():
            for keyword in info["keywords"]:
                if keyword in text:
                    info["weight"] += 1
        
        # 找出最相关的主题
        topics = sorted(topic_keywords.items(), key=lambda x: x[1]["weight"], reverse=True)
        
        # 确定主要主题
        if topics[0][1]["weight"] == 0:
            primary_topic = "general"
            confidence = 0.3
        else:
            primary_topic = topics[0][0]
            total_weight = sum(t[1]["weight"] for t in topics)
            confidence = min(topics[0][1]["weight"] / total_weight, 0.95) if total_weight > 0 else 0.5
        
        # 次要主题
        secondary_topics = [t[0] for t in topics[1:3] if t[1]["weight"] > 0]
        
        return json.dumps({
            "status": "success",
            "primary_topic": primary_topic,
            "confidence": round(confidence, 2),
            "secondary_topics": secondary_topics,
            "all_topics": {t[0]: t[1]["weight"] for t in topics if t[1]["weight"] > 0},
            "execution_time": time.time() - start_time
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"主题分类失败: {str(e)}",
            "error_code": "CLASSIFICATION_ERROR",
            "execution_time": time.time() - start_time
        }, ensure_ascii=False)


@tool
def deduplicate_feedback(
    feedback_items: str,
    similarity_threshold: float = 0.8
) -> str:
    """
    去重反馈数据
    
    基于内容相似度去除重复的反馈信息。
    
    Args:
        feedback_items: JSON格式的反馈项列表
        similarity_threshold: 相似度阈值（0-1），超过此值认为是重复
    
    Returns:
        str: JSON格式的去重后的反馈列表
    """
    start_time = time.time()
    
    try:
        # 解析输入
        try:
            items = json.loads(feedback_items) if isinstance(feedback_items, str) else feedback_items
        except json.JSONDecodeError:
            return json.dumps({
                "status": "error",
                "message": "无效的JSON格式",
                "error_code": "INVALID_JSON"
            }, ensure_ascii=False)
        
        if not isinstance(items, list):
            return json.dumps({
                "status": "error",
                "message": "输入必须是列表",
                "error_code": "INVALID_INPUT"
            }, ensure_ascii=False)
        
        if not items:
            return json.dumps({
                "status": "success",
                "original_count": 0,
                "deduplicated_count": 0,
                "removed_count": 0,
                "deduplicated_items": [],
                "execution_time": time.time() - start_time
            }, ensure_ascii=False)
        
        # 简单的去重策略：基于文本内容的哈希
        seen_hashes: Set[str] = set()
        deduplicated = []
        removed_count = 0
        
        for item in items:
            # 提取文本内容
            text = ""
            if isinstance(item, dict):
                text = item.get("snippet", "") or item.get("text", "") or item.get("title", "")
            elif isinstance(item, str):
                text = item
            
            if not text:
                continue
            
            # 计算内容哈希（使用标准化后的文本）
            normalized_text = re.sub(r'\s+', ' ', text.lower().strip())
            text_hash = hashlib.md5(normalized_text.encode()).hexdigest()
            
            # 检查是否重复
            if text_hash not in seen_hashes:
                seen_hashes.add(text_hash)
                deduplicated.append(item)
            else:
                removed_count += 1
        
        return json.dumps({
            "status": "success",
            "original_count": len(items),
            "deduplicated_count": len(deduplicated),
            "removed_count": removed_count,
            "deduplication_rate": round(removed_count / len(items), 2) if items else 0,
            "deduplicated_items": deduplicated,
            "execution_time": time.time() - start_time
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"去重失败: {str(e)}",
            "error_code": "DEDUPLICATION_ERROR",
            "execution_time": time.time() - start_time
        }, ensure_ascii=False)


@tool
def filter_quality_feedback(
    feedback_items: str,
    min_length: int = 20,
    max_length: int = 5000,
    remove_spam: bool = True
) -> str:
    """
    过滤低质量反馈
    
    基于内容长度、关键词等标准过滤低质量的反馈信息。
    
    Args:
        feedback_items: JSON格式的反馈项列表
        min_length: 最小文本长度
        max_length: 最大文本长度
        remove_spam: 是否移除垃圾信息
    
    Returns:
        str: JSON格式的过滤后的反馈列表
    """
    start_time = time.time()
    
    try:
        # 解析输入
        try:
            items = json.loads(feedback_items) if isinstance(feedback_items, str) else feedback_items
        except json.JSONDecodeError:
            return json.dumps({
                "status": "error",
                "message": "无效的JSON格式",
                "error_code": "INVALID_JSON"
            }, ensure_ascii=False)
        
        if not isinstance(items, list):
            return json.dumps({
                "status": "error",
                "message": "输入必须是列表",
                "error_code": "INVALID_INPUT"
            }, ensure_ascii=False)
        
        # 垃圾信息关键词
        spam_keywords = [
            'viagra', 'casino', 'lottery', 'porn', 'xxx', 
            '赌博', '色情', '成人', '贷款', '发票'
        ]
        
        filtered_items = []
        removed_count = 0
        removal_reasons = {
            "too_short": 0,
            "too_long": 0,
            "spam": 0,
            "empty": 0
        }
        
        for item in items:
            # 提取文本内容
            text = ""
            if isinstance(item, dict):
                text = item.get("snippet", "") or item.get("text", "") or item.get("title", "")
            elif isinstance(item, str):
                text = item
            
            # 检查是否为空
            if not text or not text.strip():
                removed_count += 1
                removal_reasons["empty"] += 1
                continue
            
            text = text.strip()
            
            # 检查长度
            if len(text) < min_length:
                removed_count += 1
                removal_reasons["too_short"] += 1
                continue
            
            if len(text) > max_length:
                removed_count += 1
                removal_reasons["too_long"] += 1
                continue
            
            # 检查垃圾信息
            if remove_spam:
                text_lower = text.lower()
                if any(keyword in text_lower for keyword in spam_keywords):
                    removed_count += 1
                    removal_reasons["spam"] += 1
                    continue
            
            # 通过所有过滤条件
            filtered_items.append(item)
        
        return json.dumps({
            "status": "success",
            "original_count": len(items),
            "filtered_count": len(filtered_items),
            "removed_count": removed_count,
            "removal_reasons": removal_reasons,
            "quality_rate": round(len(filtered_items) / len(items), 2) if items else 0,
            "filtered_items": filtered_items,
            "execution_time": time.time() - start_time
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"质量过滤失败: {str(e)}",
            "error_code": "FILTER_ERROR",
            "execution_time": time.time() - start_time
        }, ensure_ascii=False)


@tool
def aggregate_feedback_statistics(
    feedback_items: str,
    include_sentiment: bool = True,
    include_topics: bool = True
) -> str:
    """
    聚合反馈统计信息
    
    对收集的反馈进行统计分析，生成汇总报告。
    
    Args:
        feedback_items: JSON格式的反馈项列表（需包含sentiment和topic字段）
        include_sentiment: 是否包含情感统计
        include_topics: 是否包含主题统计
    
    Returns:
        str: JSON格式的统计结果
    """
    start_time = time.time()
    
    try:
        # 解析输入
        try:
            items = json.loads(feedback_items) if isinstance(feedback_items, str) else feedback_items
        except json.JSONDecodeError:
            return json.dumps({
                "status": "error",
                "message": "无效的JSON格式",
                "error_code": "INVALID_JSON"
            }, ensure_ascii=False)
        
        if not isinstance(items, list):
            return json.dumps({
                "status": "error",
                "message": "输入必须是列表",
                "error_code": "INVALID_INPUT"
            }, ensure_ascii=False)
        
        statistics = {
            "total_count": len(items),
            "sources": Counter(),
            "execution_time": 0
        }
        
        # 统计来源
        for item in items:
            if isinstance(item, dict):
                source = item.get("source_type", "unknown")
                statistics["sources"][source] += 1
        
        # 情感统计
        if include_sentiment:
            sentiment_counts = Counter()
            sentiment_confidences = []
            
            for item in items:
                if isinstance(item, dict):
                    sentiment = item.get("sentiment", "neutral")
                    sentiment_counts[sentiment] += 1
                    
                    confidence = item.get("sentiment_confidence", 0.5)
                    sentiment_confidences.append(confidence)
            
            statistics["sentiment"] = {
                "distribution": dict(sentiment_counts),
                "positive_rate": round(sentiment_counts.get("positive", 0) / len(items), 2) if items else 0,
                "negative_rate": round(sentiment_counts.get("negative", 0) / len(items), 2) if items else 0,
                "neutral_rate": round(sentiment_counts.get("neutral", 0) / len(items), 2) if items else 0,
                "average_confidence": round(sum(sentiment_confidences) / len(sentiment_confidences), 2) if sentiment_confidences else 0
            }
        
        # 主题统计
        if include_topics:
            topic_counts = Counter()
            
            for item in items:
                if isinstance(item, dict):
                    primary_topic = item.get("primary_topic", "general")
                    topic_counts[primary_topic] += 1
                    
                    # 统计次要主题
                    secondary_topics = item.get("secondary_topics", [])
                    for topic in secondary_topics:
                        topic_counts[topic] += 0.5  # 次要主题权重为0.5
            
            statistics["topics"] = {
                "distribution": {k: int(v) for k, v in topic_counts.most_common()},
                "most_common": topic_counts.most_common(5)
            }
        
        statistics["execution_time"] = time.time() - start_time
        
        return json.dumps({
            "status": "success",
            "statistics": statistics
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"统计聚合失败: {str(e)}",
            "error_code": "AGGREGATION_ERROR",
            "execution_time": time.time() - start_time
        }, ensure_ascii=False)


@tool
def generate_feedback_summary(
    feedback_items: str,
    statistics: str,
    drug_name: str,
    summary_type: str = "comprehensive"
) -> str:
    """
    生成反馈摘要报告
    
    基于收集的反馈和统计数据生成结构化的摘要报告。
    
    Args:
        feedback_items: JSON格式的反馈项列表
        statistics: JSON格式的统计信息
        drug_name: 药物名称
        summary_type: 摘要类型，可选值：brief（简要）、standard（标准）、comprehensive（全面）
    
    Returns:
        str: JSON格式的摘要报告
    """
    start_time = time.time()
    
    try:
        # 解析输入
        try:
            items = json.loads(feedback_items) if isinstance(feedback_items, str) else feedback_items
            stats = json.loads(statistics) if isinstance(statistics, str) else statistics
        except json.JSONDecodeError:
            return json.dumps({
                "status": "error",
                "message": "无效的JSON格式",
                "error_code": "INVALID_JSON"
            }, ensure_ascii=False)
        
        # 提取关键信息
        total_count = stats.get("statistics", {}).get("total_count", 0)
        sentiment_dist = stats.get("statistics", {}).get("sentiment", {}).get("distribution", {})
        topic_dist = stats.get("statistics", {}).get("topics", {}).get("distribution", {})
        
        # 生成摘要
        summary = {
            "drug_name": drug_name,
            "report_date": datetime.now().isoformat(),
            "data_overview": {
                "total_feedback_count": total_count,
                "data_sources": list(stats.get("statistics", {}).get("sources", {}).keys()),
                "collection_method": "网络搜索（DuckDuckGo）"
            }
        }
        
        # 情感概览
        if sentiment_dist:
            positive = sentiment_dist.get("positive", 0)
            negative = sentiment_dist.get("negative", 0)
            neutral = sentiment_dist.get("neutral", 0)
            
            summary["sentiment_overview"] = {
                "positive_count": positive,
                "negative_count": negative,
                "neutral_count": neutral,
                "positive_percentage": round(positive / total_count * 100, 1) if total_count > 0 else 0,
                "negative_percentage": round(negative / total_count * 100, 1) if total_count > 0 else 0,
                "overall_sentiment": "positive" if positive > negative else "negative" if negative > positive else "neutral"
            }
        
        # 主题概览
        if topic_dist:
            summary["topic_overview"] = {
                "top_topics": list(topic_dist.keys())[:5],
                "topic_distribution": topic_dist
            }
        
        # 根据摘要类型添加详细信息
        if summary_type in ["standard", "comprehensive"]:
            # 提取代表性反馈
            representative_feedback = []
            
            # 每个情感类别选择一个代表
            for sentiment_type in ["positive", "negative", "neutral"]:
                for item in items:
                    if isinstance(item, dict) and item.get("sentiment") == sentiment_type:
                        representative_feedback.append({
                            "sentiment": sentiment_type,
                            "topic": item.get("primary_topic", "general"),
                            "snippet": (item.get("snippet", "") or item.get("text", ""))[:200],
                            "source": item.get("url", "")
                        })
                        break
            
            summary["representative_feedback"] = representative_feedback
        
        if summary_type == "comprehensive":
            # 添加详细分析
            summary["detailed_analysis"] = {
                "quality_metrics": {
                    "data_coverage": "多来源（网页、新闻、论坛）",
                    "sample_size": total_count,
                    "data_reliability": "中等（基于公开网络数据）"
                },
                "key_findings": [
                    f"共收集到 {total_count} 条反馈信息",
                    f"情感倾向：{summary.get('sentiment_overview', {}).get('overall_sentiment', 'unknown')}",
                    f"主要讨论主题：{', '.join(list(topic_dist.keys())[:3]) if topic_dist else '无'}"
                ],
                "limitations": [
                    "数据来源于公开网络，可能存在偏差",
                    "情感分析基于关键词匹配，准确度有限",
                    "不能替代专业医学建议"
                ]
            }
        
        return json.dumps({
            "status": "success",
            "summary": summary,
            "execution_time": time.time() - start_time
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"生成摘要失败: {str(e)}",
            "error_code": "SUMMARY_ERROR",
            "execution_time": time.time() - start_time
        }, ensure_ascii=False)


@tool
def validate_drug_name(
    drug_name: str
) -> str:
    """
    验证药物名称
    
    检查药物名称的有效性和标准化。
    
    Args:
        drug_name: 药物名称
    
    Returns:
        str: JSON格式的验证结果
    """
    start_time = time.time()
    
    try:
        if not drug_name or not drug_name.strip():
            return json.dumps({
                "status": "error",
                "message": "药物名称不能为空",
                "is_valid": False,
                "error_code": "EMPTY_NAME"
            }, ensure_ascii=False)
        
        drug_name = drug_name.strip()
        
        # 基本验证规则
        is_valid = True
        warnings = []
        suggestions = []
        
        # 检查长度
        if len(drug_name) < 2:
            is_valid = False
            warnings.append("药物名称过短")
        
        if len(drug_name) > 100:
            warnings.append("药物名称过长，可能不是标准药名")
        
        # 检查特殊字符
        if re.search(r'[<>{}[\]\\|]', drug_name):
            warnings.append("包含不常见的特殊字符")
        
        # 检查是否为常见的非药物词汇
        non_drug_words = ['测试', 'test', '示例', 'example', '药物', 'drug', 'medicine']
        if drug_name.lower() in non_drug_words:
            warnings.append("可能不是实际的药物名称")
            suggestions.append("请输入具体的药物名称")
        
        # 标准化建议
        standardized_name = drug_name
        if drug_name != drug_name.title():
            suggestions.append(f"建议使用标准化名称：{drug_name.title()}")
            standardized_name = drug_name.title()
        
        return json.dumps({
            "status": "success",
            "is_valid": is_valid,
            "original_name": drug_name,
            "standardized_name": standardized_name,
            "warnings": warnings,
            "suggestions": suggestions,
            "execution_time": time.time() - start_time
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"验证失败: {str(e)}",
            "is_valid": False,
            "error_code": "VALIDATION_ERROR",
            "execution_time": time.time() - start_time
        }, ensure_ascii=False)


@tool
def manage_feedback_cache(
    operation: str,
    drug_name: Optional[str] = None
) -> str:
    """
    管理反馈缓存
    
    管理药物反馈的本地缓存，支持查看、清理等操作。
    
    Args:
        operation: 操作类型，可选值：list（列出缓存）、clear（清除缓存）、clear_all（清除所有缓存）、stats（统计信息）
        drug_name: 药物名称（用于clear操作）
    
    Returns:
        str: JSON格式的操作结果
    """
    start_time = time.time()
    
    try:
        cache_dir = _get_cache_dir()
        
        if operation == "list":
            # 列出所有缓存
            cache_files = list(cache_dir.glob("*.json"))
            cache_list = []
            
            for cache_file in cache_files:
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                    cache_list.append({
                        "drug_name": cache_data.get("drug_name", "unknown"),
                        "timestamp": cache_data.get("timestamp", ""),
                        "file_size": cache_file.stat().st_size,
                        "cache_key": cache_file.stem
                    })
                except Exception:
                    continue
            
            return json.dumps({
                "status": "success",
                "operation": "list",
                "cache_count": len(cache_list),
                "cache_list": cache_list,
                "execution_time": time.time() - start_time
            }, ensure_ascii=False)
        
        elif operation == "clear":
            # 清除特定药物的缓存
            if not drug_name:
                return json.dumps({
                    "status": "error",
                    "message": "清除缓存需要提供药物名称",
                    "error_code": "MISSING_PARAMETER"
                }, ensure_ascii=False)
            
            cache_file = cache_dir / f"{_get_cache_key(drug_name)}.json"
            if cache_file.exists():
                cache_file.unlink()
                return json.dumps({
                    "status": "success",
                    "operation": "clear",
                    "message": f"已清除 {drug_name} 的缓存",
                    "execution_time": time.time() - start_time
                }, ensure_ascii=False)
            else:
                return json.dumps({
                    "status": "success",
                    "operation": "clear",
                    "message": f"{drug_name} 没有缓存数据",
                    "execution_time": time.time() - start_time
                }, ensure_ascii=False)
        
        elif operation == "clear_all":
            # 清除所有缓存
            cache_files = list(cache_dir.glob("*.json"))
            for cache_file in cache_files:
                try:
                    cache_file.unlink()
                except Exception:
                    continue
            
            return json.dumps({
                "status": "success",
                "operation": "clear_all",
                "message": f"已清除 {len(cache_files)} 个缓存文件",
                "execution_time": time.time() - start_time
            }, ensure_ascii=False)
        
        elif operation == "stats":
            # 缓存统计
            cache_files = list(cache_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in cache_files)
            
            # 统计过期的缓存
            expired_count = 0
            for cache_file in cache_files:
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                    cache_time = datetime.fromisoformat(cache_data.get('timestamp', '2000-01-01T00:00:00'))
                    if datetime.now() - cache_time > timedelta(hours=1):
                        expired_count += 1
                except Exception:
                    continue
            
            return json.dumps({
                "status": "success",
                "operation": "stats",
                "statistics": {
                    "total_cache_count": len(cache_files),
                    "expired_count": expired_count,
                    "valid_count": len(cache_files) - expired_count,
                    "total_size_bytes": total_size,
                    "total_size_mb": round(total_size / 1024 / 1024, 2),
                    "cache_directory": str(cache_dir)
                },
                "execution_time": time.time() - start_time
            }, ensure_ascii=False)
        
        else:
            return json.dumps({
                "status": "error",
                "message": f"未知的操作类型: {operation}",
                "error_code": "INVALID_OPERATION"
            }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"缓存管理失败: {str(e)}",
            "error_code": "CACHE_ERROR",
            "execution_time": time.time() - start_time
        }, ensure_ascii=False)


@tool
def extract_representative_feedback(
    feedback_items: str,
    count_per_category: int = 3,
    categories: Optional[List[str]] = None
) -> str:
    """
    提取代表性反馈
    
    从大量反馈中提取最具代表性的案例。
    
    Args:
        feedback_items: JSON格式的反馈项列表
        count_per_category: 每个类别提取的数量
        categories: 要提取的类别列表（如：positive, negative, efficacy, side_effects等）
    
    Returns:
        str: JSON格式的代表性反馈列表
    """
    start_time = time.time()
    
    try:
        # 解析输入
        try:
            items = json.loads(feedback_items) if isinstance(feedback_items, str) else feedback_items
        except json.JSONDecodeError:
            return json.dumps({
                "status": "error",
                "message": "无效的JSON格式",
                "error_code": "INVALID_JSON"
            }, ensure_ascii=False)
        
        if not isinstance(items, list) or not items:
            return json.dumps({
                "status": "success",
                "representative_feedback": [],
                "execution_time": time.time() - start_time
            }, ensure_ascii=False)
        
        # 默认类别
        if categories is None:
            categories = ["positive", "negative", "neutral", "efficacy", "side_effects"]
        
        # 按类别分组
        categorized_feedback: Dict[str, List[Dict[str, Any]]] = {cat: [] for cat in categories}
        
        for item in items:
            if not isinstance(item, dict):
                continue
            
            # 按情感分类
            sentiment = item.get("sentiment", "neutral")
            if sentiment in categories:
                categorized_feedback[sentiment].append(item)
            
            # 按主题分类
            topic = item.get("primary_topic", "")
            if topic in categories:
                categorized_feedback[topic].append(item)
        
        # 从每个类别中提取代表性样本
        representative = {}
        
        for category, feedback_list in categorized_feedback.items():
            if not feedback_list:
                continue
            
            # 按置信度排序（如果有）
            sorted_feedback = sorted(
                feedback_list,
                key=lambda x: x.get("sentiment_confidence", 0.5) + x.get("topic_confidence", 0.5),
                reverse=True
            )
            
            # 提取前N个
            selected = sorted_feedback[:count_per_category]
            
            # 简化输出
            representative[category] = [
                {
                    "title": item.get("title", ""),
                    "snippet": (item.get("snippet", "") or item.get("text", ""))[:300],
                    "url": item.get("url", ""),
                    "sentiment": item.get("sentiment", ""),
                    "topic": item.get("primary_topic", ""),
                    "confidence": round(item.get("sentiment_confidence", 0.5), 2)
                }
                for item in selected
            ]
        
        return json.dumps({
            "status": "success",
            "representative_feedback": representative,
            "categories_found": list(representative.keys()),
            "total_representative_count": sum(len(v) for v in representative.values()),
            "execution_time": time.time() - start_time
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"提取代表性反馈失败: {str(e)}",
            "error_code": "EXTRACTION_ERROR",
            "execution_time": time.time() - start_time
        }, ensure_ascii=False)


@tool
def format_feedback_report(
    summary_data: str,
    output_format: str = "markdown"
) -> str:
    """
    格式化反馈报告
    
    将摘要数据格式化为易读的报告格式。
    
    Args:
        summary_data: JSON格式的摘要数据
        output_format: 输出格式，可选值：markdown、html、text
    
    Returns:
        str: 格式化后的报告内容
    """
    start_time = time.time()
    
    try:
        # 解析输入
        try:
            summary = json.loads(summary_data) if isinstance(summary_data, str) else summary_data
            if "summary" in summary:
                summary = summary["summary"]
        except json.JSONDecodeError:
            return json.dumps({
                "status": "error",
                "message": "无效的JSON格式",
                "error_code": "INVALID_JSON"
            }, ensure_ascii=False)
        
        drug_name = summary.get("drug_name", "未知药物")
        
        if output_format == "markdown":
            report = f"""# {drug_name} 网络反馈分析报告

## 报告概览
- **生成时间**: {summary.get('report_date', '')}
- **数据来源**: {', '.join(summary.get('data_overview', {}).get('data_sources', []))}
- **反馈总数**: {summary.get('data_overview', {}).get('total_feedback_count', 0)}

## 情感分析
"""
            sentiment = summary.get("sentiment_overview", {})
            if sentiment:
                report += f"""
- **正面反馈**: {sentiment.get('positive_count', 0)} ({sentiment.get('positive_percentage', 0)}%)
- **负面反馈**: {sentiment.get('negative_count', 0)} ({sentiment.get('negative_percentage', 0)}%)
- **中性反馈**: {sentiment.get('neutral_count', 0)}
- **总体情感倾向**: {sentiment.get('overall_sentiment', 'neutral')}
"""
            
            # 主题分布
            topics = summary.get("topic_overview", {})
            if topics:
                report += "\n## 主题分布\n"
                for topic, count in list(topics.get('topic_distribution', {}).items())[:5]:
                    report += f"- **{topic}**: {count}\n"
            
            # 代表性反馈
            representative = summary.get("representative_feedback", [])
            if representative:
                report += "\n## 代表性反馈\n"
                for feedback in representative[:5]:
                    report += f"\n### {feedback.get('sentiment', '').upper()} - {feedback.get('topic', '')}\n"
                    report += f"{feedback.get('snippet', '')}\n"
                    report += f"*来源: {feedback.get('url', '')}*\n"
            
            # 详细分析
            detailed = summary.get("detailed_analysis", {})
            if detailed:
                report += "\n## 关键发现\n"
                for finding in detailed.get("key_findings", []):
                    report += f"- {finding}\n"
                
                report += "\n## 局限性说明\n"
                for limitation in detailed.get("limitations", []):
                    report += f"- {limitation}\n"
            
            report += "\n---\n*本报告基于公开网络数据生成，仅供参考，不构成医学建议。*\n"
            
        elif output_format == "html":
            # HTML格式
            report = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{drug_name} 反馈分析报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .metric {{ background: #ecf0f1; padding: 10px; margin: 10px 0; border-radius: 5px; }}
        .positive {{ color: #27ae60; }}
        .negative {{ color: #e74c3c; }}
        .neutral {{ color: #95a5a6; }}
    </style>
</head>
<body>
    <h1>{drug_name} 网络反馈分析报告</h1>
    <div class="metric">
        <strong>生成时间:</strong> {summary.get('report_date', '')}<br>
        <strong>反馈总数:</strong> {summary.get('data_overview', {}).get('total_feedback_count', 0)}
    </div>
"""
            sentiment = summary.get("sentiment_overview", {})
            if sentiment:
                report += f"""
    <h2>情感分析</h2>
    <div class="metric">
        <span class="positive">正面: {sentiment.get('positive_count', 0)} ({sentiment.get('positive_percentage', 0)}%)</span><br>
        <span class="negative">负面: {sentiment.get('negative_count', 0)} ({sentiment.get('negative_percentage', 0)}%)</span><br>
        <span class="neutral">中性: {sentiment.get('neutral_count', 0)}</span>
    </div>
"""
            report += """
    <p><em>本报告基于公开网络数据生成，仅供参考，不构成医学建议。</em></p>
</body>
</html>
"""
        
        else:  # text格式
            report = f"{drug_name} 反馈分析报告\n"
            report += "=" * 50 + "\n\n"
            report += f"生成时间: {summary.get('report_date', '')}\n"
            report += f"反馈总数: {summary.get('data_overview', {}).get('total_feedback_count', 0)}\n\n"
            
            sentiment = summary.get("sentiment_overview", {})
            if sentiment:
                report += "情感分析:\n"
                report += f"  正面: {sentiment.get('positive_count', 0)} ({sentiment.get('positive_percentage', 0)}%)\n"
                report += f"  负面: {sentiment.get('negative_count', 0)} ({sentiment.get('negative_percentage', 0)}%)\n"
                report += f"  中性: {sentiment.get('neutral_count', 0)}\n\n"
        
        return json.dumps({
            "status": "success",
            "format": output_format,
            "report": report,
            "execution_time": time.time() - start_time
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"报告格式化失败: {str(e)}",
            "error_code": "FORMAT_ERROR",
            "execution_time": time.time() - start_time
        }, ensure_ascii=False)
