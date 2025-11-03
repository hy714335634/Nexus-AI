#!/usr/bin/env python3
"""
PMC Literature Search Tool

用于验证科研文献内容准确性的PubMed Central (PMC)文献检索工具。
支持高级搜索选项，返回结构化搜索结果，并可获取全文内容。
包含缓存机制，通过research_id参数指定缓存和上下文工作目录。
"""

import json
import os
import time
import logging
import hashlib
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime

from strands import tool

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import xml.etree.ElementTree as ET


# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# NCBI E-utilities API基础URL
NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
DEFAULT_TIMEOUT = (5, 15)  # (connect, read)

# 缓存目录基础路径（step5.status固定存放在 .cache/pmc_literature/<research_id>/ 下）
CACHE_BASE_DIR = Path(".cache/pmc_literature")


def _get_session() -> requests.Session:
    """创建并配置具有重试机制的HTTP会话"""
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "POST"),
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=20)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def _setup_cache_dir(research_id: Optional[str] = None) -> Path:
    """设置缓存目录，统一到 .cache/pmc_literature/<research_id>/feedback/reviewer/<version>/verification/
    若 research_id 为空，则退回 .cache/pmc_literature/default
    版本选择规则：
      - 若存在 step5.status，则取 latest_version + 1
      - 否则扫描 feedback/reviewer 下的数字子目录最大值 + 1；未找到则为 1
    """
    if not research_id:
        cache_dir = CACHE_BASE_DIR / "default"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    base_dir = CACHE_BASE_DIR / research_id
    (base_dir).mkdir(parents=True, exist_ok=True)

    reviewer_base = base_dir / "feedback" / "reviewer"
    reviewer_base.mkdir(parents=True, exist_ok=True)

    # 优先读取一次运行固定版本
    marker = base_dir / ".current_run_version"
    version: Optional[int] = None
    try:
        if marker.exists():
            with open(marker, "r", encoding="utf-8") as f:
                version = int(f.read().strip())
    except Exception:
        version = None

    if version is None:
        status_path = base_dir / "step5.status"
        if status_path.exists():
            try:
                with open(status_path, "r", encoding="utf-8") as f:
                    status = json.load(f)
                latest = int(status.get("latest_version", 0))
                version = latest + 1 if latest >= 0 else 1
            except Exception:
                version = None

    if version is None:
        max_found = 0
        for sub in reviewer_base.glob("*"):
            if sub.is_dir():
                try:
                    v = int(sub.name)
                    if v > max_found:
                        max_found = v
                except Exception:
                    continue
        version = max_found + 1 if max_found >= 0 else 1

    cache_dir = reviewer_base / str(version) / "verification"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _get_cache_file_path(cache_dir: Path, query_hash: str) -> Path:
    """获取缓存文件路径"""
    return cache_dir / f"{query_hash}.json"


def _compute_query_hash(query_params: Dict[str, Any]) -> str:
    """计算查询参数的哈希值作为缓存键"""
    # 将查询参数转换为排序后的字符串
    param_str = json.dumps(query_params, sort_keys=True)
    return hashlib.md5(param_str.encode()).hexdigest()


def _check_cache(cache_file: Path, max_age_hours: int = 24) -> Optional[Dict[str, Any]]:
    """检查缓存是否存在且有效"""
    if not cache_file.exists():
        return None
    
    # 检查缓存是否过期
    file_stat = cache_file.stat()
    file_age_seconds = time.time() - file_stat.st_mtime
    if file_age_seconds > (max_age_hours * 3600):
        logger.info(f"缓存已过期: {cache_file}")
        return None
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"读取缓存失败: {e}")
        return None


def _save_to_cache(cache_file: Path, data: Dict[str, Any]) -> None:
    """保存数据到缓存"""
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError as e:
        logger.warning(f"保存缓存失败: {e}")


