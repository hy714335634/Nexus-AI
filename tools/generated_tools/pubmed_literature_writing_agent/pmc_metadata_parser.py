#!/usr/bin/env python3
"""
PMC Metadata Parser Tool

提供PubMed Central文章元数据和内容的解析功能
支持XML和TXT格式的文章解析
"""

import json
import re
import os
from typing import Dict, List, Any, Optional, Union
import logging
from pathlib import Path
import xml.etree.ElementTree as ET
from datetime import datetime

from strands import tool

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 本地缓存目录
CACHE_DIR = Path(".cache/pubmed_literature_agent")


@tool
def parse_pmc_xml(xml_content: str) -> str:
    """
    解析PMC XML格式的文章内容
    
    Args:
        xml_content (str): XML格式的文章内容
        
    Returns:
        str: JSON格式的解析结果
    """
    try:
        # 处理可能的XML声明问题
        if not xml_content.strip().startswith('<?xml'):
            xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_content
        
        # 解析XML
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            # 尝试修复常见的XML问题
            xml_content = re.sub(r'&(?!amp;|lt;|gt;|apos;|quot;)', '&amp;', xml_content)
            try:
                root = ET.fromstring(xml_content)
            except ET.ParseError as e:
                return json.dumps({
                    "status": "error",
                    "message": f"XML解析失败: {str(e)}",
                    "content_preview": xml_content[:200] + "..."
                }, ensure_ascii=False)
        
        # 提取文章元数据
        metadata = {}
        
        # 提取PMCID
        pmcid_elem = root.find(".//article-id[@pub-id-type='pmc']")
        if pmcid_elem is not None and pmcid_elem.text:
            metadata["pmcid"] = pmcid_elem.text
        
        # 提取PMID
        pmid_elem = root.find(".//article-id[@pub-id-type='pmid']")
        if pmid_elem is not None and pmid_elem.text:
            metadata["pmid"] = pmid_elem.text
        
        # 提取DOI
        doi_elem = root.find(".//article-id[@pub-id-type='doi']")
        if doi_elem is not None and doi_elem.text:
            metadata["doi"] = doi_elem.text
        
        # 提取标题
        title_elem = root.find(".//article-title")
        if title_elem is not None:
            title_text = ''.join(title_elem.itertext())
            metadata["title"] = title_text.strip()
        
        # 提取期刊信息
        journal_elem = root.find(".//journal-title")
        if journal_elem is not None and journal_elem.text:
            metadata["journal"] = journal_elem.text.strip()
        
        # 提取发布日期
        pub_date = root.find(".//pub-date")
        if pub_date is not None:
            year = pub_date.find("year")
            month = pub_date.find("month")
            day = pub_date.find("day")
            
            date_parts = []
            if year is not None and year.text:
                date_parts.append(year.text)
            if month is not None and month.text:
                date_parts.append(month.text.zfill(2))
            if day is not None and day.text:
                date_parts.append(day.text.zfill(2))
            
            if date_parts:
                metadata["publication_date"] = "-".join(date_parts)
        
        # 提取作者信息
        authors = []
        for contrib in root.findall(".//contrib[@contrib-type='author']"):
            author = {}
            
            # 姓
            surname = contrib.find("./name/surname")
            if surname is not None and surname.text:
                author["surname"] = surname.text
            
            # 名
            given_name = contrib.find("./name/given-names")
            if given_name is not None and given_name.text:
                author["given_name"] = given_name.text
            
            # 合并姓名
            if "surname" in author or "given_name" in author:
                author["full_name"] = " ".join(filter(None, [
                    author.get("given_name", ""),
                    author.get("surname", "")
                ]))
            
            # 机构
            affiliations = []
            for aff in contrib.findall(".//aff"):
                if aff.text:
                    affiliations.append(aff.text.strip())
            if affiliations:
                author["affiliations"] = affiliations
            
            # 添加到作者列表
            if author:
                authors.append(author)
        
        if authors:
            metadata["authors"] = authors
        
        # 提取摘要
        abstract = []
        abstract_elem = root.find(".//abstract")
        if abstract_elem is not None:
            for p in abstract_elem.findall(".//p"):
                if p.text:
                    abstract.append(p.text.strip())
            
            if not abstract:  # 如果没有找到<p>标签
                abstract_text = ''.join(abstract_elem.itertext())
                if abstract_text:
                    abstract = [abstract_text.strip()]
        
        if abstract:
            metadata["abstract"] = abstract
        
        # 提取关键词
        keywords = []
        for kwd in root.findall(".//kwd"):
            if kwd.text:
                keywords.append(kwd.text.strip())
        
        if keywords:
            metadata["keywords"] = keywords
        
        # 提取全文段落
        body_text = []
        body_elem = root.find(".//body")
        if body_elem is not None:
            for section in body_elem.findall(".//sec"):
                section_data = {"type": "section"}
                
                # 提取章节标题
                title_elem = section.find("./title")
                if title_elem is not None:
                    title_text = ''.join(title_elem.itertext())
                    section_data["title"] = title_text.strip()
                
                # 提取章节内容
                paragraphs = []
                for p in section.findall("./p"):
                    p_text = ''.join(p.itertext())
                    if p_text.strip():
                        paragraphs.append(p_text.strip())
                
                if paragraphs:
                    section_data["content"] = paragraphs
                
                if "title" in section_data or "content" in section_data:
                    body_text.append(section_data)
        
        if body_text:
            metadata["body_text"] = body_text
        
        # 提取参考文献
        references = []
        ref_list = root.find(".//ref-list")
        if ref_list is not None:
            for ref in ref_list.findall("./ref"):
                ref_data = {}
                
                # 提取引用ID
                ref_id = ref.get("id")
                if ref_id:
                    ref_data["id"] = ref_id
                
                # 提取引用文本
                mixed_citation = ref.find("./mixed-citation") or ref.find("./citation") or ref.find("./element-citation")
                if mixed_citation is not None:
                    citation_text = ''.join(mixed_citation.itertext())
                    ref_data["text"] = citation_text.strip()
                
                if ref_data:
                    references.append(ref_data)
        
        if references:
            metadata["references"] = references
        
        # 提取文章类型
        article_type = root.find(".//article").get("article-type") if root.find(".//article") is not None else None
        if article_type:
            metadata["article_type"] = article_type
        
        # 提取版权信息
        copyright_elem = root.find(".//copyright-statement")
        if copyright_elem is not None and copyright_elem.text:
            metadata["copyright"] = copyright_elem.text.strip()
        
        # 提取许可信息
        license_elem = root.find(".//license")
        if license_elem is not None:
            license_url = license_elem.get("xlink:href") or license_elem.get("href")
            if license_url:
                metadata["license_url"] = license_url
            
            license_text = license_elem.find(".//license-p")
            if license_text is not None:
                license_content = ''.join(license_text.itertext())
                if license_content:
                    metadata["license_text"] = license_content.strip()
        
        return json.dumps({
            "status": "success",
            "format": "xml",
            "metadata": metadata
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"解析PMC XML失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"解析PMC XML失败: {str(e)}",
            "content_preview": xml_content[:200] + "..." if len(xml_content) > 200 else xml_content
        }, ensure_ascii=False)


