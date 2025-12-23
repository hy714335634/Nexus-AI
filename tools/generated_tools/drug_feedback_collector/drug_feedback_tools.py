#!/usr/bin/env python3
"""
药物反馈收集工具模块

提供药物反馈收集所需的核心工具函数，包括：
1. 网络搜索工具（使用DuckDuckGo）
2. 网页抓取工具
3. 内容分析工具（使用Claude）
4. 报告生成工具
5. 缓存管理工具
"""

import json
import hashlib
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse, quote_plus
import traceback

from strands import tool

# DuckDuckGo搜索（替代Tavily）
try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False

# 网页抓取
try:
    import requests
    from bs4 import BeautifulSoup
    SCRAPING_AVAILABLE = True
except ImportError:
    SCRAPING_AVAILABLE = False

# AWS Bedrock用于AI分析
try:
    import boto3
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False


# ==================== 工具1: 药物名称验证和标准化 ====================

@tool
def validate_drug_name(drug_name: str) -> str:
    """
    验证和标准化药物名称
    
    Args:
        drug_name (str): 用户输入的药物名称
        
    Returns:
        str: JSON格式的验证结果，包含标准化名称和变体
    """
    try:
        if not drug_name or not drug_name.strip():
            return json.dumps({
                "status": "error",
                "message": "请提供有效的药物名称。示例：阿司匹林、布洛芬、Aspirin",
                "valid": False
            }, ensure_ascii=False)
        
        # 清理输入
        cleaned_name = drug_name.strip()
        
        # 生成药物名称变体（用于搜索）
        variants = [cleaned_name]
        
        # 添加常见后缀变体
        common_suffixes = ["片", "胶囊", "注射液", "颗粒", "丸", "缓释片", "肠溶片"]
        for suffix in common_suffixes:
            if cleaned_name.endswith(suffix):
                base_name = cleaned_name[:-len(suffix)]
                variants.append(base_name)
                break
            else:
                variants.append(f"{cleaned_name}{suffix}")
        
        # 添加英文/中文变体（简单规则）
        if re.match(r'^[a-zA-Z\s]+$', cleaned_name):
            # 英文名称，添加常见中文翻译提示
            variants.append(f"{cleaned_name} 中文名")
        elif re.match(r'^[\u4e00-\u9fa5]+$', cleaned_name):
            # 中文名称，添加英文翻译提示
            variants.append(f"{cleaned_name} 英文名")
        
        result = {
            "status": "success",
            "valid": True,
            "original_name": drug_name,
            "standardized_name": cleaned_name,
            "search_variants": list(set(variants)),
            "validation_time": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"药物名称验证失败: {str(e)}",
            "valid": False
        }, ensure_ascii=False)


# ==================== 工具2: 网络搜索工具 ====================

@tool
def search_drug_feedback(
    drug_name: str,
    search_keywords: List[str] = None,
    max_results_per_keyword: int = 10
) -> str:
    """
    使用DuckDuckGo搜索药物反馈信息
    
    Args:
        drug_name (str): 药物名称
        search_keywords (List[str]): 搜索关键词列表，默认为["评价", "副作用", "体验", "反馈"]
        max_results_per_keyword (int): 每个关键词的最大结果数
        
    Returns:
        str: JSON格式的搜索结果
    """
    try:
        if not DDGS_AVAILABLE:
            return json.dumps({
                "status": "error",
                "message": "DuckDuckGo搜索库未安装。请安装: pip install duckduckgo-search"
            }, ensure_ascii=False)
        
        if search_keywords is None:
            search_keywords = ["评价", "副作用", "体验", "反馈", "效果"]
        
        all_results = []
        search_metadata = {
            "drug_name": drug_name,
            "keywords_used": search_keywords,
            "search_time": datetime.now().isoformat(),
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0
        }
        
        ddgs = DDGS()
        
        for keyword in search_keywords:
            query = f"{drug_name} {keyword}"
            search_metadata["total_queries"] += 1
            
            try:
                # 执行搜索
                results = ddgs.text(query, max_results=max_results_per_keyword)
                
                if results:
                    search_metadata["successful_queries"] += 1
                    for result in results:
                        all_results.append({
                            "keyword": keyword,
                            "title": result.get("title", ""),
                            "url": result.get("href", ""),
                            "snippet": result.get("body", ""),
                            "source": urlparse(result.get("href", "")).netloc
                        })
                
                # 避免触发速率限制
                time.sleep(0.5)
                
            except Exception as e:
                search_metadata["failed_queries"] += 1
                print(f"搜索关键词 '{keyword}' 失败: {e}")
                continue
        
        return json.dumps({
            "status": "success",
            "metadata": search_metadata,
            "results": all_results,
            "total_results": len(all_results)
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"搜索失败: {str(e)}",
            "traceback": traceback.format_exc()
        }, ensure_ascii=False)


