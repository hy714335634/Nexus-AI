"""
文档结构解析工具

此模块为content_processor_agent提供技术文档结构解析功能，
用于将DocumentContent对象解析为结构化的元素树，为HTML生成做准备。
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
from enum import Enum
from strands import tool


class ElementType(str, Enum):
    """文档元素类型枚举"""
    TITLE = "title"
    HEADING_1 = "h1"
    HEADING_2 = "h2"
    HEADING_3 = "h3"
    HEADING_4 = "h4"
    HEADING_5 = "h5"
    HEADING_6 = "h6"
    PARAGRAPH = "paragraph"
    CODE_BLOCK = "code_block"
    INLINE_CODE = "inline_code"
    ORDERED_LIST = "ordered_list"
    UNORDERED_LIST = "unordered_list"
    LIST_ITEM = "list_item"
    TABLE = "table"
    TABLE_HEADER = "table_header"
    TABLE_ROW = "table_row"
    TABLE_CELL = "table_cell"
    BLOCKQUOTE = "blockquote"
    LINK = "link"
    IMAGE = "image"
    HORIZONTAL_RULE = "horizontal_rule"
    SECTION = "section"
    METADATA = "metadata"


class Element:
    """文档元素类"""
    def __init__(
        self,
        element_type: ElementType,
        content: str = "",
        attributes: Dict[str, Any] = None,
        children: List['Element'] = None,
        metadata: Dict[str, Any] = None
    ):
        self.element_type = element_type
        self.content = content
        self.attributes = attributes or {}
        self.children = children or []
        self.metadata = metadata or {}
        self.element_id = self._generate_id()
    
    def _generate_id(self) -> str:
        """生成唯一的元素ID"""
        import hashlib
        import uuid
        unique_str = f"{self.element_type}_{self.content[:50]}_{uuid.uuid4()}"
        return hashlib.md5(unique_str.encode()).hexdigest()[:12]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "element_id": self.element_id,
            "element_type": self.element_type.value,
            "content": self.content,
            "attributes": self.attributes,
            "children": [child.to_dict() for child in self.children],
            "metadata": self.metadata
        }


def _parse_markdown_syntax(text: str) -> List[Element]:
    """
    解析Markdown语法的文本，识别各种元素
    
    Args:
        text: 文本内容
        
    Returns:
        元素列表
    """
    elements = []
    lines = text.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # 跳过空行
        if not stripped:
            i += 1
            continue
        
        # 标题
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
        if heading_match:
            level = len(heading_match.group(1))
            content = heading_match.group(2).strip()
            element_type = getattr(ElementType, f"HEADING_{level}")
            elements.append(Element(element_type, content))
            i += 1
            continue
        
        # 代码块
        if stripped.startswith('```'):
            code_lang = stripped[3:].strip() or "text"
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            code_content = '\n'.join(code_lines)
            elements.append(Element(
                ElementType.CODE_BLOCK,
                code_content,
                attributes={"language": code_lang}
            ))
            i += 1
            continue
        
        # 有序列表
        if re.match(r'^\d+\.\s+', stripped):
            list_items = []
            while i < len(lines):
                item_match = re.match(r'^\d+\.\s+(.+)$', lines[i].strip())
                if not item_match:
                    break
                list_items.append(Element(ElementType.LIST_ITEM, item_match.group(1)))
                i += 1
            elements.append(Element(ElementType.ORDERED_LIST, children=list_items))
            continue
        
        # 无序列表
        if re.match(r'^[\*\-\+]\s+', stripped):
            list_items = []
            while i < len(lines):
                item_match = re.match(r'^[\*\-\+]\s+(.+)$', lines[i].strip())
                if not item_match:
                    break
                list_items.append(Element(ElementType.LIST_ITEM, item_match.group(1)))
                i += 1
            elements.append(Element(ElementType.UNORDERED_LIST, children=list_items))
            continue
        
        # 引用块
        if stripped.startswith('>'):
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                quote_lines.append(lines[i].strip()[1:].strip())
                i += 1
            quote_content = '\n'.join(quote_lines)
            elements.append(Element(ElementType.BLOCKQUOTE, quote_content))
            continue
        
        # 水平分隔线
        if re.match(r'^[\*\-_]{3,}$', stripped):
            elements.append(Element(ElementType.HORIZONTAL_RULE))
            i += 1
            continue
        
        # 表格
        if '|' in stripped:
            table_lines = []
            while i < len(lines) and '|' in lines[i]:
                table_lines.append(lines[i].strip())
                i += 1
            table_element = _parse_table(table_lines)
            if table_element:
                elements.append(table_element)
            continue
        
        # 普通段落
        paragraph_lines = [stripped]
        i += 1
        while i < len(lines) and lines[i].strip() and not _is_special_line(lines[i]):
            paragraph_lines.append(lines[i].strip())
            i += 1
        
        paragraph_content = ' '.join(paragraph_lines)
        # 处理内联代码
        paragraph_content = _mark_inline_code(paragraph_content)
        elements.append(Element(ElementType.PARAGRAPH, paragraph_content))
    
    return elements


def _is_special_line(line: str) -> bool:
    """检查是否为特殊行（标题、列表、代码块等）"""
    stripped = line.strip()
    patterns = [
        r'^#{1,6}\s+',  # 标题
        r'^```',  # 代码块
        r'^\d+\.\s+',  # 有序列表
        r'^[\*\-\+]\s+',  # 无序列表
        r'^>',  # 引用
        r'^[\*\-_]{3,}$',  # 水平线
        r'\|'  # 表格
    ]
    return any(re.match(pattern, stripped) for pattern in patterns)


def _mark_inline_code(text: str) -> str:
    """标记内联代码"""
    return text


def _parse_table(table_lines: List[str]) -> Optional[Element]:
    """
    解析Markdown表格
    
    Args:
        table_lines: 表格行列表
        
    Returns:
        表格元素
    """
    if len(table_lines) < 2:
        return None
    
    # 解析表头
    header_cells = [cell.strip() for cell in table_lines[0].split('|') if cell.strip()]
    header_row = Element(
        ElementType.TABLE_HEADER,
        children=[Element(ElementType.TABLE_CELL, cell) for cell in header_cells]
    )
    
    # 跳过分隔行
    body_rows = []
    for line in table_lines[2:]:
        cells = [cell.strip() for cell in line.split('|') if cell.strip()]
        row = Element(
            ElementType.TABLE_ROW,
            children=[Element(ElementType.TABLE_CELL, cell) for cell in cells]
        )
        body_rows.append(row)
    
    return Element(
        ElementType.TABLE,
        children=[header_row] + body_rows,
        attributes={"columns": len(header_cells)}
    )


def _extract_sections(elements: List[Element]) -> List[Element]:
    """
    将元素组织为章节结构
    
    Args:
        elements: 元素列表
        
    Returns:
        章节化的元素列表
    """
    sections = []
    current_section = None
    
    for element in elements:
        # 一级标题创建新章节
        if element.element_type == ElementType.HEADING_1:
            if current_section:
                sections.append(current_section)
            current_section = Element(
                ElementType.SECTION,
                content=element.content,
                children=[element],
                attributes={"level": 1}
            )
        # 其他元素添加到当前章节
        elif current_section:
            current_section.children.append(element)
        else:
            # 如果还没有章节，创建一个默认章节
            current_section = Element(
                ElementType.SECTION,
                content="Introduction",
                children=[element],
                attributes={"level": 1}
            )
    
    if current_section:
        sections.append(current_section)
    
    return sections


@tool
def parse_document_structure(
    document_content: Dict[str, Any],
    parse_mode: str = "auto"
) -> str:
    """
    解析文档内容并识别各个章节和元素
    
    此工具接收DocumentContent对象，解析其结构并生成结构化的元素树。
    元素树包含标题、章节、代码块、列表、表格等各种文档元素。
    
    Args:
        document_content (Dict[str, Any]): DocumentContent对象，包含以下字段：
            - title: 文档标题
            - sections: 章节列表，每个章节包含content字段
            - metadata: 元数据
            - version: 版本号
        parse_mode (str): 解析模式，可选值:
            - "auto": 自动检测内容格式并解析
            - "markdown": 按Markdown格式解析
            - "plain": 按纯文本解析
            
    Returns:
        str: JSON格式的结构化元素树，包含以下结构：
            {
                "status": "success",
                "document_tree": {
                    "title": "文档标题",
                    "metadata": {...},
                    "sections": [...],  # 章节元素列表
                    "statistics": {...}  # 统计信息
                },
                "parse_info": {
                    "parse_mode": "使用的解析模式",
                    "element_count": 元素总数,
                    "parsing_time": 解析耗时(秒)
                }
            }
    """
    try:
        start_time = datetime.now()
        
        # 验证输入
        if not isinstance(document_content, dict):
            raise ValueError("document_content必须是字典类型")
        
        if "title" not in document_content or "sections" not in document_content:
            raise ValueError("document_content必须包含title和sections字段")
        
        # 提取基本信息
        title = document_content.get("title", "Untitled Document")
        sections = document_content.get("sections", [])
        metadata = document_content.get("metadata", {})
        version = document_content.get("version", "1.0")
        
        # 创建文档根元素
        all_elements = []
        
        # 添加标题
        title_element = Element(ElementType.TITLE, title)
        all_elements.append(title_element)
        
        # 解析每个章节
        for section in sections:
            section_content = section.get("content", "")
            section_title = section.get("title", "")
            
            # 如果章节有标题，添加章节标题
            if section_title:
                section_elements = [Element(ElementType.HEADING_2, section_title)]
            else:
                section_elements = []
            
            # 根据解析模式处理内容
            if parse_mode == "markdown" or (parse_mode == "auto" and _is_markdown_content(section_content)):
                parsed_elements = _parse_markdown_syntax(section_content)
                section_elements.extend(parsed_elements)
            else:
                # 纯文本模式，按段落分割
                paragraphs = [p.strip() for p in section_content.split('\n\n') if p.strip()]
                for para in paragraphs:
                    section_elements.append(Element(ElementType.PARAGRAPH, para))
            
            # 将章节元素包装为Section
            section_element = Element(
                ElementType.SECTION,
                content=section_title,
                children=section_elements,
                attributes={"section_id": section.get("id", "")},
                metadata=section.get("metadata", {})
            )
            all_elements.append(section_element)
        
        # 组织为章节结构
        organized_sections = _extract_sections(all_elements)
        
        # 计算统计信息
        statistics = _calculate_statistics(organized_sections)
        
        # 构建文档树
        document_tree = {
            "title": title,
            "metadata": {
                **metadata,
                "version": version,
                "parsed_at": datetime.now().isoformat()
            },
            "sections": [section.to_dict() for section in organized_sections],
            "statistics": statistics
        }
        
        # 计算解析时间
        end_time = datetime.now()
        parsing_time = (end_time - start_time).total_seconds()
        
        # 构建响应
        response = {
            "status": "success",
            "document_tree": document_tree,
            "parse_info": {
                "parse_mode": parse_mode,
                "element_count": statistics["total_elements"],
                "parsing_time": parsing_time
            }
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_response, ensure_ascii=False)


def _is_markdown_content(content: str) -> bool:
    """
    检测内容是否为Markdown格式
    
    Args:
        content: 内容字符串
        
    Returns:
        是否为Markdown格式
    """
    markdown_patterns = [
        r'^#{1,6}\s+',  # 标题
        r'```',  # 代码块
        r'^\d+\.\s+',  # 有序列表
        r'^[\*\-\+]\s+',  # 无序列表
        r'^\>',  # 引用
        r'\[.+\]\(.+\)',  # 链接
        r'!\[.+\]\(.+\)',  # 图片
        r'\*\*.+\*\*',  # 粗体
        r'__.+__',  # 粗体
        r'\*.+\*',  # 斜体
        r'_.+_',  # 斜体
    ]
    
    for pattern in markdown_patterns:
        if re.search(pattern, content, re.MULTILINE):
            return True
    
    return False


def _calculate_statistics(sections: List[Element]) -> Dict[str, Any]:
    """
    计算文档统计信息
    
    Args:
        sections: 章节列表
        
    Returns:
        统计信息字典
    """
    stats = {
        "total_sections": len(sections),
        "total_elements": 0,
        "element_counts": {},
        "total_words": 0,
        "code_blocks": 0,
        "tables": 0,
        "lists": 0,
        "images": 0,
        "links": 0
    }
    
    def count_elements(element: Element):
        """递归计算元素"""
        stats["total_elements"] += 1
        
        # 统计各类元素数量
        element_type = element.element_type.value
        stats["element_counts"][element_type] = stats["element_counts"].get(element_type, 0) + 1
        
        # 统计特定类型
        if element.element_type == ElementType.CODE_BLOCK:
            stats["code_blocks"] += 1
        elif element.element_type == ElementType.TABLE:
            stats["tables"] += 1
        elif element.element_type in [ElementType.ORDERED_LIST, ElementType.UNORDERED_LIST]:
            stats["lists"] += 1
        elif element.element_type == ElementType.IMAGE:
            stats["images"] += 1
        elif element.element_type == ElementType.LINK:
            stats["links"] += 1
        
        # 统计字数
        if element.content:
            words = len(element.content.split())
            stats["total_words"] += words
        
        # 递归处理子元素
        for child in element.children:
            count_elements(child)
    
    for section in sections:
        count_elements(section)
    
    return stats


@tool
def extract_document_elements(
    document_content: Dict[str, Any],
    element_types: List[str] = None,
    filter_empty: bool = True
) -> str:
    """
    从文档中提取特定类型的元素
    
    此工具用于从DocumentContent中提取特定类型的元素，如所有标题、
    所有代码块、所有表格等。
    
    Args:
        document_content (Dict[str, Any]): DocumentContent对象
        element_types (List[str]): 要提取的元素类型列表，如["h1", "h2", "code_block"]
            如果为None，则提取所有元素
        filter_empty (bool): 是否过滤空内容的元素
            
    Returns:
        str: JSON格式的提取结果，包含：
            {
                "status": "success",
                "elements": [...],  # 提取的元素列表
                "count": 元素数量,
                "element_types": 实际提取的元素类型列表
            }
    """
    try:
        # 首先解析文档结构
        parse_result = json.loads(parse_document_structure(document_content))
        
        if parse_result["status"] != "success":
            return json.dumps(parse_result, ensure_ascii=False)
        
        document_tree = parse_result["document_tree"]
        sections = document_tree["sections"]
        
        # 提取元素
        extracted_elements = []
        
        def extract_recursive(element_dict: Dict[str, Any]):
            """递归提取元素"""
            element_type = element_dict["element_type"]
            
            # 检查是否匹配目标类型
            if element_types is None or element_type in element_types:
                # 检查是否过滤空内容
                if not filter_empty or element_dict.get("content", "").strip():
                    extracted_elements.append(element_dict)
            
            # 递归处理子元素
            for child in element_dict.get("children", []):
                extract_recursive(child)
        
        # 处理所有章节
        for section in sections:
            extract_recursive(section)
        
        # 构建响应
        response = {
            "status": "success",
            "elements": extracted_elements,
            "count": len(extracted_elements),
            "element_types": list(set(elem["element_type"] for elem in extracted_elements))
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def validate_document_structure(
    document_content: Dict[str, Any],
    validation_rules: Dict[str, Any] = None
) -> str:
    """
    验证文档结构的完整性和有效性
    
    此工具用于检查DocumentContent的结构是否符合要求，
    包括必需字段、格式规范、内容完整性等。
    
    Args:
        document_content (Dict[str, Any]): DocumentContent对象
        validation_rules (Dict[str, Any]): 验证规则配置，包括：
            - require_title: 是否要求标题（默认True）
            - min_sections: 最少章节数（默认1）
            - max_sections: 最大章节数（默认None）
            - require_metadata: 是否要求元数据（默认False）
            - check_content_quality: 是否检查内容质量（默认True）
            
    Returns:
        str: JSON格式的验证结果，包含：
            {
                "status": "success" 或 "error",
                "is_valid": 是否有效,
                "validation_errors": [...],  # 验证错误列表
                "validation_warnings": [...],  # 验证警告列表
                "validation_summary": "验证摘要"
            }
    """
    try:
        # 默认验证规则
        default_rules = {
            "require_title": True,
            "min_sections": 1,
            "max_sections": None,
            "require_metadata": False,
            "check_content_quality": True
        }
        
        # 合并用户规则
        rules = {**default_rules, **(validation_rules or {})}
        
        errors = []
        warnings = []
        
        # 验证基本结构
        if not isinstance(document_content, dict):
            errors.append({
                "field": "root",
                "error": "document_content必须是字典类型"
            })
            return json.dumps({
                "status": "error",
                "is_valid": False,
                "validation_errors": errors,
                "validation_warnings": warnings,
                "validation_summary": "文档结构无效"
            }, ensure_ascii=False)
        
        # 验证标题
        if rules["require_title"]:
            title = document_content.get("title", "").strip()
            if not title:
                errors.append({
                    "field": "title",
                    "error": "标题不能为空"
                })
            elif len(title) < 3:
                warnings.append({
                    "field": "title",
                    "warning": "标题过短，建议至少3个字符"
                })
        
        # 验证章节
        sections = document_content.get("sections", [])
        if not isinstance(sections, list):
            errors.append({
                "field": "sections",
                "error": "sections必须是列表类型"
            })
        else:
            section_count = len(sections)
            
            if section_count < rules["min_sections"]:
                errors.append({
                    "field": "sections",
                    "error": f"章节数量({section_count})少于最小要求({rules['min_sections']})"
                })
            
            if rules["max_sections"] and section_count > rules["max_sections"]:
                warnings.append({
                    "field": "sections",
                    "warning": f"章节数量({section_count})超过建议最大值({rules['max_sections']})"
                })
            
            # 验证每个章节
            for i, section in enumerate(sections):
                if not isinstance(section, dict):
                    errors.append({
                        "field": f"sections[{i}]",
                        "error": "章节必须是字典类型"
                    })
                    continue
                
                if "content" not in section:
                    errors.append({
                        "field": f"sections[{i}]",
                        "error": "章节缺少content字段"
                    })
                elif not section["content"].strip():
                    warnings.append({
                        "field": f"sections[{i}]",
                        "warning": "章节内容为空"
                    })
        
        # 验证元数据
        if rules["require_metadata"]:
            metadata = document_content.get("metadata", {})
            if not metadata:
                errors.append({
                    "field": "metadata",
                    "error": "缺少元数据"
                })
        
        # 内容质量检查
        if rules["check_content_quality"]:
            quality_issues = _check_content_quality(document_content)
            warnings.extend(quality_issues)
        
        # 判断是否有效
        is_valid = len(errors) == 0
        
        # 生成验证摘要
        if is_valid:
            if warnings:
                validation_summary = f"文档结构有效，但有{len(warnings)}个警告"
            else:
                validation_summary = "文档结构完全有效"
        else:
            validation_summary = f"文档结构无效，发现{len(errors)}个错误"
        
        # 构建响应
        response = {
            "status": "success",
            "is_valid": is_valid,
            "validation_errors": errors,
            "validation_warnings": warnings,
            "validation_summary": validation_summary
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_response, ensure_ascii=False)


def _check_content_quality(document_content: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    检查内容质量
    
    Args:
        document_content: 文档内容
        
    Returns:
        质量问题列表
    """
    warnings = []
    
    sections = document_content.get("sections", [])
    
    for i, section in enumerate(sections):
        content = section.get("content", "")
        
        # 检查内容长度
        if len(content) < 50:
            warnings.append({
                "field": f"sections[{i}].content",
                "warning": "章节内容过短，建议至少50个字符"
            })
        
        # 检查是否有代码块但未标记语言
        code_blocks = re.findall(r'```(\w*)\n', content)
        for j, lang in enumerate(code_blocks):
            if not lang:
                warnings.append({
                    "field": f"sections[{i}].content",
                    "warning": f"代码块{j+1}未标记编程语言"
                })
    
    return warnings


