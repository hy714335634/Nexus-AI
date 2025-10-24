#!/usr/bin/env python3
"""
PubMed API Client Tools

提供基于 NCBI E-utilities 的 PubMed 检索与摘要获取能力：
- ESearch: 按查询获取PMID列表
- ESummary: 批量获取文献概要元数据
- ELink: 从PMID映射到PMCID（如可用）

注意：该工具仅用于“检索与元数据”，全文获取请通过 S3 的 PMC 开放数据完成。
"""

import json
import os
import time
from typing import List, Dict, Any
import logging

from strands import tool

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
DEFAULT_TIMEOUT = (5, 15)  # (connect, read)


def _get_session() -> requests.Session:
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


@tool
def search_pubmed(query: str, retmax: int = 200, retstart: int = 0, sort: str = "relevance", database: str = "pubmed") -> str:
    """
    使用 ESearch 按查询检索 PubMed 或 PMC 数据库，返回ID列表及总量。
    
    Args:
        query (str): 搜索查询
        retmax (int): 最大返回结果数
        retstart (int): 起始位置
        sort (str): 排序方式
        database (str): 数据库类型 ("pubmed" 或 "pmc")
    """
    try:
        # 验证数据库参数
        if database not in ["pubmed", "pmc"]:
            return json.dumps({
                "status": "error", 
                "message": "数据库参数必须是 'pubmed' 或 'pmc'"
            }, ensure_ascii=False)
        
        params = {
            "db": database,
            "term": query,
            "retmode": "json",
            "retmax": max(1, min(retmax, 10000)),
            "retstart": max(0, retstart),
            "sort": sort,
        }
        api_key = os.environ.get("NCBI_API_KEY")
        if api_key:
            params["api_key"] = api_key
        
        with _get_session() as s:
            r = s.get(f"{NCBI_BASE}/esearch.fcgi", params=params, timeout=DEFAULT_TIMEOUT)
            r.raise_for_status()
            data = r.json()
        
        id_list = data.get("esearchresult", {}).get("idlist", [])
        count = int(data.get("esearchresult", {}).get("count", 0))
        
        # 规范化PMC ID格式
        if database == "pmc":
            normalized_ids = []
            for id_val in id_list:
                if not id_val.startswith("PMC"):
                    normalized_ids.append(f"PMC{id_val}")
                else:
                    normalized_ids.append(id_val)
            id_list = normalized_ids
        
        return json.dumps({
            "status": "success",
            "query": query,
            "database": database,
            "count": count,
            "ids": id_list
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"ESearch失败: {e}")
        return json.dumps({"status": "error", "message": f"ESearch失败: {e}"}, ensure_ascii=False)


@tool
def fetch_pubmed_summaries(id_list: List[str], database: str = "pubmed") -> str:
    """
    使用 ESummary 批量获取文献概要（标题、作者、期刊、日期等）。
    
    **注意：ESummary API不返回摘要和作者信息**。如需获取摘要，请使用：
    1. fetch_pubmed_abstracts() - 使用EFetch获取摘要
    2. 从PMC S3获取全文 - 使用pmc_get_article_by_id()等工具
    
    Args:
        id_list (List[str]): ID列表
        database (str): 数据库类型 ("pubmed" 或 "pmc")
    """
    try:
        if not id_list:
            return json.dumps({"status": "success", "results": []}, ensure_ascii=False)

        # 验证数据库参数
        if database not in ["pubmed", "pmc"]:
            return json.dumps({
                "status": "error", 
                "message": "数据库参数必须是 'pubmed' 或 'pmc'"
            }, ensure_ascii=False)

        # 对于PMC数据库，需要移除PMC前缀
        if database == "pmc":
            processed_ids = []
            for id_val in id_list:
                if id_val.startswith("PMC"):
                    processed_ids.append(id_val[3:])  # 移除PMC前缀
                else:
                    processed_ids.append(id_val)
            id_list = processed_ids

        # ESummary 支持批量，分批以避免URL过长
        batch_size = 200
        results: List[Dict[str, Any]] = []
        api_key = os.environ.get("NCBI_API_KEY")
        with _get_session() as s:
            for i in range(0, len(id_list), batch_size):
                batch = id_list[i:i+batch_size]
                params = {
                    "db": database,
                    "id": ",".join(batch),
                    "retmode": "json",
                }
                if api_key:
                    params["api_key"] = api_key
                r = s.get(f"{NCBI_BASE}/esummary.fcgi", params=params, timeout=DEFAULT_TIMEOUT)
                r.raise_for_status()
                data = r.json()
                uids = data.get("result", {}).get("uids", [])
                for uid in uids:
                    item = data["result"].get(uid, {})
                    authors = [
                        {"full_name": a.get("name", "")} for a in item.get("authors", []) if a.get("name")
                    ]
                    pubdate = item.get("pubdate") or item.get("sortpubdate") or ""
                    journal = item.get("fulljournalname") or item.get("source") or ""
                    
                    # 构建结果
                    result_item = {
                        "title": item.get("title", ""),
                        "authors": authors,
                        "journal": journal,
                        "publication_date": pubdate,
                    }
                    
                    # 根据数据库类型设置ID字段
                    if database == "pubmed":
                        result_item["pmid"] = uid
                    else:  # pmc
                        result_item["pmcid"] = f"PMC{uid}"  # 重新添加PMC前缀
                    # ESummary不返回摘要，设置为空字符串
                    result_item["abstract"] = ""
                    
                    results.append(result_item)
                
                # 友好限速
                if i + batch_size < len(id_list):
                    time.sleep(0.34)

        return json.dumps({"status": "success", "results": results}, ensure_ascii=False)
    except Exception as e:
        logger.error(f"ESummary失败: {e}")
        return json.dumps({"status": "error", "message": f"ESummary失败: {e}"}, ensure_ascii=False)


@tool
def fetch_pubmed_abstracts(id_list: List[str], database: str = "pubmed") -> str:
    """
    使用 EFetch 获取文献的摘要信息。
    
    Args:
        id_list (List[str]): ID列表
        database (str): 数据库类型 ("pubmed" 或 "pmc")
    """
    try:
        if not id_list:
            return json.dumps({"status": "success", "results": []}, ensure_ascii=False)

        # 验证数据库参数
        if database not in ["pubmed", "pmc"]:
            return json.dumps({
                "status": "error", 
                "message": "数据库参数必须是 'pubmed' 或 'pmc'"
            }, ensure_ascii=False)

        # 对于PMC数据库，需要移除PMC前缀
        if database == "pmc":
            processed_ids = []
            for id_val in id_list:
                if id_val.startswith("PMC"):
                    processed_ids.append(id_val[3:])  # 移除PMC前缀
                else:
                    processed_ids.append(id_val)
            id_list = processed_ids

        # EFetch 支持批量，分批以避免URL过长
        batch_size = 200
        results: List[Dict[str, Any]] = []
        api_key = os.environ.get("NCBI_API_KEY")
        
        with _get_session() as s:
            for i in range(0, len(id_list), batch_size):
                batch = id_list[i:i+batch_size]
                params = {
                    "db": database,
                    "id": ",".join(batch),
                    "rettype": "abstract",
                    "retmode": "xml",
                }
                if api_key:
                    params["api_key"] = api_key
                
                r = s.get(f"{NCBI_BASE}/efetch.fcgi", params=params, timeout=DEFAULT_TIMEOUT)
                r.raise_for_status()
                xml_content = r.text
                
                # 解析XML获取摘要
                import xml.etree.ElementTree as ET
                try:
                    root = ET.fromstring(xml_content)
                    for article in root.findall(".//PubmedArticle"):
                        pmid_elem = article.find(".//PMID")
                        pmid = pmid_elem.text if pmid_elem is not None else ""
                        
                        abstract_elem = article.find(".//AbstractText")
                        abstract = abstract_elem.text if abstract_elem is not None else ""
                        
                        if pmid:
                            results.append({
                                "pmid": pmid if database == "pubmed" else f"PMC{pmid}",
                                "abstract": abstract
                            })
                except ET.ParseError:
                    logger.warning("无法解析EFetch XML响应")
                
                # 友好限速
                if i + batch_size < len(id_list):
                    time.sleep(0.34)

        return json.dumps({"status": "success", "results": results}, ensure_ascii=False)
    except Exception as e:
        logger.error(f"EFetch失败: {e}")
        return json.dumps({"status": "error", "message": f"EFetch失败: {e}"}, ensure_ascii=False)


@tool
def link_pmc_from_pmid(id_list: List[str]) -> str:
    """
    使用 ELink 从 PMID 映射到 PMCID（如可用）。
    """
    try:
        mapping: Dict[str, str] = {}
        if not id_list:
            return json.dumps({"status": "success", "mapping": mapping}, ensure_ascii=False)

        batch_size = 200
        api_key = os.environ.get("NCBI_API_KEY")
        with _get_session() as s:
            for i in range(0, len(id_list), batch_size):
                batch = id_list[i:i+batch_size]
                params = {
                    "dbfrom": "pubmed",
                    "db": "pmc",
                    "retmode": "json",
                    "id": ",".join(batch),
                }
                if api_key:
                    params["api_key"] = api_key
                r = s.get(f"{NCBI_BASE}/elink.fcgi", params=params, timeout=DEFAULT_TIMEOUT)
                r.raise_for_status()
                data = r.json()
                linksets = data.get("linksets", [])
                for ls in linksets:
                    pmid = (ls.get("ids") or [None])[0]
                    for lr in ls.get("linksetdbs", []) or []:
                        if lr.get("dbto") == "pmc":
                            links = lr.get("links", [])
                            if links:
                                mapping[str(pmid)] = links[0]
                if i + batch_size < len(id_list):
                    time.sleep(0.34)

        return json.dumps({"status": "success", "mapping": mapping}, ensure_ascii=False)
    except Exception as e:
        logger.error(f"ELink失败: {e}")
        return json.dumps({"status": "error", "message": f"ELink失败: {e}"}, ensure_ascii=False)