# ==================== 工具3: 网页内容抓取工具 ====================

@tool
def extract_webpage_content(
    url: str,
    max_content_length: int = 10240,
    timeout: int = 10
) -> str:
    """
    抓取网页内容并提取正文
    
    Args:
        url (str): 网页URL
        max_content_length (int): 最大内容长度（字节）
        timeout (int): 请求超时时间（秒）
        
    Returns:
        str: JSON格式的抓取结果
    """
    try:
        if not SCRAPING_AVAILABLE:
            return json.dumps({
                "status": "error",
                "message": "网页抓取库未安装。请安装: pip install requests beautifulsoup4 lxml"
            }, ensure_ascii=False)
        
        # 设置请求头
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
        }
        
        # 发送请求
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        
        # 解析HTML
        soup = BeautifulSoup(response.content, 'lxml')
        
        # 移除脚本和样式
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # 提取正文内容
        # 优先提取article、main、content等主要内容区域
        main_content = None
        for tag in ['article', 'main', '[role="main"]', '.content', '#content']:
            main_content = soup.select_one(tag)
            if main_content:
                break
        
        if not main_content:
            main_content = soup.body if soup.body else soup
        
        # 提取文本
        text = main_content.get_text(separator="\n", strip=True)
        
        # 清理文本
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        cleaned_text = "\n".join(lines)
        
        # 限制长度
        if len(cleaned_text) > max_content_length:
            cleaned_text = cleaned_text[:max_content_length] + "..."
        
        # 提取标题
        title = soup.title.string if soup.title else ""
        
        result = {
            "status": "success",
            "url": url,
            "title": title,
            "content": cleaned_text,
            "content_length": len(cleaned_text),
            "extraction_time": datetime.now().isoformat(),
            "source_domain": urlparse(url).netloc
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
            "message": f"内容提取失败: {str(e)}",
            "traceback": traceback.format_exc()
        }, ensure_ascii=False)


@tool
def batch_extract_webpages(
    urls: List[str],
    max_content_length: int = 10240,
    timeout: int = 10,
    max_concurrent: int = 5
) -> str:
    """
    批量抓取多个网页内容
    
    Args:
        urls (List[str]): 网页URL列表
        max_content_length (int): 每个网页的最大内容长度
        timeout (int): 请求超时时间
        max_concurrent (int): 最大并发数（当前版本顺序执行）
        
    Returns:
        str: JSON格式的批量抓取结果
    """
    try:
        results = []
        successful = 0
        failed = 0
        
        for url in urls[:max_concurrent]:  # 限制并发数
            result_json = extract_webpage_content(url, max_content_length, timeout)
            result = json.loads(result_json)
            
            if result["status"] == "success":
                successful += 1
            else:
                failed += 1
            
            results.append(result)
            
            # 避免触发速率限制
            time.sleep(1)
        
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
            "message": f"批量抓取失败: {str(e)}",
            "traceback": traceback.format_exc()
        }, ensure_ascii=False)


# ==================== 工具4: AI内容分析工具 ====================

