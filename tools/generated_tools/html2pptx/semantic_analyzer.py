"""
语义分析工具，用于分析HTML的语义结构。

此模块提供了一组工具函数，用于分析HTML文档的语义结构、识别重要内容、
提取主题和关键信息，以便在PPT中合理组织内容。
"""

import re
import json
import math
from typing import Dict, List, Any, Optional, Tuple, Union
from collections import Counter
from bs4 import BeautifulSoup, Tag, NavigableString
import nltk
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from strands import tool


@tool
def analyze_document_structure(
    html_content: str,
    parser: str = "html.parser",
    max_depth: int = 5
) -> str:
    """
    分析HTML文档的语义结构。

    Args:
        html_content (str): HTML文档内容或文件路径
        parser (str): 解析器类型，可选值: "html.parser", "lxml", "html5lib"
        max_depth (int): 分析的最大深度
        
    Returns:
        str: JSON格式的文档结构分析结果
    """
    try:
        # 检查输入是否为文件路径
        if html_content.strip().startswith(('<', '<!DOCTYPE')):
            # 这是HTML内容
            pass
        else:
            # 尝试作为文件路径读取
            try:
                with open(html_content, 'r', encoding='utf-8') as f:
                    html_content = f.read()
            except:
                # 如果无法作为文件读取，假设它是HTML内容
                pass
        
        # 解析HTML
        soup = BeautifulSoup(html_content, parser)
        
        # 提取文档基本信息
        doc_info = {
            "title": soup.title.string.strip() if soup.title else "Untitled Document",
            "lang": soup.html.get('lang') if soup.html else None,
            "meta_description": _get_meta_description(soup),
            "has_header": bool(soup.header),
            "has_footer": bool(soup.footer),
            "has_nav": bool(soup.nav),
            "has_main": bool(soup.main),
            "has_article": bool(soup.find('article')),
            "has_aside": bool(soup.find('aside'))
        }
        
        # 分析文档结构
        structure = _analyze_structure(soup, max_depth)
        
        # 提取主要内容区域
        main_content = _identify_main_content(soup)
        
        # 分析标题层次结构
        headings = _analyze_headings(soup)
        
        # 分析语义分区
        sections = _analyze_sections(soup)
        
        # 构建响应
        response = {
            "status": "success",
            "document_info": doc_info,
            "structure": structure,
            "main_content": main_content,
            "headings": headings,
            "sections": sections
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "文档结构分析失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def extract_key_content(
    html_content: str,
    parser: str = "html.parser",
    content_type: str = "all"
) -> str:
    """
    从HTML文档中提取关键内容。

    Args:
        html_content (str): HTML文档内容或文件路径
        parser (str): 解析器类型，可选值: "html.parser", "lxml", "html5lib"
        content_type (str): 内容类型，可选值: "all", "headings", "paragraphs", "lists", "tables", "quotes"
        
    Returns:
        str: JSON格式的关键内容
    """
    try:
        # 检查输入是否为文件路径
        if html_content.strip().startswith(('<', '<!DOCTYPE')):
            # 这是HTML内容
            pass
        else:
            # 尝试作为文件路径读取
            try:
                with open(html_content, 'r', encoding='utf-8') as f:
                    html_content = f.read()
            except:
                # 如果无法作为文件读取，假设它是HTML内容
                pass
        
        # 解析HTML
        soup = BeautifulSoup(html_content, parser)
        
        # 初始化结果
        result = {}
        
        # 提取标题
        if content_type in ["all", "headings"]:
            headings = []
            for i in range(1, 7):
                for heading in soup.find_all(f'h{i}'):
                    headings.append({
                        "level": i,
                        "text": heading.get_text(strip=True),
                        "id": heading.get('id', ''),
                        "importance": 7 - i  # h1最重要，h6最不重要
                    })
            result["headings"] = headings
        
        # 提取段落
        if content_type in ["all", "paragraphs"]:
            paragraphs = []
            for p in soup.find_all('p'):
                text = p.get_text(strip=True)
                if text:  # 忽略空段落
                    paragraphs.append({
                        "text": text,
                        "length": len(text),
                        "importance": _calculate_text_importance(text)
                    })
            result["paragraphs"] = paragraphs
        
        # 提取列表
        if content_type in ["all", "lists"]:
            lists = []
            for list_tag in soup.find_all(['ul', 'ol']):
                items = []
                for li in list_tag.find_all('li', recursive=False):
                    items.append(li.get_text(strip=True))
                
                if items:  # 忽略空列表
                    lists.append({
                        "type": list_tag.name,  # ul或ol
                        "items": items,
                        "item_count": len(items)
                    })
            result["lists"] = lists
        
        # 提取表格
        if content_type in ["all", "tables"]:
            tables = []
            for table in soup.find_all('table'):
                table_data = []
                headers = []
                
                # 提取表头
                thead = table.find('thead')
                if thead:
                    header_row = thead.find('tr')
                    if header_row:
                        headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
                
                # 如果没有thead，尝试使用第一行作为表头
                if not headers:
                    first_row = table.find('tr')
                    if first_row:
                        headers = [th.get_text(strip=True) for th in first_row.find_all(['th', 'td'])]
                
                # 提取表格数据
                tbody = table.find('tbody') or table
                for row in tbody.find_all('tr'):
                    row_data = [cell.get_text(strip=True) for cell in row.find_all(['td', 'th'])]
                    if row_data and row_data != headers:  # 避免重复表头
                        table_data.append(row_data)
                
                if table_data:  # 忽略空表格
                    tables.append({
                        "headers": headers,
                        "data": table_data,
                        "rows": len(table_data),
                        "columns": len(headers) if headers else (len(table_data[0]) if table_data else 0)
                    })
            result["tables"] = tables
        
        # 提取引用
        if content_type in ["all", "quotes"]:
            quotes = []
            for quote in soup.find_all('blockquote'):
                text = quote.get_text(strip=True)
                if text:  # 忽略空引用
                    quotes.append({
                        "text": text,
                        "cite": quote.get('cite', '')
                    })
            result["quotes"] = quotes
        
        # 构建响应
        response = {
            "status": "success",
            "content_type": content_type,
            "content": result
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "关键内容提取失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def identify_key_topics(
    html_content: str,
    parser: str = "html.parser",
    max_topics: int = 5
) -> str:
    """
    从HTML文档中识别关键主题。

    Args:
        html_content (str): HTML文档内容或文件路径
        parser (str): 解析器类型，可选值: "html.parser", "lxml", "html5lib"
        max_topics (int): 最大主题数量
        
    Returns:
        str: JSON格式的关键主题
    """
    try:
        # 检查输入是否为文件路径
        if html_content.strip().startswith(('<', '<!DOCTYPE')):
            # 这是HTML内容
            pass
        else:
            # 尝试作为文件路径读取
            try:
                with open(html_content, 'r', encoding='utf-8') as f:
                    html_content = f.read()
            except:
                # 如果无法作为文件读取，假设它是HTML内容
                pass
        
        # 解析HTML
        soup = BeautifulSoup(html_content, parser)
        
        # 提取文本内容
        text = _extract_main_text(soup)
        
        # 提取关键词
        keywords = _extract_keywords(text, max_topics * 3)
        
        # 从标题中提取主题
        heading_topics = _extract_topics_from_headings(soup)
        
        # 合并主题
        all_topics = []
        
        # 首先添加标题中的主题
        for topic in heading_topics[:max_topics]:
            if topic not in all_topics:
                all_topics.append(topic)
        
        # 然后添加关键词中的主题
        for keyword in keywords:
            if len(all_topics) < max_topics and keyword["word"] not in all_topics:
                all_topics.append(keyword["word"])
        
        # 计算主题重要性
        topics = []
        for i, topic in enumerate(all_topics):
            # 在标题中的主题更重要
            importance = max_topics - i
            if topic in heading_topics:
                importance += 5
            
            # 在关键词中的主题根据频率增加重要性
            for keyword in keywords:
                if keyword["word"] == topic:
                    importance += keyword["frequency"] / 10
            
            topics.append({
                "topic": topic,
                "importance": importance
            })
        
        # 按重要性排序
        topics.sort(key=lambda x: x["importance"], reverse=True)
        
        # 构建响应
        response = {
            "status": "success",
            "topics": topics[:max_topics],
            "keywords": keywords[:10],  # 返回前10个关键词
            "document_title": soup.title.string.strip() if soup.title else "Untitled Document"
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "关键主题识别失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def suggest_slide_structure(
    html_content: str,
    parser: str = "html.parser",
    max_slides: int = 10
) -> str:
    """
    根据HTML文档内容建议PPT幻灯片结构。

    Args:
        html_content (str): HTML文档内容或文件路径
        parser (str): 解析器类型，可选值: "html.parser", "lxml", "html5lib"
        max_slides (int): 最大幻灯片数量
        
    Returns:
        str: JSON格式的幻灯片结构建议
    """
    try:
        # 检查输入是否为文件路径
        if html_content.strip().startswith(('<', '<!DOCTYPE')):
            # 这是HTML内容
            pass
        else:
            # 尝试作为文件路径读取
            try:
                with open(html_content, 'r', encoding='utf-8') as f:
                    html_content = f.read()
            except:
                # 如果无法作为文件读取，假设它是HTML内容
                pass
        
        # 解析HTML
        soup = BeautifulSoup(html_content, parser)
        
        # 获取文档标题
        document_title = soup.title.string.strip() if soup.title else "Presentation"
        
        # 分析标题层次结构
        headings = _analyze_headings(soup)
        
        # 分析语义分区
        sections = _analyze_sections(soup)
        
        # 提取关键内容
        key_content_json = extract_key_content(html_content, parser)
        key_content = json.loads(key_content_json)
        
        # 创建幻灯片结构
        slides = []
        
        # 添加标题幻灯片
        slides.append({
            "slide_type": "title",
            "title": document_title,
            "subtitle": _get_meta_description(soup) or "",
            "layout": "title_slide"
        })
        
        # 添加目录幻灯片（如果有足够的内容）
        if len(headings) >= 3:
            toc_items = []
            for heading in headings:
                if heading["level"] <= 2:  # 只包括h1和h2
                    toc_items.append(heading["text"])
            
            if toc_items:
                slides.append({
                    "slide_type": "toc",
                    "title": "Agenda",
                    "content": toc_items,
                    "layout": "section"
                })
        
        # 根据标题和章节添加内容幻灯片
        content_slides = []
        
        # 首先尝试使用语义分区
        if sections and len(sections) <= max_slides - 2:  # 减去标题和目录幻灯片
            for section in sections:
                slide = {
                    "slide_type": "content",
                    "title": section["heading"] or section["type"].capitalize(),
                    "content": [],
                    "layout": "content"
                }
                
                # 添加内容
                content_items = []
                
                # 添加段落
                for p in section["content"].find_all('p', recursive=False):
                    text = p.get_text(strip=True)
                    if text:
                        content_items.append({"type": "text", "text": text})
                
                # 添加列表
                for list_tag in section["content"].find_all(['ul', 'ol'], recursive=False):
                    items = []
                    for li in list_tag.find_all('li'):
                        items.append(li.get_text(strip=True))
                    
                    if items:
                        content_items.append({
                            "type": "list",
                            "list_type": list_tag.name,
                            "items": items
                        })
                
                # 添加图片
                for img in section["content"].find_all('img', recursive=False):
                    content_items.append({
                        "type": "image",
                        "src": img.get('src', ''),
                        "alt": img.get('alt', '')
                    })
                
                # 添加表格
                for table in section["content"].find_all('table', recursive=False):
                    content_items.append({
                        "type": "table",
                        "data": "table_data_placeholder"  # 实际应用中需要提取表格数据
                    })
                
                slide["content"] = content_items
                content_slides.append(slide)
        
        # 如果没有足够的分区，使用标题结构
        if not content_slides and headings:
            current_level = 0
            current_title = ""
            current_content = []
            
            for heading in headings:
                # 只处理h1、h2和h3
                if heading["level"] > 3:
                    continue
                
                # 如果是新的主要标题或已经收集了足够的内容，创建新幻灯片
                if heading["level"] <= current_level or len(current_content) >= 5:
                    if current_title and current_content:
                        content_slides.append({
                            "slide_type": "content",
                            "title": current_title,
                            "content": current_content,
                            "layout": "content"
                        })
                        current_content = []
                
                current_level = heading["level"]
                current_title = heading["text"]
                
                # 收集标题下的内容
                next_element = heading.find_next()
                while next_element and not (next_element.name and next_element.name.startswith('h')):
                    if next_element.name == 'p':
                        text = next_element.get_text(strip=True)
                        if text:
                            current_content.append({"type": "text", "text": text})
                    elif next_element.name in ['ul', 'ol']:
                        items = []
                        for li in next_element.find_all('li'):
                            items.append(li.get_text(strip=True))
                        
                        if items:
                            current_content.append({
                                "type": "list",
                                "list_type": next_element.name,
                                "items": items
                            })
                    elif next_element.name == 'img':
                        current_content.append({
                            "type": "image",
                            "src": next_element.get('src', ''),
                            "alt": next_element.get('alt', '')
                        })
                    elif next_element.name == 'table':
                        current_content.append({
                            "type": "table",
                            "data": "table_data_placeholder"
                        })
                    
                    next_element = next_element.find_next()
            
            # 添加最后一个幻灯片
            if current_title and current_content:
                content_slides.append({
                    "slide_type": "content",
                    "title": current_title,
                    "content": current_content,
                    "layout": "content"
                })
        
        # 如果仍然没有足够的内容幻灯片，使用关键内容
        if not content_slides and "content" in key_content:
            # 使用标题作为幻灯片
            if "headings" in key_content["content"] and key_content["content"]["headings"]:
                for heading in key_content["content"]["headings"]:
                    if heading["level"] <= 2:  # 只使用h1和h2
                        content_slides.append({
                            "slide_type": "content",
                            "title": heading["text"],
                            "content": [],
                            "layout": "content"
                        })
            
            # 使用列表作为幻灯片
            if "lists" in key_content["content"] and key_content["content"]["lists"]:
                for list_item in key_content["content"]["lists"]:
                    content_slides.append({
                        "slide_type": "content",
                        "title": document_title,
                        "content": [{
                            "type": "list",
                            "list_type": list_item["type"],
                            "items": list_item["items"]
                        }],
                        "layout": "content"
                    })
            
            # 使用表格作为幻灯片
            if "tables" in key_content["content"] and key_content["content"]["tables"]:
                for table in key_content["content"]["tables"]:
                    content_slides.append({
                        "slide_type": "content",
                        "title": "Table Data",
                        "content": [{
                            "type": "table",
                            "headers": table["headers"],
                            "data": table["data"]
                        }],
                        "layout": "content"
                    })
        
        # 限制内容幻灯片数量
        content_slides = content_slides[:max_slides - 2]  # 减去标题和结束幻灯片
        
        # 添加内容幻灯片
        slides.extend(content_slides)
        
        # 添加结束幻灯片
        slides.append({
            "slide_type": "end",
            "title": "Thank You",
            "content": [],
            "layout": "section"
        })
        
        # 构建响应
        response = {
            "status": "success",
            "document_title": document_title,
            "suggested_slides": slides,
            "slide_count": len(slides)
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "幻灯片结构建议失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def analyze_content_importance(
    html_content: str,
    parser: str = "html.parser"
) -> str:
    """
    分析HTML文档中内容的重要性。

    Args:
        html_content (str): HTML文档内容或文件路径
        parser (str): 解析器类型，可选值: "html.parser", "lxml", "html5lib"
        
    Returns:
        str: JSON格式的内容重要性分析结果
    """
    try:
        # 检查输入是否为文件路径
        if html_content.strip().startswith(('<', '<!DOCTYPE')):
            # 这是HTML内容
            pass
        else:
            # 尝试作为文件路径读取
            try:
                with open(html_content, 'r', encoding='utf-8') as f:
                    html_content = f.read()
            except:
                # 如果无法作为文件读取，假设它是HTML内容
                pass
        
        # 解析HTML
        soup = BeautifulSoup(html_content, parser)
        
        # 分析标题重要性
        headings = []
        for i in range(1, 7):
            for idx, heading in enumerate(soup.find_all(f'h{i}')):
                text = heading.get_text(strip=True)
                if text:
                    # 计算重要性分数：基于标题级别、位置和内容长度
                    importance = (7 - i) * 10  # h1最重要，h6最不重要
                    importance -= idx * 0.5  # 同级标题中，前面的更重要
                    importance += min(len(text) / 20, 5)  # 内容长度适中的标题更重要
                    
                    headings.append({
                        "text": text,
                        "level": i,
                        "importance": round(importance, 2),
                        "position": idx
                    })
        
        # 按重要性排序
        headings.sort(key=lambda x: x["importance"], reverse=True)
        
        # 分析段落重要性
        paragraphs = []
        for idx, p in enumerate(soup.find_all('p')):
            text = p.get_text(strip=True)
            if text:
                # 计算段落重要性
                importance = _calculate_text_importance(text)
                
                # 检查是否在重要位置
                parent = p.parent
                if parent and parent.name in ['main', 'article']:
                    importance += 5
                elif parent and parent.name in ['aside', 'footer']:
                    importance -= 5
                
                # 检查是否包含强调元素
                if p.find(['strong', 'b', 'em', 'i', 'mark']):
                    importance += 3
                
                paragraphs.append({
                    "text": text[:100] + ("..." if len(text) > 100 else ""),
                    "importance": round(importance, 2),
                    "length": len(text),
                    "position": idx
                })
        
        # 按重要性排序
        paragraphs.sort(key=lambda x: x["importance"], reverse=True)
        
        # 分析列表重要性
        lists = []
        for idx, list_tag in enumerate(soup.find_all(['ul', 'ol'])):
            items = []
            for li in list_tag.find_all('li'):
                items.append(li.get_text(strip=True))
            
            if items:
                # 计算列表重要性
                importance = 5 + min(len(items), 10)  # 基础分数加上项目数（最多加10分）
                
                # 检查是否在重要位置
                parent = list_tag.parent
                if parent and parent.name in ['main', 'article']:
                    importance += 5
                
                # 检查是否有前导标题
                prev_element = list_tag.find_previous(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                if prev_element and prev_element.get_text(strip=True):
                    importance += (7 - int(prev_element.name[1])) * 2  # h1提供更多加分
                
                lists.append({
                    "type": list_tag.name,
                    "items": items[:5] + (["..."] if len(items) > 5 else []),
                    "item_count": len(items),
                    "importance": round(importance, 2),
                    "position": idx
                })
        
        # 按重要性排序
        lists.sort(key=lambda x: x["importance"], reverse=True)
        
        # 分析图片重要性
        images = []
        for idx, img in enumerate(soup.find_all('img')):
            src = img.get('src', '')
            alt = img.get('alt', '')
            
            if src:
                # 计算图片重要性
                importance = 5  # 基础分数
                
                # 有alt文本的图片更重要
                if alt:
                    importance += 3
                
                # 检查图片大小（如果有width和height属性）
                width = img.get('width')
                height = img.get('height')
                if width and height:
                    try:
                        area = int(width) * int(height)
                        importance += min(area / 10000, 10)  # 大图片更重要，最多加10分
                    except:
                        pass
                
                # 检查是否有图片说明（figcaption）
                parent = img.parent
                if parent and parent.name == 'figure':
                    figcaption = parent.find('figcaption')
                    if figcaption and figcaption.get_text(strip=True):
                        importance += 5
                
                images.append({
                    "src": src,
                    "alt": alt,
                    "importance": round(importance, 2),
                    "position": idx
                })
        
        # 按重要性排序
        images.sort(key=lambda x: x["importance"], reverse=True)
        
        # 构建响应
        response = {
            "status": "success",
            "importance_analysis": {
                "headings": headings[:10],  # 最多返回10个最重要的标题
                "paragraphs": paragraphs[:10],  # 最多返回10个最重要的段落
                "lists": lists[:5],  # 最多返回5个最重要的列表
                "images": images[:5]  # 最多返回5个最重要的图片
            }
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "内容重要性分析失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def extract_hierarchical_structure(
    html_content: str,
    parser: str = "html.parser",
    max_depth: int = 3
) -> str:
    """
    提取HTML文档的层次结构。

    Args:
        html_content (str): HTML文档内容或文件路径
        parser (str): 解析器类型，可选值: "html.parser", "lxml", "html5lib"
        max_depth (int): 最大深度
        
    Returns:
        str: JSON格式的层次结构
    """
    try:
        # 检查输入是否为文件路径
        if html_content.strip().startswith(('<', '<!DOCTYPE')):
            # 这是HTML内容
            pass
        else:
            # 尝试作为文件路径读取
            try:
                with open(html_content, 'r', encoding='utf-8') as f:
                    html_content = f.read()
            except:
                # 如果无法作为文件读取，假设它是HTML内容
                pass
        
        # 解析HTML
        soup = BeautifulSoup(html_content, parser)
        
        # 提取文档标题
        document_title = soup.title.string.strip() if soup.title else "Untitled Document"
        
        # 基于标题层次提取结构
        structure = _extract_heading_hierarchy(soup, max_depth)
        
        # 如果没有足够的标题结构，尝试使用语义元素
        if not structure["children"]:
            structure = _extract_semantic_hierarchy(soup, max_depth)
        
        # 构建响应
        response = {
            "status": "success",
            "document_title": document_title,
            "hierarchical_structure": structure
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "层次结构提取失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def summarize_content(
    html_content: str,
    parser: str = "html.parser",
    max_length: int = 500
) -> str:
    """
    总结HTML文档内容。

    Args:
        html_content (str): HTML文档内容或文件路径
        parser (str): 解析器类型，可选值: "html.parser", "lxml", "html5lib"
        max_length (int): 摘要最大长度
        
    Returns:
        str: JSON格式的内容摘要
    """
    try:
        # 检查输入是否为文件路径
        if html_content.strip().startswith(('<', '<!DOCTYPE')):
            # 这是HTML内容
            pass
        else:
            # 尝试作为文件路径读取
            try:
                with open(html_content, 'r', encoding='utf-8') as f:
                    html_content = f.read()
            except:
                # 如果无法作为文件读取，假设它是HTML内容
                pass
        
        # 解析HTML
        soup = BeautifulSoup(html_content, parser)
        
        # 提取文档标题
        document_title = soup.title.string.strip() if soup.title else "Untitled Document"
        
        # 提取meta描述
        meta_description = _get_meta_description(soup)
        
        # 如果有meta描述且长度合适，直接使用
        if meta_description and len(meta_description) <= max_length:
            summary = meta_description
        else:
            # 提取主要文本内容
            main_text = _extract_main_text(soup)
            
            # 提取关键句子
            key_sentences = _extract_key_sentences(main_text, max_length)
            
            # 组合成摘要
            summary = " ".join(key_sentences)
            
            # 如果摘要太长，截断
            if len(summary) > max_length:
                summary = summary[:max_length - 3] + "..."
        
        # 提取关键词
        keywords = _extract_keywords(main_text, 10)
        
        # 构建响应
        response = {
            "status": "success",
            "document_title": document_title,
            "summary": summary,
            "summary_length": len(summary),
            "keywords": [kw["word"] for kw in keywords]
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "内容总结失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


# 辅助函数

def _get_meta_description(soup: BeautifulSoup) -> str:
    """获取meta描述"""
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc and 'content' in meta_desc.attrs:
        return meta_desc['content']
    
    # 尝试Open Graph描述
    og_desc = soup.find('meta', attrs={'property': 'og:description'})
    if og_desc and 'content' in og_desc.attrs:
        return og_desc['content']
    
    return ""


def _analyze_structure(soup: BeautifulSoup, max_depth: int = 5) -> Dict[str, Any]:
    """分析文档结构"""
    structure = {
        "element_counts": {},
        "semantic_elements": {},
        "depth": 0,
        "max_nesting": 0
    }
    
    # 计算元素数量
    for tag_name in ['div', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'img', 'ul', 'ol', 'li', 'table', 'form', 'input']:
        structure["element_counts"][tag_name] = len(soup.find_all(tag_name))
    
    # 计算语义元素数量
    for tag_name in ['header', 'footer', 'nav', 'main', 'article', 'section', 'aside', 'figure', 'figcaption']:
        structure["semantic_elements"][tag_name] = len(soup.find_all(tag_name))
    
    # 计算最大嵌套深度
    if soup.html:
        structure["max_nesting"] = _calculate_max_depth(soup.html, max_depth)
    
    return structure


def _calculate_max_depth(element: Tag, max_depth: int, current_depth: int = 0) -> int:
    """计算元素的最大嵌套深度"""
    if current_depth >= max_depth:
        return current_depth
    
    max_child_depth = current_depth
    for child in element.children:
        if isinstance(child, Tag):
            child_depth = _calculate_max_depth(child, max_depth, current_depth + 1)
            max_child_depth = max(max_child_depth, child_depth)
    
    return max_child_depth


def _identify_main_content(soup: BeautifulSoup) -> Dict[str, Any]:
    """识别主要内容区域"""
    main_content = {
        "element_type": None,
        "text_length": 0,
        "content_elements": {}
    }
    
    # 尝试找到主内容区域
    main_candidates = []
    
    # 首先检查语义元素
    for tag_name in ['main', 'article']:
        elements = soup.find_all(tag_name)
        main_candidates.extend(elements)
    
    # 然后检查常见的ID和类
    for selector in ['#main', '#content', '.main', '.content', '#main-content', '.main-content']:
        elements = soup.select(selector)
        main_candidates.extend(elements)
    
    # 如果没有找到明确的主内容区域，使用启发式方法
    if not main_candidates:
        # 查找最多段落的div
        divs = soup.find_all('div')
        if divs:
            main_candidates = [max(divs, key=lambda x: len(x.find_all('p')))]
    
    # 如果仍然没有找到，使用body
    if not main_candidates and soup.body:
        main_candidates = [soup.body]
    
    # 选择文本最多的候选区域
    if main_candidates:
        main_element = max(main_candidates, key=lambda x: len(x.get_text(strip=True)))
        
        main_content["element_type"] = main_element.name
        if 'id' in main_element.attrs:
            main_content["id"] = main_element['id']
        if 'class' in main_element.attrs:
            main_content["class"] = main_element['class']
        
        main_content["text_length"] = len(main_element.get_text(strip=True))
        
        # 统计内容元素
        for tag_name in ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'img', 'table']:
            main_content["content_elements"][tag_name] = len(main_element.find_all(tag_name))
    
    return main_content


def _analyze_headings(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """分析标题层次结构"""
    headings = []
    
    # 提取所有标题
    for i in range(1, 7):
        for heading in soup.find_all(f'h{i}'):
            text = heading.get_text(strip=True)
            if text:
                headings.append({
                    "level": i,
                    "text": text,
                    "id": heading.get('id', ''),
                    "position": len(headings)
                })
    
    return headings


def _analyze_sections(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """分析语义分区"""
    sections = []
    
    # 检查显式的section元素
    for section in soup.find_all('section'):
        # 查找标题
        heading = None
        for i in range(1, 7):
            h = section.find(f'h{i}')
            if h:
                heading = h.get_text(strip=True)
                break
        
        sections.append({
            "type": "section",
            "heading": heading,
            "content": section,
            "text_length": len(section.get_text(strip=True))
        })
    
    # 检查article元素
    for article in soup.find_all('article'):
        # 查找标题
        heading = None
        for i in range(1, 7):
            h = article.find(f'h{i}')
            if h:
                heading = h.get_text(strip=True)
                break
        
        sections.append({
            "type": "article",
            "heading": heading,
            "content": article,
            "text_length": len(article.get_text(strip=True))
        })
    
    # 如果没有足够的显式分区，尝试使用标题作为分区标志
    if len(sections) < 2:
        main_content = None
        for selector in ['main', 'article', '#main', '#content', '.main', '.content']:
            elements = soup.select(selector)
            if elements:
                main_content = elements[0]
                break
        
        if not main_content and soup.body:
            main_content = soup.body
        
        if main_content:
            # 使用h1和h2作为分区标志
            current_section = None
            current_heading = None
            current_content = []
            
            for child in main_content.children:
                if isinstance(child, Tag):
                    if child.name in ['h1', 'h2']:
                        # 保存前一个分区
                        if current_heading and current_content:
                            section_content = BeautifulSoup('<div></div>', 'html.parser').div
                            for elem in current_content:
                                section_content.append(elem)
                            
                            sections.append({
                                "type": "implicit_section",
                                "heading": current_heading,
                                "content": section_content,
                                "text_length": len(section_content.get_text(strip=True))
                            })
                        
                        # 开始新分区
                        current_heading = child.get_text(strip=True)
                        current_content = []
                    elif current_heading is not None:
                        # 添加到当前分区
                        current_content.append(child)
            
            # 保存最后一个分区
            if current_heading and current_content:
                section_content = BeautifulSoup('<div></div>', 'html.parser').div
                for elem in current_content:
                    section_content.append(elem)
                
                sections.append({
                    "type": "implicit_section",
                    "heading": current_heading,
                    "content": section_content,
                    "text_length": len(section_content.get_text(strip=True))
                })
    
    return sections


def _extract_main_text(soup: BeautifulSoup) -> str:
    """提取主要文本内容"""
    # 删除脚本和样式
    for script_or_style in soup(['script', 'style', 'noscript']):
        script_or_style.extract()
    
    # 尝试找到主内容区域
    main_content = None
    for selector in ['main', 'article', '#main', '#content', '.main', '.content']:
        elements = soup.select(selector)
        if elements:
            main_content = elements[0]
            break
    
    if not main_content:
        main_content = soup.body if soup.body else soup
    
    # 提取文本
    text = main_content.get_text(separator=' ', strip=True)
    
    # 清理文本
    text = re.sub(r'\s+', ' ', text)
    
    return text


def _extract_keywords(text: str, max_keywords: int = 10) -> List[Dict[str, Any]]:
    """提取文本中的关键词"""
    # 分词
    words = word_tokenize(text.lower())
    
    # 过滤停用词和非字母词
    stop_words = set(stopwords.words('english'))
    filtered_words = [word for word in words if word.isalpha() and word not in stop_words and len(word) > 2]
    
    # 计算词频
    word_freq = Counter(filtered_words)
    
    # 提取最常见的词
    keywords = []
    for word, freq in word_freq.most_common(max_keywords):
        keywords.append({
            "word": word,
            "frequency": freq,
            "score": freq / len(filtered_words) * 100  # 频率百分比
        })
    
    return keywords


def _extract_topics_from_headings(soup: BeautifulSoup) -> List[str]:
    """从标题中提取主题"""
    topics = []
    
    # 提取所有标题文本
    headings_text = []
    for i in range(1, 4):  # 只考虑h1, h2, h3
        for heading in soup.find_all(f'h{i}'):
            text = heading.get_text(strip=True)
            if text:
                headings_text.append(text)
    
    # 分词并提取名词短语作为主题
    for text in headings_text:
        words = text.split()
        if len(words) <= 3:
            topics.append(text)
        else:
            # 提取前3个词作为主题
            topics.append(" ".join(words[:3]))
    
    # 去重
    unique_topics = []
    for topic in topics:
        if topic not in unique_topics:
            unique_topics.append(topic)
    
    return unique_topics


def _calculate_text_importance(text: str) -> float:
    """计算文本的重要性分数"""
    if not text:
        return 0
    
    # 基础分数
    importance = 5
    
    # 文本长度因素（太短或太长的段落可能不太重要）
    text_length = len(text)
    if text_length < 20:
        importance -= 2
    elif 100 <= text_length <= 500:
        importance += 3
    elif text_length > 1000:
        importance -= 1
    
    # 包含数字的文本可能更重要
    if re.search(r'\d+', text):
        importance += 1
    
    # 包含特定关键词的文本可能更重要
    important_keywords = ['important', 'significant', 'key', 'main', 'critical', 'essential', 'crucial']
    for keyword in important_keywords:
        if keyword in text.lower():
            importance += 1
    
    # 句子结构因素（包含更多句子的段落可能更重要）
    sentences = sent_tokenize(text)
    if len(sentences) >= 3:
        importance += 1
    
    return importance


def _extract_key_sentences(text: str, max_length: int) -> List[str]:
    """提取文本中的关键句子"""
    # 分句
    sentences = sent_tokenize(text)
    
    # 计算每个句子的重要性
    sentence_scores = []
    for sentence in sentences:
        score = _calculate_sentence_importance(sentence)
        sentence_scores.append((sentence, score))
    
    # 按重要性排序
    sentence_scores.sort(key=lambda x: x[1], reverse=True)
    
    # 选择最重要的句子，直到达到最大长度
    key_sentences = []
    current_length = 0
    
    for sentence, _ in sentence_scores:
        if current_length + len(sentence) <= max_length:
            key_sentences.append(sentence)
            current_length += len(sentence) + 1  # +1 for space
        else:
            break
    
    # 如果没有选择任何句子（可能是因为单个句子就超过了最大长度），选择第一个句子的一部分
    if not key_sentences and sentences:
        key_sentences = [sentences[0][:max_length - 3] + "..."]
    
    return key_sentences


def _calculate_sentence_importance(sentence: str) -> float:
    """计算句子的重要性分数"""
    if not sentence:
        return 0
    
    # 基础分数
    importance = 5
    
    # 句子长度因素（太短或太长的句子可能不太重要）
    sentence_length = len(sentence)
    if sentence_length < 10:
        importance -= 2
    elif 20 <= sentence_length <= 150:
        importance += 2
    elif sentence_length > 200:
        importance -= 1
    
    # 包含数字的句子可能更重要
    if re.search(r'\d+', sentence):
        importance += 1
    
    # 包含特定关键词的句子可能更重要
    important_keywords = ['important', 'significant', 'key', 'main', 'critical', 'essential', 'crucial']
    for keyword in important_keywords:
        if keyword in sentence.lower():
            importance += 1
    
    # 句子位置因素（段落的第一句和最后一句可能更重要）
    # 在这个函数中我们无法判断句子在段落中的位置，所以忽略这个因素
    
    return importance


def _extract_heading_hierarchy(soup: BeautifulSoup, max_depth: int) -> Dict[str, Any]:
    """基于标题层次提取文档结构"""
    # 创建根节点
    root = {
        "title": soup.title.string.strip() if soup.title else "Document",
        "type": "document",
        "children": []
    }
    
    # 提取所有标题
    headings = []
    for i in range(1, 7):
        for heading in soup.find_all(f'h{i}'):
            text = heading.get_text(strip=True)
            if text:
                headings.append({
                    "level": i,
                    "text": text,
                    "element": heading
                })
    
    # 如果没有标题，返回空结构
    if not headings:
        return root
    
    # 构建层次结构
    current_path = [root]
    
    for heading in headings:
        level = heading["level"]
        
        # 确保不超过最大深度
        if level > max_depth:
            continue
        
        # 调整当前路径
        while len(current_path) > level:
            current_path.pop()
        
        while len(current_path) < level:
            # 如果路径不够长，添加空节点
            empty_node = {
                "title": "Untitled Section",
                "type": f"h{len(current_path)}",
                "children": []
            }
            current_path[-1]["children"].append(empty_node)
            current_path.append(empty_node)
        
        # 创建新节点
        new_node = {
            "title": heading["text"],
            "type": f"h{level}",
            "children": []
        }
        
        # 提取该标题下的内容
        content = []
        next_element = heading["element"].next_sibling
        while next_element:
            if isinstance(next_element, Tag) and next_element.name.startswith('h') and int(next_element.name[1]) <= level:
                break
            if isinstance(next_element, Tag):
                content_text = next_element.get_text(strip=True)
                if content_text:
                    content.append({
                        "type": next_element.name,
                        "text": content_text[:100] + ("..." if len(content_text) > 100 else "")
                    })
            next_element = next_element.next_sibling
        
        if content:
            new_node["content"] = content
        
        # 添加到当前路径
        current_path[-1]["children"].append(new_node)
        current_path[-1] = new_node
    
    return root


def _extract_semantic_hierarchy(soup: BeautifulSoup, max_depth: int) -> Dict[str, Any]:
    """基于语义元素提取文档结构"""
    # 创建根节点
    root = {
        "title": soup.title.string.strip() if soup.title else "Document",
        "type": "document",
        "children": []
    }
    
    # 查找主要内容区域
    main_content = None
    for selector in ['main', 'article', '#main', '#content', '.main', '.content']:
        elements = soup.select(selector)
        if elements:
            main_content = elements[0]
            break
    
    if not main_content and soup.body:
        main_content = soup.body
    
    if not main_content:
        return root
    
    # 提取语义结构
    _extract_semantic_children(main_content, root, 1, max_depth)
    
    return root


def _extract_semantic_children(element: Tag, parent_node: Dict[str, Any], current_depth: int, max_depth: int):
    """递归提取语义子元素"""
    if current_depth > max_depth:
        return
    
    # 查找语义元素
    semantic_elements = []
    for tag_name in ['section', 'article', 'aside', 'nav', 'header', 'footer']:
        for elem in element.find_all(tag_name, recursive=False):
            semantic_elements.append(elem)
    
    # 如果没有语义元素，查找div
    if not semantic_elements:
        for div in element.find_all('div', recursive=False):
            # 只包含有意义的div
            if div.get('id') or div.get('class') or len(div.get_text(strip=True)) > 100:
                semantic_elements.append(div)
    
    # 处理每个语义元素
    for elem in semantic_elements:
        # 查找标题
        heading_text = None
        for i in range(1, 7):
            h = elem.find(f'h{i}')
            if h:
                heading_text = h.get_text(strip=True)
                break
        
        # 如果没有标题，使用元素类型
        if not heading_text:
            if elem.get('id'):
                heading_text = f"{elem.name.capitalize()} ({elem.get('id')})"
            elif elem.get('class'):
                heading_text = f"{elem.name.capitalize()} ({' '.join(elem.get('class'))})"
            else:
                heading_text = elem.name.capitalize()
        
        # 创建节点
        node = {
            "title": heading_text,
            "type": elem.name,
            "children": []
        }
        
        # 提取内容
        content = []
        for child in elem.children:
            if isinstance(child, Tag) and child.name not in ['section', 'article', 'aside', 'nav', 'header', 'footer', 'div']:
                if child.name not in ['script', 'style', 'noscript']:
                    content_text = child.get_text(strip=True)
                    if content_text:
                        content.append({
                            "type": child.name,
                            "text": content_text[:100] + ("..." if len(content_text) > 100 else "")
                        })
        
        if content:
            node["content"] = content
        
        # 添加到父节点
        parent_node["children"].append(node)
        
        # 递归处理子元素
        _extract_semantic_children(elem, node, current_depth + 1, max_depth)