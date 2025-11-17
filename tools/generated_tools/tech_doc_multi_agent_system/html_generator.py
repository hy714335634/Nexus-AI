"""
HTML生成工具

此模块为content_processor_agent提供HTML文档生成功能，
将解析的文档结构树转换为符合HTML5标准的完整HTML文档。
"""

import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
from html import escape
from strands import tool


class HTMLGenerator:
    """HTML生成器类"""
    
    def __init__(self, style_config: Dict[str, Any] = None):
        self.style_config = style_config or {}
        self.indent_level = 0
        self.indent_size = 2
    
    def generate(self, document_tree: Dict[str, Any]) -> str:
        """
        生成HTML文档
        
        Args:
            document_tree: 文档树结构
            
        Returns:
            完整的HTML字符串
        """
        html_parts = []
        
        # HTML文档头部
        html_parts.append(self._generate_doctype())
        html_parts.append(self._generate_html_open())
        html_parts.append(self._generate_head(document_tree))
        html_parts.append(self._generate_body_open())
        
        # 文档内容
        html_parts.append(self._generate_header(document_tree))
        html_parts.append(self._generate_toc(document_tree))
        html_parts.append(self._generate_main_content(document_tree))
        html_parts.append(self._generate_footer(document_tree))
        
        # HTML文档尾部
        html_parts.append(self._generate_body_close())
        html_parts.append(self._generate_html_close())
        
        return '\n'.join(html_parts)
    
    def _generate_doctype(self) -> str:
        """生成DOCTYPE声明"""
        return "<!DOCTYPE html>"
    
    def _generate_html_open(self) -> str:
        """生成HTML开标签"""
        lang = self.style_config.get("language", "en")
        return f'<html lang="{lang}">'
    
    def _generate_html_close(self) -> str:
        """生成HTML闭标签"""
        return "</html>"
    
    def _generate_head(self, document_tree: Dict[str, Any]) -> str:
        """生成HTML头部"""
        title = escape(document_tree.get("title", "Technical Document"))
        metadata = document_tree.get("metadata", {})
        
        head_parts = ["<head>"]
        head_parts.append('  <meta charset="UTF-8">')
        head_parts.append('  <meta name="viewport" content="width=device-width, initial-scale=1.0">')
        head_parts.append(f'  <title>{title}</title>')
        
        # 添加元数据
        if "description" in metadata:
            description = escape(str(metadata["description"]))
            head_parts.append(f'  <meta name="description" content="{description}">')
        
        if "author" in metadata:
            author = escape(str(metadata["author"]))
            head_parts.append(f'  <meta name="author" content="{author}">')
        
        if "keywords" in metadata:
            keywords = escape(str(metadata["keywords"]))
            head_parts.append(f'  <meta name="keywords" content="{keywords}">')
        
        # 添加CSS样式
        head_parts.append(self._generate_styles())
        
        head_parts.append("</head>")
        return '\n'.join(head_parts)
    
    def _generate_styles(self) -> str:
        """生成CSS样式"""
        theme = self.style_config.get("theme", "default")
        
        if theme == "dark":
            primary_color = "#1e1e1e"
            text_color = "#e0e0e0"
            bg_color = "#121212"
            code_bg = "#2d2d2d"
        else:
            primary_color = "#2c3e50"
            text_color = "#333333"
            bg_color = "#ffffff"
            code_bg = "#f5f5f5"
        
        styles = f"""  <style>
    /* 重置和基础样式 */
    * {{
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }}
    
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
      font-size: 16px;
      line-height: 1.6;
      color: {text_color};
      background-color: {bg_color};
      max-width: 1200px;
      margin: 0 auto;
      padding: 20px;
    }}
    
    /* 标题样式 */
    h1, h2, h3, h4, h5, h6 {{
      color: {primary_color};
      margin-top: 1.5em;
      margin-bottom: 0.5em;
      font-weight: 600;
      line-height: 1.3;
    }}
    
    h1 {{
      font-size: 2.5em;
      border-bottom: 3px solid {primary_color};
      padding-bottom: 0.3em;
    }}
    
    h2 {{
      font-size: 2em;
      border-bottom: 2px solid {primary_color};
      padding-bottom: 0.3em;
    }}
    
    h3 {{
      font-size: 1.5em;
    }}
    
    h4 {{
      font-size: 1.25em;
    }}
    
    h5 {{
      font-size: 1.1em;
    }}
    
    h6 {{
      font-size: 1em;
    }}
    
    /* 段落样式 */
    p {{
      margin: 1em 0;
      text-align: justify;
    }}
    
    /* 代码样式 */
    code {{
      font-family: 'Courier New', Courier, monospace;
      background-color: {code_bg};
      padding: 2px 6px;
      border-radius: 3px;
      font-size: 0.9em;
    }}
    
    pre {{
      background-color: {code_bg};
      border: 1px solid #ddd;
      border-radius: 5px;
      padding: 15px;
      overflow-x: auto;
      margin: 1em 0;
    }}
    
    pre code {{
      background-color: transparent;
      padding: 0;
      border-radius: 0;
    }}
    
    /* 列表样式 */
    ul, ol {{
      margin: 1em 0;
      padding-left: 2em;
    }}
    
    li {{
      margin: 0.5em 0;
    }}
    
    /* 表格样式 */
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 1em 0;
      background-color: {bg_color};
    }}
    
    th, td {{
      border: 1px solid #ddd;
      padding: 12px;
      text-align: left;
    }}
    
    th {{
      background-color: {primary_color};
      color: white;
      font-weight: 600;
    }}
    
    tr:nth-child(even) {{
      background-color: rgba(0, 0, 0, 0.02);
    }}
    
    /* 引用块样式 */
    blockquote {{
      border-left: 4px solid {primary_color};
      padding-left: 1em;
      margin: 1em 0;
      font-style: italic;
      color: #666;
    }}
    
    /* 链接样式 */
    a {{
      color: {primary_color};
      text-decoration: none;
    }}
    
    a:hover {{
      text-decoration: underline;
    }}
    
    /* 图片样式 */
    img {{
      max-width: 100%;
      height: auto;
      display: block;
      margin: 1em auto;
    }}
    
    /* 水平分隔线 */
    hr {{
      border: none;
      border-top: 2px solid #ddd;
      margin: 2em 0;
    }}
    
    /* 导航目录样式 */
    .toc {{
      background-color: {code_bg};
      border: 1px solid #ddd;
      border-radius: 5px;
      padding: 20px;
      margin: 2em 0;
    }}
    
    .toc h2 {{
      margin-top: 0;
      font-size: 1.5em;
    }}
    
    .toc ul {{
      list-style-type: none;
      padding-left: 0;
    }}
    
    .toc ul ul {{
      padding-left: 1.5em;
    }}
    
    .toc li {{
      margin: 0.5em 0;
    }}
    
    /* 页眉样式 */
    header {{
      border-bottom: 3px solid {primary_color};
      padding-bottom: 20px;
      margin-bottom: 30px;
    }}
    
    header h1 {{
      border-bottom: none;
      margin-bottom: 10px;
    }}
    
    .metadata {{
      color: #666;
      font-size: 0.9em;
    }}
    
    /* 页脚样式 */
    footer {{
      border-top: 2px solid #ddd;
      padding-top: 20px;
      margin-top: 50px;
      text-align: center;
      color: #666;
      font-size: 0.9em;
    }}
    
    /* 响应式设计 */
    @media (max-width: 768px) {{
      body {{
        padding: 10px;
        font-size: 14px;
      }}
      
      h1 {{
        font-size: 2em;
      }}
      
      h2 {{
        font-size: 1.5em;
      }}
      
      table {{
        font-size: 0.9em;
      }}
    }}
  </style>"""
        
        return styles
    
    def _generate_body_open(self) -> str:
        """生成body开标签"""
        return "<body>"
    
    def _generate_body_close(self) -> str:
        """生成body闭标签"""
        return "</body>"
    
    def _generate_header(self, document_tree: Dict[str, Any]) -> str:
        """生成页眉"""
        title = escape(document_tree.get("title", "Technical Document"))
        metadata = document_tree.get("metadata", {})
        
        header_parts = ["<header>"]
        header_parts.append(f"  <h1>{title}</h1>")
        
        # 添加元数据信息
        meta_items = []
        if "author" in metadata:
            meta_items.append(f"Author: {escape(str(metadata['author']))}")
        if "version" in metadata:
            meta_items.append(f"Version: {escape(str(metadata['version']))}")
        if "created_at" in metadata:
            meta_items.append(f"Created: {escape(str(metadata['created_at']))}")
        
        if meta_items:
            header_parts.append(f'  <div class="metadata">{" | ".join(meta_items)}</div>')
        
        header_parts.append("</header>")
        return '\n'.join(header_parts)
    
    def _generate_toc(self, document_tree: Dict[str, Any]) -> str:
        """生成目录"""
        if not self.style_config.get("include_toc", True):
            return ""
        
        sections = document_tree.get("sections", [])
        if not sections:
            return ""
        
        toc_parts = ['<nav class="toc">']
        toc_parts.append("  <h2>Table of Contents</h2>")
        toc_parts.append("  <ul>")
        
        for section in sections:
            section_title = escape(section.get("content", "Section"))
            section_id = section.get("element_id", "")
            toc_parts.append(f'    <li><a href="#{section_id}">{section_title}</a></li>')
        
        toc_parts.append("  </ul>")
        toc_parts.append("</nav>")
        return '\n'.join(toc_parts)
    
    def _generate_main_content(self, document_tree: Dict[str, Any]) -> str:
        """生成主要内容"""
        sections = document_tree.get("sections", [])
        
        main_parts = ["<main>"]
        
        for section in sections:
            section_html = self._generate_element(section, indent=1)
            main_parts.append(section_html)
        
        main_parts.append("</main>")
        return '\n'.join(main_parts)
    
    def _generate_element(self, element: Dict[str, Any], indent: int = 0) -> str:
        """
        递归生成元素HTML
        
        Args:
            element: 元素字典
            indent: 缩进级别
            
        Returns:
            HTML字符串
        """
        element_type = element.get("element_type", "")
        content = element.get("content", "")
        attributes = element.get("attributes", {})
        children = element.get("children", [])
        element_id = element.get("element_id", "")
        
        indent_str = "  " * indent
        
        # 根据元素类型生成HTML
        if element_type == "title":
            return f'{indent_str}<h1>{escape(content)}</h1>'
        
        elif element_type.startswith("h"):
            level = element_type[1]
            id_attr = f' id="{element_id}"' if element_id else ''
            return f'{indent_str}<{element_type}{id_attr}>{escape(content)}</{element_type}>'
        
        elif element_type == "paragraph":
            # 处理内联代码和链接
            processed_content = self._process_inline_elements(content)
            return f'{indent_str}<p>{processed_content}</p>'
        
        elif element_type == "code_block":
            language = attributes.get("language", "text")
            escaped_code = escape(content)
            return f'{indent_str}<pre><code class="language-{language}">{escaped_code}</code></pre>'
        
        elif element_type == "inline_code":
            return f'<code>{escape(content)}</code>'
        
        elif element_type == "ordered_list":
            list_html = [f'{indent_str}<ol>']
            for child in children:
                list_html.append(self._generate_element(child, indent + 1))
            list_html.append(f'{indent_str}</ol>')
            return '\n'.join(list_html)
        
        elif element_type == "unordered_list":
            list_html = [f'{indent_str}<ul>']
            for child in children:
                list_html.append(self._generate_element(child, indent + 1))
            list_html.append(f'{indent_str}</ul>')
            return '\n'.join(list_html)
        
        elif element_type == "list_item":
            return f'{indent_str}<li>{escape(content)}</li>'
        
        elif element_type == "table":
            return self._generate_table(element, indent)
        
        elif element_type == "blockquote":
            return f'{indent_str}<blockquote>{escape(content)}</blockquote>'
        
        elif element_type == "link":
            href = attributes.get("href", "#")
            return f'<a href="{escape(href)}">{escape(content)}</a>'
        
        elif element_type == "image":
            src = attributes.get("src", "")
            alt = attributes.get("alt", "")
            return f'{indent_str}<img src="{escape(src)}" alt="{escape(alt)}" />'
        
        elif element_type == "horizontal_rule":
            return f'{indent_str}<hr />'
        
        elif element_type == "section":
            section_html = [f'{indent_str}<section id="{element_id}">']
            for child in children:
                section_html.append(self._generate_element(child, indent + 1))
            section_html.append(f'{indent_str}</section>')
            return '\n'.join(section_html)
        
        else:
            # 未知类型，作为div处理
            return f'{indent_str}<div>{escape(content)}</div>'
    
    def _generate_table(self, table_element: Dict[str, Any], indent: int) -> str:
        """生成表格HTML"""
        indent_str = "  " * indent
        children = table_element.get("children", [])
        
        table_html = [f'{indent_str}<table>']
        
        # 处理表头
        if children and children[0].get("element_type") == "table_header":
            header = children[0]
            table_html.append(f'{indent_str}  <thead>')
            table_html.append(f'{indent_str}    <tr>')
            for cell in header.get("children", []):
                cell_content = escape(cell.get("content", ""))
                table_html.append(f'{indent_str}      <th>{cell_content}</th>')
            table_html.append(f'{indent_str}    </tr>')
            table_html.append(f'{indent_str}  </thead>')
            
            # 处理表体
            if len(children) > 1:
                table_html.append(f'{indent_str}  <tbody>')
                for row in children[1:]:
                    if row.get("element_type") == "table_row":
                        table_html.append(f'{indent_str}    <tr>')
                        for cell in row.get("children", []):
                            cell_content = escape(cell.get("content", ""))
                            table_html.append(f'{indent_str}      <td>{cell_content}</td>')
                        table_html.append(f'{indent_str}    </tr>')
                table_html.append(f'{indent_str}  </tbody>')
        
        table_html.append(f'{indent_str}</table>')
        return '\n'.join(table_html)
    
    def _process_inline_elements(self, text: str) -> str:
        """
        处理内联元素（代码、链接、粗体、斜体等）
        
        Args:
            text: 文本内容
            
        Returns:
            处理后的HTML
        """
        # 内联代码
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
        
        # 粗体
        text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'__([^_]+)__', r'<strong>\1</strong>', text)
        
        # 斜体
        text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
        text = re.sub(r'_([^_]+)_', r'<em>\1</em>', text)
        
        # 链接
        text = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', lambda m: f'<a href="{escape(m.group(2))}">{escape(m.group(1))}</a>', text)
        
        # 图片
        text = re.sub(r'!\[([^\]]*)\]\(([^\)]+)\)', lambda m: f'<img src="{escape(m.group(2))}" alt="{escape(m.group(1))}" />', text)
        
        return text
    
    def _generate_footer(self, document_tree: Dict[str, Any]) -> str:
        """生成页脚"""
        metadata = document_tree.get("metadata", {})
        
        footer_parts = ["<footer>"]
        
        generated_at = metadata.get("parsed_at", datetime.now().isoformat())
        footer_parts.append(f'  <p>Generated on {generated_at}</p>')
        
        if "copyright" in metadata:
            copyright_text = escape(str(metadata["copyright"]))
            footer_parts.append(f'  <p>{copyright_text}</p>')
        
        footer_parts.append("</footer>")
        return '\n'.join(footer_parts)