@tool
def analyze_feedback_with_claude(
    content: str,
    drug_name: str,
    analysis_type: str = "comprehensive"
) -> str:
    """
    使用Claude模型分析药物反馈内容
    
    Args:
        content (str): 要分析的文本内容
        drug_name (str): 药物名称
        analysis_type (str): 分析类型（basic/comprehensive/detailed）
        
    Returns:
        str: JSON格式的分析结果
    """
    try:
        if not BOTO3_AVAILABLE:
            return json.dumps({
                "status": "error",
                "message": "boto3库未安装。请安装: pip install boto3"
            }, ensure_ascii=False)
        
        # 创建Bedrock客户端
        bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name='us-east-1'
        )
        
        # 构建分析提示词
        analysis_prompt = f"""请分析以下关于药物"{drug_name}"的用户反馈内容，提取关键信息并分类。

内容：
{content[:8000]}  # 限制输入长度

请按以下结构提取信息：
1. 反馈类型：疗效评价、副作用、使用体验、价格评价
2. 情感倾向：正面、负面、中性
3. 关键信息：提取具体的疗效描述、副作用描述、使用体验描述
4. 可信度：根据描述的具体性和逻辑性评估（高/中/低）

请以JSON格式返回结果，格式如下：
{{
  "feedback_type": "疗效评价/副作用/使用体验/价格评价",
  "sentiment": "positive/negative/neutral",
  "efficacy": {{"description": "疗效描述", "mentioned": true/false}},
  "side_effects": {{"description": "副作用描述", "mentioned": true/false}},
  "experience": {{"description": "使用体验描述", "mentioned": true/false}},
  "price": {{"description": "价格评价", "mentioned": true/false}},
  "credibility": "high/medium/low",
  "key_points": ["关键点1", "关键点2"]
}}
"""
        
        # 调用Claude模型
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,
            "messages": [
                {
                    "role": "user",
                    "content": analysis_prompt
                }
            ],
            "temperature": 0.3
        }
        
        response = bedrock_runtime.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        analysis_text = response_body['content'][0]['text']
        
        # 尝试解析JSON结果
        try:
            # 提取JSON部分
            json_match = re.search(r'\{[\s\S]*\}', analysis_text)
            if json_match:
                analysis_result = json.loads(json_match.group())
            else:
                # 如果没有找到JSON，返回原始文本
                analysis_result = {
                    "feedback_type": "unknown",
                    "sentiment": "neutral",
                    "raw_analysis": analysis_text,
                    "parsing_note": "无法解析为结构化JSON，返回原始分析"
                }
        except:
            analysis_result = {
                "feedback_type": "unknown",
                "sentiment": "neutral",
                "raw_analysis": analysis_text,
                "parsing_note": "JSON解析失败，返回原始分析"
            }
        
        return json.dumps({
            "status": "success",
            "drug_name": drug_name,
            "analysis_type": analysis_type,
            "analysis_result": analysis_result,
            "analysis_time": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"AI分析失败: {str(e)}",
            "traceback": traceback.format_exc()
        }, ensure_ascii=False)


@tool
def batch_analyze_feedback(
    contents: List[Dict[str, str]],
    drug_name: str
) -> str:
    """
    批量分析多个反馈内容
    
    Args:
        contents (List[Dict[str, str]]): 内容列表，每个元素包含url和content
        drug_name (str): 药物名称
        
    Returns:
        str: JSON格式的批量分析结果
    """
    try:
        analyzed_results = []
        successful = 0
        failed = 0
        
        for item in contents:
            content = item.get("content", "")
            url = item.get("url", "")
            
            if not content:
                failed += 1
                continue
            
            # 分析单个内容
            result_json = analyze_feedback_with_claude(content, drug_name, "basic")
            result = json.loads(result_json)
            
            if result["status"] == "success":
                successful += 1
                result["source_url"] = url
                analyzed_results.append(result)
            else:
                failed += 1
            
            # 避免触发API速率限制
            time.sleep(1)
        
        return json.dumps({
            "status": "success",
            "drug_name": drug_name,
            "total_items": len(contents),
            "successful": successful,
            "failed": failed,
            "results": analyzed_results,
            "analysis_time": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"批量分析失败: {str(e)}",
            "traceback": traceback.format_exc()
        }, ensure_ascii=False)