@tool
def normalize_document_structure(
    document_content: Dict[str, Any],
    normalization_options: Dict[str, Any] = None
) -> str:
    """
    规范化文档结构，修复常见问题
    
    此工具用于自动修复文档结构中的常见问题，如缺失字段、
    格式不一致、空内容等。
    
    Args:
        document_content (Dict[str, Any]): DocumentContent对象
        normalization_options (Dict[str, Any]): 规范化选项，包括：
            - add_default_title: 是否添加默认标题（默认True）
            - remove_empty_sections: 是否移除空章节（默认True）
            - fix_heading_levels: 是否修复标题层级（默认True）
            - standardize_code_blocks: 是否标准化代码块（默认True）
            
    Returns:
        str: JSON格式的规范化后的文档内容
    """
    try:
        # 默认选项
        default_options = {
            "add_default_title": True,
            "remove_empty_sections": True,
            "fix_heading_levels": True,
            "standardize_code_blocks": True
        }
        
        # 合并用户选项
        options = {**default_options, **(normalization_options or {})}
        
        # 复制文档内容以避免修改原始数据
        normalized_content = json.loads(json.dumps(document_content))
        
        modifications = []
        
        # 添加默认标题
        if options["add_default_title"] and not normalized_content.get("title", "").strip():
            normalized_content["title"] = "Technical Document"
            modifications.append("添加了默认标题")
        
        # 处理章节
        sections = normalized_content.get("sections", [])
        if not sections:
            normalized_content["sections"] = [{
                "title": "Introduction",
                "content": ""
            }]
            modifications.append("添加了默认章节")
        
        # 移除空章节
        if options["remove_empty_sections"]:
            original_count = len(sections)
            sections = [s for s in sections if s.get("content", "").strip()]
            normalized_content["sections"] = sections
            removed = original_count - len(sections)
            if removed > 0:
                modifications.append(f"移除了{removed}个空章节")
        
        # 修复标题层级
        if options["fix_heading_levels"]:
            for section in normalized_content["sections"]:
                content = section.get("content", "")
                # 确保标题层级连续
                content = _fix_heading_hierarchy(content)
                section["content"] = content
            modifications.append("修复了标题层级")
        
        # 标准化代码块
        if options["standardize_code_blocks"]:
            for section in normalized_content["sections"]:
                content = section.get("content", "")
                content = _standardize_code_blocks(content)
                section["content"] = content
            modifications.append("标准化了代码块格式")
        
        # 添加元数据
        if "metadata" not in normalized_content:
            normalized_content["metadata"] = {}
        
        normalized_content["metadata"]["normalized_at"] = datetime.now().isoformat()
        normalized_content["metadata"]["modifications"] = modifications
        
        # 构建响应
        response = {
            "status": "success",
            "normalized_content": normalized_content,
            "modifications": modifications,
            "modification_count": len(modifications)
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_response, ensure_ascii=False)


