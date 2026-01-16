#!/usr/bin/env python3
"""
HTML report generator tools using Jinja2 templates.
Supports multi-format report generation with rich formatting.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

from strands import tool

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape, Template
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False


# 默认HTML模板
DEFAULT_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        header {
            border-bottom: 3px solid #2c3e50;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        
        h1 {
            color: #2c3e50;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .meta-info {
            color: #7f8c8d;
            font-size: 0.9em;
        }
        
        .meta-info span {
            margin-right: 20px;
        }
        
        h2 {
            color: #34495e;
            font-size: 1.8em;
            margin-top: 30px;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #ecf0f1;
        }
        
        h3 {
            color: #34495e;
            font-size: 1.3em;
            margin-top: 20px;
            margin-bottom: 10px;
        }
        
        .section {
            margin-bottom: 40px;
        }
        
        .summary {
            background: #ecf0f1;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 30px;
        }
        
        .summary-item {
            display: inline-block;
            margin-right: 30px;
            margin-bottom: 10px;
        }
        
        .summary-label {
            font-weight: bold;
            color: #2c3e50;
        }
        
        .summary-value {
            color: #3498db;
            font-size: 1.2em;
            font-weight: bold;
        }
        
        .article-list {
            list-style: none;
        }
        
        .article-item {
            background: #f9f9f9;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 5px;
            border-left: 4px solid #3498db;
            transition: all 0.3s ease;
        }
        
        .article-item:hover {
            background: #e8f4f8;
            transform: translateX(5px);
        }
        
        .article-title {
            font-size: 1.2em;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 8px;
        }
        
        .article-title a {
            color: #2c3e50;
            text-decoration: none;
        }
        
        .article-title a:hover {
            color: #3498db;
        }
        
        .article-meta {
            color: #7f8c8d;
            font-size: 0.9em;
            margin-bottom: 10px;
        }
        
        .article-meta span {
            margin-right: 15px;
        }
        
        .article-snippet {
            color: #555;
            line-height: 1.6;
        }
        
        .category-badge {
            display: inline-block;
            background: #3498db;
            color: white;
            padding: 3px 10px;
            border-radius: 3px;
            font-size: 0.85em;
            margin-right: 5px;
        }
        
        .source-badge {
            display: inline-block;
            background: #95a5a6;
            color: white;
            padding: 3px 10px;
            border-radius: 3px;
            font-size: 0.85em;
        }
        
        .statistics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        
        .stat-value {
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .stat-label {
            font-size: 0.9em;
            opacity: 0.9;
        }
        
        footer {
            margin-top: 50px;
            padding-top: 20px;
            border-top: 2px solid #ecf0f1;
            text-align: center;
            color: #7f8c8d;
            font-size: 0.9em;
        }
        
        .chart-placeholder {
            background: #ecf0f1;
            padding: 40px;
            text-align: center;
            border-radius: 5px;
            margin: 20px 0;
            color: #7f8c8d;
        }
        
        @media print {
            body {
                background: white;
                padding: 0;
            }
            
            .container {
                box-shadow: none;
                padding: 20px;
            }
            
            .article-item:hover {
                transform: none;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{{ title }}</h1>
            <div class="meta-info">
                <span>📅 生成时间: {{ generation_time }}</span>
                <span>📊 数据来源: {{ data_sources }}</span>
                {% if author %}
                <span>👤 生成者: {{ author }}</span>
                {% endif %}
            </div>
        </header>
        
        {% if summary %}
        <section class="section">
            <div class="summary">
                <h2>📋 摘要统计</h2>
                <div class="statistics">
                    {% for key, value in summary.items() %}
                    <div class="stat-card">
                        <div class="stat-value">{{ value }}</div>
                        <div class="stat-label">{{ key }}</div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </section>
        {% endif %}
        
        {% if sections %}
        {% for section in sections %}
        <section class="section">
            <h2>{{ section.title }}</h2>
            
            {% if section.description %}
            <p>{{ section.description }}</p>
            {% endif %}
            
            {% if section.articles %}
            <ul class="article-list">
                {% for article in section.articles %}
                <li class="article-item">
                    <div class="article-title">
                        <a href="{{ article.url }}" target="_blank">{{ article.title }}</a>
                    </div>
                    
                    <div class="article-meta">
                        {% if article.date %}
                        <span>📅 {{ article.date }}</span>
                        {% endif %}
                        
                        {% if article.source %}
                        <span class="source-badge">{{ article.source }}</span>
                        {% endif %}
                        
                        {% if article.category %}
                        <span class="category-badge">{{ article.category }}</span>
                        {% endif %}
                    </div>
                    
                    {% if article.snippet %}
                    <div class="article-snippet">
                        {{ article.snippet }}
                    </div>
                    {% endif %}
                </li>
                {% endfor %}
            </ul>
            {% endif %}
            
            {% if section.content %}
            <div class="section-content">
                {{ section.content | safe }}
            </div>
            {% endif %}
        </section>
        {% endfor %}
        {% endif %}
        
        <footer>
            <p>本报告由能源新闻分析智能体自动生成</p>
            <p>生成时间: {{ generation_time }}</p>
        </footer>
    </div>
</body>
</html>
"""