# ==================== 工具5: 反馈报告生成工具 ====================

@tool
def generate_feedback_report(
    drug_name: str,
    analyzed_feedbacks: List[Dict[str, Any]],
    include_sources: bool = True
) -> str:
    """
    生成药物反馈报告
    
    Args:
        drug_name (str): 药物名称
        analyzed_feedbacks (List[Dict]): 已分析的反馈列表
        include_sources (bool): 是否包含来源信息
        
    Returns:
        str: JSON格式的反馈报告
    """
    try:
        # 统计分析
        total_feedbacks = len(analyzed_feedbacks)
        
        # 按情感分类
        sentiment_stats = {"positive": 0, "negative": 0, "neutral": 0}
        
        # 按反馈类型分类
        type_stats = {
            "疗效评价": 0,
            "副作用": 0,
            "使用体验": 0,
            "价格评价": 0,
            "其他": 0
        }
        
        # 收集具体反馈
        efficacy_feedbacks = []
        side_effect_feedbacks = []
        experience_feedbacks = []
        price_feedbacks = []
        
        # 来源列表
        sources = []
        
        for feedback in analyzed_feedbacks:
            analysis = feedback.get("analysis_result", {})
            
            # 统计情感
            sentiment = analysis.get("sentiment", "neutral")
            if sentiment in sentiment_stats:
                sentiment_stats[sentiment] += 1
            
            # 统计类型
            feedback_type = analysis.get("feedback_type", "其他")
            if feedback_type in type_stats:
                type_stats[feedback_type] += 1
            else:
                type_stats["其他"] += 1
            
            # 收集具体反馈
            if analysis.get("efficacy", {}).get("mentioned"):
                efficacy_feedbacks.append({
                    "description": analysis["efficacy"]["description"],
                    "sentiment": sentiment,
                    "source_url": feedback.get("source_url", "")
                })
            
            if analysis.get("side_effects", {}).get("mentioned"):
                side_effect_feedbacks.append({
                    "description": analysis["side_effects"]["description"],
                    "sentiment": sentiment,
                    "source_url": feedback.get("source_url", "")
                })
            
            if analysis.get("experience", {}).get("mentioned"):
                experience_feedbacks.append({
                    "description": analysis["experience"]["description"],
                    "sentiment": sentiment,
                    "source_url": feedback.get("source_url", "")
                })
            
            if analysis.get("price", {}).get("mentioned"):
                price_feedbacks.append({
                    "description": analysis["price"]["description"],
                    "sentiment": sentiment,
                    "source_url": feedback.get("source_url", "")
                })
            
            # 收集来源
            if include_sources and feedback.get("source_url"):
                sources.append({
                    "url": feedback["source_url"],
                    "title": feedback.get("title", ""),
                    "credibility": analysis.get("credibility", "unknown")
                })
        
        # 计算统计百分比
        sentiment_percentages = {
            k: round(v / total_feedbacks * 100, 1) if total_feedbacks > 0 else 0
            for k, v in sentiment_stats.items()
        }
        
        # 生成报告
        report = {
            "report_metadata": {
                "drug_name": drug_name,
                "generation_time": datetime.now().isoformat(),
                "total_feedbacks_analyzed": total_feedbacks,
                "report_version": "1.0"
            },
            "summary": {
                "overall_sentiment": _determine_overall_sentiment(sentiment_stats),
                "sentiment_distribution": {
                    "positive": f"{sentiment_percentages['positive']}%",
                    "negative": f"{sentiment_percentages['negative']}%",
                    "neutral": f"{sentiment_percentages['neutral']}%"
                },
                "feedback_type_distribution": type_stats,
                "key_insights": [
                    f"共收集{total_feedbacks}条反馈",
                    f"正面反馈占{sentiment_percentages['positive']}%",
                    f"负面反馈占{sentiment_percentages['negative']}%",
                    f"提到疗效的反馈有{len(efficacy_feedbacks)}条",
                    f"提到副作用的反馈有{len(side_effect_feedbacks)}条"
                ]
            },
            "detailed_feedback": {
                "efficacy": {
                    "count": len(efficacy_feedbacks),
                    "feedbacks": efficacy_feedbacks[:20]  # 限制数量
                },
                "side_effects": {
                    "count": len(side_effect_feedbacks),
                    "feedbacks": side_effect_feedbacks[:20]
                },
                "experience": {
                    "count": len(experience_feedbacks),
                    "feedbacks": experience_feedbacks[:20]
                },
                "price": {
                    "count": len(price_feedbacks),
                    "feedbacks": price_feedbacks[:20]
                }
            },
            "sources": sources if include_sources else [],
            "disclaimer": "本报告基于公开网络信息整理，仅供参考，不构成医疗建议。使用任何药物前请咨询专业医生。"
        }
        
        return json.dumps(report, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"报告生成失败: {str(e)}",
            "traceback": traceback.format_exc()
        }, ensure_ascii=False)


