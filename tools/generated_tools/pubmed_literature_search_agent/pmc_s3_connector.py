#!/usr/bin/env python3
"""
PMC S3 Connector Tool

提供与AWS S3 PubMed Central开放数据的连接和访问功能
使用no-sign-request方式访问PMC公开数据
"""

import json
import os
import boto3
from botocore import UNSIGNED
from botocore.config import Config
from typing import Dict, List, Any, Optional, Union
import logging
from pathlib import Path

from strands import tool

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# PMC S3存储桶常量
PMC_BUCKET_NAME = "pmc-oa-opendata"
PMC_REGION = "us-east-1"
PMC_DIRECTORIES = ["oa_comm", "oa_noncomm", "phe_timebound", "author_manuscript"]
PMC_FORMATS = ["txt", "xml"]

# 本地缓存目录
CACHE_DIR = Path(".cache/pubmed_literature_agent")


@tool
def pmc_s3_connect(directory: str = "oa_comm", list_files: bool = False, max_files: int = 10) -> str:
    """
    连接到PMC S3存储桶并列出文件
    
    Args:
        directory (str): PMC目录名称 (oa_comm, oa_noncomm, phe_timebound)
        list_files (bool): 是否列出文件
        max_files (int): 最大文件数量
        
    Returns:
        str: JSON格式的连接结果和文件列表
    """
    try:
        # 验证目录参数
        if directory not in PMC_DIRECTORIES:
            return json.dumps({
                "status": "error",
                "message": f"无效的目录名称。请使用以下之一: {', '.join(PMC_DIRECTORIES)}"
            }, ensure_ascii=False)
        
        # 创建无签名S3客户端
        s3_client = boto3.client(
            's3',
            region_name=PMC_REGION,
            config=Config(signature_version=UNSIGNED)
        )
        
        # 构建基本响应
        response = {
            "status": "success",
            "bucket": PMC_BUCKET_NAME,
            "directory": directory,
            "connection": "established",
            "message": f"成功连接到PMC S3存储桶: {PMC_BUCKET_NAME}, 目录: {directory}"
        }
        
        # 如果请求列出文件
        if list_files:
            try:
                # 列出目录中的文件
                prefix = f"{directory}/"
                file_list = []
                
                paginator = s3_client.get_paginator('list_objects_v2')
                pages = paginator.paginate(
                    Bucket=PMC_BUCKET_NAME,
                    Prefix=prefix,
                    PaginationConfig={'MaxItems': max_files}
                )
                
                for page in pages:
                    if 'Contents' in page:
                        for obj in page['Contents']:
                            file_list.append({
                                "key": obj['Key'],
                                "size": obj['Size'],
                                "last_modified": obj['LastModified'].isoformat()
                            })
                            if len(file_list) >= max_files:
                                break
                    if len(file_list) >= max_files:
                        break
                
                response["files"] = file_list
                response["file_count"] = len(file_list)
                response["message"] = f"成功连接并列出{len(file_list)}个文件"
            except Exception as e:
                logger.error(f"列出文件时出错: {str(e)}")
                response["status"] = "partial_success"
                response["message"] = f"已连接，但列出文件失败: {str(e)}"
        
        return json.dumps(response, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"连接PMC S3失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"连接PMC S3失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def pmc_list_directories() -> str:
    """
    列出PMC S3存储桶中的可用目录
    
    Returns:
        str: JSON格式的目录列表和描述
    """
    try:
        # 创建无签名S3客户端
        s3_client = boto3.client(
            's3',
            region_name=PMC_REGION,
            config=Config(signature_version=UNSIGNED)
        )
        
        # 尝试列出存储桶的根目录
        response = s3_client.list_objects_v2(
            Bucket=PMC_BUCKET_NAME,
            Delimiter='/'
        )
        
        directories = []
        if 'CommonPrefixes' in response:
            for prefix in response['CommonPrefixes']:
                dir_name = prefix['Prefix'].rstrip('/')
                directories.append(dir_name)
        
        # 如果API没有返回目录，使用已知的目录列表
        if not directories:
            directories = PMC_DIRECTORIES
        
        # 构建目录描述
        directory_info = [
            {
                "name": "oa_comm",
                "description": "Open Access Commercial Use Collection - 允许商业使用的开放获取文章",
                "formats": PMC_FORMATS
            },
            {
                "name": "oa_noncomm",
                "description": "Open Access Non-Commercial Use Collection - 仅限非商业使用的开放获取文章",
                "formats": PMC_FORMATS
            },
            {
                "name": "phe_timebound",
                "description": "Public Health Emergency Collection - 公共卫生紧急情况相关文章",
                "formats": PMC_FORMATS
            }
        ]
        
        return json.dumps({
            "status": "success",
            "bucket": PMC_BUCKET_NAME,
            "directories": directory_info
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"列出PMC目录失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"列出PMC目录失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def pmc_download_file(file_key: str, format_type: str = "xml", save_to_cache: bool = True) -> str:
    """
    从PMC S3下载指定文件
    
    Args:
        file_key (str): 文件的S3键
        format_type (str): 文件格式类型 (xml, txt)
        save_to_cache (bool): 是否保存到本地缓存
        
    Returns:
        str: 文件内容或JSON格式的下载结果
    """
    try:
        # 验证格式类型
        if format_type not in PMC_FORMATS:
            return json.dumps({
                "status": "error",
                "message": f"无效的格式类型。请使用以下之一: {', '.join(PMC_FORMATS)}"
            }, ensure_ascii=False)
        
        # 确保文件键格式正确
        if not file_key.startswith(tuple(d + '/' for d in PMC_DIRECTORIES)):
            return json.dumps({
                "status": "error",
                "message": f"无效的文件键格式。应以有效目录开头: {', '.join(PMC_DIRECTORIES)}"
            }, ensure_ascii=False)
        
        # 创建缓存目录（如果需要）
        if save_to_cache:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_file = CACHE_DIR / Path(file_key).name
            
            # 检查缓存
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                return json.dumps({
                    "status": "success",
                    "source": "cache",
                    "file_key": file_key,
                    "format": format_type,
                    "content": content[:1000] + "..." if len(content) > 1000 else content,
                    "content_length": len(content),
                    "cache_path": str(cache_file)
                }, ensure_ascii=False)
        
        # 创建无签名S3客户端
        s3_client = boto3.client(
            's3',
            region_name=PMC_REGION,
            config=Config(signature_version=UNSIGNED)
        )
        
        # 下载文件
        response = s3_client.get_object(
            Bucket=PMC_BUCKET_NAME,
            Key=file_key
        )
        
        # 容错解码
        body_bytes = response['Body'].read()
        try:
            content = body_bytes.decode('utf-8')
        except Exception:
            try:
                content = body_bytes.decode('utf-8', errors='ignore')
            except Exception:
                content = body_bytes.decode('latin-1', errors='ignore')
        
        # 保存到缓存
        if save_to_cache:
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return json.dumps({
            "status": "success",
            "source": "s3",
            "file_key": file_key,
            "format": format_type,
            "content": content[:1000] + "..." if len(content) > 1000 else content,
            "content_length": len(content),
            "cache_path": str(cache_file) if save_to_cache else None
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"下载文件失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"下载文件失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def pmc_search_files(search_term: str, directory: str = "oa_comm", format_type: str = "xml", max_results: int = 20, time_budget_seconds: int = 10) -> str:
    """
    在PMC S3中搜索文件
    
    Args:
        search_term (str): 搜索词
        directory (str): PMC目录名称 (oa_comm, oa_noncomm, phe_timebound)
        format_type (str): 文件格式类型 (xml, txt)
        max_results (int): 最大结果数量
        
    Returns:
        str: JSON格式的搜索结果
    """
    try:
        # 验证参数
        if directory not in PMC_DIRECTORIES:
            return json.dumps({
                "status": "error",
                "message": f"无效的目录名称。请使用以下之一: {', '.join(PMC_DIRECTORIES)}"
            }, ensure_ascii=False)
        
        if format_type not in PMC_FORMATS:
            return json.dumps({
                "status": "error",
                "message": f"无效的格式类型。请使用以下之一: {', '.join(PMC_FORMATS)}"
            }, ensure_ascii=False)
        
        # 基于本地缓存的 filelist.csv 搜索，避免大规模 S3 遍历
        import time as _time
        start_ts = _time.time()
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = CACHE_DIR / f"{directory}_filelist.csv"

        # 若无缓存则尝试下载一次 filelist.csv
        if not cache_file.exists():
            _ = pmc_get_filelist_csv(directory=directory, save_to_cache=True)

        results = []
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8', errors='ignore') as f:
                # 跳过标题行
                header = f.readline()
                for line in f:
                    if ( _time.time() - start_ts ) > max(3, time_budget_seconds):
                        break
                    parts = line.strip().split(',')
                    if not parts:
                        continue
                    file_name = parts[0]
                    pmcid = parts[1] if len(parts) > 1 else ''
                    pmid = parts[2] if len(parts) > 2 else ''
                    license_info = parts[3] if len(parts) > 3 else ''

                    haystack = (file_name + ' ' + pmcid + ' ' + pmid + ' ' + license_info).lower()
                    if search_term.lower() in haystack:
                        results.append({
                            "key": f"{directory}/{format_type}/{file_name}",
                            "pmcid": pmcid,
                            "pmid": pmid,
                            "license": license_info
                        })
                        if len(results) >= max_results:
                            break

        status = "success" if results else "partial_success"
        return json.dumps({
            "status": status,
            "search_term": search_term,
            "directory": directory,
            "format": format_type,
            "result_count": len(results),
            "results": results,
            "method": "filelist_cache"
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"搜索文件失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"搜索文件失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def pmc_get_filelist_csv(directory: str = "oa_comm", save_to_cache: bool = True) -> str:
    """
    获取PMC目录的filelist.csv文件
    
    Args:
        directory (str): PMC目录名称 (oa_comm, oa_noncomm, phe_timebound)
        save_to_cache (bool): 是否保存到本地缓存
        
    Returns:
        str: JSON格式的filelist.csv内容
    """
    try:
        # 验证目录参数
        if directory not in PMC_DIRECTORIES:
            return json.dumps({
                "status": "error",
                "message": f"无效的目录名称。请使用以下之一: {', '.join(PMC_DIRECTORIES)}"
            }, ensure_ascii=False)
        
        # 缓存文件路径
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = CACHE_DIR / f"{directory}_filelist.csv"
        
        # 检查缓存
        if save_to_cache and cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 解析CSV内容的前几行
            lines = content.split('\n')
            headers = lines[0].split(',') if lines else []
            sample_rows = [line.split(',') for line in lines[1:6] if line]
            
            return json.dumps({
                "status": "success",
                "source": "cache",
                "directory": directory,
                "file": "filelist.csv",
                "headers": headers,
                "sample_rows": sample_rows,
                "total_rows": len(lines) - 1 if lines else 0,
                "cache_path": str(cache_file)
            }, ensure_ascii=False)
        
        # 创建无签名S3客户端
        s3_client = boto3.client(
            's3',
            region_name=PMC_REGION,
            config=Config(signature_version=UNSIGNED)
        )
        
        # 下载filelist.csv
        file_key = f"{directory}/filelist.csv"
        
        try:
            response = s3_client.get_object(
                Bucket=PMC_BUCKET_NAME,
                Key=file_key
            )
            
            content = response['Body'].read().decode('utf-8')
            
            # 保存到缓存
            if save_to_cache:
                with open(cache_file, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            # 解析CSV内容的前几行
            lines = content.split('\n')
            headers = lines[0].split(',') if lines else []
            sample_rows = [line.split(',') for line in lines[1:6] if line]
            
            return json.dumps({
                "status": "success",
                "source": "s3",
                "directory": directory,
                "file": "filelist.csv",
                "headers": headers,
                "sample_rows": sample_rows,
                "total_rows": len(lines) - 1 if lines else 0,
                "cache_path": str(cache_file) if save_to_cache else None
            }, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"下载filelist.csv失败: {str(e)}")
            return json.dumps({
                "status": "error",
                "message": f"下载filelist.csv失败: {str(e)}"
            }, ensure_ascii=False)
            
    except Exception as e:
        logger.error(f"获取filelist.csv失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"获取filelist.csv失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def pmc_get_metadata_by_pmcid(pmcid: str, directory: str = None, timeout_seconds: int = 30) -> str:
    """
    通过PMCID获取文章元数据（改进版，增加超时控制）
    
    Args:
        pmcid (str): PubMed Central ID (例如: PMC1234567)
        directory (str): PMC目录名称，如果不指定则搜索所有目录
        timeout_seconds (int): 超时时间（秒）
        
    Returns:
        str: JSON格式的文章元数据
    """
    import signal
    import time
    
    def timeout_handler(signum, frame):
        raise TimeoutError(f"操作超时（{timeout_seconds}秒）")
    
    try:
        # 设置超时
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_seconds)
        
        # 规范化PMCID
        if not pmcid.startswith("PMC"):
            pmcid = f"PMC{pmcid}"
        
        logger.info(f"开始搜索PMCID: {pmcid}")
        
        # 要搜索的目录
        directories_to_search = [directory] if directory in PMC_DIRECTORIES else PMC_DIRECTORIES
        
        # 创建无签名S3客户端
        s3_client = boto3.client(
            's3',
            region_name=PMC_REGION,
            config=Config(signature_version=UNSIGNED)
        )
        
        # 首先尝试从缓存中快速查找
        logger.info("检查缓存文件...")
        for dir_name in directories_to_search:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_file = CACHE_DIR / f"{dir_name}_filelist.csv"
            
            if cache_file.exists():
                logger.info(f"在缓存中搜索 {dir_name}...")
                with open(cache_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for line in content.split('\n'):
                    if pmcid in line:
                        parts = line.split(',')
                        if len(parts) >= 2:
                            logger.info(f"在缓存中找到 {pmcid}")
                            
                            # 优先尝试XML格式
                            for format_type in ['xml', 'txt']:
                                file_key = f"{dir_name}/{format_type}/{parts[0]}"
                                
                                try:
                                    response = s3_client.get_object(
                                        Bucket=PMC_BUCKET_NAME,
                                        Key=file_key
                                    )
                                    
                                    content = response['Body'].read().decode('utf-8')
                                    
                                    # 提取基本元数据
                                    metadata = {
                                        "pmcid": pmcid,
                                        "file_key": file_key,
                                        "format": format_type,
                                        "directory": dir_name,
                                        "content_length": len(content),
                                        "status": "success"
                                    }
                                    
                                    # 从内容中提取更多元数据
                                    if format_type == 'xml':
                                        import re
                                        
                                        # 提取标题
                                        title_match = re.search(r'<article-title>(.*?)</article-title>', content)
                                        if title_match:
                                            metadata["title"] = title_match.group(1)
                                        
                                        # 提取作者
                                        author_matches = re.findall(r'<contrib contrib-type="author">(.*?)</contrib>', content, re.DOTALL)
                                        authors = []
                                        for author_xml in author_matches:
                                            surname_match = re.search(r'<surname>(.*?)</surname>', author_xml)
                                            given_names_match = re.search(r'<given-names>(.*?)</given-names>', author_xml)
                                            if surname_match and given_names_match:
                                                authors.append(f"{given_names_match.group(1)} {surname_match.group(1)}")
                                        metadata["authors"] = authors
                                        
                                        # 提取期刊信息
                                        journal_match = re.search(r'<journal-title>(.*?)</journal-title>', content)
                                        if journal_match:
                                            metadata["journal"] = journal_match.group(1)
                                        
                                        # 提取发布日期
                                        pub_date_match = re.search(r'<pub-date[^>]*>(.*?)</pub-date>', content, re.DOTALL)
                                        if pub_date_match:
                                            year_match = re.search(r'<year>(.*?)</year>', pub_date_match.group(1))
                                            month_match = re.search(r'<month>(.*?)</month>', pub_date_match.group(1))
                                            day_match = re.search(r'<day>(.*?)</day>', pub_date_match.group(1))
                                            
                                            year = year_match.group(1) if year_match else ""
                                            month = month_match.group(1) if month_match else ""
                                            day = day_match.group(1) if day_match else ""
                                            
                                            metadata["publication_date"] = f"{year}-{month}-{day}".rstrip("-")
                                        
                                        # 提取摘要
                                        abstract_match = re.search(r'<abstract>(.*?)</abstract>', content, re.DOTALL)
                                        if abstract_match:
                                            # 移除HTML标签
                                            abstract_text = re.sub(r'<[^>]+>', ' ', abstract_match.group(1))
                                            abstract_text = re.sub(r'\s+', ' ', abstract_text).strip()
                                            metadata["abstract"] = abstract_text
                                    
                                    signal.alarm(0)  # 取消超时
                                    return json.dumps(metadata, ensure_ascii=False, indent=2)
                                    
                                except Exception as e:
                                    logger.warning(f"无法下载文件 {file_key}: {str(e)}")
                                    continue
        
        # 如果缓存中没有找到，返回快速失败信息
        signal.alarm(0)  # 取消超时
        logger.warning(f"在缓存中未找到 {pmcid}")
        return json.dumps({
            "status": "not_found_in_cache",
            "message": f"PMCID {pmcid} 在缓存中未找到。建议先运行 pmc_get_filelist_csv 更新缓存，或使用 pmc_search_files 进行搜索。",
            "pmcid": pmcid,
            "suggestion": "尝试使用 pmc_search_files 工具进行更广泛的搜索"
        }, ensure_ascii=False)
        
    except TimeoutError as e:
        signal.alarm(0)  # 取消超时
        logger.error(f"搜索超时: {str(e)}")
        return json.dumps({
            "status": "timeout",
            "message": f"搜索超时（{timeout_seconds}秒）。建议使用 pmc_search_files 工具进行搜索。",
            "pmcid": pmcid
        }, ensure_ascii=False)
        
    except Exception as e:
        signal.alarm(0)  # 取消超时
        logger.error(f"获取文章元数据失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"获取文章元数据失败: {str(e)}",
            "pmcid": pmcid
        }, ensure_ascii=False)


@tool
def pmc_get_article_by_id(pmcid: str, format_type: str = "xml", verify_content: bool = False, expected_title: str = None, expected_keywords: List[str] = None) -> str:
    """
    直接通过PMCID获取文章（优化版，集成内容验证）
    
    Args:
        pmcid (str): PubMed Central ID (例如: PMC1234567)
        format_type (str): 文件格式 (xml, txt)
        verify_content (bool): 是否验证内容匹配性
        expected_title (str): 预期的标题（用于验证）
        expected_keywords (List[str]): 预期的关键词列表
        
    Returns:
        str: JSON格式的文章内容和元数据
    """
    try:
        # 规范化PMCID
        if not pmcid.startswith("PMC"):
            pmcid = f"PMC{pmcid}"
        
        logger.info(f"直接获取文章: {pmcid} ({format_type})")
        
        # 创建无签名S3客户端
        s3_client = boto3.client(
            's3',
            region_name=PMC_REGION,
            config=Config(signature_version=UNSIGNED)
        )
        
        # 构建文件路径并尝试获取
        for directory in PMC_DIRECTORIES:
            file_key = f"{directory}/{format_type}/all/{pmcid}.{format_type}"
            
            try:
                logger.info(f"尝试获取: {file_key}")
                response = s3_client.get_object(
                    Bucket=PMC_BUCKET_NAME,
                    Key=file_key
                )
                
                content = response['Body'].read().decode('utf-8')
                
                # 提取元数据
                metadata = {
                    "pmcid": pmcid,
                    "file_key": file_key,
                    "format": format_type,
                    "directory": directory,
                    "content_length": len(content),
                    "status": "success"
                }
                
                # 根据格式提取基本信息
                if format_type == "xml":
                    import re
                    
                    # 提取标题
                    title_match = re.search(r'<article-title>(.*?)</article-title>', content)
                    if title_match:
                        metadata["title"] = title_match.group(1)
                    
                    # 提取作者
                    author_matches = re.findall(r'<contrib contrib-type="author">(.*?)</contrib>', content, re.DOTALL)
                    authors = []
                    for author_xml in author_matches:
                        surname_match = re.search(r'<surname>(.*?)</surname>', author_xml)
                        given_names_match = re.search(r'<given-names>(.*?)</given-names>', author_xml)
                        if surname_match and given_names_match:
                            authors.append(f"{given_names_match.group(1)} {surname_match.group(1)}")
                    metadata["authors"] = authors
                    
                    # 提取期刊信息
                    journal_match = re.search(r'<journal-title>(.*?)</journal-title>', content)
                    if journal_match:
                        metadata["journal"] = journal_match.group(1)
                    
                    # 提取发布日期
                    pub_date_match = re.search(r'<pub-date[^>]*>(.*?)</pub-date>', content, re.DOTALL)
                    if pub_date_match:
                        year_match = re.search(r'<year>(.*?)</year>', pub_date_match.group(1))
                        month_match = re.search(r'<month>(.*?)</month>', pub_date_match.group(1))
                        day_match = re.search(r'<day>(.*?)</day>', pub_date_match.group(1))
                        
                        year = year_match.group(1) if year_match else ""
                        month = month_match.group(1) if month_match else ""
                        day = day_match.group(1) if day_match else ""
                        
                        metadata["publication_date"] = f"{year}-{month}-{day}".rstrip("-")
                        metadata["year"] = year
                    
                    # 提取摘要
                    abstract_match = re.search(r'<abstract>(.*?)</abstract>', content, re.DOTALL)
                    if abstract_match:
                        # 移除HTML标签
                        abstract_text = re.sub(r'<[^>]+>', ' ', abstract_match.group(1))
                        abstract_text = re.sub(r'\s+', ' ', abstract_text).strip()
                        metadata["abstract"] = abstract_text
                
                elif format_type == "txt":
                    # 对于txt格式，提取基本信息
                    lines = content.split('\n')
                    if lines:
                        # 假设第一行或前几行包含标题信息
                        metadata["title"] = lines[0].strip() if lines[0].strip() else "Unknown Title"
                        
                        # 查找摘要部分
                        abstract_start = None
                        for i, line in enumerate(lines):
                            if re.match(r'^ABSTRACT\s*:?$|^SUMMARY\s*:?$', line, re.IGNORECASE):
                                abstract_start = i + 1
                                break
                        
                        if abstract_start:
                            abstract_lines = []
                            for i in range(abstract_start, min(abstract_start + 10, len(lines))):
                                if lines[i].strip():
                                    abstract_lines.append(lines[i].strip())
                            metadata["abstract"] = ' '.join(abstract_lines)
                
                # 添加内容（截取前1000字符用于预览）
                metadata["content_preview"] = content[:1000] + "..." if len(content) > 1000 else content
                
                # 内容验证（如果启用）
                if verify_content:
                    verification_result = _verify_content_match(metadata, expected_title, expected_keywords)
                    metadata["content_verification"] = verification_result
                    
                    # 如果验证失败，添加警告
                    if verification_result.get("overall_assessment") == "content_mismatch":
                        metadata["warning"] = "内容验证失败：获取的文章内容与预期不匹配"
                        logger.warning(f"PMCID {pmcid} 内容验证失败: {verification_result.get('recommendation')}")
                
                return json.dumps(metadata, ensure_ascii=False, indent=2)
                
            except Exception as e:
                logger.debug(f"在 {directory} 中未找到 {file_key}: {str(e)}")
                continue
        
        # 如果所有目录都没找到
        return json.dumps({
            "status": "not_found",
            "message": f"未找到PMCID为{pmcid}的{format_type}格式文章",
            "pmcid": pmcid,
            "format": format_type,
            "searched_directories": PMC_DIRECTORIES,
            "suggestion": "尝试使用不同的格式类型或检查PMCID是否正确"
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"获取文章失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"获取文章失败: {str(e)}",
            "pmcid": pmcid
        }, ensure_ascii=False)


def _verify_content_match(metadata: dict, expected_title: str = None, expected_keywords: List[str] = None) -> dict:
    """
    验证内容匹配性的内部函数
    
    Args:
        metadata: 文章元数据
        expected_title: 预期标题
        expected_keywords: 预期关键词列表
        
    Returns:
        dict: 验证结果
    """
    verification_result = {
        "title_match": None,
        "keyword_match": None,
        "content_relevance": None
    }
    
    # 验证标题匹配
    if expected_title:
        actual_title = metadata.get("title", "").lower().strip()
        expected_title_lower = expected_title.lower().strip()
        
        if actual_title == expected_title_lower:
            verification_result["title_match"] = "exact"
        elif expected_title_lower in actual_title or actual_title in expected_title_lower:
            verification_result["title_match"] = "partial"
        else:
            verification_result["title_match"] = "mismatch"
            verification_result["title_mismatch_details"] = {
                "expected": expected_title,
                "actual": metadata.get("title", "")
            }
    
    # 验证关键词匹配
    if expected_keywords:
        content_text = metadata.get("content_preview", "").lower()
        title_text = metadata.get("title", "").lower()
        full_text = f"{title_text} {content_text}"
        
        matched_keywords = []
        for keyword in expected_keywords:
            if keyword.lower() in full_text:
                matched_keywords.append(keyword)
        
        verification_result["keyword_match"] = {
            "matched_count": len(matched_keywords),
            "total_count": len(expected_keywords),
            "matched_keywords": matched_keywords,
            "match_ratio": len(matched_keywords) / len(expected_keywords) if expected_keywords else 0
        }
    
    # 内容相关性评估
    if expected_keywords:
        match_ratio = verification_result["keyword_match"]["match_ratio"]
        if match_ratio >= 0.7:
            verification_result["content_relevance"] = "high"
        elif match_ratio >= 0.3:
            verification_result["content_relevance"] = "medium"
        else:
            verification_result["content_relevance"] = "low"
    
    # 总体评估
    if verification_result["title_match"] == "mismatch":
        verification_result["overall_assessment"] = "content_mismatch"
        verification_result["recommendation"] = "此PMCID的内容与预期不匹配，建议重新验证PMID到PMCID的映射"
    elif verification_result["content_relevance"] == "low":
        verification_result["overall_assessment"] = "low_relevance"
        verification_result["recommendation"] = "内容相关性较低，可能不是目标文章"
    else:
        verification_result["overall_assessment"] = "content_match"
        verification_result["recommendation"] = "内容匹配良好"
    
    return verification_result


@tool
def pmc_quick_search(pmcid: str) -> str:
    """
    快速搜索PMCID（优化版，直接构建路径）
    
    Args:
        pmcid (str): PubMed Central ID (例如: PMC1234567)
        
    Returns:
        str: JSON格式的搜索结果和建议
    """
    try:
        # 规范化PMCID
        if not pmcid.startswith("PMC"):
            pmcid = f"PMC{pmcid}"
        
        logger.info(f"快速搜索PMCID: {pmcid}")
        
        # 创建无签名S3客户端
        s3_client = boto3.client(
            's3',
            region_name=PMC_REGION,
            config=Config(signature_version=UNSIGNED)
        )
        
        # 直接尝试获取XML格式（优先）
        for directory in PMC_DIRECTORIES:
            file_key = f"{directory}/xml/all/{pmcid}.xml"
            
            try:
                logger.info(f"尝试获取XML: {file_key}")
                response = s3_client.get_object(
                    Bucket=PMC_BUCKET_NAME,
                    Key=file_key
                )
                
                content = response['Body'].read().decode('utf-8')
                
                # 提取基本元数据
                metadata = {
                    "pmcid": pmcid,
                    "file_key": file_key,
                    "format": "xml",
                    "directory": directory,
                    "content_length": len(content),
                    "status": "found"
                }
                
                # 简单提取标题
                import re
                title_match = re.search(r'<article-title>(.*?)</article-title>', content)
                if title_match:
                    metadata["title"] = title_match.group(1)
                
                # 提取期刊
                journal_match = re.search(r'<journal-title>(.*?)</journal-title>', content)
                if journal_match:
                    metadata["journal"] = journal_match.group(1)
                
                # 提取年份
                year_match = re.search(r'<year>(.*?)</year>', content)
                if year_match:
                    metadata["year"] = year_match.group(1)
                
                return json.dumps(metadata, ensure_ascii=False, indent=2)
                
            except Exception as e:
                logger.debug(f"XML格式未找到: {file_key}")
                continue
        
        # 如果XML没找到，尝试TXT格式
        for directory in PMC_DIRECTORIES:
            file_key = f"{directory}/txt/all/{pmcid}.txt"
            
            try:
                logger.info(f"尝试获取TXT: {file_key}")
                response = s3_client.get_object(
                    Bucket=PMC_BUCKET_NAME,
                    Key=file_key
                )
                
                content = response['Body'].read().decode('utf-8')
                
                # 提取基本元数据
                metadata = {
                    "pmcid": pmcid,
                    "file_key": file_key,
                    "format": "txt",
                    "directory": directory,
                    "content_length": len(content),
                    "status": "found"
                }
                
                # 简单提取标题（第一行）
                lines = content.split('\n')
                if lines and lines[0].strip():
                    metadata["title"] = lines[0].strip()
                
                return json.dumps(metadata, ensure_ascii=False, indent=2)
                
            except Exception as e:
                logger.debug(f"TXT格式未找到: {file_key}")
                continue
        
        # 如果都没找到，返回建议
        return json.dumps({
            "status": "not_found",
            "message": f"PMCID {pmcid} 未找到",
            "pmcid": pmcid,
            "searched_directories": PMC_DIRECTORIES,
            "searched_formats": ["xml", "txt"],
            "suggestions": [
                "1. 确认PMCID是否正确",
                "2. 检查文章是否在PMC开放数据中",
                "3. 尝试使用 pmc_search_files 进行关键词搜索",
                "4. 使用 pmc_get_article_by_id 指定格式类型"
            ]
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"快速搜索失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"快速搜索失败: {str(e)}",
            "pmcid": pmcid
        }, ensure_ascii=False)


@tool
def pmc_cache_status() -> str:
    """
    获取PMC本地缓存状态
    
    Returns:
        str: JSON格式的缓存状态信息
    """
    try:
        # 确保缓存目录存在
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        # 收集缓存文件信息
        cache_files = list(CACHE_DIR.glob('*'))
        
        cache_info = []
        total_size = 0
        
        for file_path in cache_files:
            size = file_path.stat().st_size
            total_size += size
            
            cache_info.append({
                "filename": file_path.name,
                "path": str(file_path),
                "size_bytes": size,
                "size_mb": round(size / (1024 * 1024), 2),
                "last_modified": file_path.stat().st_mtime
            })
        
        return json.dumps({
            "status": "success",
            "cache_directory": str(CACHE_DIR),
            "file_count": len(cache_info),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "files": cache_info
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"获取缓存状态失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"获取缓存状态失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def pmc_clear_cache(confirm: bool = False) -> str:
    """
    清除PMC本地缓存
    
    Args:
        confirm (bool): 确认清除缓存
        
    Returns:
        str: JSON格式的操作结果
    """
    try:
        if not confirm:
            return json.dumps({
                "status": "warning",
                "message": "需要确认才能清除缓存。请设置confirm=True确认操作。"
            }, ensure_ascii=False)
        
        # 确保缓存目录存在
        if not CACHE_DIR.exists():
            return json.dumps({
                "status": "success",
                "message": "缓存目录不存在，无需清除。"
            }, ensure_ascii=False)
        
        # 收集清除前的缓存信息
        cache_files = list(CACHE_DIR.glob('*'))
        file_count = len(cache_files)
        
        # 清除缓存文件
        for file_path in cache_files:
            if file_path.is_file():
                file_path.unlink()
        
        return json.dumps({
            "status": "success",
            "message": f"成功清除{file_count}个缓存文件",
            "cache_directory": str(CACHE_DIR),
            "files_removed": file_count
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"清除缓存失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"清除缓存失败: {str(e)}"
        }, ensure_ascii=False)