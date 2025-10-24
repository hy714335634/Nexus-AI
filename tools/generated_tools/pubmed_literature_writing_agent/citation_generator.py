#!/usr/bin/env python3
"""
Citation Generator Tool

提供生成多种格式的引用信息的功能
支持APA、MLA、Chicago、Harvard、Vancouver等格式
"""

import json
import re
from typing import Dict, List, Any, Optional, Union
import logging
from datetime import datetime

from strands import tool

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _format_authors_apa(authors: List[Any]) -> str:
    """
    格式化APA格式的作者列表
    
    Args:
        authors: 作者列表
        
    Returns:
        格式化的作者字符串
    """
    if not authors:
        return ""
    
    formatted_authors = []
    
    for author in authors:
        if isinstance(author, dict):
            if "surname" in author and "given_name" in author:
                # 姓在前，名的首字母在后
                surname = author["surname"]
                given_name_initials = "".join([name[0] + "." for name in author["given_name"].split() if name])
                formatted_authors.append(f"{surname}, {given_name_initials}")
            elif "full_name" in author:
                # 尝试从全名中分离姓和名
                name_parts = author["full_name"].split()
                if len(name_parts) > 1:
                    surname = name_parts[-1]
                    given_names = name_parts[:-1]
                    given_name_initials = "".join([name[0] + "." for name in given_names if name])
                    formatted_authors.append(f"{surname}, {given_name_initials}")
                else:
                    formatted_authors.append(author["full_name"])
        elif isinstance(author, str):
            # 尝试从字符串中分离姓和名
            name_parts = author.split()
            if len(name_parts) > 1:
                surname = name_parts[-1]
                given_names = name_parts[:-1]
                given_name_initials = "".join([name[0] + "." for name in given_names if name])
                formatted_authors.append(f"{surname}, {given_name_initials}")
            else:
                formatted_authors.append(author)
    
    # 根据APA格式组合作者
    if len(formatted_authors) == 1:
        return formatted_authors[0]
    elif len(formatted_authors) == 2:
        return formatted_authors[0] + " & " + formatted_authors[1]
    elif len(formatted_authors) > 2:
        return ", ".join(formatted_authors[:-1]) + ", & " + formatted_authors[-1]
    else:
        return ""


def _format_authors_mla(authors: List[Any]) -> str:
    """
    格式化MLA格式的作者列表
    
    Args:
        authors: 作者列表
        
    Returns:
        格式化的作者字符串
    """
    if not authors:
        return ""
    
    formatted_authors = []
    
    for author in authors:
        if isinstance(author, dict):
            if "surname" in author and "given_name" in author:
                # 第一个作者：姓在前，名在后
                if not formatted_authors:
                    formatted_authors.append(f"{author['surname']}, {author['given_name']}")
                else:
                    # 其他作者：名在前，姓在后
                    formatted_authors.append(f"{author['given_name']} {author['surname']}")
            elif "full_name" in author:
                # 尝试从全名中分离姓和名
                name_parts = author["full_name"].split()
                if len(name_parts) > 1:
                    surname = name_parts[-1]
                    given_names = " ".join(name_parts[:-1])
                    # 第一个作者：姓在前，名在后
                    if not formatted_authors:
                        formatted_authors.append(f"{surname}, {given_names}")
                    else:
                        # 其他作者：名在前，姓在后
                        formatted_authors.append(f"{given_names} {surname}")
                else:
                    formatted_authors.append(author["full_name"])
        elif isinstance(author, str):
            # 尝试从字符串中分离姓和名
            name_parts = author.split()
            if len(name_parts) > 1:
                surname = name_parts[-1]
                given_names = " ".join(name_parts[:-1])
                # 第一个作者：姓在前，名在后
                if not formatted_authors:
                    formatted_authors.append(f"{surname}, {given_names}")
                else:
                    # 其他作者：名在前，姓在后
                    formatted_authors.append(f"{given_names} {surname}")
            else:
                formatted_authors.append(author)
    
    # 根据MLA格式组合作者
    if len(formatted_authors) == 1:
        return formatted_authors[0]
    elif len(formatted_authors) == 2:
        return formatted_authors[0] + ", and " + formatted_authors[1]
    elif len(formatted_authors) > 2:
        if len(formatted_authors) <= 3:
            return ", ".join(formatted_authors[:-1]) + ", and " + formatted_authors[-1]
        else:
            return formatted_authors[0] + ", et al"
    else:
        return ""