def _fix_heading_hierarchy(content: str) -> str:
    """
    修复标题层级，确保标题级别连续
    
    Args:
        content: 内容文本
        
    Returns:
        修复后的内容
    """
    lines = content.split('\n')
    fixed_lines = []
    current_level = 0
    
    for line in lines:
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', line.strip())
        if heading_match:
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2)
            
            # 确保层级不跳跃
            if current_level == 0:
                adjusted_level = 1
            elif level > current_level + 1:
                adjusted_level = current_level + 1
            else:
                adjusted_level = level
            
            current_level = adjusted_level
            fixed_lines.append(f"{'#' * adjusted_level} {heading_text}")
        else:
            fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def _standardize_code_blocks(content: str) -> str:
    """
    标准化代码块格式
    
    Args:
        content: 内容文本
        
    Returns:
        标准化后的内容
    """
    # 为未标记语言的代码块添加默认语言
    def replace_code_block(match):
        lang = match.group(1).strip()
        code = match.group(2)
        if not lang:
            lang = "text"
        return f"```{lang}\n{code}\n```"
    
    content = re.sub(r'```(\w*)\n(.*?)\n```', replace_code_block, content, flags=re.DOTALL)
    
    return content


@tool
def analyze_document_complexity(
    document_content: Dict[str, Any]
) -> str:
    """
    分析文档的复杂度
    
    此工具用于评估文档的复杂程度，包括结构复杂度、内容复杂度等，
    为HTML样式选择和布局优化提供参考。
    
    Args:
        document_content (Dict[str, Any]): DocumentContent对象
            
    Returns:
        str: JSON格式的复杂度分析结果，包含：
            {
                "status": "success",
                "complexity_score": 复杂度评分(0-100),
                "complexity_level": "simple" | "moderate" | "complex",
                "factors": {
                    "structure_complexity": 结构复杂度,
                    "content_complexity": 内容复杂度,
                    "element_diversity": 元素多样性
                },
                "recommendations": [...]  # 建议列表
            }
    """
    try:
        # 解析文档结构
        parse_result = json.loads(parse_document_structure(document_content))
        
        if parse_result["status"] != "success":
            return json.dumps(parse_result, ensure_ascii=False)
        
        document_tree = parse_result["document_tree"]
        statistics = document_tree["statistics"]
        
        # 计算各项复杂度因子
        
        # 1. 结构复杂度（基于章节数量和嵌套深度）
        section_count = statistics["total_sections"]
        structure_score = min(section_count * 5, 40)  # 最高40分
        
        # 2. 内容复杂度（基于元素数量和类型多样性）
        element_count = statistics["total_elements"]
        element_types = len(statistics["element_counts"])
        content_score = min(element_count * 0.5 + element_types * 2, 40)  # 最高40分
        
        # 3. 元素多样性（基于特殊元素数量）
        special_elements = (
            statistics.get("code_blocks", 0) +
            statistics.get("tables", 0) +
            statistics.get("images", 0)
        )
        diversity_score = min(special_elements * 5, 20)  # 最高20分
        
        # 总复杂度评分
        complexity_score = structure_score + content_score + diversity_score
        
        # 确定复杂度等级
        if complexity_score < 30:
            complexity_level = "simple"
        elif complexity_score < 60:
            complexity_level = "moderate"
        else:
            complexity_level = "complex"
        
        # 生成建议
        recommendations = []
        
        if complexity_level == "simple":
            recommendations.append("文档结构简单，可使用基础HTML模板")
            recommendations.append("建议使用单列布局")
        elif complexity_level == "moderate":
            recommendations.append("文档结构中等，建议使用标准HTML模板")
            recommendations.append("可以考虑添加目录导航")
            recommendations.append("建议使用响应式布局")
        else:
            recommendations.append("文档结构复杂，建议使用高级HTML模板")
            recommendations.append("强烈建议添加交互式目录")
            recommendations.append("建议实现章节折叠功能")
            recommendations.append("考虑添加搜索功能")
        
        if statistics.get("code_blocks", 0) > 0:
            recommendations.append("包含代码块，建议使用语法高亮")
        
        if statistics.get("tables", 0) > 0:
            recommendations.append("包含表格，建议使用表格样式优化")
        
        # 构建响应
        response = {
            "status": "success",
            "complexity_score": round(complexity_score, 2),
            "complexity_level": complexity_level,
            "factors": {
                "structure_complexity": round(structure_score, 2),
                "content_complexity": round(content_score, 2),
                "element_diversity": round(diversity_score, 2)
            },
            "statistics": statistics,
            "recommendations": recommendations
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_response, ensure_ascii=False)
