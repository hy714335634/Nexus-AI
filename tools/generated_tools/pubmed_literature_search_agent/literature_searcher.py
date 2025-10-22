#!/usr/bin/env python3
"""
Literature Searcher Tool

提供基于关键词和主题的文献检索功能
支持高级搜索语法和布尔操作符
"""

import json
import re
import os
import csv
from typing import Dict, List, Any, Optional, Union, Set, Tuple
import logging
from pathlib import Path
import boto3
from botocore import UNSIGNED
from botocore.config import Config
from datetime import datetime
import time
import concurrent.futures

from strands import tool

# PubMed API 工具（用于检索与元数据）
try:
    from .pubmed_api_client import search_pubmed as api_search_pubmed
    from .pubmed_api_client import fetch_pubmed_summaries as api_fetch_pubmed_summaries
    from .pubmed_api_client import link_pmc_from_pmid as api_link_pmc_from_pmid
except Exception:
    api_search_pubmed = None
    api_fetch_pubmed_summaries = None
    api_link_pmc_from_pmid = None

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# PMC S3存储桶常量
PMC_BUCKET_NAME = "pmc-oa-opendata"
PMC_REGION = "us-east-1"
PMC_DIRECTORIES = ["oa_comm", "oa_noncomm", "phe_timebound"]
PMC_FORMATS = ["txt", "xml"]

# 本地缓存目录
CACHE_DIR = Path(".cache/pubmed_literature_agent")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 文件列表缓存
FILELIST_CACHE = {}


def _get_s3_client():
    """获取无签名S3客户端"""
    return boto3.client(
        's3',
        region_name=PMC_REGION,
        config=Config(signature_version=UNSIGNED)
    )