def _format_authors_chicago(authors: List[Any]) -> str:
    """
    格式化Chicago格式的作者列表
    
    Args:
        authors: 作者列表
        
    Returns:
        格式化的作者字符串
    """
    if not authors:
        return ""
    
    formatted_authors = []
    
    for author in authors:
        if isinstance(author, dict):
            if "surname" in author and "given_name" in author:
                # 第一个作者：姓在前，名在后
                if not formatted_authors:
                    formatted_authors.append(f"{author['surname']}, {author['given_name']}")
                else:
                    # 其他作者：名在前，姓在后
                    formatted_authors.append(f"{author['given_name']} {author['surname']}")
            elif "full_name" in author:
                # 尝试从全名中分离姓和名
                name_parts = author["full_name"].split()
                if len(name_parts) > 1:
                    surname = name_parts[-1]
                    given_names = " ".join(name_parts[:-1])
                    # 第一个作者：姓在前，名在后
                    if not formatted_authors:
                        formatted_authors.append(f"{surname}, {given_names}")
                    else:
                        # 其他作者：名在前，姓在后
                        formatted_authors.append(f"{given_names} {surname}")
                else:
                    formatted_authors.append(author["full_name"])
        elif isinstance(author, str):
            # 尝试从字符串中分离姓和名
            name_parts = author.split()
            if len(name_parts) > 1:
                surname = name_parts[-1]
                given_names = " ".join(name_parts[:-1])
                # 第一个作者：姓在前，名在后
                if not formatted_authors:
                    formatted_authors.append(f"{surname}, {given_names}")
                else:
                    # 其他作者：名在前，姓在后
                    formatted_authors.append(f"{given_names} {surname}")
            else:
                formatted_authors.append(author)
    
    # 根据Chicago格式组合作者
    if len(formatted_authors) == 1:
        return formatted_authors[0]
    elif len(formatted_authors) == 2:
        return formatted_authors[0] + " and " + formatted_authors[1]
    elif len(formatted_authors) > 2:
        if len(formatted_authors) <= 7:
            return ", ".join(formatted_authors[:-1]) + ", and " + formatted_authors[-1]
        else:
            return ", ".join(formatted_authors[:7]) + ", et al"
    else:
        return ""


def _format_authors_harvard(authors: List[Any]) -> str:
    """
    格式化Harvard格式的作者列表
    
    Args:
        authors: 作者列表
        
    Returns:
        格式化的作者字符串
    """
    if not authors:
        return ""
    
    formatted_authors = []
    
    for author in authors:
        if isinstance(author, dict):
            if "surname" in author and "given_name" in author:
                # 姓在前，名的首字母在后
                surname = author["surname"]
                given_name_initials = "".join([name[0] + "." for name in author["given_name"].split() if name])
                formatted_authors.append(f"{surname}, {given_name_initials}")
            elif "full_name" in author:
                # 尝试从全名中分离姓和名
                name_parts = author["full_name"].split()
                if len(name_parts) > 1:
                    surname = name_parts[-1]
                    given_names = name_parts[:-1]
                    given_name_initials = "".join([name[0] + "." for name in given_names if name])
                    formatted_authors.append(f"{surname}, {given_name_initials}")
                else:
                    formatted_authors.append(author["full_name"])
        elif isinstance(author, str):
            # 尝试从字符串中分离姓和名
            name_parts = author.split()
            if len(name_parts) > 1:
                surname = name_parts[-1]
                given_names = name_parts[:-1]
                given_name_initials = "".join([name[0] + "." for name in given_names if name])
                formatted_authors.append(f"{surname}, {given_name_initials}")
            else:
                formatted_authors.append(author)
    
    # 根据Harvard格式组合作者
    if len(formatted_authors) == 1:
        return formatted_authors[0]
    elif len(formatted_authors) == 2:
        return formatted_authors[0] + " and " + formatted_authors[1]
    elif len(formatted_authors) > 2:
        if len(formatted_authors) <= 3:
            return ", ".join(formatted_authors[:-1]) + " and " + formatted_authors[-1]
        else:
            return formatted_authors[0] + " et al."
    else:
        return ""


