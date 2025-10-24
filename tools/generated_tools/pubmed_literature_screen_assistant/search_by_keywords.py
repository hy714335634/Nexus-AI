#!/usr/bin/env python3
"""基于关键词查询PubMed/PMC文献库"""

import json
import os
import time
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import boto3
from botocore.config import Config
from botocore import UNSIGNED
from strands import tool

NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
PMC_BUCKET = "pmc-oa-opendata"
PMC_REGION = "us-east-1"


def _get_session():
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=0.5, status_forcelist=(429, 500, 502, 503, 504))
    session.mount("http://", HTTPAdapter(max_retries=retries))
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session


def _get_s3_client():
    return boto3.client('s3', region_name=PMC_REGION, config=Config(signature_version=UNSIGNED))


def _find_and_download_fulltext(s3_client, pmc_id: str, paper_dir: Path):
    """查找并下载TXT全文，返回摘要"""
    possible_paths = [
        f"oa_comm/txt/all/{pmc_id}.txt",
        f"oa_noncomm/txt/all/{pmc_id}.txt"
    ]
    
    for s3_key in possible_paths:
        try:
            cache_file = paper_dir / f"{pmc_id}.txt"
            s3_client.download_file(PMC_BUCKET, s3_key, str(cache_file))
            
            # 解析TXT提取摘要
            with open(cache_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 去除空行
            lines = [line for line in content.split('\n') if line.strip()]
            content = '\n'.join(lines)
            
            # 提取==== Front和==== Body之间的内容作为摘要
            if '==== Front' in content and '==== Body' in content:
                start = content.find('==== Front') + len('==== Front')
                end = content.find('==== Body')
                abstract = content[start:end].strip()
                return abstract
            
            return ""
        except:
            continue
    
    return ""


@tool
def search_by_keywords(keywords: str, research_id: str, max_results: int = 100) -> str:
    """
    基于关键词查询PubMed/PMC文献库，获取文献元数据、下载全文并提取摘要
    
    Args:
        keywords: 查询关键词
        research_id: 研究项目ID，用于组织缓存目录
        max_results: 最大返回结果数
        
    Returns:
        JSON字符串，包含文献ID列表和缓存状态
    """
    try:
        api_key = os.environ.get("NCBI_API_KEY", "")
        cache_dir = Path(f".cache/pmc_literature/{research_id}/meta_data")
        paper_dir = Path(f".cache/pmc_literature/{research_id}/paper")
        cache_dir.mkdir(parents=True, exist_ok=True)
        paper_dir.mkdir(parents=True, exist_ok=True)
        
        # 搜索PMC数据库
        params = {
            "db": "pmc",
            "term": keywords,
            "retmode": "json",
            "retmax": max_results,
            "sort": "relevance"
        }
        if api_key:
            params["api_key"] = api_key
            
        with _get_session() as s:
            r = s.get(f"{NCBI_BASE}/esearch.fcgi", params=params, timeout=(5, 15))
            r.raise_for_status()
            data = r.json()
        
        id_list = data.get("esearchresult", {}).get("idlist", [])
        pmc_ids = [f"PMC{id_val}" if not id_val.startswith("PMC") else id_val for id_val in id_list]
        
        if not pmc_ids:
            return json.dumps({"status": "success", "count": 0, "ids": [], "cached": []})
        
        # 批量获取元数据
        cached_ids = []
        batch_size = 200
        s3_client = _get_s3_client()
        
        for i in range(0, len(pmc_ids), batch_size):
            batch = pmc_ids[i:i+batch_size]
            batch_ids = [pid[3:] for pid in batch]
            
            params = {
                "db": "pmc",
                "id": ",".join(batch_ids),
                "retmode": "json"
            }
            if api_key:
                params["api_key"] = api_key
                
            r = s.get(f"{NCBI_BASE}/esummary.fcgi", params=params, timeout=(5, 15))
            r.raise_for_status()
            summary_data = r.json()
            
            uids = summary_data.get("result", {}).get("uids", [])
            for uid in uids:
                item = summary_data["result"].get(uid, {})
                pmcid = f"PMC{uid}"
                
                # 下载全文并提取摘要
                abstract = _find_and_download_fulltext(s3_client, pmcid, paper_dir)
                
                metadata = {
                    "pmcid": pmcid,
                    "title": item.get("title", ""),
                    "authors": [{"name": a.get("name", "")} for a in item.get("authors", [])],
                    "journal": item.get("fulljournalname", ""),
                    "publication_date": item.get("pubdate", ""),
                    "abstract": abstract
                }
                
                cache_file = cache_dir / f"{pmcid}.json"
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
                cached_ids.append(pmcid)
            
            if i + batch_size < len(pmc_ids):
                time.sleep(0.34)
        
        return json.dumps({
            "status": "success",
            "count": len(pmc_ids),
            "ids": pmc_ids,
            "cached": cached_ids
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)



@tool
def search_by_keywords(keywords: str, research_id: str, max_results: int = 100) -> str:
    """
    基于关键词查询PubMed/PMC文献库，获取文献元数据、下载全文并提取摘要
    
    Args:
        keywords: 查询关键词
        research_id: 研究项目ID，用于组织缓存目录
        max_results: 最大返回结果数
        
    Returns:
        JSON字符串，包含文献ID列表和缓存状态
    """
    try:
        api_key = os.environ.get("NCBI_API_KEY", "")
        cache_dir = Path(f".cache/pmc_literature/{research_id}/meta_data")
        paper_dir = Path(f".cache/pmc_literature/{research_id}/paper")
        cache_dir.mkdir(parents=True, exist_ok=True)
        paper_dir.mkdir(parents=True, exist_ok=True)
        
        # 搜索PMC数据库
        params = {
            "db": "pmc",
            "term": keywords,
            "retmode": "json",
            "retmax": max_results,
            "sort": "relevance"
        }
        if api_key:
            params["api_key"] = api_key
            
        with _get_session() as s:
            r = s.get(f"{NCBI_BASE}/esearch.fcgi", params=params, timeout=(5, 15))
            r.raise_for_status()
            data = r.json()
        
        id_list = data.get("esearchresult", {}).get("idlist", [])
        pmc_ids = [f"PMC{id_val}" if not id_val.startswith("PMC") else id_val for id_val in id_list]
        
        if not pmc_ids:
            return json.dumps({"status": "success", "count": 0, "ids": [], "cached": []})
        
        # 批量获取元数据
        cached_ids = []
        batch_size = 200
        s3_client = _get_s3_client()
        
        for i in range(0, len(pmc_ids), batch_size):
            batch = pmc_ids[i:i+batch_size]
            batch_ids = [pid[3:] for pid in batch]
            
            params = {
                "db": "pmc",
                "id": ",".join(batch_ids),
                "retmode": "json"
            }
            if api_key:
                params["api_key"] = api_key
                
            r = s.get(f"{NCBI_BASE}/esummary.fcgi", params=params, timeout=(5, 15))
            r.raise_for_status()
            summary_data = r.json()
            
            uids = summary_data.get("result", {}).get("uids", [])
            for uid in uids:
                item = summary_data["result"].get(uid, {})
                pmcid = f"PMC{uid}"
                
                # 下载全文并提取摘要
                abstract = _find_and_download_fulltext(s3_client, pmcid, paper_dir)
                
                metadata = {
                    "pmcid": pmcid,
                    "title": item.get("title", ""),
                    "authors": [{"name": a.get("name", "")} for a in item.get("authors", [])],
                    "journal": item.get("fulljournalname", ""),
                    "publication_date": item.get("pubdate", ""),
                    "abstract": abstract
                }
                
                cache_file = cache_dir / f"{pmcid}.json"
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
                cached_ids.append(pmcid)
            
            if i + batch_size < len(pmc_ids):
                time.sleep(0.34)
        
        return json.dumps({
            "status": "success",
            "count": len(pmc_ids),
            "ids": pmc_ids,
            "cached": cached_ids
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)