@tool
def parse_pmc_txt(txt_content: str) -> str:
    """
    解析PMC TXT格式的文章内容
    
    Args:
        txt_content (str): TXT格式的文章内容
        
    Returns:
        str: JSON格式的解析结果
    """
    try:
        metadata = {}
        lines = txt_content.split('\n')
        
        # 提取PMCID
        pmcid_match = re.search(r'PMCID:\s*(PMC\d+)', txt_content)
        if pmcid_match:
            metadata["pmcid"] = pmcid_match.group(1)
        
        # 提取PMID
        pmid_match = re.search(r'PMID:\s*(\d+)', txt_content)
        if pmid_match:
            metadata["pmid"] = pmid_match.group(1)
        
        # 提取DOI
        doi_match = re.search(r'DOI:\s*(10\.\d+/[^\s]+)', txt_content)
        if doi_match:
            metadata["doi"] = doi_match.group(1)
        
        # 提取标题 (假设标题在文件的开头几行)
        title_lines = []
        for i in range(min(5, len(lines))):
            if lines[i].strip() and not any(x in lines[i].lower() for x in ['pmcid', 'pmid', 'doi', 'copyright']):
                title_lines.append(lines[i].strip())
        
        if title_lines:
            metadata["title"] = ' '.join(title_lines)
        
        # 提取期刊信息
        journal_match = re.search(r'([\w\s]+)\.\s*\d{4}\s*;', txt_content)
        if journal_match:
            metadata["journal"] = journal_match.group(1).strip()
        
        # 提取发布日期
        date_match = re.search(r'(\d{4}\s+\w+\s+\d{1,2}|\d{4}-\d{2}-\d{2}|\w+\s+\d{1,2},\s*\d{4})', txt_content)
        if date_match:
            metadata["publication_date"] = date_match.group(1)
        
        # 提取作者信息 (这比较复杂，简化处理)
        author_section = None
        for i, line in enumerate(lines[:20]):  # 只在前20行中查找
            if re.search(r'^AUTHORS?:|^BY\s+:', line, re.IGNORECASE):
                author_section = line.split(':', 1)[1].strip()
                break
        
        if author_section:
            # 简单分割作者
            authors = []
            for author_name in re.split(r',\s*|\s+and\s+', author_section):
                if author_name.strip():
                    authors.append({"full_name": author_name.strip()})
            
            if authors:
                metadata["authors"] = authors
        
        # 提取摘要
        abstract = []
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
            for i in range(abstract_start, abstract_end):
                if i < len(lines) and lines[i].strip():
                    abstract.append(lines[i].strip())
        
        if abstract:
            metadata["abstract"] = abstract
        
        # 提取关键词
        keywords = []
        for i, line in enumerate(lines):
            if re.match(r'^KEYWORDS\s*:?$', line, re.IGNORECASE):
                if i + 1 < len(lines) and lines[i + 1].strip():
                    keywords_text = lines[i + 1].strip()
                    for kw in re.split(r'[,;]\s*', keywords_text):
                        if kw.strip():
                            keywords.append(kw.strip())
                break
        
        if keywords:
            metadata["keywords"] = keywords
        
        # 提取正文 (简化处理，将剩余内容分成段落)
        body_start = None
        for i, line in enumerate(lines):
            if re.match(r'^INTRODUCTION|^BACKGROUND|^METHODS', line, re.IGNORECASE):
                body_start = i
                break
        
        if body_start:
            body_text = []
            current_section = {"type": "section", "title": lines[body_start].strip(), "content": []}
            
            for i in range(body_start + 1, len(lines)):
                line = lines[i].strip()
                
                if not line:
                    continue
                
                # 检查是否是新的章节标题
                if re.match(r'^[A-Z\s]{3,}$', line) and len(line) < 50:
                    # 保存当前章节
                    if current_section["content"]:
                        body_text.append(current_section)
                    
                    # 创建新章节
                    current_section = {"type": "section", "title": line, "content": []}
                else:
                    current_section["content"].append(line)
            
            # 添加最后一个章节
            if current_section["content"]:
                body_text.append(current_section)
            
            if body_text:
                metadata["body_text"] = body_text
        
        # 提取参考文献
        references = []
        ref_start = None
        
        for i, line in enumerate(lines):
            if re.match(r'^REFERENCES$|^BIBLIOGRAPHY$|^LITERATURE CITED$', line, re.IGNORECASE):
                ref_start = i + 1
                break
        
        if ref_start:
            current_ref = ""
            
            for i in range(ref_start, len(lines)):
                line = lines[i].strip()
                
                if not line:
                    if current_ref:
                        references.append({"text": current_ref})
                        current_ref = ""
                else:
                    if re.match(r'^\d+\.', line):  # 新的编号引用
                        if current_ref:
                            references.append({"text": current_ref})
                        current_ref = line
                    else:
                        current_ref += " " + line
            
            # 添加最后一个引用
            if current_ref:
                references.append({"text": current_ref})
        
        if references:
            metadata["references"] = references
        
        return json.dumps({
            "status": "success",
            "format": "txt",
            "metadata": metadata
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"解析PMC TXT失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"解析PMC TXT失败: {str(e)}",
            "content_preview": txt_content[:200] + "..." if len(txt_content) > 200 else txt_content
        }, ensure_ascii=False)