def _format_authors_vancouver(authors: List[Any]) -> str:
    """
    格式化Vancouver格式的作者列表
    
    Args:
        authors: 作者列表
        
    Returns:
        格式化的作者字符串
    """
    if not authors:
        return ""
    
    formatted_authors = []
    
    for author in authors:
        if isinstance(author, dict):
            if "surname" in author and "given_name" in author:
                # 姓在前，名的首字母在后
                surname = author["surname"]
                given_name_initials = "".join([name[0] for name in author["given_name"].split() if name])
                formatted_authors.append(f"{surname} {given_name_initials}")
            elif "full_name" in author:
                # 尝试从全名中分离姓和名
                name_parts = author["full_name"].split()
                if len(name_parts) > 1:
                    surname = name_parts[-1]
                    given_names = name_parts[:-1]
                    given_name_initials = "".join([name[0] for name in given_names if name])
                    formatted_authors.append(f"{surname} {given_name_initials}")
                else:
                    formatted_authors.append(author["full_name"])
        elif isinstance(author, str):
            # 尝试从字符串中分离姓和名
            name_parts = author.split()
            if len(name_parts) > 1:
                surname = name_parts[-1]
                given_names = name_parts[:-1]
                given_name_initials = "".join([name[0] for name in given_names if name])
                formatted_authors.append(f"{surname} {given_name_initials}")
            else:
                formatted_authors.append(author)
    
    # 根据Vancouver格式组合作者
    if len(formatted_authors) == 1:
        return formatted_authors[0]
    elif len(formatted_authors) <= 6:
        return ", ".join(formatted_authors)
    else:
        return ", ".join(formatted_authors[:6]) + ", et al"


def _extract_year(date_str: Optional[str]) -> str:
    """
    从日期字符串中提取年份
    
    Args:
        date_str: 日期字符串
        
    Returns:
        年份字符串
    """
    if not date_str:
        return ""
    
    # 尝试匹配年份
    year_match = re.search(r'\b(19|20)\d{2}\b', date_str)
    if year_match:
        return year_match.group(0)
    
    return ""


def _format_date_apa(date_str: Optional[str]) -> str:
    """
    格式化APA格式的日期
    
    Args:
        date_str: 日期字符串
        
    Returns:
        格式化的日期字符串
    """
    if not date_str:
        return ""
    
    # 提取年份
    year = _extract_year(date_str)
    if year:
        return f"({year})"
    
    return ""


def _format_date_mla(date_str: Optional[str]) -> str:
    """
    格式化MLA格式的日期
    
    Args:
        date_str: 日期字符串
        
    Returns:
        格式化的日期字符串
    """
    if not date_str:
        return ""
    
    # 提取年份
    year = _extract_year(date_str)
    if year:
        return year
    
    return ""