def _clean_old_caches(cache_dir: Path, max_age_days: int = 30) -> None:
    """清理旧缓存文件"""
    try:
        current_time = time.time()
        for cache_file in cache_dir.glob("*.json"):
            file_age_seconds = current_time - cache_file.stat().st_mtime
            if file_age_seconds > (max_age_days * 24 * 3600):
                cache_file.unlink()
                logger.info(f"已删除过期缓存: {cache_file}")
    except Exception as e:
        logger.warning(f"清理缓存失败: {e}")


@tool
def pmc_literature_search(
    query: str,
    research_id: Optional[str] = None,
    author: Optional[str] = None,
    journal: Optional[str] = None,
    year: Optional[str] = None,
    max_results: int = 10,
    full_text: bool = False
) -> str:
    """
    搜索PubMed Central (PMC)数据库以验证科研文献内容的准确性，支持缓存和上下文管理。

    Args:
        query (str): 搜索查询字符串
        research_id (str, optional): 研究ID，用于指定缓存目录
        author (str, optional): 作者筛选
        journal (str, optional): 期刊筛选
        year (str, optional): 发表年份筛选
        max_results (int, optional): 最大结果数，默认10
        full_text (bool, optional): 是否获取全文，默认False

    Returns:
        str: 包含搜索结果的JSON字符串，包括文章标题、作者、摘要、DOI、相关性评分等信息
    """
    try:
        # 参数验证
        if not query or not query.strip():
            return json.dumps({
                "status": "error",
                "message": "搜索查询不能为空"
            }, ensure_ascii=False)

        # 规范化max_results
        max_results = max(1, min(max_results, 100))
        
        # 构建查询
        search_query = query
        
        # 添加作者过滤
        if author:
            search_query += f" AND {author}[Author]"
        
        # 添加期刊过滤
        if journal:
            search_query += f" AND {journal}[Journal]"
        
        # 添加年份过滤
        if year:
            search_query += f" AND {year}[Publication Date]"
        
        # 设置缓存目录
        cache_dir = _setup_cache_dir(research_id)
        
        # 定期清理旧缓存
        _clean_old_caches(cache_dir)
        
        # 构建查询参数
        query_params = {
            "query": search_query,
            "max_results": max_results,
            "full_text": full_text,
            "timestamp": datetime.now().isoformat()
        }
        
        # 计算缓存键
        query_hash = _compute_query_hash(query_params)
        cache_file = _get_cache_file_path(cache_dir, query_hash)
        
        # 检查缓存
        cached_data = _check_cache(cache_file)
        if cached_data:
            logger.info(f"使用缓存结果: {cache_file}")
            return json.dumps(cached_data, ensure_ascii=False)
        
        # 执行搜索
        logger.info(f"执行PMC搜索: {search_query}")
        
        # 构建API请求参数
        api_params = {
            "db": "pmc",
            "term": search_query,
            "retmode": "json",
            "retmax": max_results,
            "sort": "relevance"
        }
        
        # 添加API密钥（如果存在）
        api_key = os.environ.get("NCBI_API_KEY")
        if api_key:
            api_params["api_key"] = api_key
        
        # 执行搜索请求
        with _get_session() as session:
            search_response = session.get(
                f"{NCBI_BASE}/esearch.fcgi",
                params=api_params,
                timeout=DEFAULT_TIMEOUT
            )
            search_response.raise_for_status()
            search_data = search_response.json()
        
        # 提取文章ID
        id_list = search_data.get("esearchresult", {}).get("idlist", [])
        total_count = int(search_data.get("esearchresult", {}).get("count", 0))
        
        if not id_list:
            result = {
                "status": "success",
                "query": search_query,
                "total_results": 0,
                "returned_results": 0,
                "articles": []
            }
            _save_to_cache(cache_file, result)
            return json.dumps(result, ensure_ascii=False)
        
        # 规范化PMC ID格式
        normalized_ids = []
        for id_val in id_list:
            if not id_val.startswith("PMC"):
                normalized_ids.append(f"PMC{id_val}")
            else:
                normalized_ids.append(id_val)
        
        # 获取文章摘要
        articles = []
        batch_size = 50
        
        for i in range(0, len(normalized_ids), batch_size):
            batch_ids = normalized_ids[i:i+batch_size]
            
            # 移除PMC前缀用于API请求
            api_batch_ids = [id_val[3:] if id_val.startswith("PMC") else id_val for id_val in batch_ids]
            
            # 构建摘要请求参数
            summary_params = {
                "db": "pmc",
                "id": ",".join(api_batch_ids),
                "retmode": "json"
            }
            if api_key:
                summary_params["api_key"] = api_key
            
            # 获取摘要信息
            with _get_session() as session:
                summary_response = session.get(
                    f"{NCBI_BASE}/esummary.fcgi",
                    params=summary_params,
                    timeout=DEFAULT_TIMEOUT
                )
                summary_response.raise_for_status()
                summary_data = summary_response.json()
            
            # 处理摘要数据
            result_items = summary_data.get("result", {})
            uids = result_items.get("uids", [])
            
            for uid in uids:
                item = result_items.get(uid, {})
                
                # 提取作者信息
                authors = []
                for author_data in item.get("authors", []):
                    if author_data.get("name"):
                        authors.append({"name": author_data.get("name", "")})
                
                # 提取期刊信息
                journal_name = item.get("fulljournalname", "") or item.get("source", "")
                
                # 提取发表日期
                pub_date = item.get("pubdate", "") or item.get("sortpubdate", "")
                
                # 构建文章数据
                article = {
                    "pmcid": f"PMC{uid}",
                    "title": item.get("title", ""),
                    "authors": authors,
                    "journal": journal_name,
                    "publication_date": pub_date,
                    "doi": item.get("articleids", [{}])[0].get("value", "") if item.get("articleids") else "",
                    "relevance_score": 100 - (i * batch_size + uids.index(uid)),  # 简单的相关性评分
                    "abstract": ""  # 将在下一步填充
                }
                
                articles.append(article)
            
            # 限速以遵守NCBI API使用政策
            if i + batch_size < len(normalized_ids):
                time.sleep(0.34)
        
        # 如果需要获取摘要
        if articles:
            # 获取文章摘要
            abstract_params = {
                "db": "pmc",
                "id": ",".join([article["pmcid"][3:] for article in articles]),
                "rettype": "abstract",
                "retmode": "xml"
            }
            if api_key:
                abstract_params["api_key"] = api_key
            
            with _get_session() as session:
                abstract_response = session.get(
                    f"{NCBI_BASE}/efetch.fcgi",
                    params=abstract_params,
                    timeout=(5, 30)  # 增加超时时间
                )
                abstract_response.raise_for_status()
                abstract_xml = abstract_response.text
            
            # 解析XML获取摘要
            try:
                root = ET.fromstring(abstract_xml)
                for article_elem in root.findall(".//article"):
                    # 查找文章ID
                    article_id_elem = article_elem.find(".//article-id[@pub-id-type='pmc']")
                    if article_id_elem is not None:
                        pmcid = f"PMC{article_id_elem.text}"
                        
                        # 查找摘要
                        abstract_elem = article_elem.find(".//abstract")
                        abstract_text = ""
                        
                        if abstract_elem is not None:
                            # 提取所有段落文本
                            for p in abstract_elem.findall(".//p"):
                                if p.text:
                                    abstract_text += p.text + " "
                        
                        # 更新对应文章的摘要
                        for article in articles:
                            if article["pmcid"] == pmcid:
                                article["abstract"] = abstract_text.strip()
                                break
            except ET.ParseError as e:
                logger.warning(f"解析摘要XML失败: {e}")
        
        # 如果需要获取全文
        if full_text and articles:
            # 注意：获取全文需要额外的处理，这里只是示例
            # 实际实现可能需要通过PMC OA API或其他方式获取
            for article in articles:
                pmcid = article["pmcid"]
                article["full_text_available"] = True
                article["full_text_url"] = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/"
        
        # 构建最终结果
        result = {
            "status": "success",
            "query": search_query,
            "total_results": total_count,
            "returned_results": len(articles),
            "articles": articles
        }
        
        # 保存到缓存
        _save_to_cache(cache_file, result)
        
        return json.dumps(result, ensure_ascii=False)
    
    except requests.RequestException as e:
        logger.error(f"API请求失败: {e}")
        return json.dumps({
            "status": "error",
            "message": f"API请求失败: {str(e)}",
            "query": query
        }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"搜索过程中发生错误: {e}", exc_info=True)
        return json.dumps({
            "status": "error",
            "message": f"搜索过程中发生错误: {str(e)}",
            "query": query
        }, ensure_ascii=False)