def _determine_overall_sentiment(sentiment_stats: Dict[str, int]) -> str:
    """根据情感统计确定整体情感倾向"""
    total = sum(sentiment_stats.values())
    if total == 0:
        return "neutral"
    
    positive_ratio = sentiment_stats["positive"] / total
    negative_ratio = sentiment_stats["negative"] / total
    
    if positive_ratio > 0.6:
        return "positive"
    elif negative_ratio > 0.6:
        return "negative"
    else:
        return "mixed"


# ==================== 工具6: 缓存管理工具 ====================

@tool
def check_cache(
    drug_name: str,
    cache_type: str = "report",
    max_age_days: int = 7
) -> str:
    """
    检查缓存是否存在且有效
    
    Args:
        drug_name (str): 药物名称
        cache_type (str): 缓存类型（search_results/report）
        max_age_days (int): 最大缓存天数
        
    Returns:
        str: JSON格式的缓存检查结果
    """
    try:
        # 生成缓存键
        cache_key = hashlib.sha256(drug_name.lower().strip().encode()).hexdigest()
        
        # 缓存目录
        cache_dir = Path(f".cache/drug_feedback_collector/{cache_key}")
        
        if not cache_dir.exists():
            return json.dumps({
                "status": "not_found",
                "cache_exists": False,
                "message": "缓存不存在"
            }, ensure_ascii=False)
        
        # 检查缓存文件
        cache_file = cache_dir / f"{cache_type}.json"
        
        if not cache_file.exists():
            return json.dumps({
                "status": "not_found",
                "cache_exists": False,
                "message": f"缓存文件不存在: {cache_type}.json"
            }, ensure_ascii=False)
        
        # 检查缓存时间
        cache_mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
        cache_age = datetime.now() - cache_mtime
        
        if cache_age.days > max_age_days:
            return json.dumps({
                "status": "expired",
                "cache_exists": True,
                "cache_age_days": cache_age.days,
                "max_age_days": max_age_days,
                "message": f"缓存已过期（{cache_age.days}天）"
            }, ensure_ascii=False)
        
        # 读取缓存
        with open(cache_file, 'r', encoding='utf-8') as f:
            cached_data = json.load(f)
        
        return json.dumps({
            "status": "valid",
            "cache_exists": True,
            "cache_age_days": cache_age.days,
            "cache_path": str(cache_file),
            "cached_data": cached_data,
            "message": "缓存有效"
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"缓存检查失败: {str(e)}",
            "traceback": traceback.format_exc()
        }, ensure_ascii=False)