@tool
def generate_citation_apa(article_metadata: Dict[str, Any]) -> str:
    """
    生成APA格式的引用
    
    Args:
        article_metadata (Dict[str, Any]): 文章元数据
        
    Returns:
        str: APA格式的引用
    """
    try:
        # 提取必要的元数据
        authors = article_metadata.get("authors", [])
        title = article_metadata.get("title", "")
        journal = article_metadata.get("journal", "")
        year = _extract_year(article_metadata.get("publication_date", "") or article_metadata.get("year", ""))
        volume = article_metadata.get("volume", "")
        issue = article_metadata.get("issue", "")
        pages = article_metadata.get("pages", "")
        doi = article_metadata.get("doi", "")
        
        # 格式化作者
        formatted_authors = _format_authors_apa(authors)
        
        # 构建引用
        citation = ""
        
        # 作者和年份
        if formatted_authors:
            citation += formatted_authors
            if year:
                citation += f" ({year}). "
            else:
                citation += ". "
        elif year:
            citation += f"({year}). "
        
        # 标题
        if title:
            citation += f"{title}. "
        
        # 期刊信息
        if journal:
            citation += f"{journal}"
            
            # 卷、期和页码
            if volume:
                citation += f", {volume}"
                if issue:
                    citation += f"({issue})"
            
            if pages:
                citation += f", {pages}"
            
            citation += ". "
        
        # DOI
        if doi:
            citation += f"https://doi.org/{doi}"
        
        return citation.strip()
        
    except Exception as e:
        logger.error(f"生成APA引用失败: {str(e)}")
        return f"引用生成错误: {str(e)}"


@tool
def generate_citation_mla(article_metadata: Dict[str, Any]) -> str:
    """
    生成MLA格式的引用
    
    Args:
        article_metadata (Dict[str, Any]): 文章元数据
        
    Returns:
        str: MLA格式的引用
    """
    try:
        # 提取必要的元数据
        authors = article_metadata.get("authors", [])
        title = article_metadata.get("title", "")
        journal = article_metadata.get("journal", "")
        year = _extract_year(article_metadata.get("publication_date", "") or article_metadata.get("year", ""))
        volume = article_metadata.get("volume", "")
        issue = article_metadata.get("issue", "")
        pages = article_metadata.get("pages", "")
        doi = article_metadata.get("doi", "")
        
        # 格式化作者
        formatted_authors = _format_authors_mla(authors)
        
        # 构建引用
        citation = ""
        
        # 作者
        if formatted_authors:
            citation += formatted_authors + ". "
        
        # 标题（加引号）
        if title:
            citation += f'"{title}." '
        
        # 期刊信息（斜体）
        if journal:
            citation += f"*{journal}*"
            
            # 卷和期
            if volume:
                citation += f", vol. {volume}"
                if issue:
                    citation += f", no. {issue}"
            
            # 年份
            if year:
                citation += f", {year}"
            
            # 页码
            if pages:
                citation += f", pp. {pages}"
            
            citation += ". "
        
        # DOI
        if doi:
            citation += f"DOI: {doi}."
        
        return citation.strip()
        
    except Exception as e:
        logger.error(f"生成MLA引用失败: {str(e)}")
        return f"引用生成错误: {str(e)}"


@tool
def generate_citation_chicago(article_metadata: Dict[str, Any]) -> str:
    """
    生成Chicago格式的引用
    
    Args:
        article_metadata (Dict[str, Any]): 文章元数据
        
    Returns:
        str: Chicago格式的引用
    """
    try:
        # 提取必要的元数据
        authors = article_metadata.get("authors", [])
        title = article_metadata.get("title", "")
        journal = article_metadata.get("journal", "")
        year = _extract_year(article_metadata.get("publication_date", "") or article_metadata.get("year", ""))
        volume = article_metadata.get("volume", "")
        issue = article_metadata.get("issue", "")
        pages = article_metadata.get("pages", "")
        doi = article_metadata.get("doi", "")
        
        # 格式化作者
        formatted_authors = _format_authors_chicago(authors)
        
        # 构建引用
        citation = ""
        
        # 作者
        if formatted_authors:
            citation += formatted_authors + ". "
        
        # 标题（加引号）
        if title:
            citation += f'"{title}." '
        
        # 期刊信息（斜体）
        if journal:
            citation += f"*{journal}*"
            
            # 卷和期
            if volume:
                citation += f" {volume}"
                if issue:
                    citation += f", no. {issue}"
            
            # 年份
            if year:
                citation += f" ({year})"
            
            # 页码
            if pages:
                citation += f": {pages}"
            
            citation += ". "
        
        # DOI
        if doi:
            citation += f"https://doi.org/{doi}."
        
        return citation.strip()
        
    except Exception as e:
        logger.error(f"生成Chicago引用失败: {str(e)}")
        return f"引用生成错误: {str(e)}"