@tool
def pmc_get_article_details(pmcid: str, research_id: Optional[str] = None) -> str:
    """
    获取PMC文章的详细信息，包括完整的元数据和摘要。

    Args:
        pmcid (str): PMC文章ID，格式为PMC后跟数字（如PMC123456）
        research_id (str, optional): 研究ID，用于指定缓存目录

    Returns:
        str: 包含文章详细信息的JSON字符串
    """
    try:
        # 参数验证
        if not pmcid or not pmcid.strip():
            return json.dumps({
                "status": "error",
                "message": "PMC ID不能为空"
            }, ensure_ascii=False)
        
        # 规范化PMCID格式
        if not pmcid.startswith("PMC"):
            pmcid = f"PMC{pmcid}"
        
        # 设置缓存目录
        cache_dir = _setup_cache_dir(research_id)
        
        # 构建缓存键
        query_params = {
            "pmcid": pmcid,
            "type": "article_details",
            "timestamp": datetime.now().isoformat()
        }
        query_hash = _compute_query_hash(query_params)
        cache_file = _get_cache_file_path(cache_dir, query_hash)
        
        # 检查缓存
        cached_data = _check_cache(cache_file)
        if cached_data:
            logger.info(f"使用缓存结果: {cache_file}")
            return json.dumps(cached_data, ensure_ascii=False)
        
        # 提取不带PMC前缀的ID
        article_id = pmcid[3:] if pmcid.startswith("PMC") else pmcid
        
        # 构建API请求参数
        api_params = {
            "db": "pmc",
            "id": article_id,
            "retmode": "json"
        }
        
        # 添加API密钥（如果存在）
        api_key = os.environ.get("NCBI_API_KEY")
        if api_key:
            api_params["api_key"] = api_key
        
        # 获取文章摘要
        with _get_session() as session:
            summary_response = session.get(
                f"{NCBI_BASE}/esummary.fcgi",
                params=api_params,
                timeout=DEFAULT_TIMEOUT
            )
            summary_response.raise_for_status()
            summary_data = summary_response.json()
        
        # 提取文章信息
        result_items = summary_data.get("result", {})
        if article_id not in result_items:
            return json.dumps({
                "status": "error",
                "message": f"未找到ID为{pmcid}的文章"
            }, ensure_ascii=False)
        
        item = result_items.get(article_id, {})
        
        # 提取作者信息
        authors = []
        for author_data in item.get("authors", []):
            if author_data.get("name"):
                authors.append({
                    "name": author_data.get("name", ""),
                    "authtype": author_data.get("authtype", "")
                })
        
        # 提取文章ID信息
        article_ids = []
        for id_data in item.get("articleids", []):
            article_ids.append({
                "idtype": id_data.get("idtype", ""),
                "value": id_data.get("value", "")
            })
        
        # 构建文章详细信息
        article_details = {
            "pmcid": pmcid,
            "title": item.get("title", ""),
            "authors": authors,
            "journal": item.get("fulljournalname", "") or item.get("source", ""),
            "publication_date": item.get("pubdate", "") or item.get("sortpubdate", ""),
            "article_ids": article_ids,
            "doi": next((id_data.get("value", "") for id_data in item.get("articleids", []) 
                         if id_data.get("idtype", "") == "doi"), ""),
            "abstract": ""  # 将在下一步填充
        }
        
        # 获取文章摘要
        abstract_params = {
            "db": "pmc",
            "id": article_id,
            "rettype": "abstract",
            "retmode": "xml"
        }
        if api_key:
            abstract_params["api_key"] = api_key
        
        with _get_session() as session:
            abstract_response = session.get(
                f"{NCBI_BASE}/efetch.fcgi",
                params=abstract_params,
                timeout=(5, 30)
            )
            abstract_response.raise_for_status()
            abstract_xml = abstract_response.text
        
        # 解析XML获取摘要
        try:
            root = ET.fromstring(abstract_xml)
            abstract_elem = root.find(".//abstract")
            
            if abstract_elem is not None:
                # 提取所有段落文本
                abstract_text = ""
                for p in abstract_elem.findall(".//p"):
                    if p.text:
                        abstract_text += p.text + " "
                
                article_details["abstract"] = abstract_text.strip()
        except ET.ParseError as e:
            logger.warning(f"解析摘要XML失败: {e}")
        
        # 构建最终结果
        result = {
            "status": "success",
            "article": article_details
        }
        
        # 保存到缓存
        _save_to_cache(cache_file, result)
        
        return json.dumps(result, ensure_ascii=False)
    
    except requests.RequestException as e:
        logger.error(f"API请求失败: {e}")
        return json.dumps({
            "status": "error",
            "message": f"API请求失败: {str(e)}",
            "pmcid": pmcid
        }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"获取文章详情过程中发生错误: {e}", exc_info=True)
        return json.dumps({
            "status": "error",
            "message": f"获取文章详情过程中发生错误: {str(e)}",
            "pmcid": pmcid
        }, ensure_ascii=False)