@tool
def generate_html_report(
    title: str,
    sections: List[Dict[str, Any]],
    summary: Optional[Dict[str, Any]] = None,
    output_path: Optional[str] = None,
    template_path: Optional[str] = None,
    author: Optional[str] = None
) -> str:
    """
    生成HTML格式的分析报告
    
    Args:
        title (str): 报告标题
        sections (List[Dict]): 报告章节列表，每个章节包含title、description、articles等字段
        summary (Dict, optional): 摘要统计数据
        output_path (str, optional): 输出文件路径，不指定则返回HTML内容
        template_path (str, optional): 自定义模板路径
        author (str, optional): 报告作者
        
    Returns:
        str: JSON格式的生成结果
    """
    try:
        if not JINJA2_AVAILABLE:
            return json.dumps({
                "status": "error",
                "message": "Jinja2库未安装。请安装: pip install jinja2"
            }, ensure_ascii=False)
        
        # 准备模板数据
        template_data = {
            "title": title,
            "sections": sections,
            "summary": summary or {},
            "generation_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data_sources": "Bing搜索API、能源新闻网站",
            "author": author
        }
        
        # 加载模板
        if template_path and os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            template = Template(template_content)
        else:
            template = Template(DEFAULT_HTML_TEMPLATE)
        
        # 渲染HTML
        html_content = template.render(**template_data)
        
        # 保存到文件或返回内容
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            return json.dumps({
                "status": "success",
                "message": "HTML报告生成成功",
                "output_path": str(output_file.absolute()),
                "file_size": len(html_content),
                "generation_time": datetime.now().isoformat()
            }, ensure_ascii=False, indent=2)
        else:
            return json.dumps({
                "status": "success",
                "message": "HTML报告生成成功",
                "html_content": html_content,
                "content_size": len(html_content),
                "generation_time": datetime.now().isoformat()
            }, ensure_ascii=False, indent=2)
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"HTML报告生成失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def generate_markdown_report(
    title: str,
    sections: List[Dict[str, Any]],
    summary: Optional[Dict[str, Any]] = None,
    output_path: Optional[str] = None
) -> str:
    """
    生成Markdown格式的分析报告
    
    Args:
        title (str): 报告标题
        sections (List[Dict]): 报告章节列表
        summary (Dict, optional): 摘要统计数据
        output_path (str, optional): 输出文件路径
        
    Returns:
        str: JSON格式的生成结果
    """
    try:
        # 构建Markdown内容
        md_lines = [
            f"# {title}",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            ""
        ]
        
        # 添加摘要
        if summary:
            md_lines.append("## 📊 摘要统计")
            md_lines.append("")
            for key, value in summary.items():
                md_lines.append(f"- **{key}**: {value}")
            md_lines.append("")
            md_lines.append("---")
            md_lines.append("")
        
        # 添加章节
        for section in sections:
            md_lines.append(f"## {section['title']}")
            md_lines.append("")
            
            if section.get('description'):
                md_lines.append(section['description'])
                md_lines.append("")
            
            # 添加文章列表
            if section.get('articles'):
                for idx, article in enumerate(section['articles'], 1):
                    md_lines.append(f"### {idx}. {article['title']}")
                    md_lines.append("")
                    
                    # 添加元数据
                    meta_parts = []
                    if article.get('date'):
                        meta_parts.append(f"📅 {article['date']}")
                    if article.get('source'):
                        meta_parts.append(f"📰 {article['source']}")
                    if article.get('category'):
                        meta_parts.append(f"🏷️ {article['category']}")
                    
                    if meta_parts:
                        md_lines.append(" | ".join(meta_parts))
                        md_lines.append("")
                    
                    # 添加链接
                    md_lines.append(f"🔗 [查看原文]({article['url']})")
                    md_lines.append("")
                    
                    # 添加摘要
                    if article.get('snippet'):
                        md_lines.append(f"> {article['snippet']}")
                        md_lines.append("")
            
            # 添加自定义内容
            if section.get('content'):
                md_lines.append(section['content'])
                md_lines.append("")
            
            md_lines.append("---")
            md_lines.append("")
        
        # 添加页脚
        md_lines.append("## 📝 报告说明")
        md_lines.append("")
        md_lines.append("本报告由能源新闻分析智能体自动生成")
        md_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        markdown_content = "\n".join(md_lines)
        
        # 保存到文件或返回内容
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            return json.dumps({
                "status": "success",
                "message": "Markdown报告生成成功",
                "output_path": str(output_file.absolute()),
                "file_size": len(markdown_content),
                "generation_time": datetime.now().isoformat()
            }, ensure_ascii=False, indent=2)
        else:
            return json.dumps({
                "status": "success",
                "message": "Markdown报告生成成功",
                "markdown_content": markdown_content,
                "content_size": len(markdown_content),
                "generation_time": datetime.now().isoformat()
            }, ensure_ascii=False, indent=2)
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Markdown报告生成失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def generate_json_report(
    title: str,
    sections: List[Dict[str, Any]],
    summary: Optional[Dict[str, Any]] = None,
    output_path: Optional[str] = None,
    pretty_print: bool = True
) -> str:
    """
    生成JSON格式的分析报告
    
    Args:
        title (str): 报告标题
        sections (List[Dict]): 报告章节列表
        summary (Dict, optional): 摘要统计数据
        output_path (str, optional): 输出文件路径
        pretty_print (bool): 是否格式化输出
        
    Returns:
        str: JSON格式的生成结果
    """
    try:
        # 构建JSON数据
        report_data = {
            "title": title,
            "generation_time": datetime.now().isoformat(),
            "summary": summary or {},
            "sections": sections,
            "metadata": {
                "generator": "能源新闻分析智能体",
                "version": "1.0",
                "data_sources": ["Bing搜索API", "能源新闻网站"]
            }
        }
        
        # 序列化JSON
        if pretty_print:
            json_content = json.dumps(report_data, ensure_ascii=False, indent=2)
        else:
            json_content = json.dumps(report_data, ensure_ascii=False)
        
        # 保存到文件或返回内容
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(json_content)
            
            return json.dumps({
                "status": "success",
                "message": "JSON报告生成成功",
                "output_path": str(output_file.absolute()),
                "file_size": len(json_content),
                "generation_time": datetime.now().isoformat()
            }, ensure_ascii=False, indent=2)
        else:
            return json.dumps({
                "status": "success",
                "message": "JSON报告生成成功",
                "report_data": report_data,
                "content_size": len(json_content),
                "generation_time": datetime.now().isoformat()
            }, ensure_ascii=False, indent=2)
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"JSON报告生成失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def generate_multi_format_reports(
    title: str,
    sections: List[Dict[str, Any]],
    summary: Optional[Dict[str, Any]] = None,
    output_directory: str = "./reports",
    formats: Optional[List[str]] = None,
    base_filename: Optional[str] = None
) -> str:
    """
    生成多种格式的分析报告
    
    Args:
        title (str): 报告标题
        sections (List[Dict]): 报告章节列表
        summary (Dict, optional): 摘要统计数据
        output_directory (str): 输出目录
        formats (List[str], optional): 输出格式列表（html, markdown, json）
        base_filename (str, optional): 基础文件名
        
    Returns:
        str: JSON格式的生成结果
    """
    try:
        if formats is None:
            formats = ["html", "markdown", "json"]
        
        # 生成基础文件名
        if not base_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = f"energy_report_{timestamp}"
        
        # 创建输出目录
        output_dir = Path(output_directory)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        results = {
            "status": "success",
            "title": title,
            "output_directory": str(output_dir.absolute()),
            "generated_files": [],
            "generation_time": datetime.now().isoformat()
        }
        
        # 生成HTML报告
        if "html" in formats:
            html_path = output_dir / f"{base_filename}.html"
            html_result = generate_html_report(
                title=title,
                sections=sections,
                summary=summary,
                output_path=str(html_path)
            )
            html_data = json.loads(html_result)
            if html_data["status"] == "success":
                results["generated_files"].append({
                    "format": "html",
                    "path": html_data["output_path"],
                    "size": html_data["file_size"]
                })
        
        # 生成Markdown报告
        if "markdown" in formats:
            md_path = output_dir / f"{base_filename}.md"
            md_result = generate_markdown_report(
                title=title,
                sections=sections,
                summary=summary,
                output_path=str(md_path)
            )
            md_data = json.loads(md_result)
            if md_data["status"] == "success":
                results["generated_files"].append({
                    "format": "markdown",
                    "path": md_data["output_path"],
                    "size": md_data["file_size"]
                })
        
        # 生成JSON报告
        if "json" in formats:
            json_path = output_dir / f"{base_filename}.json"
            json_result = generate_json_report(
                title=title,
                sections=sections,
                summary=summary,
                output_path=str(json_path)
            )
            json_data = json.loads(json_result)
            if json_data["status"] == "success":
                results["generated_files"].append({
                    "format": "json",
                    "path": json_data["output_path"],
                    "size": json_data["file_size"]
                })
        
        results["total_files"] = len(results["generated_files"])
        
        return json.dumps(results, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"多格式报告生成失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def create_report_template(
    template_name: str,
    template_content: str,
    template_directory: str = "./templates"
) -> str:
    """
    创建自定义报告模板
    
    Args:
        template_name (str): 模板名称
        template_content (str): 模板内容（Jinja2格式）
        template_directory (str): 模板目录
        
    Returns:
        str: JSON格式的创建结果
    """
    try:
        # 创建模板目录
        template_dir = Path(template_directory)
        template_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存模板
        template_path = template_dir / f"{template_name}.html"
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(template_content)
        
        return json.dumps({
            "status": "success",
            "message": "报告模板创建成功",
            "template_name": template_name,
            "template_path": str(template_path.absolute()),
            "template_size": len(template_content),
            "creation_time": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"模板创建失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def generate_report_from_json(
    data_json: str,
    date: str,
    output_base_dir: str = "./reports",
    newsletter_title: str = "能源行业新闻分析报告"
) -> str:
    """
    从JSON数据生成HTML报告文件（使用固定模板，减少token消耗）
    
    Agent只需提供JSON数据，工具内部加载固定模板进行渲染，无需将模板内容加载到上下文。
    
    Args:
        data_json: JSON格式的数据，包含以下结构：
            {
                "stats": {
                    "total_articles": 42,
                    "total_categories": 4,
                    "total_sources": 10,
                    "coverage": "100%"
                },
                "insights": {
                    "content_insights": [
                        "insight topic 1: xxxx",
                        "insight topic 2: xxxx"
                    ]
                },
                "categories": [
                    {
                        "id": "policy",
                        "name": "政策类",
                        "icon": "📜",
                        "articles": [
                            {
                                "title": "文章标题",
                                "url": "https://example.com/article",
                                "summary": "文章摘要",
                                "source": "来源名称",
                                "date": "2026-01-15"
                            }
                        ]
                    }
                ],
                "data_sources": "SerpAPI、北极星能源网、国家能源局等数据源名称"
            }
        date: 报告日期，格式：YYYY年MM月DD日 或 YYYY-MM-DD
        output_base_dir: 输出目录基础路径（默认：./reports）
        newsletter_title: 报告标题（默认：能源行业新闻分析报告）
    
    Returns:
        str: JSON格式的结果，包含文件路径等信息
        {
            "success": true,
            "file_path": "./reports/2026/01/15/energy_report_20260115_143022.html",
            "relative_path": "./reports/2026/01/15/energy_report_20260115_143022.html",
            "absolute_path": "/full/path/to/file.html",
            "date": "2026年1月15日",
            "timestamp": "2026-01-15T14:30:22"
        }
    """
    try:
        import re
        
        # 解析JSON数据
        if isinstance(data_json, str):
            try:
                data = json.loads(data_json)
            except json.JSONDecodeError as e:
                # 尝试修复：移除可能导致问题的控制字符
                cleaned_json = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', data_json)
                try:
                    data = json.loads(cleaned_json)
                except json.JSONDecodeError as e2:
                    return json.dumps({
                        "success": False,
                        "error": f"JSON解析失败: {str(e2)}",
                        "hint": "请确保传入有效的JSON字符串，检查是否有未转义的引号或特殊字符"
                    }, ensure_ascii=False, indent=2)
        elif isinstance(data_json, dict):
            data = data_json
        else:
            return json.dumps({
                "success": False,
                "error": f"数据格式错误: 期望 str 或 dict，实际为 {type(data_json).__name__}"
            }, ensure_ascii=False, indent=2)
        
        # 验证数据结构
        if "categories" not in data:
            return json.dumps({
                "success": False,
                "error": "JSON数据中缺少必需的 'categories' 字段"
            }, ensure_ascii=False, indent=2)
        
        # 处理日期格式
        try:
            if "年" in date or "月" in date or "日" in date:
                # 已经是中文格式，直接使用
                formatted_date = date
                # 提取年月日用于目录
                date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date)
                if date_match:
                    y, m, d = date_match.groups()
                    year, month, day = y, f"{int(m):02d}", f"{int(d):02d}"
                else:
                    # 使用当前日期
                    now = datetime.now()
                    year, month, day = str(now.year), f"{now.month:02d}", f"{now.day:02d}"
            else:
                # YYYY-MM-DD 格式，转换为中文格式
                date_obj = datetime.strptime(date, "%Y-%m-%d")
                formatted_date = date_obj.strftime("%Y年%m月%d日")
                year, month, day = str(date_obj.year), f"{date_obj.month:02d}", f"{date_obj.day:02d}"
        except Exception as e:
            # 日期解析失败，使用当前日期
            now = datetime.now()
            formatted_date = now.strftime("%Y年%m月%d日")
            year, month, day = str(now.year), f"{now.month:02d}", f"{now.day:02d}"
        
        # 获取模板路径（相对于项目根目录）
        project_root = Path(__file__).parent.parent.parent.parent
        template_path = project_root / "agents/generated_agents/energy_news_analysis_agent/templates" / "energy_report_template.j2"
        
        if not template_path.exists():
            return json.dumps({
                "success": False,
                "error": f"模板文件不存在: {template_path}",
                "hint": "请确保模板文件位于 agents/generated_agents/energy_news_analysis_agent/templates/energy_report_template.j2"
            }, ensure_ascii=False, indent=2)
        
        # 加载模板
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            template = Template(template_content)
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"模板加载失败: {str(e)}"
            }, ensure_ascii=False, indent=2)
        
        # 准备模板变量
        template_vars = {
            "newsletter_title": newsletter_title,
            "newsletter_date": formatted_date,
            "categories": data.get("categories", []),
            "stats": data.get("stats", {}),
            "insights": data.get("insights", {}),
            "data_sources": data.get("data_sources", "能源新闻数据源"),
            "current_year": datetime.now().year
        }
        
        # 渲染HTML
        try:
            html_content = template.render(**template_vars)
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"模板渲染失败: {str(e)}"
            }, ensure_ascii=False, indent=2)
        
        # 创建输出目录结构：reports/YYYY/MM/DD/
        output_dir = Path(output_base_dir) / year / month / day
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名：energy_report_YYYYMMDD_HHMMSS.html
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"energy_report_{timestamp_str}.html"
        file_path = output_dir / filename
        
        # 保存HTML文件
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"文件保存失败: {str(e)}"
            }, ensure_ascii=False, indent=2)
        
        # 计算相对路径（相对于output_base_dir）
        relative_path = f"{year}/{month}/{day}/{filename}"
        
        # 计算文件路径（优先使用相对路径，失败则使用绝对路径）
        try:
            display_path = str(file_path.relative_to(Path.cwd()))
        except ValueError:
            # 如果文件不在当前工作目录下，使用绝对路径
            display_path = str(file_path.absolute())
        
        return json.dumps({
            "success": True,
            "message": "HTML报告生成成功，内容完整",
            "file_path": display_path,
            "absolute_path": str(file_path.absolute()),
            "file_size_bytes": file_path.stat().st_size,
            "articles_count": sum(len(cat.get("articles", [])) for cat in data.get("categories", []))
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"生成报告失败: {str(e)}",
            "traceback": str(e.__class__.__name__)
        }, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # 测试工具
    print("🧪 测试报告生成工具...")
    
    # 测试数据
    test_sections = [
        {
            "title": "新能源汽车行业动态",
            "description": "最新的新能源汽车行业新闻和政策",
            "articles": [
                {
                    "title": "新能源汽车补贴政策延续至2025年",
                    "url": "https://example.com/article1",
                    "date": "2024-01-15",
                    "source": "人民日报",
                    "category": "政策",
                    "snippet": "国家发改委宣布新能源汽车购置补贴政策将延续至2025年底..."
                }
            ]
        }
    ]
    
    test_summary = {
        "总文章数": 25,
        "数据来源": 5,
        "政策类": 8,
        "技术类": 10,
        "市场类": 7
    }
    
    # 测试HTML报告生成
    html_result = generate_html_report(
        title="能源新闻分析报告",
        sections=test_sections,
        summary=test_summary
    )
    print("📄 HTML报告生成:", json.loads(html_result)["status"])
    
    # 测试Markdown报告生成
    md_result = generate_markdown_report(
        title="能源新闻分析报告",
        sections=test_sections,
        summary=test_summary
    )
    print("📝 Markdown报告生成:", json.loads(md_result)["status"])
    
    print("✅ 工具测试完成！")