@tool
def save_to_cache(
    drug_name: str,
    data: Dict[str, Any],
    cache_type: str = "report"
) -> str:
    """
    保存数据到缓存
    
    Args:
        drug_name (str): 药物名称
        data (Dict): 要缓存的数据
        cache_type (str): 缓存类型（search_results/report）
        
    Returns:
        str: JSON格式的保存结果
    """
    try:
        # 生成缓存键
        cache_key = hashlib.sha256(drug_name.lower().strip().encode()).hexdigest()
        
        # 创建缓存目录
        cache_dir = Path(f".cache/drug_feedback_collector/{cache_key}")
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存缓存文件
        cache_file = cache_dir / f"{cache_type}.json"
        
        # 添加元数据
        cache_data = {
            "drug_name": drug_name,
            "cache_type": cache_type,
            "cached_time": datetime.now().isoformat(),
            "data": data
        }
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        
        return json.dumps({
            "status": "success",
            "cache_path": str(cache_file),
            "cache_size": cache_file.stat().st_size,
            "message": "缓存保存成功"
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"缓存保存失败: {str(e)}",
            "traceback": traceback.format_exc()
        }, ensure_ascii=False)


@tool
def clear_cache(
    drug_name: str = None,
    older_than_days: int = None
) -> str:
    """
    清理缓存
    
    Args:
        drug_name (str): 特定药物名称，如果不提供则清理所有缓存
        older_than_days (int): 清理指定天数之前的缓存
        
    Returns:
        str: JSON格式的清理结果
    """
    try:
        cache_base_dir = Path(".cache/drug_feedback_collector")
        
        if not cache_base_dir.exists():
            return json.dumps({
                "status": "success",
                "message": "缓存目录不存在，无需清理",
                "deleted_count": 0
            }, ensure_ascii=False)
        
        deleted_count = 0
        deleted_items = []
        
        if drug_name:
            # 清理特定药物的缓存
            cache_key = hashlib.sha256(drug_name.lower().strip().encode()).hexdigest()
            cache_dir = cache_base_dir / cache_key
            
            if cache_dir.exists():
                import shutil
                shutil.rmtree(cache_dir)
                deleted_count = 1
                deleted_items.append(drug_name)
        else:
            # 清理所有缓存或过期缓存
            for cache_dir in cache_base_dir.iterdir():
                if cache_dir.is_dir():
                    should_delete = False
                    
                    if older_than_days is not None:
                        # 检查缓存年龄
                        report_file = cache_dir / "report.json"
                        if report_file.exists():
                            cache_mtime = datetime.fromtimestamp(report_file.stat().st_mtime)
                            cache_age = datetime.now() - cache_mtime
                            if cache_age.days > older_than_days:
                                should_delete = True
                    else:
                        # 清理所有缓存
                        should_delete = True
                    
                    if should_delete:
                        import shutil
                        shutil.rmtree(cache_dir)
                        deleted_count += 1
                        deleted_items.append(cache_dir.name)
        
        return json.dumps({
            "status": "success",
            "deleted_count": deleted_count,
            "deleted_items": deleted_items,
            "message": f"成功清理{deleted_count}个缓存项"
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"缓存清理失败: {str(e)}",
            "traceback": traceback.format_exc()
        }, ensure_ascii=False)


