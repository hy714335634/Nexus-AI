"""
HTML解析和处理工具，用于解析HTML文档结构和内容。

此模块提供了一组工具函数，用于解析HTML文档、提取元素、分析结构和处理内容。
基于BeautifulSoup和lxml库实现，支持复杂的HTML文档处理。
"""

import json
import os
import re
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag, NavigableString
import requests
from strands import tool


@tool
def parse_html(
    html_content: str,
    parser: str = "html.parser",
    encoding: str = "utf-8"
) -> str:
    """
    解析HTML内容并返回文档结构信息。

    Args:
        html_content (str): HTML文档内容或文件路径
        parser (str): 解析器类型，可选值: "html.parser", "lxml", "html5lib"
        encoding (str): 文档编码，默认为utf-8
        
    Returns:
        str: JSON格式的文档结构信息，包含标题、元数据、主要元素等
    """
    try:
        # 检查输入是否为文件路径
        if os.path.exists(html_content) and os.path.isfile(html_content):
            with open(html_content, 'r', encoding=encoding) as f:
                html_content = f.read()
        
        # 解析HTML
        soup = BeautifulSoup(html_content, parser)
        
        # 提取文档信息
        document_info = {
            "title": soup.title.string if soup.title else "No title",
            "meta": _extract_meta_tags(soup),
            "structure": {
                "headings": _count_elements_by_type(soup, ["h1", "h2", "h3", "h4", "h5", "h6"]),
                "paragraphs": len(soup.find_all("p")),
                "links": len(soup.find_all("a")),
                "images": len(soup.find_all("img")),
                "tables": len(soup.find_all("table")),
                "lists": len(soup.find_all(["ul", "ol"])),
                "forms": len(soup.find_all("form"))
            },
            "main_content": _identify_main_content(soup)
        }
        
        return json.dumps(document_info, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "error": str(e),
            "status": "failed",
            "message": "HTML解析失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def extract_elements(
    html_content: str,
    selector: str,
    parser: str = "html.parser",
    extract_attributes: List[str] = None,
    limit: int = 0
) -> str:
    """
    使用CSS选择器从HTML中提取特定元素。

    Args:
        html_content (str): HTML文档内容或文件路径
        selector (str): CSS选择器表达式
        parser (str): 解析器类型，可选值: "html.parser", "lxml", "html5lib"
        extract_attributes (List[str]): 要提取的属性列表，默认为None表示提取文本内容
        limit (int): 限制结果数量，0表示不限制
        
    Returns:
        str: JSON格式的提取结果
    """
    try:
        # 检查输入是否为文件路径
        if os.path.exists(html_content) and os.path.isfile(html_content):
            with open(html_content, 'r', encoding='utf-8') as f:
                html_content = f.read()
        
        # 解析HTML
        soup = BeautifulSoup(html_content, parser)
        
        # 提取元素
        elements = soup.select(selector)
        if limit > 0:
            elements = elements[:limit]
        
        results = []
        for element in elements:
            if extract_attributes:
                # 提取指定属性
                attrs = {}
                for attr in extract_attributes:
                    if attr in element.attrs:
                        attrs[attr] = element[attr]
                    elif attr == "text":
                        attrs["text"] = element.get_text(strip=True)
                    elif attr == "html":
                        attrs["html"] = str(element)
                results.append(attrs)
            else:
                # 默认提取文本
                results.append(element.get_text(strip=True))
        
        response = {
            "status": "success",
            "count": len(results),
            "results": results
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "error": str(e),
            "status": "failed",
            "message": "元素提取失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def extract_text_content(
    html_content: str,
    clean: bool = True,
    preserve_formatting: bool = False,
    parser: str = "html.parser"
) -> str:
    """
    从HTML中提取纯文本内容。

    Args:
        html_content (str): HTML文档内容或文件路径
        clean (bool): 是否清理文本（删除多余空格、换行等）
        preserve_formatting (bool): 是否保留段落格式
        parser (str): 解析器类型，可选值: "html.parser", "lxml", "html5lib"
        
    Returns:
        str: JSON格式的文本内容
    """
    try:
        # 检查输入是否为文件路径
        if os.path.exists(html_content) and os.path.isfile(html_content):
            with open(html_content, 'r', encoding='utf-8') as f:
                html_content = f.read()
        
        # 解析HTML
        soup = BeautifulSoup(html_content, parser)
        
        # 删除脚本和样式元素
        for script_or_style in soup(["script", "style"]):
            script_or_style.extract()
        
        # 获取文本
        if preserve_formatting:
            # 保留段落格式
            paragraphs = []
            for element in soup.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6", "li"]):
                text = element.get_text(strip=True)
                if text:
                    paragraphs.append(text)
            
            text_content = "\n\n".join(paragraphs)
        else:
            # 获取所有文本
            text_content = soup.get_text()
            
            # 清理文本
            if clean:
                # 删除多余空白
                text_content = re.sub(r'\s+', ' ', text_content)
                text_content = text_content.strip()
        
        response = {
            "status": "success",
            "text_content": text_content,
            "length": len(text_content),
            "word_count": len(text_content.split())
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "error": str(e),
            "status": "failed",
            "message": "文本提取失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def extract_links(
    html_content: str,
    base_url: str = None,
    filter_external: bool = False,
    include_text: bool = True,
    parser: str = "html.parser"
) -> str:
    """
    从HTML中提取所有链接。

    Args:
        html_content (str): HTML文档内容或文件路径
        base_url (str): 基础URL，用于转换相对链接为绝对链接
        filter_external (bool): 是否只包含外部链接
        include_text (bool): 是否包含链接文本
        parser (str): 解析器类型，可选值: "html.parser", "lxml", "html5lib"
        
    Returns:
        str: JSON格式的链接列表
    """
    try:
        # 检查输入是否为文件路径
        if os.path.exists(html_content) and os.path.isfile(html_content):
            with open(html_content, 'r', encoding='utf-8') as f:
                html_content = f.read()
        
        # 解析HTML
        soup = BeautifulSoup(html_content, parser)
        
        # 提取链接
        links = []
        for link in soup.find_all('a'):
            href = link.get('href')
            if not href:
                continue
            
            # 转换为绝对URL
            if base_url and not bool(urlparse(href).netloc):
                href = urljoin(base_url, href)
            
            # 过滤外部链接
            if filter_external and base_url:
                base_domain = urlparse(base_url).netloc
                link_domain = urlparse(href).netloc
                if not link_domain or link_domain == base_domain:
                    continue
            
            link_info = {"url": href}
            
            # 包含链接文本
            if include_text:
                link_info["text"] = link.get_text(strip=True)
            
            # 包含标题属性
            if link.get('title'):
                link_info["title"] = link['title']
            
            links.append(link_info)
        
        response = {
            "status": "success",
            "count": len(links),
            "links": links
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "error": str(e),
            "status": "failed",
            "message": "链接提取失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def extract_tables(
    html_content: str,
    parser: str = "html.parser",
    include_headers: bool = True,
    max_tables: int = 0
) -> str:
    """
    从HTML中提取表格数据。

    Args:
        html_content (str): HTML文档内容或文件路径
        parser (str): 解析器类型，可选值: "html.parser", "lxml", "html5lib"
        include_headers (bool): 是否将第一行作为表头
        max_tables (int): 最大提取表格数，0表示不限制
        
    Returns:
        str: JSON格式的表格数据
    """
    try:
        # 检查输入是否为文件路径
        if os.path.exists(html_content) and os.path.isfile(html_content):
            with open(html_content, 'r', encoding='utf-8') as f:
                html_content = f.read()
        
        # 解析HTML
        soup = BeautifulSoup(html_content, parser)
        
        # 提取表格
        tables_data = []
        tables = soup.find_all('table')
        
        if max_tables > 0:
            tables = tables[:max_tables]
        
        for table_idx, table in enumerate(tables):
            rows = table.find_all('tr')
            if not rows:
                continue
            
            table_data = []
            headers = []
            
            # 处理表头
            if include_headers:
                header_row = rows[0]
                header_cells = header_row.find_all(['th', 'td'])
                headers = [cell.get_text(strip=True) for cell in header_cells]
            
            # 处理数据行
            start_idx = 1 if include_headers and headers else 0
            for row in rows[start_idx:]:
                cells = row.find_all(['td', 'th'])
                row_data = [cell.get_text(strip=True) for cell in cells]
                if any(row_data):  # 跳过空行
                    table_data.append(row_data)
            
            tables_data.append({
                "id": table_idx,
                "headers": headers,
                "data": table_data,
                "rows": len(table_data),
                "columns": len(headers) if headers else (len(table_data[0]) if table_data else 0)
            })
        
        response = {
            "status": "success",
            "count": len(tables_data),
            "tables": tables_data
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "error": str(e),
            "status": "failed",
            "message": "表格提取失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def extract_images(
    html_content: str,
    base_url: str = None,
    download: bool = False,
    output_dir: str = "./images",
    parser: str = "html.parser"
) -> str:
    """
    从HTML中提取图片信息和链接。

    Args:
        html_content (str): HTML文档内容或文件路径
        base_url (str): 基础URL，用于转换相对链接为绝对链接
        download (bool): 是否下载图片到本地
        output_dir (str): 图片下载目录
        parser (str): 解析器类型，可选值: "html.parser", "lxml", "html5lib"
        
    Returns:
        str: JSON格式的图片信息
    """
    try:
        # 检查输入是否为文件路径
        if os.path.exists(html_content) and os.path.isfile(html_content):
            with open(html_content, 'r', encoding='utf-8') as f:
                html_content = f.read()
        
        # 解析HTML
        soup = BeautifulSoup(html_content, parser)
        
        # 提取图片
        images = []
        for img in soup.find_all('img'):
            src = img.get('src')
            if not src:
                continue
            
            # 转换为绝对URL
            if base_url and not bool(urlparse(src).netloc):
                src = urljoin(base_url, src)
            
            image_info = {
                "src": src,
                "alt": img.get('alt', ''),
                "title": img.get('title', ''),
                "width": img.get('width', ''),
                "height": img.get('height', '')
            }
            
            # 下载图片
            if download:
                try:
                    # 创建输出目录
                    os.makedirs(output_dir, exist_ok=True)
                    
                    # 生成文件名
                    filename = os.path.basename(urlparse(src).path)
                    if not filename:
                        filename = f"image_{len(images)}.jpg"
                    
                    # 确保文件名唯一
                    file_path = os.path.join(output_dir, filename)
                    if os.path.exists(file_path):
                        name, ext = os.path.splitext(filename)
                        filename = f"{name}_{hashlib.md5(src.encode()).hexdigest()[:6]}{ext}"
                        file_path = os.path.join(output_dir, filename)
                    
                    # 下载图片
                    response = requests.get(src, stream=True, timeout=10)
                    if response.status_code == 200:
                        with open(file_path, 'wb') as f:
                            for chunk in response.iter_content(1024):
                                f.write(chunk)
                        image_info["local_path"] = file_path
                        image_info["downloaded"] = True
                    else:
                        image_info["downloaded"] = False
                        image_info["download_error"] = f"HTTP错误: {response.status_code}"
                
                except Exception as e:
                    image_info["downloaded"] = False
                    image_info["download_error"] = str(e)
            
            images.append(image_info)
        
        response = {
            "status": "success",
            "count": len(images),
            "images": images,
            "download_info": {
                "enabled": download,
                "output_directory": os.path.abspath(output_dir) if download else None
            }
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "error": str(e),
            "status": "failed",
            "message": "图片提取失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def analyze_document_structure(
    html_content: str,
    parser: str = "html.parser",
    detailed: bool = False
) -> str:
    """
    分析HTML文档结构，提取层次结构和语义信息。

    Args:
        html_content (str): HTML文档内容或文件路径
        parser (str): 解析器类型，可选值: "html.parser", "lxml", "html5lib"
        detailed (bool): 是否返回详细结构信息
        
    Returns:
        str: JSON格式的文档结构分析结果
    """
    try:
        # 检查输入是否为文件路径
        if os.path.exists(html_content) and os.path.isfile(html_content):
            with open(html_content, 'r', encoding='utf-8') as f:
                html_content = f.read()
        
        # 解析HTML
        soup = BeautifulSoup(html_content, parser)
        
        # 基本文档信息
        document_info = {
            "title": soup.title.string if soup.title else "No title",
            "lang": soup.html.get('lang') if soup.html else None,
            "meta": _extract_meta_tags(soup),
            "sections": []
        }
        
        # 提取主要部分
        main_sections = _extract_document_sections(soup)
        document_info["sections"] = main_sections
        
        # 提取标题层次结构
        headings_structure = _extract_heading_structure(soup)
        document_info["heading_hierarchy"] = headings_structure
        
        # 语义结构分析
        document_info["semantic_structure"] = _analyze_semantic_structure(soup)
        
        # 详细结构
        if detailed:
            document_info["detailed_structure"] = _generate_detailed_structure(soup)
        
        return json.dumps(document_info, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "error": str(e),
            "status": "failed",
            "message": "文档结构分析失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


# 辅助函数

def _extract_meta_tags(soup: BeautifulSoup) -> Dict[str, str]:
    """提取HTML文档中的meta标签信息"""
    meta_tags = {}
    
    for meta in soup.find_all('meta'):
        # 处理name属性
        if meta.get('name') and meta.get('content'):
            meta_tags[meta['name']] = meta['content']
        
        # 处理property属性 (Open Graph等)
        elif meta.get('property') and meta.get('content'):
            meta_tags[meta['property']] = meta['content']
        
        # 处理http-equiv属性
        elif meta.get('http-equiv') and meta.get('content'):
            meta_tags[f"http-equiv:{meta['http-equiv']}"] = meta['content']
    
    return meta_tags


def _count_elements_by_type(soup: BeautifulSoup, element_types: List[str]) -> Dict[str, int]:
    """计算指定类型元素的数量"""
    counts = {}
    for element_type in element_types:
        counts[element_type] = len(soup.find_all(element_type))
    return counts


def _identify_main_content(soup: BeautifulSoup) -> Dict[str, Any]:
    """识别文档的主要内容区域"""
    main_content = {}
    
    # 尝试找到主内容区域
    main_candidates = soup.select('main, article, [role=main], #main, #content, .main, .content')
    
    if main_candidates:
        main_element = main_candidates[0]
        main_content["element_type"] = main_element.name
        main_content["id"] = main_element.get('id', '')
        main_content["classes"] = main_element.get('class', [])
        
        # 提取主内容区域的基本统计信息
        main_content["text_length"] = len(main_element.get_text(strip=True))
        main_content["paragraphs"] = len(main_element.find_all('p'))
        main_content["headings"] = len(main_element.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']))
        main_content["images"] = len(main_element.find_all('img'))
    else:
        # 如果找不到明确的主内容区域，使用启发式方法
        body = soup.body
        if body:
            # 假设正文在body下的主要块级元素中
            main_blocks = body.find_all(['div', 'section'], recursive=False)
            if main_blocks:
                # 选择包含最多段落的块作为主内容
                main_block = max(main_blocks, key=lambda x: len(x.find_all('p')))
                main_content["element_type"] = main_block.name
                main_content["id"] = main_block.get('id', '')
                main_content["classes"] = main_block.get('class', [])
                main_content["text_length"] = len(main_block.get_text(strip=True))
                main_content["paragraphs"] = len(main_block.find_all('p'))
                main_content["headings"] = len(main_block.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']))
                main_content["images"] = len(main_block.find_all('img'))
            else:
                main_content["element_type"] = "body"
                main_content["text_length"] = len(body.get_text(strip=True))
                main_content["paragraphs"] = len(body.find_all('p'))
                main_content["headings"] = len(body.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']))
                main_content["images"] = len(body.find_all('img'))
    
    return main_content


def _extract_document_sections(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """提取文档的主要部分"""
    sections = []
    
    # 检查是否有明确的section元素
    explicit_sections = soup.find_all('section')
    if explicit_sections:
        for idx, section in enumerate(explicit_sections):
            section_info = {
                "id": idx,
                "element_id": section.get('id', ''),
                "classes": section.get('class', []),
                "heading": _get_section_heading(section),
                "text_length": len(section.get_text(strip=True)),
                "paragraphs": len(section.find_all('p')),
                "images": len(section.find_all('img'))
            }
            sections.append(section_info)
    else:
        # 使用标题作为分节点
        headings = soup.find_all(['h1', 'h2'])
        for idx, heading in enumerate(headings):
            # 找到该标题后的所有元素，直到下一个相同级别或更高级别的标题
            section_content = []
            current = heading.next_sibling
            while current:
                if current.name in ['h1', 'h2'] and current != heading:
                    break
                if isinstance(current, Tag):
                    section_content.append(current)
                current = current.next_sibling
            
            # 计算该部分的统计信息
            section_text = ' '.join([elem.get_text(strip=True) for elem in section_content if isinstance(elem, Tag)])
            section_info = {
                "id": idx,
                "heading": heading.get_text(strip=True),
                "heading_level": int(heading.name[1]),
                "text_length": len(section_text),
                "paragraphs": sum(1 for elem in section_content if elem.name == 'p'),
                "images": sum(1 for elem in section_content if elem.name == 'img')
            }
            sections.append(section_info)
    
    return sections


def _get_section_heading(section: Tag) -> str:
    """获取section元素的标题"""
    headings = section.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'], recursive=False)
    if headings:
        return headings[0].get_text(strip=True)
    return ""


def _extract_heading_structure(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """提取标题层次结构"""
    headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    heading_structure = []
    
    for heading in headings:
        level = int(heading.name[1])
        text = heading.get_text(strip=True)
        
        heading_info = {
            "level": level,
            "text": text,
            "id": heading.get('id', ''),
            "position": _get_element_position(heading)
        }
        
        heading_structure.append(heading_info)
    
    return heading_structure


def _get_element_position(element: Tag) -> Dict[str, int]:
    """获取元素在文档中的相对位置"""
    # 获取所有元素
    all_elements = list(element.find_all())
    if element in all_elements:
        index = all_elements.index(element)
        return {
            "index": index,
            "percentage": round(index / len(all_elements) * 100) if all_elements else 0
        }
    return {"index": -1, "percentage": 0}


def _analyze_semantic_structure(soup: BeautifulSoup) -> Dict[str, Any]:
    """分析文档的语义结构"""
    semantic_structure = {
        "has_header": bool(soup.header),
        "has_footer": bool(soup.footer),
        "has_nav": bool(soup.nav),
        "has_main": bool(soup.main),
        "has_article": bool(soup.find('article')),
        "has_aside": bool(soup.find('aside')),
        "semantic_elements": {}
    }
    
    # 检查常见的语义元素
    semantic_tags = [
        'header', 'footer', 'nav', 'main', 'article', 'section', 
        'aside', 'figure', 'figcaption', 'time', 'mark', 'details', 
        'summary'
    ]
    
    for tag in semantic_tags:
        elements = soup.find_all(tag)
        if elements:
            semantic_structure["semantic_elements"][tag] = len(elements)
    
    return semantic_structure


def _generate_detailed_structure(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """生成详细的文档结构"""
    structure = []
    
    def process_element(element, depth=0):
        if isinstance(element, NavigableString):
            return None
        
        if not element.name:
            return None
        
        element_info = {
            "tag": element.name,
            "depth": depth,
            "id": element.get('id', ''),
            "classes": element.get('class', []),
            "children_count": len([c for c in element.children if isinstance(c, Tag)])
        }
        
        # 只包含有意义的属性
        important_attrs = ['href', 'src', 'alt', 'title', 'role', 'aria-label']
        attrs = {}
        for attr in important_attrs:
            if attr in element.attrs:
                attrs[attr] = element[attr]
        
        if attrs:
            element_info["attributes"] = attrs
        
        return element_info
    
    # 处理body下的直接子元素
    if soup.body:
        for child in soup.body.children:
            if isinstance(child, Tag):
                element_info = process_element(child)
                if element_info:
                    structure.append(element_info)
    
    return structure