@tool
def generate_citation_harvard(article_metadata: Dict[str, Any]) -> str:
    """
    生成Harvard格式的引用
    
    Args:
        article_metadata (Dict[str, Any]): 文章元数据
        
    Returns:
        str: Harvard格式的引用
    """
    try:
        # 提取必要的元数据
        authors = article_metadata.get("authors", [])
        title = article_metadata.get("title", "")
        journal = article_metadata.get("journal", "")
        year = _extract_year(article_metadata.get("publication_date", "") or article_metadata.get("year", ""))
        volume = article_metadata.get("volume", "")
        issue = article_metadata.get("issue", "")
        pages = article_metadata.get("pages", "")
        doi = article_metadata.get("doi", "")
        
        # 格式化作者
        formatted_authors = _format_authors_harvard(authors)
        
        # 构建引用
        citation = ""
        
        # 作者和年份
        if formatted_authors:
            citation += formatted_authors
            if year:
                citation += f" {year}, "
            else:
                citation += ", "
        elif year:
            citation += f"{year}, "
        
        # 标题
        if title:
            citation += f"'{title}', "
        
        # 期刊信息（斜体）
        if journal:
            citation += f"*{journal}*"
            
            # 卷和期
            if volume:
                citation += f", vol. {volume}"
                if issue:
                    citation += f", no. {issue}"
            
            # 页码
            if pages:
                citation += f", pp. {pages}"
            
            citation += ". "
        
        # DOI
        if doi:
            citation += f"DOI: {doi}."
        
        return citation.strip()
        
    except Exception as e:
        logger.error(f"生成Harvard引用失败: {str(e)}")
        return f"引用生成错误: {str(e)}"


@tool
def generate_citation_vancouver(article_metadata: Dict[str, Any]) -> str:
    """
    生成Vancouver格式的引用
    
    Args:
        article_metadata (Dict[str, Any]): 文章元数据
        
    Returns:
        str: Vancouver格式的引用
    """
    try:
        # 提取必要的元数据
        authors = article_metadata.get("authors", [])
        title = article_metadata.get("title", "")
        journal = article_metadata.get("journal", "")
        year = _extract_year(article_metadata.get("publication_date", "") or article_metadata.get("year", ""))
        volume = article_metadata.get("volume", "")
        issue = article_metadata.get("issue", "")
        pages = article_metadata.get("pages", "")
        doi = article_metadata.get("doi", "")
        
        # 格式化作者
        formatted_authors = _format_authors_vancouver(authors)
        
        # 构建引用
        citation = ""
        
        # 作者
        if formatted_authors:
            citation += formatted_authors + ". "
        
        # 标题
        if title:
            citation += f"{title}. "
        
        # 期刊信息（缩写）
        if journal:
            citation += f"{journal} "
            
            # 年份
            if year:
                citation += f"{year}"
            
            # 卷和期
            if volume:
                citation += f";{volume}"
                if issue:
                    citation += f"({issue})"
            
            # 页码
            if pages:
                citation += f":{pages}"
            
            citation += ". "
        
        # DOI
        if doi:
            citation += f"doi: {doi}."
        
        return citation.strip()
        
    except Exception as e:
        logger.error(f"生成Vancouver引用失败: {str(e)}")
        return f"引用生成错误: {str(e)}"


