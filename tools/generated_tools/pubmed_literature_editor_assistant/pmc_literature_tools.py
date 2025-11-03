#!/usr/bin/env python3
"""
PMC文献工具集

提供PubMed Central (PMC)文献检索、元数据解析、内容提取和文件管理功能：
- PMC文献检索：搜索PMC数据库获取相关文献
- 文献元数据解析：解析文献的标题、作者、摘要等元数据
- 文献内容提取：获取文献全文或特定部分内容
- 文件系统操作：管理工作目录和缓存
- JSON处理：生成结构化输出

注意：工具支持research_id参数，用于指定缓存和工作目录
"""

import json
import os
import time
import re
import shutil
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple
import xml.etree.ElementTree as ET

from strands import tool

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# NCBI E-utilities API基础URL
NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
DEFAULT_TIMEOUT = (5, 15)  # (connect, read)

# PMC开放数据S3基础URL
PMC_S3_BASE = "https://ftp.ncbi.nlm.nih.gov/pub/pmc"


def _get_session() -> requests.Session:
    """创建一个具有重试机制的请求会话"""
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


def _ensure_directory(path: str) -> str:
    """确保目录存在，如果不存在则创建"""
    os.makedirs(path, exist_ok=True)
    return path


def _get_cache_dir(research_id: str, version: str = "v1") -> str:
    """获取缓存目录路径"""
    cache_dir = f".cache/pmc_literature/{research_id}/feedback/editor/{version}"
    return _ensure_directory(cache_dir)


def _get_verification_dir(research_id: str, version: str = "v1") -> str:
    """获取验证目录路径"""
    verification_dir = f".cache/pmc_literature/{research_id}/feedback/editor/{version}/verification"
    return _ensure_directory(verification_dir)


def _get_status_file_path(research_id: str) -> str:
    """获取状态文件路径"""
    status_dir = f".cache/pmc_literature/{research_id}"
    _ensure_directory(status_dir)
    return os.path.join(status_dir, "step6.status")