def _load_filelist(directory: str) -> List[Dict]:
    """
    加载并解析目录的filelist.csv
    
    Args:
        directory: PMC目录名称
        
    Returns:
        解析后的文件列表
    """
    # 检查缓存
    if directory in FILELIST_CACHE:
        return FILELIST_CACHE[directory]
    
    # 缓存文件路径
    cache_file = CACHE_DIR / f"{directory}_filelist.csv"
    
    # 如果缓存文件存在，从缓存加载
    if cache_file.exists():
        try:
            articles = []
            with open(cache_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader)  # 跳过标题行
                
                for row in reader:
                    if len(row) >= 2:  # 确保至少有文件名和PMCID
                        article = {
                            "file_name": row[0],
                            "pmcid": row[1]
                        }
                        
                        # 添加其他可用的元数据
                        if len(row) > 2 and row[2]:
                            article["pmid"] = row[2]
                        if len(row) > 3 and row[3]:
                            article["license"] = row[3]
                        
                        articles.append(article)
            
            # 保存到内存缓存
            FILELIST_CACHE[directory] = articles
            return articles
            
        except Exception as e:
            logger.error(f"从缓存加载filelist.csv失败: {str(e)}")
    
    # 如果缓存不存在，从S3下载
    try:
        s3_client = _get_s3_client()
        file_key = f"{directory}/filelist.csv"
        
        response = s3_client.get_object(
            Bucket=PMC_BUCKET_NAME,
            Key=file_key
        )
        
        content = response['Body'].read().decode('utf-8')
        
        # 保存到缓存
        with open(cache_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 解析CSV
        articles = []
        for i, line in enumerate(content.split('\n')):
            if i == 0:  # 跳过标题行
                continue
                
            row = line.split(',')
            if len(row) >= 2:  # 确保至少有文件名和PMCID
                article = {
                    "file_name": row[0],
                    "pmcid": row[1]
                }
                
                # 添加其他可用的元数据
                if len(row) > 2 and row[2]:
                    article["pmid"] = row[2]
                if len(row) > 3 and row[3]:
                    article["license"] = row[3]
                
                articles.append(article)
        
        # 保存到内存缓存
        FILELIST_CACHE[directory] = articles
        return articles
        
    except Exception as e:
        logger.error(f"从S3下载filelist.csv失败: {str(e)}")
        return []


def _download_article_content(directory: str, file_name: str, format_type: str = "xml") -> Optional[str]:
    """
    下载文章内容
    
    Args:
        directory: PMC目录名称
        file_name: 文件名
        format_type: 文件格式类型
        
    Returns:
        文章内容或None
    """
    try:
        # 构建文件键
        file_key = f"{directory}/{format_type}/{file_name}"
        
        # 检查缓存
        cache_file = CACHE_DIR / f"{file_name}"
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        
        # 从S3下载
        s3_client = _get_s3_client()
        
        try:
            response = s3_client.get_object(
                Bucket=PMC_BUCKET_NAME,
                Key=file_key
            )
            
            content = response['Body'].read().decode('utf-8', errors='ignore')
            
            # 保存到缓存
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return content
            
        except Exception as e:
            logger.error(f"下载文章内容失败: {str(e)}")
            return None
            
    except Exception as e:
        logger.error(f"处理文章内容失败: {str(e)}")
        return None


def _extract_basic_metadata(content: str, format_type: str) -> Dict:
    """
    从文章内容中提取基本元数据
    
    Args:
        content: 文章内容
        format_type: 内容格式类型
        
    Returns:
        基本元数据字典
    """
    metadata = {}
    
    try:
        if format_type == "xml":
            # 提取PMCID
            pmcid_match = re.search(r'<article-id pub-id-type="pmc">(PMC\d+)</article-id>', content)
            if pmcid_match:
                metadata["pmcid"] = pmcid_match.group(1)
            
            # 提取标题
            title_match = re.search(r'<article-title>(.*?)</article-title>', content)
            if title_match:
                metadata["title"] = title_match.group(1)
            
            # 提取摘要
            abstract_match = re.search(r'<abstract>(.*?)</abstract>', content, re.DOTALL)
            if abstract_match:
                # 移除HTML标签
                abstract_text = re.sub(r'<[^>]+>', ' ', abstract_match.group(1))
                abstract_text = re.sub(r'\s+', ' ', abstract_text).strip()
                metadata["abstract"] = abstract_text
            
            # 提取期刊
            journal_match = re.search(r'<journal-title>(.*?)</journal-title>', content)
            if journal_match:
                metadata["journal"] = journal_match.group(1)
            
            # 提取发布日期
            pub_date_match = re.search(r'<pub-date[^>]*>(.*?)</pub-date>', content, re.DOTALL)
            if pub_date_match:
                year_match = re.search(r'<year>(.*?)</year>', pub_date_match.group(1))
                if year_match:
                    metadata["year"] = year_match.group(1)
            
        elif format_type == "txt":
            # 提取PMCID
            pmcid_match = re.search(r'PMCID:\s*(PMC\d+)', content)
            if pmcid_match:
                metadata["pmcid"] = pmcid_match.group(1)
            
            # 提取标题 (假设标题在文件的开头几行)
            lines = content.split('\n')
            title_lines = []
            for i in range(min(5, len(lines))):
                if lines[i].strip() and not any(x in lines[i].lower() for x in ['pmcid', 'pmid', 'doi', 'copyright']):
                    title_lines.append(lines[i].strip())
            
            if title_lines:
                metadata["title"] = ' '.join(title_lines)
            
            # 提取摘要
            abstract_start = None
            abstract_end = None
            
            for i, line in enumerate(lines):
                if re.match(r'^ABSTRACT\s*:?$|^SUMMARY\s*:?$', line, re.IGNORECASE):
                    abstract_start = i + 1
                elif abstract_start and re.match(r'^INTRODUCTION|^BACKGROUND|^METHODS|^KEYWORDS', line, re.IGNORECASE):
                    abstract_end = i
                    break
            
            if abstract_start and not abstract_end:
                # 如果没有找到明确的结束，假设摘要最多10行
                abstract_end = abstract_start + 10
            
            if abstract_start and abstract_end:
                abstract_lines = []
                for i in range(abstract_start, abstract_end):
                    if i < len(lines) and lines[i].strip():
                        abstract_lines.append(lines[i].strip())
                
                if abstract_lines:
                    metadata["abstract"] = ' '.join(abstract_lines)
            
            # 提取期刊信息
            journal_match = re.search(r'([\w\s]+)\.\s*\d{4}\s*;', content)
            if journal_match:
                metadata["journal"] = journal_match.group(1).strip()
            
            # 提取年份
            year_match = re.search(r'\b(19|20)\d{2}\b', content)
            if year_match:
                metadata["year"] = year_match.group(0)
    
    except Exception as e:
        logger.error(f"提取元数据失败: {str(e)}")
    
    return metadata


@tool
def search_literature(keywords: str, directories: List[str] = None, max_results: int = 20, format_type: str = "xml", use_pubmed_api: bool = True) -> str:
    """
    基于关键词搜索文献
    
    Args:
        keywords (str): 搜索关键词，支持布尔操作符 (AND, OR, NOT)
        directories (List[str]): 要搜索的PMC目录列表
        max_results (int): 最大结果数量
        format_type (str): 文件格式类型 (xml, txt)
        
    Returns:
        str: JSON格式的搜索结果
    """
    try:
        # 默认搜索所有目录
        if directories is None:
            directories = PMC_DIRECTORIES
        else:
            # 验证目录
            for directory in directories:
                if directory not in PMC_DIRECTORIES:
                    return json.dumps({
                        "status": "error",
                        "message": f"无效的目录名称: {directory}。请使用以下之一: {', '.join(PMC_DIRECTORIES)}"
                    }, ensure_ascii=False)
        
        # 验证格式类型
        if format_type not in PMC_FORMATS:
            return json.dumps({
                "status": "error",
                "message": f"无效的格式类型。请使用以下之一: {', '.join(PMC_FORMATS)}"
            }, ensure_ascii=False)
        
        # 解析布尔操作符
        search_terms = []
        excluded_terms = []
        
        # 处理NOT操作符
        not_parts = keywords.split(" NOT ")
        if len(not_parts) > 1:
            keywords = not_parts[0]
            for part in not_parts[1:]:
                excluded_terms.extend([term.strip().lower() for term in part.split() if term.strip()])
        
        # 处理AND和OR操作符
        for term in keywords.split(" AND "):
            or_terms = term.split(" OR ")
            search_terms.append([t.strip().lower() for t in or_terms if t.strip()])
        
        # 如果启用 PubMed API，先走 API 流程（更高召回、更快）
        if use_pubmed_api and api_search_pubmed and api_fetch_pubmed_summaries:
            try:
                api_res = api_search_pubmed(keywords, retmax=max_results * 3)
                api_data = json.loads(api_res) if isinstance(api_res, str) else api_res
                id_list = api_data.get("ids", [])
                summaries_res = api_fetch_pubmed_summaries(id_list)
                summaries_data = json.loads(summaries_res) if isinstance(summaries_res, str) else summaries_res

                pmid_to_pmcid = {}
                try:
                    if api_link_pmc_from_pmid and id_list:
                        link_res = api_link_pmc_from_pmid(id_list)
                        link_data = json.loads(link_res) if isinstance(link_res, str) else link_res
                        mapping = link_data.get("mapping", {})
                        # mapping 形如 { pmid: pmcid or pmc link id }
                        pmid_to_pmcid = {str(k): str(v) for k, v in mapping.items()}
                except Exception:
                    pass

                results_from_api = []
                for item in summaries_data.get("results", []):
                    pmid = item.get("pmid")
                    pmcid = pmid_to_pmcid.get(str(pmid))
                    results_from_api.append({
                        "pmid": pmid,
                        "pmcid": pmcid,
                        "title": item.get("title", ""),
                        "abstract": item.get("abstract", ""),
                        "authors": item.get("authors", []),
                        "journal": item.get("journal", ""),
                        "publication_date": item.get("publication_date", ""),
                        "format": format_type,
                        "source": "pubmed_api"
                    })

                # 截断到 max_results
                return json.dumps({
                    "status": "success",
                    "search_query": keywords,
                    "directories_searched": directories,
                    "format": format_type,
                    "result_count": min(len(results_from_api), max_results),
                    "results": results_from_api[:max_results]
                }, ensure_ascii=False, indent=2)
            except Exception as _api_e:
                logger.warning(f"PubMed API 检索失败，回退到 S3 模式: {_api_e}")

        # 回退：S3 模式（本地采样+全文匹配）
        results = []
        
        # 对每个目录进行搜索
        for directory in directories:
            # 加载文件列表
            articles = _load_filelist(directory)
            
            # 随机抽样进行搜索（避免搜索全部文件）
            import random
            sample_size = min(1000, len(articles))
            sampled_articles = random.sample(articles, sample_size)
            
            # 创建线程池进行并行搜索
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                # 提交搜索任务
                future_to_article = {}
                for article in sampled_articles:
                    file_name = article["file_name"]
                    future = executor.submit(
                        _download_article_content, 
                        directory, 
                        file_name, 
                        format_type
                    )
                    future_to_article[future] = article
                
                # 处理搜索结果
                for future in concurrent.futures.as_completed(future_to_article):
                    article = future_to_article[future]
                    try:
                        content = future.result()
                        if content is None:
                            continue
                        
                        # 提取基本元数据
                        metadata = _extract_basic_metadata(content, format_type)
                        metadata.update(article)
                        metadata["directory"] = directory
                        metadata["format"] = format_type
                        
                        # 检查是否匹配搜索条件
                        content_lower = content.lower()
                        
                        # 检查是否包含所有必要的搜索词组（AND逻辑）
                        all_terms_matched = True
                        for or_group in search_terms:
                            # 检查OR组中是否至少有一个词匹配（OR逻辑）
                            or_matched = False
                            for term in or_group:
                                if term in content_lower:
                                    or_matched = True
                                    break
                            
                            if not or_matched:
                                all_terms_matched = False
                                break
                        
                        # 检查是否包含排除词
                        has_excluded_term = False
                        for term in excluded_terms:
                            if term in content_lower:
                                has_excluded_term = True
                                break
                        
                        # 如果匹配所有条件，添加到结果
                        if all_terms_matched and not has_excluded_term:
                            # 添加匹配上下文
                            context = []
                            for or_group in search_terms:
                                for term in or_group:
                                    # 查找术语上下文
                                    term_index = content_lower.find(term)
                                    if term_index >= 0:
                                        start = max(0, term_index - 50)
                                        end = min(len(content), term_index + len(term) + 50)
                                        context_text = content[start:end]
                                        # 突出显示术语
                                        highlight_term = content[term_index:term_index + len(term)]
                                        context_text = context_text.replace(highlight_term, f"**{highlight_term}**")
                                        context.append(context_text)
                            
                            if context:
                                metadata["context"] = context[:3]  # 最多显示3个上下文
                            
                            results.append(metadata)
                            
                            # 如果达到最大结果数，提前结束
                            if len(results) >= max_results:
                                break
                    
                    except Exception as e:
                        logger.error(f"处理文章失败: {str(e)}")
                
                # 如果达到最大结果数，提前结束
                if len(results) >= max_results:
                    break
        
        # 对结果进行排序（按相关性）
        def calculate_relevance(article):
            relevance = 0
            content_lower = ''.join([
                article.get("title", "").lower(),
                article.get("abstract", "").lower(),
                ' '.join(article.get("context", []).lower()) if isinstance(article.get("context"), list) else ""
            ])
            
            # 计算匹配的搜索词数量
            for or_group in search_terms:
                for term in or_group:
                    if term in content_lower:
                        # 标题匹配权重更高
                        if term in article.get("title", "").lower():
                            relevance += 5
                        # 摘要匹配
                        if term in article.get("abstract", "").lower():
                            relevance += 3
                        # 上下文匹配
                        if article.get("context") and any(term in ctx.lower() for ctx in article.get("context", [])):
                            relevance += 1
            
            return relevance
        
        results.sort(key=calculate_relevance, reverse=True)
        
        return json.dumps({
            "status": "success",
            "search_query": keywords,
            "directories_searched": directories,
            "format": format_type,
            "result_count": len(results),
            "results": results[:max_results]
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"搜索文献失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"搜索文献失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def search_by_topic(topic: str, subtopics: List[str] = None, max_results: int = 20, directories: List[str] = None) -> str:
    """
    基于主题和子主题搜索文献
    
    Args:
        topic (str): 主要研究主题
        subtopics (List[str]): 子主题列表
        max_results (int): 最大结果数量
        directories (List[str]): 要搜索的PMC目录列表
        
    Returns:
        str: JSON格式的搜索结果
    """
    try:
        # 构建搜索查询
        if subtopics and len(subtopics) > 0:
            # 使用主题和子主题构建查询
            query_parts = [topic]
            for subtopic in subtopics:
                query_parts.append(f"({topic} AND {subtopic})")
            
            search_query = " OR ".join(query_parts)
        else:
            # 仅使用主题
            search_query = topic
        
        # 执行搜索
        search_result = search_literature(
            keywords=search_query,
            directories=directories,
            max_results=max_results,
            format_type="xml"  # 默认使用XML格式获取更完整的元数据
        )
        
        # 解析搜索结果
        result_data = json.loads(search_result)
        
        # 如果搜索成功，添加主题信息
        if result_data.get("status") == "success":
            result_data["topic"] = topic
            result_data["subtopics"] = subtopics if subtopics else []
            
            # 对结果按主题相关性重新排序
            if "results" in result_data:
                def topic_relevance(article):
                    relevance = 0
                    content = ''.join([
                        article.get("title", "").lower(),
                        article.get("abstract", "").lower()
                    ])
                    
                    # 主题匹配
                    if topic.lower() in content:
                        relevance += 10
                    
                    # 子主题匹配
                    if subtopics:
                        for subtopic in subtopics:
                            if subtopic.lower() in content:
                                relevance += 5
                    
                    return relevance
                
                result_data["results"].sort(key=topic_relevance, reverse=True)
        
        return json.dumps(result_data, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"主题搜索失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"主题搜索失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def advanced_search(query_params: Dict[str, Any], max_results: int = 20) -> str:
    """
    高级文献搜索
    
    Args:
        query_params (Dict[str, Any]): 搜索参数
            - keywords (str): 关键词
            - title (str): 标题中包含的词
            - abstract (str): 摘要中包含的词
            - author (str): 作者名
            - journal (str): 期刊名
            - year_from (int): 起始年份
            - year_to (int): 结束年份
        max_results (int): 最大结果数量
        
    Returns:
        str: JSON格式的搜索结果
    """
    try:
        # 构建搜索查询
        search_parts = []
        
        # 处理关键词
        if "keywords" in query_params and query_params["keywords"]:
            search_parts.append(query_params["keywords"])
        
        # 构建布尔查询
        search_query = " AND ".join(search_parts) if search_parts else ""
        
        # 如果没有提供任何搜索条件
        if not search_query:
            return json.dumps({
                "status": "error",
                "message": "请提供至少一个搜索条件"
            }, ensure_ascii=False)
        
        # 执行基本搜索
        search_result = search_literature(
            keywords=search_query,
            max_results=max_results * 2,  # 获取更多结果用于后处理筛选
            format_type="xml"  # 默认使用XML格式获取更完整的元数据
        )
        
        # 解析搜索结果
        result_data = json.loads(search_result)
        
        # 如果搜索成功，进行后处理筛选
        if result_data.get("status") == "success" and "results" in result_data:
            filtered_results = []
            
            for article in result_data["results"]:
                # 标题筛选
                if "title" in query_params and query_params["title"] and article.get("title"):
                    if query_params["title"].lower() not in article["title"].lower():
                        continue
                
                # 摘要筛选
                if "abstract" in query_params and query_params["abstract"] and article.get("abstract"):
                    if query_params["abstract"].lower() not in article["abstract"].lower():
                        continue
                
                # 作者筛选
                if "author" in query_params and query_params["author"] and article.get("authors"):
                    author_match = False
                    for author in article["authors"]:
                        if isinstance(author, dict) and "full_name" in author:
                            if query_params["author"].lower() in author["full_name"].lower():
                                author_match = True
                                break
                    if not author_match:
                        continue
                
                # 期刊筛选
                if "journal" in query_params and query_params["journal"] and article.get("journal"):
                    if query_params["journal"].lower() not in article["journal"].lower():
                        continue
                
                # 年份筛选
                if "year_from" in query_params and query_params["year_from"] and article.get("year"):
                    try:
                        if int(article["year"]) < int(query_params["year_from"]):
                            continue
                    except (ValueError, TypeError):
                        pass
                
                if "year_to" in query_params and query_params["year_to"] and article.get("year"):
                    try:
                        if int(article["year"]) > int(query_params["year_to"]):
                            continue
                    except (ValueError, TypeError):
                        pass
                
                # 通过所有筛选，添加到结果
                filtered_results.append(article)
                
                # 如果达到最大结果数，提前结束
                if len(filtered_results) >= max_results:
                    break
            
            # 更新结果
            result_data["results"] = filtered_results
            result_data["result_count"] = len(filtered_results)
            result_data["search_params"] = query_params
        
        return json.dumps(result_data, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"高级搜索失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"高级搜索失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def batch_search(queries: List[str], max_results_per_query: int = 10) -> str:
    """
    批量搜索多个查询
    
    Args:
        queries (List[str]): 查询列表
        max_results_per_query (int): 每个查询的最大结果数量
        
    Returns:
        str: JSON格式的批量搜索结果
    """
    try:
        # 验证输入
        if not queries or not isinstance(queries, list):
            return json.dumps({
                "status": "error",
                "message": "请提供有效的查询列表"
            }, ensure_ascii=False)
        
        # 批量执行搜索
        batch_results = []
        
        for i, query in enumerate(queries):
            logger.info(f"执行批量搜索 {i+1}/{len(queries)}: {query}")
            
            # 执行搜索
            search_result = search_literature(
                keywords=query,
                max_results=max_results_per_query,
                format_type="xml"  # 默认使用XML格式获取更完整的元数据
            )
            
            # 解析搜索结果
            result_data = json.loads(search_result)
            
            # 添加查询信息
            result_data["query_index"] = i
            result_data["query"] = query
            
            batch_results.append(result_data)
            
            # 避免请求过于频繁
            if i < len(queries) - 1:
                time.sleep(1)
        
        # 汇总结果
        total_results = sum(result["result_count"] for result in batch_results if result.get("status") == "success")
        
        return json.dumps({
            "status": "success",
            "total_queries": len(queries),
            "total_results": total_results,
            "batch_results": batch_results
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"批量搜索失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"批量搜索失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def search_by_pmcid(pmcids: List[str]) -> str:
    """
    通过PMCID列表搜索文献
    
    Args:
        pmcids (List[str]): PMCID列表
        
    Returns:
        str: JSON格式的搜索结果
    """
    try:
        # 验证输入
        if not pmcids or not isinstance(pmcids, list):
            return json.dumps({
                "status": "error",
                "message": "请提供有效的PMCID列表"
            }, ensure_ascii=False)
        
        # 规范化PMCID
        normalized_pmcids = []
        for pmcid in pmcids:
            if not pmcid.startswith("PMC"):
                normalized_pmcids.append(f"PMC{pmcid}")
            else:
                normalized_pmcids.append(pmcid)
        
        # 搜索结果
        results = []
        
        # 对每个目录进行搜索
        for directory in PMC_DIRECTORIES:
            # 加载文件列表
            articles = _load_filelist(directory)
            
            # 查找匹配的文章
            for article in articles:
                if article.get("pmcid") in normalized_pmcids:
                    # 下载文章内容
                    content = _download_article_content(directory, article["file_name"], "xml")
                    
                    if content:
                        # 提取元数据
                        metadata = _extract_basic_metadata(content, "xml")
                        metadata.update(article)
                        metadata["directory"] = directory
                        metadata["format"] = "xml"
                        
                        results.append(metadata)
                        
                        # 从待查找列表中移除已找到的PMCID
                        normalized_pmcids.remove(article.get("pmcid"))
                        
                        # 如果所有PMCID都已找到，提前结束
                        if not normalized_pmcids:
                            break
            
            # 如果所有PMCID都已找到，提前结束
            if not normalized_pmcids:
                break
        
        # 返回结果
        return json.dumps({
            "status": "success",
            "requested_pmcids": pmcids,
            "found_count": len(results),
            "not_found": normalized_pmcids,
            "results": results
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"通过PMCID搜索失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"通过PMCID搜索失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def get_search_statistics() -> str:
    """
    获取搜索统计信息
    
    Returns:
        str: JSON格式的搜索统计信息
    """
    try:
        stats = {
            "cache_status": {
                "directory": str(CACHE_DIR),
                "exists": CACHE_DIR.exists(),
                "file_count": len(list(CACHE_DIR.glob('*'))) if CACHE_DIR.exists() else 0
            },
            "filelist_cache": {
                "directories": list(FILELIST_CACHE.keys()),
                "total_articles": sum(len(articles) for articles in FILELIST_CACHE.values())
            },
            "available_directories": PMC_DIRECTORIES,
            "available_formats": PMC_FORMATS
        }
        
        # 如果有文件列表缓存，提供更详细的统计信息
        if FILELIST_CACHE:
            directory_stats = []
            
            for directory, articles in FILELIST_CACHE.items():
                # 计算每个目录的文章数量
                directory_stats.append({
                    "directory": directory,
                    "article_count": len(articles),
                    "has_pmid": sum(1 for a in articles if "pmid" in a),
                    "has_license": sum(1 for a in articles if "license" in a)
                })
            
            stats["directory_statistics"] = directory_stats
        
        return json.dumps({
            "status": "success",
            "statistics": stats
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"获取搜索统计信息失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"获取搜索统计信息失败: {str(e)}"
        }, ensure_ascii=False)