@tool
def generate_all_citations(article_metadata: Dict[str, Any]) -> str:
    """
    生成所有格式的引用
    
    Args:
        article_metadata (Dict[str, Any]): 文章元数据
        
    Returns:
        str: JSON格式的所有引用格式
    """
    try:
        # 生成各种格式的引用
        apa_citation = generate_citation_apa(article_metadata)
        mla_citation = generate_citation_mla(article_metadata)
        chicago_citation = generate_citation_chicago(article_metadata)
        harvard_citation = generate_citation_harvard(article_metadata)
        vancouver_citation = generate_citation_vancouver(article_metadata)
        
        # 构建结果
        citations = {
            "status": "success",
            "article_id": article_metadata.get("pmcid", article_metadata.get("pmid", "unknown")),
            "article_title": article_metadata.get("title", "Untitled"),
            "citations": {
                "apa": apa_citation,
                "mla": mla_citation,
                "chicago": chicago_citation,
                "harvard": harvard_citation,
                "vancouver": vancouver_citation
            }
        }
        
        return json.dumps(citations, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"生成所有引用失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"生成所有引用失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def batch_generate_citations(articles: List[Dict[str, Any]], format_type: str = "apa") -> str:
    """
    批量生成引用
    
    Args:
        articles (List[Dict[str, Any]]): 文章元数据列表
        format_type (str): 引用格式类型 (apa, mla, chicago, harvard, vancouver, all)
        
    Returns:
        str: JSON格式的批量引用结果
    """
    try:
        # 验证格式类型
        valid_formats = ["apa", "mla", "chicago", "harvard", "vancouver", "all"]
        if format_type.lower() not in valid_formats:
            return json.dumps({
                "status": "error",
                "message": f"无效的引用格式类型: {format_type}。请使用以下之一: {', '.join(valid_formats)}"
            }, ensure_ascii=False)
        
        # 批量生成引用
        citations = []
        
        for article in articles:
            citation_result = {}
            
            # 添加文章标识信息
            citation_result["article_id"] = article.get("pmcid", article.get("pmid", "unknown"))
            citation_result["article_title"] = article.get("title", "Untitled")
            
            # 根据格式类型生成引用
            if format_type.lower() == "all":
                citation_result["citations"] = {
                    "apa": generate_citation_apa(article),
                    "mla": generate_citation_mla(article),
                    "chicago": generate_citation_chicago(article),
                    "harvard": generate_citation_harvard(article),
                    "vancouver": generate_citation_vancouver(article)
                }
            else:
                # 调用相应的引用生成函数
                if format_type.lower() == "apa":
                    citation_result["citation"] = generate_citation_apa(article)
                elif format_type.lower() == "mla":
                    citation_result["citation"] = generate_citation_mla(article)
                elif format_type.lower() == "chicago":
                    citation_result["citation"] = generate_citation_chicago(article)
                elif format_type.lower() == "harvard":
                    citation_result["citation"] = generate_citation_harvard(article)
                elif format_type.lower() == "vancouver":
                    citation_result["citation"] = generate_citation_vancouver(article)
            
            citations.append(citation_result)
        
        # 构建结果
        batch_result = {
            "status": "success",
            "format_type": format_type,
            "total_articles": len(articles),
            "citations": citations
        }
        
        return json.dumps(batch_result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"批量生成引用失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"批量生成引用失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def format_bibliography(citations: List[str], format_type: str = "apa") -> str:
    """
    格式化参考文献列表
    
    Args:
        citations (List[str]): 引用列表
        format_type (str): 引用格式类型 (apa, mla, chicago, harvard, vancouver)
        
    Returns:
        str: 格式化的参考文献列表
    """
    try:
        # 验证格式类型
        valid_formats = ["apa", "mla", "chicago", "harvard", "vancouver"]
        if format_type.lower() not in valid_formats:
            return json.dumps({
                "status": "error",
                "message": f"无效的引用格式类型: {format_type}。请使用以下之一: {', '.join(valid_formats)}"
            }, ensure_ascii=False)
        
        # 根据格式类型设置标题
        titles = {
            "apa": "References",
            "mla": "Works Cited",
            "chicago": "Bibliography",
            "harvard": "Reference List",
            "vancouver": "References"
        }
        
        title = titles.get(format_type.lower(), "References")
        
        # 构建参考文献列表
        bibliography = f"{title}\n\n"
        
        for citation in citations:
            if citation.strip():
                bibliography += f"{citation}\n\n"
        
        return bibliography.strip()
        
    except Exception as e:
        logger.error(f"格式化参考文献列表失败: {str(e)}")
        return f"格式化参考文献列表失败: {str(e)}"