@tool
def parse_pmc_content(content: str, format_type: str = None) -> str:
    """
    自动检测并解析PMC文章内容
    
    Args:
        content (str): 文章内容
        format_type (str): 内容格式类型 (xml, txt)，如果不提供则自动检测
        
    Returns:
        str: JSON格式的解析结果
    """
    try:
        # 自动检测格式类型
        if format_type is None:
            if content.strip().startswith('<?xml') or content.strip().startswith('<'):
                format_type = 'xml'
            else:
                format_type = 'txt'
        
        # 根据格式类型调用相应的解析函数
        if format_type.lower() == 'xml':
            return parse_pmc_xml(content)
        elif format_type.lower() == 'txt':
            return parse_pmc_txt(content)
        else:
            return json.dumps({
                "status": "error",
                "message": f"不支持的格式类型: {format_type}",
                "content_preview": content[:200] + "..." if len(content) > 200 else content
            }, ensure_ascii=False)
            
    except Exception as e:
        logger.error(f"解析PMC内容失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"解析PMC内容失败: {str(e)}",
            "content_preview": content[:200] + "..." if len(content) > 200 else content
        }, ensure_ascii=False)


@tool
def extract_pmc_metadata_from_file(file_path: str, format_type: str = None) -> str:
    """
    从文件中提取PMC元数据
    
    Args:
        file_path (str): 文件路径
        format_type (str): 内容格式类型 (xml, txt)，如果不提供则自动检测
        
    Returns:
        str: JSON格式的元数据
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return json.dumps({
                "status": "error",
                "message": f"文件不存在: {file_path}"
            }, ensure_ascii=False)
        
        # 自动检测格式类型
        if format_type is None:
            if file_path.endswith('.xml'):
                format_type = 'xml'
            elif file_path.endswith('.txt'):
                format_type = 'txt'
            else:
                # 读取文件的前几行来判断
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    first_line = f.readline().strip()
                    if first_line.startswith('<?xml') or first_line.startswith('<'):
                        format_type = 'xml'
                    else:
                        format_type = 'txt'
        
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # 解析内容
        result = parse_pmc_content(content, format_type)
        
        # 添加文件信息
        result_dict = json.loads(result)
        if result_dict.get("status") == "success":
            result_dict["file_info"] = {
                "path": file_path,
                "size": os.path.getsize(file_path),
                "last_modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
            }
            
            return json.dumps(result_dict, ensure_ascii=False, indent=2)
        else:
            return result
            
    except Exception as e:
        logger.error(f"从文件提取元数据失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"从文件提取元数据失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def extract_pmc_citations(metadata_json: str) -> str:
    """
    从PMC元数据中提取引用信息
    
    Args:
        metadata_json (str): JSON格式的PMC元数据
        
    Returns:
        str: JSON格式的引用信息
    """
    try:
        # 解析元数据
        try:
            metadata = json.loads(metadata_json)
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
        except:
            return json.dumps({
                "status": "error",
                "message": "无效的JSON元数据"
            }, ensure_ascii=False)
        
        # 提取元数据中的引用信息
        references = []
        
        # 处理嵌套结构
        if "metadata" in metadata:
            metadata = metadata["metadata"]
        
        # 提取引用列表
        if "references" in metadata:
            for ref in metadata["references"]:
                if isinstance(ref, dict):
                    references.append(ref)
                else:
                    references.append({"text": str(ref)})
        
        # 如果没有引用，尝试从正文中提取可能的引用
        if not references and "body_text" in metadata:
            # 在正文中查找可能的引用模式
            ref_patterns = [
                r'\[\d+\]',  # [1], [2], etc.
                r'\(\w+\s+et\s+al\.\s*,\s*\d{4}\)',  # (Smith et al., 2020)
                r'\(\w+\s+and\s+\w+\s*,\s*\d{4}\)'   # (Smith and Jones, 2020)
            ]
            
            potential_refs = set()
            
            for section in metadata["body_text"]:
                if "content" in section:
                    for paragraph in section["content"]:
                        for pattern in ref_patterns:
                            matches = re.findall(pattern, paragraph)
                            potential_refs.update(matches)
            
            # 将可能的引用添加到列表中
            for ref in sorted(potential_refs):
                references.append({"text": ref, "extracted_from": "body_text"})
        
        return json.dumps({
            "status": "success",
            "citation_count": len(references),
            "citations": references
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"提取引用信息失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"提取引用信息失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def extract_pmc_sections(metadata_json: str) -> str:
    """
    从PMC元数据中提取文章章节结构
    
    Args:
        metadata_json (str): JSON格式的PMC元数据
        
    Returns:
        str: JSON格式的章节结构
    """
    try:
        # 解析元数据
        try:
            metadata = json.loads(metadata_json)
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
        except:
            return json.dumps({
                "status": "error",
                "message": "无效的JSON元数据"
            }, ensure_ascii=False)
        
        # 提取章节结构
        sections = []
        
        # 处理嵌套结构
        if "metadata" in metadata:
            metadata = metadata["metadata"]
        
        # 从body_text中提取章节
        if "body_text" in metadata:
            for section in metadata["body_text"]:
                if isinstance(section, dict):
                    section_info = {
                        "title": section.get("title", "Untitled Section"),
                        "content_length": sum(len(p) for p in section.get("content", [])),
                        "paragraph_count": len(section.get("content", []))
                    }
                    
                    # 提取章节的前几个段落作为摘要
                    if "content" in section and section["content"]:
                        preview = section["content"][0]
                        if len(preview) > 200:
                            preview = preview[:197] + "..."
                        section_info["preview"] = preview
                    
                    sections.append(section_info)
        
        # 如果没有找到章节，尝试从文本中提取可能的章节标题
        if not sections and "abstract" in metadata:
            sections.append({
                "title": "Abstract",
                "content_length": sum(len(p) for p in metadata["abstract"]) if isinstance(metadata["abstract"], list) else len(metadata["abstract"]),
                "paragraph_count": len(metadata["abstract"]) if isinstance(metadata["abstract"], list) else 1,
                "preview": metadata["abstract"][0][:200] + "..." if isinstance(metadata["abstract"], list) and metadata["abstract"] else "No preview available"
            })
        
        return json.dumps({
            "status": "success",
            "section_count": len(sections),
            "sections": sections
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"提取章节结构失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"提取章节结构失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def extract_pmc_keywords(metadata_json: str, generate_if_missing: bool = True) -> str:
    """
    从PMC元数据中提取或生成关键词
    
    Args:
        metadata_json (str): JSON格式的PMC元数据
        generate_if_missing (bool): 如果元数据中没有关键词，是否自动生成
        
    Returns:
        str: JSON格式的关键词列表
    """
    try:
        # 解析元数据
        try:
            metadata = json.loads(metadata_json)
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
        except:
            return json.dumps({
                "status": "error",
                "message": "无效的JSON元数据"
            }, ensure_ascii=False)
        
        # 处理嵌套结构
        if "metadata" in metadata:
            metadata = metadata["metadata"]
        
        # 提取关键词
        keywords = []
        
        # 从元数据中提取显式的关键词
        if "keywords" in metadata:
            keywords = metadata["keywords"]
        
        # 如果没有找到关键词且需要生成
        if not keywords and generate_if_missing:
            # 从标题和摘要中提取潜在的关键词
            text_to_analyze = ""
            
            if "title" in metadata:
                text_to_analyze += metadata["title"] + " "
            
            if "abstract" in metadata:
                if isinstance(metadata["abstract"], list):
                    text_to_analyze += " ".join(metadata["abstract"])
                else:
                    text_to_analyze += metadata["abstract"]
            
            # 简单的关键词提取算法
            # 1. 分词
            words = re.findall(r'\b[a-zA-Z][\w-]*\b', text_to_analyze.lower())
            
            # 2. 过滤常见停用词
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'if', 'because', 'as', 'what',
                         'which', 'this', 'that', 'these', 'those', 'then', 'just', 'so', 'than',
                         'such', 'both', 'through', 'about', 'for', 'is', 'of', 'while', 'during',
                         'to', 'from', 'in', 'on', 'by', 'with', 'without', 'at', 'between'}
            
            filtered_words = [word for word in words if word not in stop_words and len(word) > 3]
            
            # 3. 计算词频
            word_freq = {}
            for word in filtered_words:
                word_freq[word] = word_freq.get(word, 0) + 1
            
            # 4. 提取高频词作为关键词
            top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
            keywords = [word for word, freq in top_keywords]
            
            # 5. 尝试提取多词短语
            phrases = re.findall(r'\b[a-zA-Z][\w-]*\s+[a-zA-Z][\w-]*\b', text_to_analyze.lower())
            phrase_freq = {}
            for phrase in phrases:
                if not any(word in stop_words for word in phrase.split()):
                    phrase_freq[phrase] = phrase_freq.get(phrase, 0) + 1
            
            # 添加高频短语
            top_phrases = sorted(phrase_freq.items(), key=lambda x: x[1], reverse=True)[:5]
            keywords.extend([phrase for phrase, freq in top_phrases])
        
        return json.dumps({
            "status": "success",
            "keyword_count": len(keywords),
            "keywords": keywords,
            "generated": not "keywords" in metadata and generate_if_missing
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"提取关键词失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"提取关键词失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def merge_pmc_metadata(metadata_list: List[str]) -> str:
    """
    合并多个PMC元数据对象
    
    Args:
        metadata_list (List[str]): JSON格式的PMC元数据列表
        
    Returns:
        str: JSON格式的合并元数据
    """
    try:
        merged_data = {
            "articles": [],
            "summary": {
                "total_articles": 0,
                "journals": set(),
                "publication_years": set(),
                "unique_authors": set()
            }
        }
        
        for metadata_json in metadata_list:
            try:
                # 解析元数据
                metadata = json.loads(metadata_json)
                
                # 处理嵌套结构
                if "metadata" in metadata:
                    metadata = metadata["metadata"]
                
                # 添加到文章列表
                merged_data["articles"].append(metadata)
                
                # 更新摘要信息
                merged_data["summary"]["total_articles"] += 1
                
                if "journal" in metadata:
                    merged_data["summary"]["journals"].add(metadata["journal"])
                
                if "publication_date" in metadata:
                    # 提取年份
                    year_match = re.search(r'\b(19|20)\d{2}\b', metadata["publication_date"])
                    if year_match:
                        merged_data["summary"]["publication_years"].add(year_match.group(0))
                
                if "authors" in metadata:
                    for author in metadata["authors"]:
                        if isinstance(author, dict) and "full_name" in author:
                            merged_data["summary"]["unique_authors"].add(author["full_name"])
                
            except Exception as e:
                logger.warning(f"处理元数据时出错: {str(e)}")
                continue
        
        # 将集合转换为列表以便JSON序列化
        merged_data["summary"]["journals"] = list(merged_data["summary"]["journals"])
        merged_data["summary"]["publication_years"] = list(merged_data["summary"]["publication_years"])
        merged_data["summary"]["unique_authors"] = list(merged_data["summary"]["unique_authors"])
        
        # 添加额外的摘要信息
        merged_data["summary"]["journal_count"] = len(merged_data["summary"]["journals"])
        merged_data["summary"]["author_count"] = len(merged_data["summary"]["unique_authors"])
        merged_data["summary"]["year_range"] = f"{min(merged_data['summary']['publication_years']) if merged_data['summary']['publication_years'] else 'N/A'}-{max(merged_data['summary']['publication_years']) if merged_data['summary']['publication_years'] else 'N/A'}"
        
        return json.dumps({
            "status": "success",
            "merged_data": merged_data
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"合并元数据失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"合并元数据失败: {str(e)}"
        }, ensure_ascii=False)