"""
生命科学新闻通讯生成工具模块

该模块提供：
- HTML通讯模板渲染
- 邮件内容生成
- 图片处理和优化
- AWS SES邮件发送
- 通讯预览和测试
"""

import json
import base64
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
from strands import tool


# ============================================================================
# HTML 通讯渲染工具
# ============================================================================

@tool
def render_newsletter_html(
    template_path: str,
    articles: List[Dict[str, Any]],
    newsletter_title: str,
    newsletter_date: str,
    header_image_url: Optional[str] = None,
    footer_text: Optional[str] = None
) -> str:
    """
    渲染通讯HTML内容
    
    Args:
        template_path: HTML模板文件路径
        articles: 文章列表
        newsletter_title: 通讯标题
        newsletter_date: 通讯日期
        header_image_url: 头部图片URL（可选）
        footer_text: 页脚文本（可选）
    
    Returns:
        str: JSON格式的渲染结果
    """
    try:
        from jinja2 import Template
        
        # 读取模板
        template_file = Path(template_path)
        if not template_file.exists():
            return json.dumps({
                "success": False,
                "error": f"模板文件不存在: {template_path}"
            }, ensure_ascii=False, indent=2)
        
        with open(template_file, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # 创建Jinja2模板
        template = Template(template_content)
        
        # 渲染模板
        html_content = template.render(
            newsletter_title=newsletter_title,
            newsletter_date=newsletter_date,
            articles=articles,
            header_image_url=header_image_url,
            footer_text=footer_text or "© 2026 生命科学新闻通讯",
            current_year=datetime.now().year
        )
        
        return json.dumps({
            "success": True,
            "template_path": template_path,
            "articles_count": len(articles),
            "html_length": len(html_content),
            "html_content": html_content,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"模板渲染失败: {str(e)}",
            "template_path": template_path
        }, ensure_ascii=False, indent=2)


@tool
def generate_simple_newsletter_html(
    articles_json: str,
    newsletter_title: str = "生命科学新闻周报",
    max_articles: int = 10
) -> str:
    """
    生成简单的通讯HTML（内置模板）
    
    Args:
        articles_json: 文章列表的JSON字符串，每个文章包含 title, url, summary, date, category, tags 字段
        newsletter_title: 通讯标题
        max_articles: 最大文章数
    
    Returns:
        str: JSON格式的生成结果
    
    Example:
        articles_json = '[{"title": "文章标题", "url": "https://...", "summary": "文章摘要", "date": "2026-01-07", "category": "药物研发与创新"}]'
    """
    try:
        # 解析 articles JSON
        if isinstance(articles_json, str):
            try:
                articles = json.loads(articles_json)
            except json.JSONDecodeError as e:
                return json.dumps({
                    "success": False,
                    "error": f"articles_json 解析失败: {str(e)}，请确保传入有效的JSON字符串"
                }, ensure_ascii=False, indent=2)
        elif isinstance(articles_json, list):
            # 兼容直接传入列表的情况
            articles = articles_json
        else:
            return json.dumps({
                "success": False,
                "error": f"articles_json 类型错误: 期望 str 或 list，实际为 {type(articles_json).__name__}"
            }, ensure_ascii=False, indent=2)
        
        if not articles:
            return json.dumps({
                "success": False,
                "error": "articles_json 为空，请提供至少一篇文章"
            }, ensure_ascii=False, indent=2)
        
        # 限制文章数量
        selected_articles = articles[:max_articles]
        
        # 构建HTML
        html_parts = [
            '<!DOCTYPE html>',
            '<html lang="zh-CN">',
            '<head>',
            '    <meta charset="UTF-8">',
            '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
            f'    <title>{newsletter_title}</title>',
            '    <style>',
            '        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }',
            '        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 8px; margin-bottom: 30px; }',
            '        .article { background: #f9f9f9; padding: 20px; margin-bottom: 20px; border-radius: 8px; border-left: 4px solid #667eea; }',
            '        .article h2 { color: #667eea; margin-top: 0; }',
            '        .article .meta { color: #666; font-size: 14px; margin-bottom: 10px; }',
            '        .article .summary { margin: 10px 0; }',
            '        .article .tags { margin-top: 10px; }',
            '        .tag { background: #667eea; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; margin-right: 8px; display: inline-block; }',
            '        .read-more { color: #667eea; text-decoration: none; font-weight: bold; }',
            '        .footer { text-align: center; padding: 20px; color: #666; border-top: 1px solid #ddd; margin-top: 30px; }',
            '    </style>',
            '</head>',
            '<body>',
            '    <div class="header">',
            f'        <h1>{newsletter_title}</h1>',
            f'        <p>{datetime.now().strftime("%Y年%m月%d日")}</p>',
            '    </div>',
            '    <div class="content">'
        ]
        
        # 添加文章
        for idx, article in enumerate(selected_articles, 1):
            title = article.get("title", "无标题")
            summary = article.get("summary", article.get("snippet", ""))
            url = article.get("url", "#")
            date = article.get("date", article.get("published_date", ""))
            category = article.get("category", "")
            tags = article.get("tags", [])
            
            html_parts.extend([
                '        <div class="article">',
                f'            <h2>{idx}. {title}</h2>',
                f'            <div class="meta">',
            ])
            
            if date:
                html_parts.append(f'                发布日期: {date}')
            if category:
                html_parts.append(f' | 分类: {category}')
            
            html_parts.extend([
                '            </div>',
                f'            <div class="summary">{summary}</div>',
            ])
            
            if tags:
                html_parts.append('            <div class="tags">')
                for tag in tags[:5]:
                    html_parts.append(f'                <span class="tag">{tag}</span>')
                html_parts.append('            </div>')
            
            html_parts.extend([
                f'            <p><a href="{url}" class="read-more">阅读全文 →</a></p>',
                '        </div>'
            ])
        
        # 添加页脚
        html_parts.extend([
            '    </div>',
            '    <div class="footer">',
            '        <p>© 2026 生命科学新闻通讯</p>',
            '        <p>本通讯由AI自动生成</p>',
            '    </div>',
            '</body>',
            '</html>'
        ])
        
        html_content = '\n'.join(html_parts)
        
        return json.dumps({
            "success": True,
            "newsletter_title": newsletter_title,
            "articles_count": len(selected_articles),
            "html_length": len(html_content),
            "html_content": html_content,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"通讯生成失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


# ============================================================================
# 固定模板HTML生成工具（减少token消耗）
# ============================================================================

@tool
def generate_newsletter_from_json(
    data_json: str,
    date: str,
    output_base_dir: str = "./reports",
    newsletter_title: str = "生命科学行业新闻周报"
) -> str:
    """
    从JSON数据生成HTML报告文件（使用固定模板，减少token消耗）
    
    Agent只需提供JSON数据，工具内部加载固定模板进行渲染，无需将模板内容加载到上下文。
    
    Args:
        data_json: JSON格式的数据，包含以下结构：
            {
                "stats": {
                    "total_articles": 42,
                    "total_categories": 7,
                    "total_sources": 15,
                    "coverage": "100%"
                },
                "insights": {
                    "content_insights": [
                        "insight topic 1: xxxx",
                        "insight topic 2: xxxx"
                    ],
                    "aws_perspective": "从AWS角度对行业趋势的分析和洞察，包括技术机会、市场趋势、AWS服务应用场景等（可选）"
                },
                "categories": [
                    {
                        "id": "policy",
                        "name": "政策法规类",
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
                "data_sources": "Google Search、丁香园、医学界等数据源名称"
            }
        date: 报告日期，格式：YYYY年MM月DD日 或 YYYY-MM-DD
        output_base_dir: 输出目录基础路径（默认：./reports）
        newsletter_title: 通讯标题（默认：生命科学行业新闻周报）
    
    Returns:
        str: JSON格式的结果，包含文件路径等信息
        {
            "success": true,
            "file_path": "./reports/2026/01/15/newsletter_20260115_143022.html",
            "relative_path": "./reports/2026/01/15/newsletter_20260115_143022.html",
            "absolute_path": "/full/path/to/file.html",
            "date": "2026年1月15日",
            "timestamp": "2026-01-15T14:30:22"
        }
    """
    try:
        from jinja2 import Template, Environment, FileSystemLoader
        import re
        
        # 解析JSON数据
        if isinstance(data_json, str):
            # 预处理：修复常见的JSON格式问题
            cleaned_json = data_json
            
            # 尝试解析JSON
            try:
                data = json.loads(cleaned_json)
            except json.JSONDecodeError as e:
                # 尝试修复：移除可能导致问题的控制字符
                cleaned_json = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', data_json)
                # 再次尝试解析
                try:
                    data = json.loads(cleaned_json)
                except json.JSONDecodeError as e2:
                    return json.dumps({
                        "success": False,
                        "error": f"JSON解析失败: {str(e2)}",
                        "hint": "请确保传入有效的JSON字符串，检查是否有未转义的引号或特殊字符",
                        "error_position": f"行 {e2.lineno}, 列 {e2.colno}"
                    }, ensure_ascii=False, indent=2)
            
            # 兼容处理：如果解析结果包含 data_json 字段，说明是嵌套结构
            if isinstance(data, dict) and "data_json" in data:
                inner_json = data.get("data_json", "{}")
                # 更新其他参数（如果外层提供了）
                if "date" in data:
                    date = data["date"]
                if "output_base_dir" in data:
                    output_base_dir = data["output_base_dir"]
                if "newsletter_title" in data:
                    newsletter_title = data["newsletter_title"]
                # 解析内层JSON
                if isinstance(inner_json, str):
                    try:
                        data = json.loads(inner_json)
                    except json.JSONDecodeError as e:
                        return json.dumps({
                            "success": False,
                            "error": f"内层data_json解析失败: {str(e)}",
                            "hint": "data_json字段内容不是有效的JSON"
                        }, ensure_ascii=False, indent=2)
                elif isinstance(inner_json, dict):
                    data = inner_json
                    
        elif isinstance(data_json, dict):
            data = data_json
            # 同样处理嵌套情况
            if "data_json" in data:
                inner_json = data.get("data_json", {})
                if "date" in data:
                    date = data["date"]
                if "output_base_dir" in data:
                    output_base_dir = data["output_base_dir"]
                if "newsletter_title" in data:
                    newsletter_title = data["newsletter_title"]
                if isinstance(inner_json, str):
                    data = json.loads(inner_json)
                elif isinstance(inner_json, dict):
                    data = inner_json
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
                import re
                date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date)
                if date_match:
                    y, m, d = date_match.groups()
                    # 确保月份和日期是两位数格式（补零）
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
        template_path = project_root / "agents/generated_agents/lifescience_news_collector/templates" / "newsletter_template.j2"
        
        if not template_path.exists():
            return json.dumps({
                "success": False,
                "error": f"模板文件不存在: {template_path}",
                "hint": "请确保模板文件位于 templates/newsletter_template.j2"
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
            "data_sources": data.get("data_sources", "生命科学新闻数据源"),
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
        
        # 生成文件名：newsletter_YYYYMMDD_HHMMSS.html
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"newsletter_{timestamp_str}.html"
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


# ============================================================================
# 邮件内容生成工具
# ============================================================================

@tool
def generate_email_subject(
    newsletter_title: str,
    date: Optional[str] = None,
    article_count: Optional[int] = None
) -> str:
    """
    生成邮件主题
    
    Args:
        newsletter_title: 通讯标题
        date: 日期（可选）
        article_count: 文章数量（可选）
    
    Returns:
        str: JSON格式的邮件主题
    """
    try:
        subject_parts = [newsletter_title]
        
        if date:
            subject_parts.append(f"- {date}")
        elif not date:
            subject_parts.append(f"- {datetime.now().strftime('%Y年%m月%d日')}")
        
        if article_count:
            subject_parts.append(f"({article_count}篇精选)")
        
        subject = " ".join(subject_parts)
        
        return json.dumps({
            "success": True,
            "subject": subject,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"邮件主题生成失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def generate_email_preview_text(
    articles: List[Dict[str, Any]],
    max_length: int = 100
) -> str:
    """
    生成邮件预览文本
    
    Args:
        articles: 文章列表
        max_length: 最大长度
    
    Returns:
        str: JSON格式的预览文本
    """
    try:
        if not articles:
            preview_text = "本期没有新文章"
        else:
            # 使用前几篇文章的标题
            titles = [article.get("title", "") for article in articles[:3]]
            preview_text = "本期精选: " + "、".join(titles)
            
            if len(preview_text) > max_length:
                preview_text = preview_text[:max_length - 3] + "..."
        
        return json.dumps({
            "success": True,
            "preview_text": preview_text,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"预览文本生成失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


# ============================================================================
# 图片处理工具
# ============================================================================

@tool
def optimize_image_for_email(
    image_path: str,
    max_width: int = 600,
    quality: int = 85
) -> str:
    """
    优化图片用于邮件
    
    Args:
        image_path: 图片文件路径
        max_width: 最大宽度（像素）
        quality: JPEG质量（1-100）
    
    Returns:
        str: JSON格式的优化结果
    """
    try:
        from PIL import Image
        import io
        
        # 打开图片
        img = Image.open(image_path)
        
        # 计算新尺寸
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
        
        # 转换为RGB（如果是RGBA）
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        
        # 保存为JPEG
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)
        
        # 转换为base64
        image_base64 = base64.b64encode(output.read()).decode('utf-8')
        
        return json.dumps({
            "success": True,
            "original_path": image_path,
            "original_size": f"{img.width}x{img.height}",
            "optimized_size": f"{img.width}x{img.height}",
            "base64_length": len(image_base64),
            "base64_data": image_base64,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"图片优化失败: {str(e)}",
            "image_path": image_path
        }, ensure_ascii=False, indent=2)


@tool
def embed_image_in_html(
    html_content: str,
    image_base64: str,
    image_alt: str = "Newsletter Image"
) -> str:
    """
    将base64图片嵌入HTML
    
    Args:
        html_content: HTML内容
        image_base64: base64编码的图片
        image_alt: 图片alt属性
    
    Returns:
        str: JSON格式的嵌入结果
    """
    try:
        # 构建img标签
        img_tag = f'<img src="data:image/jpeg;base64,{image_base64}" alt="{image_alt}" style="max-width: 100%; height: auto;">'
        
        # 在HTML中查找插入位置（例如header后）
        if '<div class="header">' in html_content:
            html_content = html_content.replace(
                '</div>',
                f'{img_tag}</div>',
                1
            )
        else:
            # 如果没有header，插入到body开头
            html_content = html_content.replace(
                '<body>',
                f'<body>\n{img_tag}\n'
            )
        
        return json.dumps({
            "success": True,
            "html_length": len(html_content),
            "html_content": html_content,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"图片嵌入失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


# ============================================================================
# AWS SES 邮件发送工具
# ============================================================================

@tool
def send_email_via_ses(
    sender: str,
    recipients: List[str],
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
    reply_to: Optional[List[str]] = None,
    region: str = "us-east-1"
) -> str:
    """
    通过AWS SES发送邮件
    
    Args:
        sender: 发件人邮箱
        recipients: 收件人邮箱列表
        subject: 邮件主题
        html_body: HTML邮件正文
        text_body: 纯文本邮件正文（可选）
        reply_to: 回复地址列表（可选）
        region: AWS区域（默认us-east-1）
    
    Returns:
        str: JSON格式的发送结果
    """
    try:
        ses_client = boto3.client('ses', region_name=region)
        
        # 构建邮件内容
        message = {
            'Subject': {
                'Data': subject,
                'Charset': 'UTF-8'
            },
            'Body': {
                'Html': {
                    'Data': html_body,
                    'Charset': 'UTF-8'
                }
            }
        }
        
        # 添加纯文本正文
        if text_body:
            message['Body']['Text'] = {
                'Data': text_body,
                'Charset': 'UTF-8'
            }
        
        # 发送邮件
        send_params = {
            'Source': sender,
            'Destination': {
                'ToAddresses': recipients
            },
            'Message': message
        }
        
        if reply_to:
            send_params['ReplyToAddresses'] = reply_to
        
        response = ses_client.send_email(**send_params)
        
        return json.dumps({
            "success": True,
            "message_id": response['MessageId'],
            "sender": sender,
            "recipients": recipients,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except ClientError as e:
        return json.dumps({
            "success": False,
            "error": f"SES发送失败: {e.response['Error']['Message']}",
            "error_code": e.response['Error']['Code']
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"邮件发送异常: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def send_bulk_email_via_ses(
    sender: str,
    recipients: List[str],
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
    batch_size: int = 50,
    region: str = "us-east-1"
) -> str:
    """
    通过AWS SES批量发送邮件
    
    Args:
        sender: 发件人邮箱
        recipients: 收件人邮箱列表
        subject: 邮件主题
        html_body: HTML邮件正文
        text_body: 纯文本邮件正文（可选）
        batch_size: 批次大小（默认50）
        region: AWS区域（默认us-east-1）
    
    Returns:
        str: JSON格式的批量发送结果
    """
    try:
        total_sent = 0
        failed_recipients = []
        
        # 分批发送
        for i in range(0, len(recipients), batch_size):
            batch = recipients[i:i + batch_size]
            
            send_result = send_email_via_ses(
                sender=sender,
                recipients=batch,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
                region=region
            )
            
            result_data = json.loads(send_result)
            
            if result_data.get("success"):
                total_sent += len(batch)
            else:
                failed_recipients.extend(batch)
        
        return json.dumps({
            "success": True,
            "total_recipients": len(recipients),
            "sent_count": total_sent,
            "failed_count": len(failed_recipients),
            "failed_recipients": failed_recipients,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"批量发送失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


# ============================================================================
# 通讯预览和测试工具
# ============================================================================

@tool
def save_newsletter_preview(
    html_content: str,
    output_path: str = "newsletter_preview.html"
) -> str:
    """
    保存通讯预览文件
    
    Args:
        html_content: HTML内容
        output_path: 输出文件路径
    
    Returns:
        str: JSON格式的保存结果
    """
    try:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return json.dumps({
            "success": True,
            "output_path": str(path.absolute()),
            "file_size": path.stat().st_size,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"预览保存失败: {str(e)}",
            "output_path": output_path
        }, ensure_ascii=False, indent=2)


@tool
def send_test_email(
    sender: str,
    test_recipient: str,
    html_content: str,
    subject: str = "【测试】生命科学新闻通讯",
    region: str = "us-east-1"
) -> str:
    """
    发送测试邮件
    
    Args:
        sender: 发件人邮箱
        test_recipient: 测试收件人邮箱
        html_content: HTML内容
        subject: 邮件主题
        region: AWS区域（默认us-east-1）
    
    Returns:
        str: JSON格式的发送结果
    """
    try:
        # 在主题前添加测试标记
        test_subject = f"【测试】{subject}"
        
        # 在HTML内容顶部添加测试标记
        test_html = f'''
        <div style="background: #ff9800; color: white; padding: 10px; text-align: center; font-weight: bold;">
            ⚠️ 这是一封测试邮件 ⚠️
        </div>
        {html_content}
        '''
        
        # 发送测试邮件
        result = send_email_via_ses(
            sender=sender,
            recipients=[test_recipient],
            subject=test_subject,
            html_body=test_html,
            region=region
        )
        
        return result
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"测试邮件发送失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


# ============================================================================
# 通讯统计工具
# ============================================================================

@tool
def generate_newsletter_stats(
    articles: List[Dict[str, Any]]
) -> str:
    """
    生成通讯统计信息
    
    Args:
        articles: 文章列表
    
    Returns:
        str: JSON格式的统计信息
    """
    try:
        from collections import Counter
        
        # 基本统计
        total_articles = len(articles)
        
        # 分类统计
        categories = [article.get("category", "未分类") for article in articles]
        category_counts = dict(Counter(categories))
        
        # 标签统计
        all_tags = []
        for article in articles:
            tags = article.get("tags", [])
            all_tags.extend(tags)
        tag_counts = dict(Counter(all_tags).most_common(10))
        
        # 来源统计
        sources = [article.get("source", "未知来源") for article in articles]
        source_counts = dict(Counter(sources))
        
        # 内容长度统计
        content_lengths = [len(article.get("content", "")) for article in articles]
        avg_length = sum(content_lengths) / len(content_lengths) if content_lengths else 0
        
        return json.dumps({
            "success": True,
            "total_articles": total_articles,
            "category_distribution": category_counts,
            "top_tags": tag_counts,
            "source_distribution": source_counts,
            "average_content_length": int(avg_length),
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"统计生成失败: {str(e)}"
        }, ensure_ascii=False, indent=2)
