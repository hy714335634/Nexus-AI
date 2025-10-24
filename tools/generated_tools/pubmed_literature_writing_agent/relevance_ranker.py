#!/usr/bin/env python3
"""
Relevance Ranker Tool

提供计算文献相关性并排序的功能
使用多维度评分算法
"""

import json
import re
import math
from typing import Dict, List, Any, Optional, Union, Set, Tuple
import logging
from datetime import datetime
from collections import Counter

from strands import tool

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _calculate_term_frequency(text: str, term: str) -> float:
    """
    计算词频
    
    Args:
        text: 文本内容
        term: 搜索词
        
    Returns:
        词频
    """
    if not text or not term:
        return 0.0
    
    # 规范化文本和术语
    text_lower = text.lower()
    term_lower = term.lower()
    
    # 计算术语出现次数
    term_count = text_lower.count(term_lower)
    
    # 计算总词数
    total_words = len(text_lower.split())
    
    # 避免除以零
    if total_words == 0:
        return 0.0
    
    # 返回词频
    return term_count / total_words


def _calculate_keyword_position_score(text: str, term: str) -> float:
    """
    计算关键词位置得分
    
    Args:
        text: 文本内容
        term: 搜索词
        
    Returns:
        位置得分
    """
    if not text or not term:
        return 0.0
    
    # 规范化文本和术语
    text_lower = text.lower()
    term_lower = term.lower()
    
    # 查找术语位置
    position = text_lower.find(term_lower)
    
    # 如果没有找到，返回0
    if position == -1:
        return 0.0
    
    # 计算位置得分（越靠前得分越高）
    text_length = len(text_lower)
    if text_length == 0:
        return 0.0
    
    # 位置得分：1 - (位置 / 文本长度)
    position_score = 1.0 - (position / text_length)
    
    return position_score


def _calculate_field_weight(field_name: str) -> float:
    """
    计算字段权重
    
    Args:
        field_name: 字段名称
        
    Returns:
        字段权重
    """
    # 设置不同字段的权重
    field_weights = {
        "title": 5.0,
        "abstract": 3.0,
        "keywords": 4.0,
        "journal": 1.0,
        "authors": 1.0,
        "body_text": 2.0,
        "context": 2.5
    }
    
    # 返回字段权重，默认为1.0
    return field_weights.get(field_name, 1.0)


def _calculate_recency_score(year: Optional[int]) -> float:
    """
    计算时效性得分
    
    Args:
        year: 发表年份
        
    Returns:
        时效性得分
    """
    if year is None:
        return 0.5  # 默认中等时效性
    
    current_year = datetime.now().year
    years_diff = current_year - year
    
    # 计算时效性得分（越近得分越高）
    if years_diff <= 0:
        return 1.0  # 今年或未来（可能是预印本）
    elif years_diff <= 2:
        return 0.9  # 近2年
    elif years_diff <= 5:
        return 0.7  # 近5年
    elif years_diff <= 10:
        return 0.5  # 近10年
    else:
        return 0.3  # 10年以上


def _calculate_impact_factor_score(impact_factor: Optional[float]) -> float:
    """
    计算影响因子得分
    
    Args:
        impact_factor: 期刊影响因子
        
    Returns:
        影响因子得分
    """
    if impact_factor is None:
        return 0.5  # 默认中等影响力
    
    # 计算影响因子得分（使用对数缩放）
    if impact_factor <= 0:
        return 0.1
    elif impact_factor < 1:
        return 0.3
    elif impact_factor < 3:
        return 0.5
    elif impact_factor < 10:
        return 0.7
    else:
        return 0.9


def _calculate_citation_count_score(citation_count: Optional[int]) -> float:
    """
    计算引用次数得分
    
    Args:
        citation_count: 引用次数
        
    Returns:
        引用次数得分
    """
    if citation_count is None:
        return 0.5  # 默认中等引用
    
    # 计算引用次数得分（使用对数缩放）
    if citation_count <= 0:
        return 0.1
    elif citation_count < 10:
        return 0.3 + (citation_count / 10) * 0.2
    elif citation_count < 50:
        return 0.5 + ((citation_count - 10) / 40) * 0.2
    elif citation_count < 200:
        return 0.7 + ((citation_count - 50) / 150) * 0.2
    else:
        return 0.9