@tool
def get_cache_statistics() -> str:
    """
    获取缓存统计信息
    
    Returns:
        str: JSON格式的缓存统计
    """
    try:
        cache_base_dir = Path(".cache/drug_feedback_collector")
        
        if not cache_base_dir.exists():
            return json.dumps({
                "status": "success",
                "total_cached_drugs": 0,
                "total_cache_size": 0,
                "message": "缓存目录不存在"
            }, ensure_ascii=False)
        
        total_drugs = 0
        total_size = 0
        cache_items = []
        
        for cache_dir in cache_base_dir.iterdir():
            if cache_dir.is_dir():
                total_drugs += 1
                
                # 计算目录大小
                dir_size = sum(f.stat().st_size for f in cache_dir.rglob('*') if f.is_file())
                total_size += dir_size
                
                # 获取药物名称和缓存时间
                report_file = cache_dir / "report.json"
                if report_file.exists():
                    with open(report_file, 'r', encoding='utf-8') as f:
                        report_data = json.load(f)
                        cache_items.append({
                            "drug_name": report_data.get("drug_name", "unknown"),
                            "cached_time": report_data.get("cached_time", "unknown"),
                            "cache_size": dir_size,
                            "cache_key": cache_dir.name
                        })
        
        return json.dumps({
            "status": "success",
            "total_cached_drugs": total_drugs,
            "total_cache_size": total_size,
            "total_cache_size_mb": round(total_size / 1024 / 1024, 2),
            "cache_items": cache_items,
            "cache_base_dir": str(cache_base_dir)
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"缓存统计失败: {str(e)}",
            "traceback": traceback.format_exc()
        }, ensure_ascii=False)


# ==================== 辅助函数 ====================

def _format_markdown_report(report: Dict[str, Any]) -> str:
    """将报告转换为Markdown格式"""
    md = f"""# {report['report_metadata']['drug_name']} - 用户反馈报告

**生成时间**: {report['report_metadata']['generation_time']}  
**分析反馈数**: {report['report_metadata']['total_feedbacks_analyzed']}条

---

## 📊 整体评价

**总体情感倾向**: {report['summary']['overall_sentiment']}

### 情感分布
- 正面反馈: {report['summary']['sentiment_distribution']['positive']}
- 负面反馈: {report['summary']['sentiment_distribution']['negative']}
- 中性反馈: {report['summary']['sentiment_distribution']['neutral']}

### 关键洞察
"""
    for insight in report['summary']['key_insights']:
        md += f"- {insight}\n"
    
    md += "\n---\n\n## 💊 疗效反馈\n\n"
    efficacy = report['detailed_feedback']['efficacy']
    md += f"共{efficacy['count']}条反馈提到疗效\n\n"
    
    for i, feedback in enumerate(efficacy['feedbacks'][:10], 1):
        sentiment_emoji = "👍" if feedback['sentiment'] == "positive" else "👎" if feedback['sentiment'] == "negative" else "😐"
        md += f"{i}. {sentiment_emoji} {feedback['description']}\n"
        if feedback.get('source_url'):
            md += f"   - 来源: {feedback['source_url']}\n"
    
    md += "\n---\n\n## ⚠️ 副作用反馈\n\n"
    side_effects = report['detailed_feedback']['side_effects']
    md += f"共{side_effects['count']}条反馈提到副作用\n\n"
    
    for i, feedback in enumerate(side_effects['feedbacks'][:10], 1):
        md += f"{i}. {feedback['description']}\n"
        if feedback.get('source_url'):
            md += f"   - 来源: {feedback['source_url']}\n"
    
    md += "\n---\n\n## 💬 使用体验\n\n"
    experience = report['detailed_feedback']['experience']
    md += f"共{experience['count']}条反馈提到使用体验\n\n"
    
    for i, feedback in enumerate(experience['feedbacks'][:10], 1):
        sentiment_emoji = "👍" if feedback['sentiment'] == "positive" else "👎" if feedback['sentiment'] == "negative" else "😐"
        md += f"{i}. {sentiment_emoji} {feedback['description']}\n"
        if feedback.get('source_url'):
            md += f"   - 来源: {feedback['source_url']}\n"
    
    md += f"\n---\n\n## 📌 免责声明\n\n{report['disclaimer']}\n"
    
    return md


if __name__ == "__main__":
    print("🧪 测试药物反馈收集工具...")
    
    # 测试药物名称验证
    validation_result = validate_drug_name("阿司匹林")
    print("✅ 药物名称验证:", json.loads(validation_result)["standardized_name"])
    
    # 测试缓存统计
    stats_result = get_cache_statistics()
    print("📊 缓存统计:", json.loads(stats_result)["total_cached_drugs"])
    
    print("✅ 工具测试完成！")