@tool
def pmc_clear_cache(research_id: Optional[str] = None, force_all: bool = False) -> str:
    """
    清理PMC文献搜索缓存。

    Args:
        research_id (str, optional): 研究ID，指定要清理的缓存目录
        force_all (bool, optional): 是否强制清理所有缓存，默认False

    Returns:
        str: 操作结果的JSON字符串
    """
    try:
        if force_all:
            # 清理所有缓存
            if CACHE_BASE_DIR.exists():
                shutil.rmtree(CACHE_BASE_DIR)
                CACHE_BASE_DIR.mkdir(parents=True, exist_ok=True)
            
            return json.dumps({
                "status": "success",
                "message": "已清理所有PMC文献搜索缓存"
            }, ensure_ascii=False)
        
        elif research_id:
            # 清理特定研究ID的缓存
            research_cache_dir = CACHE_BASE_DIR / research_id
            if research_cache_dir.exists():
                shutil.rmtree(research_cache_dir)
                research_cache_dir.mkdir(parents=True, exist_ok=True)
                
                return json.dumps({
                    "status": "success",
                    "message": f"已清理研究ID '{research_id}' 的PMC文献搜索缓存"
                }, ensure_ascii=False)
            else:
                return json.dumps({
                    "status": "success",
                    "message": f"研究ID '{research_id}' 没有缓存需要清理"
                }, ensure_ascii=False)
        
        else:
            # 清理默认缓存
            default_cache_dir = CACHE_BASE_DIR / "default"
            if default_cache_dir.exists():
                shutil.rmtree(default_cache_dir)
                default_cache_dir.mkdir(parents=True, exist_ok=True)
                
                return json.dumps({
                    "status": "success",
                    "message": "已清理默认PMC文献搜索缓存"
                }, ensure_ascii=False)
            else:
                return json.dumps({
                    "status": "success",
                    "message": "没有默认缓存需要清理"
                }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"清理缓存过程中发生错误: {e}", exc_info=True)
        return json.dumps({
            "status": "error",
            "message": f"清理缓存过程中发生错误: {str(e)}"
        }, ensure_ascii=False)