@tool
def generate_html(
    element_tree: Dict[str, Any],
    style_config: Dict[str, Any] = None
) -> str:
    """
    将解析的结构转换为HTML代码
    
    此工具接收文档元素树和样式配置，生成符合HTML5标准的完整HTML文档。
    
    Args:
        element_tree (Dict[str, Any]): 元素树，由parse_document_structure生成
        style_config (Dict[str, Any]): 样式配置，包括：
            - theme: 主题（"default" | "dark" | "light"）
            - include_toc: 是否包含目录（默认True）
            - language: 文档语言（默认"en"）
            - custom_css: 自定义CSS样式
            
    Returns:
        str: JSON格式的生成结果，包含：
            {
                "status": "success",
                "html_content": "完整的HTML字符串",
                "html_size": HTML大小(字节),
                "generation_info": {
                    "theme": "使用的主题",
                    "generation_time": 生成耗时(秒)
                }
            }
    """
    try:
        start_time = datetime.now()
        
        # 验证输入
        if not isinstance(element_tree, dict):
            raise ValueError("element_tree必须是字典类型")
        
        if "document_tree" in element_tree:
            document_tree = element_tree["document_tree"]
        else:
            document_tree = element_tree
        
        # 创建HTML生成器
        generator = HTMLGenerator(style_config or {})
        
        # 生成HTML
        html_content = generator.generate(document_tree)
        
        # 计算生成时间
        end_time = datetime.now()
        generation_time = (end_time - start_time).total_seconds()
        
        # 构建响应
        response = {
            "status": "success",
            "html_content": html_content,
            "html_size": len(html_content.encode('utf-8')),
            "generation_info": {
                "theme": style_config.get("theme", "default") if style_config else "default",
                "include_toc": style_config.get("include_toc", True) if style_config else True,
                "generation_time": generation_time
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


@tool
def generate_html_with_syntax_highlighting(
    element_tree: Dict[str, Any],
    style_config: Dict[str, Any] = None,
    highlight_library: str = "prism"
) -> str:
    """
    生成带语法高亮的HTML文档
    
    此工具在基础HTML生成的基础上，添加代码语法高亮支持。
    
    Args:
        element_tree (Dict[str, Any]): 元素树
        style_config (Dict[str, Any]): 样式配置
        highlight_library (str): 语法高亮库（"prism" | "highlight.js"）
            
    Returns:
        str: JSON格式的生成结果，包含带语法高亮的HTML
    """
    try:
        # 先生成基础HTML
        base_result = json.loads(generate_html(element_tree, style_config))
        
        if base_result["status"] != "success":
            return json.dumps(base_result, ensure_ascii=False)
        
        html_content = base_result["html_content"]
        
        # 添加语法高亮库
        if highlight_library == "prism":
            highlight_css = '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism.min.css" />'
            highlight_js = '<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>'
        elif highlight_library == "highlight.js":
            highlight_css = '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/default.min.css" />'
            highlight_js = '<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>\n  <script>hljs.highlightAll();</script>'
        else:
            highlight_css = ""
            highlight_js = ""
        
        # 在</head>前插入CSS
        if highlight_css:
            html_content = html_content.replace("</head>", f"  {highlight_css}\n</head>")
        
        # 在</body>前插入JS
        if highlight_js:
            html_content = html_content.replace("</body>", f"  {highlight_js}\n</body>")
        
        # 构建响应
        response = {
            "status": "success",
            "html_content": html_content,
            "html_size": len(html_content.encode('utf-8')),
            "generation_info": {
                **base_result["generation_info"],
                "syntax_highlighting": highlight_library
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


@tool
def generate_responsive_html(
    element_tree: Dict[str, Any],
    style_config: Dict[str, Any] = None,
    breakpoints: Dict[str, int] = None
) -> str:
    """
    生成响应式HTML文档
    
    此工具生成支持多种设备的响应式HTML文档。
    
    Args:
        element_tree (Dict[str, Any]): 元素树
        style_config (Dict[str, Any]): 样式配置
        breakpoints (Dict[str, int]): 响应式断点配置，如：
            {
                "mobile": 480,
                "tablet": 768,
                "desktop": 1024
            }
            
    Returns:
        str: JSON格式的生成结果，包含响应式HTML
    """
    try:
        # 默认断点
        default_breakpoints = {
            "mobile": 480,
            "tablet": 768,
            "desktop": 1024
        }
        
        breakpoints = breakpoints or default_breakpoints
        
        # 更新样式配置以支持响应式
        enhanced_style_config = style_config or {}
        enhanced_style_config["responsive"] = True
        enhanced_style_config["breakpoints"] = breakpoints
        
        # 生成HTML
        result = json.loads(generate_html(element_tree, enhanced_style_config))
        
        if result["status"] != "success":
            return json.dumps(result, ensure_ascii=False)
        
        html_content = result["html_content"]
        
        # 添加响应式meta标签（如果还没有）
        if 'name="viewport"' not in html_content:
            html_content = html_content.replace(
                '<meta charset="UTF-8">',
                '<meta charset="UTF-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1.0">'
            )
        
        # 添加额外的响应式CSS
        responsive_css = f"""
    /* 额外的响应式样式 */
    @media (max-width: {breakpoints['mobile']}px) {{
      body {{
        font-size: 14px;
        padding: 10px;
      }}
      
      h1 {{
        font-size: 1.8em;
      }}
      
      h2 {{
        font-size: 1.5em;
      }}
      
      .toc {{
        padding: 15px;
      }}
    }}
    
    @media (min-width: {breakpoints['mobile'] + 1}px) and (max-width: {breakpoints['tablet']}px) {{
      body {{
        font-size: 15px;
        padding: 15px;
      }}
    }}
    
    @media (min-width: {breakpoints['tablet'] + 1}px) {{
      body {{
        font-size: 16px;
        padding: 20px;
      }}
    }}
  </style>"""
        
        # 在</style>前插入响应式CSS
        html_content = html_content.replace("</style>", f"{responsive_css}\n  </style>")
        
        # 构建响应
        response = {
            "status": "success",
            "html_content": html_content,
            "html_size": len(html_content.encode('utf-8')),
            "generation_info": {
                **result["generation_info"],
                "responsive": True,
                "breakpoints": breakpoints
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


@tool
def generate_html_fragment(
    elements: List[Dict[str, Any]],
    wrapper_tag: str = "div"
) -> str:
    """
    生成HTML片段（不包含完整的HTML文档结构）
    
    此工具用于生成HTML片段，可用于嵌入到其他HTML文档中。
    
    Args:
        elements (List[Dict[str, Any]]): 元素列表
        wrapper_tag (str): 包装标签（默认"div"）
            
    Returns:
        str: JSON格式的生成结果，包含HTML片段
    """
    try:
        generator = HTMLGenerator()
        
        html_parts = []
        if wrapper_tag:
            html_parts.append(f"<{wrapper_tag}>")
        
        for element in elements:
            element_html = generator._generate_element(element, indent=1 if wrapper_tag else 0)
            html_parts.append(element_html)
        
        if wrapper_tag:
            html_parts.append(f"</{wrapper_tag}>")
        
        html_fragment = '\n'.join(html_parts)
        
        # 构建响应
        response = {
            "status": "success",
            "html_fragment": html_fragment,
            "fragment_size": len(html_fragment.encode('utf-8')),
            "element_count": len(elements)
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