@tool
def calculate_relevance_score(article: Dict[str, Any], search_terms: List[str]) -> str:
    """
    计算单篇文章的相关性得分
    
    Args:
        article (Dict[str, Any]): 文章元数据
        search_terms (List[str]): 搜索词列表
        
    Returns:
        str: JSON格式的相关性得分
    """
    try:
        # 初始化得分
        relevance_scores = {
            "term_frequency": {},
            "position": {},
            "field_weights": {},
            "total_score": 0.0
        }
        
        # 需要评分的字段
        fields_to_score = ["title", "abstract", "keywords", "journal"]
        
        # 对每个搜索词计算得分
        for term in search_terms:
            term_scores = {}
            
            # 对每个字段计算得分
            for field in fields_to_score:
                if field in article and article[field]:
                    # 获取字段内容
                    field_content = article[field]
                    if isinstance(field_content, list):
                        field_content = " ".join(field_content)
                    
                    # 计算词频得分
                    tf_score = _calculate_term_frequency(field_content, term)
                    
                    # 计算位置得分
                    position_score = _calculate_keyword_position_score(field_content, term)
                    
                    # 获取字段权重
                    field_weight = _calculate_field_weight(field)
                    
                    # 计算加权得分
                    weighted_score = (tf_score * 0.6 + position_score * 0.4) * field_weight
                    
                    # 保存字段得分
                    term_scores[field] = {
                        "tf_score": tf_score,
                        "position_score": position_score,
                        "field_weight": field_weight,
                        "weighted_score": weighted_score
                    }
            
            # 保存搜索词得分
            relevance_scores["term_frequency"][term] = term_scores
        
        # 计算上下文得分
        context_score = 0.0
        if "context" in article and article["context"]:
            context_texts = article["context"]
            if isinstance(context_texts, list):
                for context in context_texts:
                    for term in search_terms:
                        if term.lower() in context.lower():
                            context_score += 0.5
            else:
                for term in search_terms:
                    if term.lower() in context_texts.lower():
                        context_score += 0.5
        
        # 计算时效性得分
        year = None
        if "year" in article:
            try:
                year = int(article["year"])
            except (ValueError, TypeError):
                pass
        elif "extracted_year" in article:
            year = article["extracted_year"]
        
        recency_score = _calculate_recency_score(year)
        
        # 计算影响因子得分
        impact_factor = article.get("impact_factor")
        impact_score = _calculate_impact_factor_score(impact_factor)
        
        # 计算引用次数得分
        citation_count = article.get("citation_count")
        citation_score = _calculate_citation_count_score(citation_count)
        
        # 计算总得分
        # 1. 术语匹配得分
        term_match_scores = []
        for term, fields in relevance_scores["term_frequency"].items():
            term_score = sum(field["weighted_score"] for field in fields.values())
            term_match_scores.append(term_score)
        
        # 如果有多个搜索词，取平均值
        avg_term_score = sum(term_match_scores) / len(term_match_scores) if term_match_scores else 0.0
        
        # 2. 组合所有维度的得分
        # 权重分配：术语匹配(50%), 上下文(20%), 时效性(15%), 影响因子(10%), 引用次数(5%)
        total_score = (
            avg_term_score * 0.5 +
            context_score * 0.2 +
            recency_score * 0.15 +
            impact_score * 0.1 +
            citation_score * 0.05
        )
        
        # 归一化总得分到0-100范围
        normalized_score = min(100, max(0, total_score * 100))
        
        # 添加维度得分
        relevance_scores["dimension_scores"] = {
            "term_match": avg_term_score * 100,
            "context": context_score * 100,
            "recency": recency_score * 100,
            "impact_factor": impact_score * 100,
            "citation": citation_score * 100
        }
        
        # 添加总得分
        relevance_scores["total_score"] = normalized_score
        
        return json.dumps({
            "status": "success",
            "article_id": article.get("pmcid", "unknown"),
            "article_title": article.get("title", "Untitled"),
            "relevance_scores": relevance_scores
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"计算相关性得分失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"计算相关性得分失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def rank_literature_by_relevance(literature_results: str, search_terms: List[str] = None) -> str:
    """
    按相关性对文献进行排序
    
    Args:
        literature_results (str): JSON格式的文献结果
        search_terms (List[str]): 搜索词列表，如果为None则从结果中提取
        
    Returns:
        str: JSON格式的排序结果
    """
    try:
        # 解析文献结果
        try:
            results = json.loads(literature_results)
        except json.JSONDecodeError:
            return json.dumps({
                "status": "error",
                "message": "无效的JSON格式文献结果"
            }, ensure_ascii=False)
        
        # 获取文献列表
        articles = []
        if "results" in results:
            articles = results["results"]
        
        # 如果没有提供搜索词，尝试从结果中提取
        if search_terms is None:
            search_terms = []
            
            # 从search_query中提取
            if "search_query" in results:
                query = results["search_query"]
                # 提取词语，排除常见的布尔操作符
                terms = re.findall(r'\b[a-zA-Z0-9]+\b', query)
                search_terms.extend([term for term in terms if term.lower() not in ["and", "or", "not"]])
            
            # 从topic中提取
            if "topic" in results:
                search_terms.append(results["topic"])
            
            # 从subtopics中提取
            if "subtopics" in results and isinstance(results["subtopics"], list):
                search_terms.extend(results["subtopics"])
        
        # 确保搜索词不为空
        if not search_terms:
            search_terms = ["research", "study"]  # 默认通用搜索词
        
        # 计算每篇文章的相关性得分
        for article in articles:
            # 计算相关性得分
            score_result = calculate_relevance_score(article, search_terms)
            
            try:
                score_data = json.loads(score_result)
                if score_data.get("status") == "success":
                    # 添加相关性得分到文章
                    article["relevance_score"] = score_data["relevance_scores"]["total_score"]
                    article["dimension_scores"] = score_data["relevance_scores"]["dimension_scores"]
            except Exception as e:
                logger.error(f"解析相关性得分失败: {str(e)}")
                article["relevance_score"] = 0.0
        
        # 按相关性得分排序
        sorted_articles = sorted(articles, key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        # 构建结果
        rank_result = {
            "status": "success",
            "ranking_method": "multi_dimensional_relevance",
            "search_terms": search_terms,
            "original_count": len(articles),
            "ranked_results": sorted_articles
        }
        
        # 保留原始查询信息
        for key in ["search_query", "topic", "subtopics", "directories_searched"]:
            if key in results:
                rank_result[key] = results[key]
        
        return json.dumps(rank_result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"按相关性排序失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"按相关性排序失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def rank_by_custom_criteria(literature_results: str, criteria: Dict[str, float]) -> str:
    """
    按自定义标准对文献进行排序
    
    Args:
        literature_results (str): JSON格式的文献结果
        criteria (Dict[str, float]): 排序标准和权重
            - relevance: 相关性权重
            - recency: 时效性权重
            - impact_factor: 影响因子权重
            - citation_count: 引用次数权重
        
    Returns:
        str: JSON格式的排序结果
    """
    try:
        # 解析文献结果
        try:
            results = json.loads(literature_results)
        except json.JSONDecodeError:
            return json.dumps({
                "status": "error",
                "message": "无效的JSON格式文献结果"
            }, ensure_ascii=False)
        
        # 获取文献列表
        articles = []
        if "results" in results:
            articles = results["results"]
        
        # 设置默认权重
        default_criteria = {
            "relevance": 0.5,
            "recency": 0.2,
            "impact_factor": 0.2,
            "citation_count": 0.1
        }
        
        # 合并用户提供的标准
        for key, value in criteria.items():
            if key in default_criteria:
                default_criteria[key] = value
        
        # 归一化权重
        total_weight = sum(default_criteria.values())
        if total_weight > 0:
            for key in default_criteria:
                default_criteria[key] /= total_weight
        
        # 计算每篇文章的综合得分
        for article in articles:
            # 1. 相关性得分
            relevance_score = article.get("relevance_score", 0.0)
            if relevance_score is None:
                relevance_score = 0.0
            
            # 2. 时效性得分
            year = None
            if "year" in article:
                try:
                    year = int(article["year"])
                except (ValueError, TypeError):
                    pass
            elif "extracted_year" in article:
                year = article["extracted_year"]
            
            recency_score = _calculate_recency_score(year) * 100
            
            # 3. 影响因子得分
            impact_factor = article.get("impact_factor")
            impact_score = _calculate_impact_factor_score(impact_factor) * 100
            
            # 4. 引用次数得分
            citation_count = article.get("citation_count")
            citation_score = _calculate_citation_count_score(citation_count) * 100
            
            # 计算综合得分
            combined_score = (
                relevance_score * default_criteria["relevance"] +
                recency_score * default_criteria["recency"] +
                impact_score * default_criteria["impact_factor"] +
                citation_score * default_criteria["citation_count"]
            )
            
            # 添加得分到文章
            article["custom_score"] = combined_score
            article["score_components"] = {
                "relevance": relevance_score,
                "recency": recency_score,
                "impact_factor": impact_score,
                "citation_count": citation_score
            }
        
        # 按综合得分排序
        sorted_articles = sorted(articles, key=lambda x: x.get("custom_score", 0), reverse=True)
        
        # 构建结果
        rank_result = {
            "status": "success",
            "ranking_method": "custom_criteria",
            "criteria": default_criteria,
            "original_count": len(articles),
            "ranked_results": sorted_articles
        }
        
        # 保留原始查询信息
        for key in ["search_query", "topic", "subtopics", "directories_searched"]:
            if key in results:
                rank_result[key] = results[key]
        
        return json.dumps(rank_result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"按自定义标准排序失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"按自定义标准排序失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def cluster_by_topic(literature_results: str, num_clusters: int = 3) -> str:
    """
    按主题对文献进行聚类
    
    Args:
        literature_results (str): JSON格式的文献结果
        num_clusters (int): 聚类数量
        
    Returns:
        str: JSON格式的聚类结果
    """
    try:
        # 解析文献结果
        try:
            results = json.loads(literature_results)
        except json.JSONDecodeError:
            return json.dumps({
                "status": "error",
                "message": "无效的JSON格式文献结果"
            }, ensure_ascii=False)
        
        # 获取文献列表
        articles = []
        if "results" in results:
            articles = results["results"]
        
        # 如果文章数量少于聚类数量，调整聚类数量
        if len(articles) < num_clusters:
            num_clusters = max(1, len(articles))
        
        # 提取文章的关键词和主题
        article_topics = []
        
        for article in articles:
            # 收集文章的所有文本内容
            text_content = []
            
            # 添加标题
            if "title" in article and article["title"]:
                text_content.append(article["title"])
            
            # 添加摘要
            if "abstract" in article and article["abstract"]:
                if isinstance(article["abstract"], list):
                    text_content.extend(article["abstract"])
                else:
                    text_content.append(article["abstract"])
            
            # 添加关键词
            if "keywords" in article and article["keywords"]:
                if isinstance(article["keywords"], list):
                    text_content.extend(article["keywords"])
                else:
                    text_content.append(article["keywords"])
            
            # 合并文本内容
            combined_text = " ".join(text_content)
            
            # 提取关键词
            words = re.findall(r'\b[a-zA-Z]{3,}\b', combined_text.lower())
            
            # 过滤常见停用词
            stop_words = {"the", "and", "for", "with", "that", "this", "was", "were", "are", "from", "have", "has", "had", "not", "but", "what", "all", "when", "where", "who", "which", "how", "why", "been", "being", "can", "may", "should", "would", "could", "did", "does", "doing", "done", "will", "shall", "should", "must", "might", "their", "they", "them", "these", "those", "there", "here", "then", "than", "thus", "though", "although", "however", "therefore", "hence", "thereby", "thereof", "therein", "thereon", "thereupon", "thereafter", "furthermore", "moreover", "nevertheless", "nonetheless", "notwithstanding", "consequently", "accordingly", "subsequently"}
            
            filtered_words = [word for word in words if word not in stop_words]
            
            # 计算词频
            word_counts = Counter(filtered_words)
            
            # 提取前10个高频词作为主题
            top_words = word_counts.most_common(10)
            
            article_topics.append({
                "article": article,
                "topics": [word for word, count in top_words]
            })
        
        # 简单聚类：基于主题词的重叠度
        clusters = []
        
        # 初始化聚类中心
        if article_topics:
            # 选择具有最多主题词的文章作为初始聚类中心
            sorted_by_topics = sorted(article_topics, key=lambda x: len(x["topics"]), reverse=True)
            
            # 选择前num_clusters个作为聚类中心
            centers = sorted_by_topics[:num_clusters]
            
            # 初始化聚类
            for i, center in enumerate(centers):
                clusters.append({
                    "cluster_id": i,
                    "center_article": center["article"].get("pmcid", f"article_{i}"),
                    "center_topics": center["topics"],
                    "articles": [center["article"]],
                    "member_topics": [center["topics"]]
                })
            
            # 分配其余文章到最相似的聚类
            for article_topic in article_topics:
                # 跳过已经作为中心的文章
                if article_topic["article"] in [center["article"] for center in centers]:
                    continue
                
                # 计算与每个聚类中心的相似度
                max_similarity = -1
                best_cluster = 0
                
                for i, cluster in enumerate(clusters):
                    # 计算主题词重叠度
                    overlap = set(article_topic["topics"]) & set(cluster["center_topics"])
                    similarity = len(overlap) / max(1, len(set(article_topic["topics"]) | set(cluster["center_topics"])))
                    
                    if similarity > max_similarity:
                        max_similarity = similarity
                        best_cluster = i
                
                # 将文章添加到最佳聚类
                clusters[best_cluster]["articles"].append(article_topic["article"])
                clusters[best_cluster]["member_topics"].append(article_topic["topics"])
        
        # 为每个聚类生成主题标签
        for cluster in clusters:
            # 收集聚类中所有文章的主题词
            all_topics = []
            for topics in cluster["member_topics"]:
                all_topics.extend(topics)
            
            # 计算主题词频率
            topic_counts = Counter(all_topics)
            
            # 提取前5个高频词作为聚类主题
            top_topics = topic_counts.most_common(5)
            cluster["cluster_topics"] = [topic for topic, count in top_topics]
            
            # 生成聚类标签
            if cluster["cluster_topics"]:
                cluster["cluster_label"] = ", ".join(cluster["cluster_topics"][:3])
            else:
                cluster["cluster_label"] = f"Cluster {cluster['cluster_id']}"
            
            # 添加文章数量
            cluster["article_count"] = len(cluster["articles"])
            
            # 移除中间数据
            del cluster["member_topics"]
        
        # 构建结果
        cluster_result = {
            "status": "success",
            "clustering_method": "topic_based",
            "num_clusters": len(clusters),
            "total_articles": len(articles),
            "clusters": clusters
        }
        
        # 保留原始查询信息
        for key in ["search_query", "topic", "subtopics", "directories_searched"]:
            if key in results:
                cluster_result[key] = results[key]
        
        return json.dumps(cluster_result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"按主题聚类失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"按主题聚类失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def get_top_ranked_literature(literature_results: str, top_n: int = 10) -> str:
    """
    获取排名前N的文献
    
    Args:
        literature_results (str): JSON格式的文献结果
        top_n (int): 返回的文献数量
        
    Returns:
        str: JSON格式的排名前N的文献
    """
    try:
        # 解析文献结果
        try:
            results = json.loads(literature_results)
        except json.JSONDecodeError:
            return json.dumps({
                "status": "error",
                "message": "无效的JSON格式文献结果"
            }, ensure_ascii=False)
        
        # 获取文献列表
        articles = []
        if "results" in results:
            articles = results["results"]
        elif "ranked_results" in results:
            articles = results["ranked_results"]
        
        # 确保top_n不超过文章数量
        top_n = min(top_n, len(articles))
        
        # 如果文章已经有相关性得分，按得分排序
        if any("relevance_score" in article for article in articles):
            sorted_articles = sorted(articles, key=lambda x: x.get("relevance_score", 0), reverse=True)
        elif any("custom_score" in article for article in articles):
            sorted_articles = sorted(articles, key=lambda x: x.get("custom_score", 0), reverse=True)
        else:
            # 没有得分，保持原始顺序
            sorted_articles = articles
        
        # 获取前N篇文章
        top_articles = sorted_articles[:top_n]
        
        # 构建结果
        top_result = {
            "status": "success",
            "top_n": top_n,
            "total_articles": len(articles),
            "top_articles": top_articles
        }
        
        # 保留原始查询信息
        for key in ["search_query", "topic", "subtopics", "directories_searched"]:
            if key in results:
                top_result[key] = results[key]
        
        return json.dumps(top_result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"获取排名前N的文献失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"获取排名前N的文献失败: {str(e)}"
        }, ensure_ascii=False)