def _update_status(research_id: str, status: str, progress: int, current_step: str, result_path: str = "") -> None:
    """更新处理状态文件"""
    status_file = _get_status_file_path(research_id)
    status_data = {
        "research_id": research_id,
        "status": status,  # "started", "in_progress", "completed", "failed"
        "progress": progress,  # 0-100
        "current_step": current_step,
        "result_path": result_path,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(status_data, f, ensure_ascii=False, indent=2)


def _get_status(research_id: str) -> Dict[str, Any]:
    """获取处理状态"""
    status_file = _get_status_file_path(research_id)
    if os.path.exists(status_file):
        try:
            with open(status_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"读取状态文件失败: {e}")
            return {"status": "unknown", "error": str(e)}
    return {"status": "not_started"}


@tool
def search_pmc_literature(query: str, research_id: str, max_results: int = 50, version: str = "v1") -> str:
    """
    搜索PMC文献库，获取与查询相关的文献列表
    
    Args:
        query (str): 搜索查询字符串
        research_id (str): 研究ID，用于指定缓存和工作目录
        max_results (int): 最大返回结果数，默认50
        version (str): 版本号，默认v1
        
    Returns:
        str: JSON格式的搜索结果，包含文献ID列表和元数据
    """
    try:
        # 更新状态为开始
        _update_status(research_id, "started", 0, "搜索PMC文献")
        
        # 创建缓存目录
        cache_dir = _get_cache_dir(research_id, version)
        verification_dir = _get_verification_dir(research_id, version)
        
        # 缓存文件路径
        cache_file = os.path.join(verification_dir, f"search_results_{hashlib.md5(query.encode()).hexdigest()}.json")
        
        # 检查缓存
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                logger.info(f"从缓存加载搜索结果: {cache_file}")
                _update_status(research_id, "completed", 100, "从缓存加载搜索结果", cache_file)
                return json.load(f)
        
        # 构建API请求参数
        params = {
            "db": "pmc",
            "term": query,
            "retmode": "json",
            "retmax": max(1, min(max_results, 1000)),
            "retstart": 0,
            "sort": "relevance",
        }
        
        # 添加API密钥（如果有）
        api_key = os.environ.get("NCBI_API_KEY")
        if api_key:
            params["api_key"] = api_key
        
        # 发送请求
        _update_status(research_id, "in_progress", 20, "发送PMC搜索请求")
        with _get_session() as s:
            r = s.get(f"{NCBI_BASE}/esearch.fcgi", params=params, timeout=DEFAULT_TIMEOUT)
            r.raise_for_status()
            data = r.json()
        
        # 解析结果
        id_list = data.get("esearchresult", {}).get("idlist", [])
        count = int(data.get("esearchresult", {}).get("count", 0))
        
        # 规范化PMC ID格式
        normalized_ids = []
        for id_val in id_list:
            if not id_val.startswith("PMC"):
                normalized_ids.append(f"PMC{id_val}")
            else:
                normalized_ids.append(id_val)
        
        _update_status(research_id, "in_progress", 40, "获取文献摘要")
        
        # 获取文献摘要和元数据
        results = []
        if normalized_ids:
            # 分批处理ID
            batch_size = 20
            for i in range(0, len(normalized_ids), batch_size):
                batch = normalized_ids[i:i+batch_size]
                # 移除PMC前缀用于API调用
                processed_ids = [id_val[3:] if id_val.startswith("PMC") else id_val for id_val in batch]
                
                # 获取摘要
                params = {
                    "db": "pmc",
                    "id": ",".join(processed_ids),
                    "rettype": "abstract",
                    "retmode": "xml",
                }
                if api_key:
                    params["api_key"] = api_key
                
                progress = 40 + int((i / len(normalized_ids)) * 50)
                _update_status(research_id, "in_progress", progress, f"获取批次 {i//batch_size + 1}/{(len(normalized_ids)-1)//batch_size + 1} 的摘要")
                
                with _get_session() as s:
                    r = s.get(f"{NCBI_BASE}/efetch.fcgi", params=params, timeout=DEFAULT_TIMEOUT)
                    r.raise_for_status()
                    xml_content = r.text
                
                # 解析XML获取摘要
                try:
                    root = ET.fromstring(xml_content)
                    for article in root.findall(".//article"):
                        # 提取PMCID
                        pmcid_elem = article.find(".//article-id[@pub-id-type='pmc']")
                        pmcid = f"PMC{pmcid_elem.text}" if pmcid_elem is not None else ""
                        
                        # 提取标题
                        title_elem = article.find(".//article-title")
                        title = "".join(title_elem.itertext()) if title_elem is not None else ""
                        
                        # 提取作者
                        authors = []
                        for author_elem in article.findall(".//contrib[@contrib-type='author']"):
                            surname = author_elem.find(".//surname")
                            given_names = author_elem.find(".//given-names")
                            if surname is not None and given_names is not None:
                                authors.append({
                                    "surname": surname.text,
                                    "given_names": given_names.text,
                                    "full_name": f"{given_names.text} {surname.text}"
                                })
                        
                        # 提取摘要
                        abstract = ""
                        abstract_elem = article.find(".//abstract")
                        if abstract_elem is not None:
                            abstract = " ".join("".join(p.itertext()) for p in abstract_elem.findall(".//p"))
                        
                        # 提取期刊信息
                        journal_elem = article.find(".//journal-title")
                        journal = journal_elem.text if journal_elem is not None else ""
                        
                        # 提取发布日期
                        pub_date = ""
                        pub_date_elem = article.find(".//pub-date")
                        if pub_date_elem is not None:
                            year = pub_date_elem.find("year")
                            month = pub_date_elem.find("month")
                            day = pub_date_elem.find("day")
                            if year is not None:
                                pub_date = year.text
                                if month is not None:
                                    pub_date = f"{pub_date}-{month.text}"
                                    if day is not None:
                                        pub_date = f"{pub_date}-{day.text}"
                        
                        # 添加到结果列表
                        if pmcid:
                            results.append({
                                "pmcid": pmcid,
                                "title": title,
                                "authors": authors,
                                "abstract": abstract,
                                "journal": journal,
                                "publication_date": pub_date
                            })
                except ET.ParseError as e:
                    logger.warning(f"无法解析EFetch XML响应: {e}")
                
                # 友好限速
                if i + batch_size < len(normalized_ids):
                    time.sleep(0.34)
        
        # 准备结果
        search_results = {
            "status": "success",
            "query": query,
            "count": count,
            "results": results
        }
        
        # 缓存结果
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(search_results, f, ensure_ascii=False, indent=2)
        
        # 更新状态为完成
        _update_status(research_id, "completed", 100, "PMC搜索完成", cache_file)
        
        return json.dumps(search_results, ensure_ascii=False)
    except Exception as e:
        logger.error(f"PMC搜索失败: {e}")
        _update_status(research_id, "failed", 0, f"PMC搜索失败: {e}")
        return json.dumps({
            "status": "error", 
            "message": f"PMC搜索失败: {e}"
        }, ensure_ascii=False)


@tool
def extract_pmc_metadata(pmcid: str, research_id: str, version: str = "v1") -> str:
    """
    从PMC ID提取文献元数据
    
    Args:
        pmcid (str): PMC ID，格式为PMC加数字（例如PMC1234567）
        research_id (str): 研究ID，用于指定缓存和工作目录
        version (str): 版本号，默认v1
        
    Returns:
        str: JSON格式的文献元数据
    """
    try:
        # 规范化PMCID
        if not pmcid.startswith("PMC"):
            pmcid = f"PMC{pmcid}"
        
        # 更新状态
        _update_status(research_id, "in_progress", 0, f"提取文献元数据: {pmcid}")
        
        # 创建缓存目录
        verification_dir = _get_verification_dir(research_id, version)
        
        # 缓存文件路径
        cache_file = os.path.join(verification_dir, f"{pmcid}_metadata.json")
        
        # 检查缓存
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                logger.info(f"从缓存加载元数据: {cache_file}")
                _update_status(research_id, "completed", 100, f"从缓存加载元数据: {pmcid}", cache_file)
                return json.load(f)
        
        # 移除PMC前缀用于API调用
        id_for_api = pmcid[3:] if pmcid.startswith("PMC") else pmcid
        
        # 构建API请求参数
        params = {
            "db": "pmc",
            "id": id_for_api,
            "rettype": "full",
            "retmode": "xml",
        }
        
        # 添加API密钥（如果有）
        api_key = os.environ.get("NCBI_API_KEY")
        if api_key:
            params["api_key"] = api_key
        
        # 发送请求
        _update_status(research_id, "in_progress", 30, f"获取{pmcid}的XML数据")
        with _get_session() as s:
            r = s.get(f"{NCBI_BASE}/efetch.fcgi", params=params, timeout=DEFAULT_TIMEOUT)
            r.raise_for_status()
            xml_content = r.text
        
        # 解析XML获取元数据
        _update_status(research_id, "in_progress", 60, f"解析{pmcid}的XML数据")
        try:
            root = ET.fromstring(xml_content)
            
            # 提取文章元数据
            article = root.find(".//article")
            if article is None:
                raise ValueError(f"未找到文章数据: {pmcid}")
            
            # 提取PMCID
            pmcid_elem = article.find(".//article-id[@pub-id-type='pmc']")
            pmcid_value = f"PMC{pmcid_elem.text}" if pmcid_elem is not None else pmcid
            
            # 提取PMID（如果有）
            pmid_elem = article.find(".//article-id[@pub-id-type='pmid']")
            pmid = pmid_elem.text if pmid_elem is not None else ""
            
            # 提取DOI（如果有）
            doi_elem = article.find(".//article-id[@pub-id-type='doi']")
            doi = doi_elem.text if doi_elem is not None else ""
            
            # 提取标题
            title_elem = article.find(".//article-title")
            title = "".join(title_elem.itertext()) if title_elem is not None else ""
            
            # 提取作者
            authors = []
            for author_elem in article.findall(".//contrib[@contrib-type='author']"):
                surname = author_elem.find(".//surname")
                given_names = author_elem.find(".//given-names")
                if surname is not None and given_names is not None:
                    authors.append({
                        "surname": surname.text,
                        "given_names": given_names.text,
                        "full_name": f"{given_names.text} {surname.text}"
                    })
            
            # 提取摘要
            abstract = ""
            abstract_elem = article.find(".//abstract")
            if abstract_elem is not None:
                abstract = " ".join("".join(p.itertext()) for p in abstract_elem.findall(".//p"))
            
            # 提取期刊信息
            journal_elem = article.find(".//journal-title")
            journal = journal_elem.text if journal_elem is not None else ""
            
            # 提取发布日期
            pub_date = ""
            pub_date_elem = article.find(".//pub-date")
            if pub_date_elem is not None:
                year = pub_date_elem.find("year")
                month = pub_date_elem.find("month")
                day = pub_date_elem.find("day")
                if year is not None:
                    pub_date = year.text
                    if month is not None:
                        pub_date = f"{pub_date}-{month.text}"
                        if day is not None:
                            pub_date = f"{pub_date}-{day.text}"
            
            # 提取关键词
            keywords = []
            for kwd_elem in article.findall(".//kwd"):
                if kwd_elem.text:
                    keywords.append(kwd_elem.text)
            
            # 提取引用数量
            ref_count = len(article.findall(".//ref"))
            
            # 准备元数据结果
            metadata = {
                "pmcid": pmcid_value,
                "pmid": pmid,
                "doi": doi,
                "title": title,
                "authors": authors,
                "abstract": abstract,
                "journal": journal,
                "publication_date": pub_date,
                "keywords": keywords,
                "reference_count": ref_count
            }
            
            # 缓存结果
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            # 更新状态为完成
            _update_status(research_id, "completed", 100, f"元数据提取完成: {pmcid}", cache_file)
            
            return json.dumps(metadata, ensure_ascii=False)
        except ET.ParseError as e:
            logger.error(f"解析XML失败: {e}")
            _update_status(research_id, "failed", 0, f"解析XML失败: {e}")
            return json.dumps({
                "status": "error", 
                "message": f"解析XML失败: {e}"
            }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"提取元数据失败: {e}")
        _update_status(research_id, "failed", 0, f"提取元数据失败: {e}")
        return json.dumps({
            "status": "error", 
            "message": f"提取元数据失败: {e}"
        }, ensure_ascii=False)


@tool
def extract_pmc_content(pmcid: str, research_id: str, section: str = "full", version: str = "v1") -> str:
    """
    从PMC提取文献内容
    
    Args:
        pmcid (str): PMC ID，格式为PMC加数字（例如PMC1234567）
        research_id (str): 研究ID，用于指定缓存和工作目录
        section (str): 要提取的部分，可选值：full（全文）、abstract（摘要）、introduction（引言）、
                      methods（方法）、results（结果）、discussion（讨论）、conclusion（结论）
        version (str): 版本号，默认v1
        
    Returns:
        str: JSON格式的文献内容
    """
    try:
        # 规范化PMCID
        if not pmcid.startswith("PMC"):
            pmcid = f"PMC{pmcid}"
        
        # 验证section参数
        valid_sections = ["full", "abstract", "introduction", "methods", "results", "discussion", "conclusion"]
        if section not in valid_sections:
            return json.dumps({
                "status": "error", 
                "message": f"无效的section参数: {section}，有效值为: {', '.join(valid_sections)}"
            }, ensure_ascii=False)
        
        # 更新状态
        _update_status(research_id, "in_progress", 0, f"提取文献内容: {pmcid}, 部分: {section}")
        
        # 创建缓存目录
        verification_dir = _get_verification_dir(research_id, version)
        
        # 缓存文件路径
        cache_file = os.path.join(verification_dir, f"{pmcid}_{section}_content.json")
        
        # 检查缓存
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                logger.info(f"从缓存加载内容: {cache_file}")
                _update_status(research_id, "completed", 100, f"从缓存加载内容: {pmcid}, 部分: {section}", cache_file)
                return json.load(f)
        
        # 移除PMC前缀用于API调用
        id_for_api = pmcid[3:] if pmcid.startswith("PMC") else pmcid
        
        # 构建API请求参数
        params = {
            "db": "pmc",
            "id": id_for_api,
            "rettype": "full",
            "retmode": "xml",
        }
        
        # 添加API密钥（如果有）
        api_key = os.environ.get("NCBI_API_KEY")
        if api_key:
            params["api_key"] = api_key
        
        # 发送请求
        _update_status(research_id, "in_progress", 30, f"获取{pmcid}的XML数据")
        with _get_session() as s:
            r = s.get(f"{NCBI_BASE}/efetch.fcgi", params=params, timeout=DEFAULT_TIMEOUT)
            r.raise_for_status()
            xml_content = r.text
        
        # 解析XML获取内容
        _update_status(research_id, "in_progress", 60, f"解析{pmcid}的XML数据，提取{section}部分")
        try:
            root = ET.fromstring(xml_content)
            
            # 提取文章
            article = root.find(".//article")
            if article is None:
                raise ValueError(f"未找到文章数据: {pmcid}")
            
            # 提取PMCID
            pmcid_elem = article.find(".//article-id[@pub-id-type='pmc']")
            pmcid_value = f"PMC{pmcid_elem.text}" if pmcid_elem is not None else pmcid
            
            # 提取标题
            title_elem = article.find(".//article-title")
            title = "".join(title_elem.itertext()) if title_elem is not None else ""
            
            content = {}
            
            # 根据请求的部分提取内容
            if section == "abstract" or section == "full":
                abstract_elem = article.find(".//abstract")
                if abstract_elem is not None:
                    content["abstract"] = " ".join("".join(p.itertext()) for p in abstract_elem.findall(".//p"))
                else:
                    content["abstract"] = ""
            
            # 提取正文部分
            body_elem = article.find(".//body")
            if body_elem is not None:
                # 处理引言
                if section == "introduction" or section == "full":
                    intro_sections = []
                    for sec in body_elem.findall(".//sec"):
                        sec_title = sec.find("title")
                        if sec_title is not None and re.search(r"introduction|background", sec_title.text, re.IGNORECASE):
                            intro_sections.append(" ".join("".join(p.itertext()) for p in sec.findall(".//p")))
                    content["introduction"] = "\n\n".join(intro_sections)
                
                # 处理方法
                if section == "methods" or section == "full":
                    method_sections = []
                    for sec in body_elem.findall(".//sec"):
                        sec_title = sec.find("title")
                        if sec_title is not None and re.search(r"methods|materials|methodology", sec_title.text, re.IGNORECASE):
                            method_sections.append(" ".join("".join(p.itertext()) for p in sec.findall(".//p")))
                    content["methods"] = "\n\n".join(method_sections)
                
                # 处理结果
                if section == "results" or section == "full":
                    result_sections = []
                    for sec in body_elem.findall(".//sec"):
                        sec_title = sec.find("title")
                        if sec_title is not None and re.search(r"results|findings", sec_title.text, re.IGNORECASE):
                            result_sections.append(" ".join("".join(p.itertext()) for p in sec.findall(".//p")))
                    content["results"] = "\n\n".join(result_sections)
                
                # 处理讨论
                if section == "discussion" or section == "full":
                    discussion_sections = []
                    for sec in body_elem.findall(".//sec"):
                        sec_title = sec.find("title")
                        if sec_title is not None and re.search(r"discussion", sec_title.text, re.IGNORECASE):
                            discussion_sections.append(" ".join("".join(p.itertext()) for p in sec.findall(".//p")))
                    content["discussion"] = "\n\n".join(discussion_sections)
                
                # 处理结论
                if section == "conclusion" or section == "full":
                    conclusion_sections = []
                    for sec in body_elem.findall(".//sec"):
                        sec_title = sec.find("title")
                        if sec_title is not None and re.search(r"conclusion|summary", sec_title.text, re.IGNORECASE):
                            conclusion_sections.append(" ".join("".join(p.itertext()) for p in sec.findall(".//p")))
                    content["conclusion"] = "\n\n".join(conclusion_sections)
            
            # 如果请求特定部分但未找到，返回空字符串
            if section != "full" and section not in content:
                content[section] = ""
            
            # 准备结果
            result = {
                "pmcid": pmcid_value,
                "title": title,
                "content": content if section == "full" else {section: content.get(section, "")}
            }
            
            # 缓存结果
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            # 更新状态为完成
            _update_status(research_id, "completed", 100, f"内容提取完成: {pmcid}, 部分: {section}", cache_file)
            
            return json.dumps(result, ensure_ascii=False)
        except ET.ParseError as e:
            logger.error(f"解析XML失败: {e}")
            _update_status(research_id, "failed", 0, f"解析XML失败: {e}")
            return json.dumps({
                "status": "error", 
                "message": f"解析XML失败: {e}"
            }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"提取内容失败: {e}")
        _update_status(research_id, "failed", 0, f"提取内容失败: {e}")
        return json.dumps({
            "status": "error", 
            "message": f"提取内容失败: {e}"
        }, ensure_ascii=False)


@tool
def manage_literature_files(action: str, research_id: str, file_path: str = "", content: str = "", version: str = "v1") -> str:
    """
    管理文献相关文件（创建、读取、写入、删除）
    
    Args:
        action (str): 操作类型，可选值：read（读取）、write（写入）、delete（删除）、list（列出文件）
        research_id (str): 研究ID，用于指定工作目录
        file_path (str): 文件路径（相对于工作目录）
        content (str): 要写入的内容（仅在action为write时使用）
        version (str): 版本号，默认v1
        
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 验证action参数
        valid_actions = ["read", "write", "delete", "list"]
        if action not in valid_actions:
            return json.dumps({
                "status": "error", 
                "message": f"无效的action参数: {action}，有效值为: {', '.join(valid_actions)}"
            }, ensure_ascii=False)
        
        # 获取工作目录
        cache_dir = _get_cache_dir(research_id, version)
        verification_dir = _get_verification_dir(research_id, version)
        
        # 根据操作类型执行相应操作
        if action == "list":
            # 列出工作目录中的文件
            cache_files = [f for f in os.listdir(cache_dir) if os.path.isfile(os.path.join(cache_dir, f))]
            verification_files = [f for f in os.listdir(verification_dir) if os.path.isfile(os.path.join(verification_dir, f))]
            
            return json.dumps({
                "status": "success",
                "cache_directory": cache_dir,
                "verification_directory": verification_dir,
                "cache_files": cache_files,
                "verification_files": verification_files
            }, ensure_ascii=False)
        
        # 对于其他操作，需要文件路径
        if not file_path:
            return json.dumps({
                "status": "error", 
                "message": "file_path参数不能为空"
            }, ensure_ascii=False)
        
        # 确定完整文件路径
        if file_path.startswith("verification/"):
            full_path = os.path.join(verification_dir, os.path.basename(file_path))
        else:
            full_path = os.path.join(cache_dir, file_path)
        
        # 执行相应操作
        if action == "read":
            # 读取文件
            if not os.path.exists(full_path):
                return json.dumps({
                    "status": "error", 
                    "message": f"文件不存在: {full_path}"
                }, ensure_ascii=False)
            
            with open(full_path, "r", encoding="utf-8") as f:
                file_content = f.read()
            
            return json.dumps({
                "status": "success",
                "file_path": full_path,
                "content": file_content
            }, ensure_ascii=False)
        
        elif action == "write":
            # 写入文件
            if not content:
                return json.dumps({
                    "status": "error", 
                    "message": "content参数不能为空"
                }, ensure_ascii=False)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            return json.dumps({
                "status": "success",
                "file_path": full_path,
                "message": f"内容已写入文件: {full_path}"
            }, ensure_ascii=False)
        
        elif action == "delete":
            # 删除文件
            if not os.path.exists(full_path):
                return json.dumps({
                    "status": "error", 
                    "message": f"文件不存在: {full_path}"
                }, ensure_ascii=False)
            
            os.remove(full_path)
            
            return json.dumps({
                "status": "success",
                "file_path": full_path,
                "message": f"文件已删除: {full_path}"
            }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"文件操作失败: {e}")
        return json.dumps({
            "status": "error", 
            "message": f"文件操作失败: {e}"
        }, ensure_ascii=False)


@tool
def generate_editor_feedback(research_id: str, feedback_data: Dict[str, Any], version: str = "v1") -> str:
    """
    生成编辑反馈JSON文件
    
    Args:
        research_id (str): 研究ID，用于指定工作目录
        feedback_data (Dict[str, Any]): 编辑反馈数据
        version (str): 版本号，默认v1
        
    Returns:
        str: JSON格式的操作结果，包含生成的文件路径
    """
    try:
        # 更新状态
        _update_status(research_id, "in_progress", 80, "生成编辑反馈文件")
        
        # 获取工作目录
        cache_dir = _get_cache_dir(research_id, version)
        
        # 生成时间戳
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        
        # 构建文件名
        file_name = f"editor_{version}_{timestamp}.json"
        file_path = os.path.join(cache_dir, file_name)
        
        # 添加元数据
        feedback_data.update({
            "metadata": {
                "research_id": research_id,
                "version": version,
                "timestamp": datetime.utcnow().isoformat(),
                "generator": "pubmed_literature_editor_assistant"
            }
        })
        
        # 写入文件
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(feedback_data, f, ensure_ascii=False, indent=2)
        
        # 更新状态为完成
        _update_status(research_id, "completed", 100, "编辑反馈生成完成", file_path)
        
        return json.dumps({
            "status": "success",
            "file_path": file_path,
            "message": f"编辑反馈已生成: {file_path}"
        }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"生成编辑反馈失败: {e}")
        _update_status(research_id, "failed", 0, f"生成编辑反馈失败: {e}")
        return json.dumps({
            "status": "error", 
            "message": f"生成编辑反馈失败: {e}"
        }, ensure_ascii=False)


@tool
def get_processing_status(research_id: str) -> str:
    """
    获取处理状态
    
    Args:
        research_id (str): 研究ID
        
    Returns:
        str: JSON格式的处理状态
    """
    try:
        status = _get_status(research_id)
        return json.dumps(status, ensure_ascii=False)
    except Exception as e:
        logger.error(f"获取处理状态失败: {e}")
        return json.dumps({
            "status": "error", 
            "message": f"获取处理状态失败: {e}"
        }, ensure_ascii=False)