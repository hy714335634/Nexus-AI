#!/usr/bin/env python3
"""
PPT to Markdown Converter Agent

专业的PPT内容提取和Markdown转换专家，能够解析PPT文件、提取每页内容并生成完整Markdown格式总结报告。
支持各种PPT文件格式，保持原始内容的层次结构和格式，提供高质量的Markdown输出。
"""

import os
import json
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry
from nexus_utils.config_loader import ConfigLoader
config = ConfigLoader() 
# 设置环境变量和遥测
os.environ["BYPASS_TOOL_CONSENT"] = "true"
otel_endpoint = config.get_with_env_override(
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "nexus_ai", "OTEL_EXPORTER_OTLP_ENDPOINT",
    default="http://localhost:4318"
)
os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", otel_endpoint)
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

# 创建 agent 的通用参数
agent_params = {
    "env": "production",
    "version": "latest", 
    "model_id": "us.anthropic.claude-3-7-sonnet-20250219-v1:0",  # 使用Claude 3.7 Sonnet模型
    "enable_logging": True
}

# 使用 agent_factory 创建 agent
ppt_to_markdown_converter = create_agent_from_prompt_template(
    agent_name="generated_agents_prompts/ppt_to_markdown/ppt_to_markdown_converter", 
    **agent_params
)

def validate_file_path(file_path: str) -> bool:
    """
    验证文件路径是否存在且是PPT文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        bool: 是否是有效的PPT文件
    """
    path = Path(file_path)
    if not path.exists():
        return False
    
    if not path.is_file():
        return False
        
    extension = path.suffix.lower()
    return extension in ['.ppt', '.pptx']

def process_user_input(user_input: str) -> Dict[str, Any]:
    """
    处理用户输入，提取文件路径和其他参数
    
    Args:
        user_input: 用户输入的文本
        
    Returns:
        Dict: 包含文件路径和参数的字典
    """
    # 初始化结果字典
    result = {
        "file_path": None,
        "include_page_numbers": True,
        "include_slide_titles": True,
        "extract_notes": False,
        "include_images": False,
        "output_file": None,
        "add_toc": False,
        "format_style": "default",
        "valid_request": False,
        "error_message": None
    }
    
    # 尝试从输入中提取文件路径
    lines = user_input.strip().split('\n')
    for line in lines:
        # 检查是否包含文件路径
        if any(keyword in line.lower() for keyword in ['文件', '路径', 'file', 'path', 'ppt', 'pptx']):
            # 尝试提取引号中的路径
            import re
            path_match = re.search(r'[\'"]([^\'"]+)[\'"]', line)
            if path_match:
                result["file_path"] = path_match.group(1)
            else:
                # 尝试提取冒号后的路径
                colon_match = re.search(r'[:：]\s*(.+)', line)
                if colon_match:
                    result["file_path"] = colon_match.group(1).strip()
                else:
                    # 尝试提取可能的路径字符串
                    words = line.split()
                    for word in words:
                        if ('.' in word and ('ppt' in word.lower() or 'pptx' in word.lower())) or \
                           ('/' in word or '\\' in word):
                            result["file_path"] = word
                            break
        
        # 检查其他参数
        if "不包含页码" in line.lower() or "no page numbers" in line.lower():
            result["include_page_numbers"] = False
        
        if "不包含标题" in line.lower() or "no titles" in line.lower():
            result["include_slide_titles"] = False
            
        if "包含笔记" in line.lower() or "include notes" in line.lower() or "extract notes" in line.lower():
            result["extract_notes"] = True
            
        if "包含图片" in line.lower() or "include images" in line.lower():
            result["include_images"] = True
            
        if "添加目录" in line.lower() or "add toc" in line.lower() or "table of contents" in line.lower():
            result["add_toc"] = True
            
        # 检查输出文件
        output_match = re.search(r'输出[到至][\s:：]*([^\s]+)', line) or \
                      re.search(r'保存[到至][\s:：]*([^\s]+)', line) or \
                      re.search(r'output[\s:]*([^\s]+)', line) or \
                      re.search(r'save[\s:]*([^\s]+)', line)
        if output_match:
            result["output_file"] = output_match.group(1)
            
        # 检查格式样式
        if "学术" in line.lower() or "academic" in line.lower():
            result["format_style"] = "academic"
        elif "商业" in line.lower() or "business" in line.lower():
            result["format_style"] = "business"
        elif "简约" in line.lower() or "minimal" in line.lower():
            result["format_style"] = "minimal"
    
    # 验证文件路径
    if result["file_path"]:
        result["valid_request"] = True
    else:
        result["error_message"] = "未能从输入中提取有效的PPT文件路径"
        
    return result

def format_conversion_result(conversion_result: Dict[str, Any]) -> str:
    """
    格式化转换结果为可读的文本
    
    Args:
        conversion_result: 转换结果字典
        
    Returns:
        str: 格式化后的结果文本
    """
    if conversion_result.get("status") == "error":
        return f"转换失败: {conversion_result.get('error_message', '未知错误')}"
    
    metadata = conversion_result.get("metadata", {})
    slide_count = metadata.get("slide_count", "未知")
    title = metadata.get("title", "未命名演示文稿")
    processing_time = metadata.get("processing_time", 0)
    
    result = f"✅ 转换成功!\n\n"
    result += f"📊 演示文稿: {title}\n"
    result += f"📑 幻灯片数量: {slide_count}\n"
    result += f"⏱️ 处理时间: {processing_time:.2f} 秒\n"
    
    if "output_file" in conversion_result:
        result += f"📄 输出文件: {conversion_result['output_file']}\n"
        
    return result

def handle_conversion_request(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    处理PPT转换请求
    
    Args:
        params: 转换参数
        
    Returns:
        Dict: 转换结果
    """
    try:
        from strands import tool
        
        # 验证文件
        validate_result_json = tool.validate_ppt_file(file_path=params["file_path"])
        validate_result = json.loads(validate_result_json)
        
        if not validate_result.get("is_valid", False):
            return {
                "status": "error",
                "error_message": validate_result.get("error_message", "无效的PPT文件")
            }
        
        # 转换PPT到Markdown
        convert_result_json = tool.ppt_to_markdown_converter(
            file_path=params["file_path"],
            include_page_numbers=params["include_page_numbers"],
            include_slide_titles=params["include_slide_titles"],
            extract_notes=params["extract_notes"],
            include_images=params["include_images"],
            output_file=params["output_file"]
        )
        convert_result = json.loads(convert_result_json)
        
        if convert_result.get("status") != "success":
            return convert_result
        
        # 应用格式化和样式
        markdown_content = convert_result.get("markdown_content", "")
        
        # 添加目录
        if params["add_toc"]:
            format_result_json = tool.format_markdown_document(
                markdown_content=markdown_content,
                add_toc=True
            )
            format_result = json.loads(format_result_json)
            if format_result.get("status") == "success":
                markdown_content = format_result.get("formatted_content", markdown_content)
        
        # 应用样式
        style_result_json = tool.customize_markdown_styling(
            markdown_content=markdown_content,
            style_preset=params["format_style"],
            enhance_lists=True,
            enhance_tables=True,
            add_page_breaks=True
        )
        style_result = json.loads(style_result_json)
        if style_result.get("status") == "success":
            markdown_content = style_result.get("styled_content", markdown_content)
        
        # 如果有输出文件但之前没有保存，则保存文件
        if params["output_file"] and not convert_result.get("output_file"):
            output_dir = str(Path(params["output_file"]).parent)
            file_name = Path(params["output_file"]).name
            
            save_result_json = tool.save_markdown_file(
                content=markdown_content,
                output_directory=output_dir,
                file_name=file_name,
                overwrite=True
            )
            save_result = json.loads(save_result_json)
            if save_result.get("status") == "success":
                convert_result["output_file"] = save_result.get("file_path")
        
        # 更新结果中的Markdown内容
        convert_result["markdown_content"] = markdown_content
        return convert_result
    
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"转换过程中发生错误: {str(e)}"
        }

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='PPT到Markdown转换Agent')
    parser.add_argument('-f', '--file', type=str, 
                       help='要转换的PPT文件路径')
    parser.add_argument('-o', '--output', type=str, 
                       help='输出Markdown文件路径')
    parser.add_argument('-q', '--query', type=str, 
                       default="请将这个PPT文件转换为Markdown格式",
                       help='转换请求或问题')
    parser.add_argument('--no-page-numbers', action='store_true',
                       help='不包含页码')
    parser.add_argument('--no-titles', action='store_true',
                       help='不包含幻灯片标题')
    parser.add_argument('--extract-notes', action='store_true',
                       help='提取演讲者笔记')
    parser.add_argument('--include-images', action='store_true',
                       help='包含图片引用')
    parser.add_argument('--add-toc', action='store_true',
                       help='添加目录')
    parser.add_argument('--style', type=str, default='default',
                       choices=['default', 'academic', 'business', 'minimal'],
                       help='Markdown样式')
    args = parser.parse_args()
    
    print(f"✅ PPT to Markdown Converter Agent 创建成功: {ppt_to_markdown_converter.name}")
    
    # 构建测试输入
    test_input = args.query
    if args.file:
        test_input += f"\n文件路径: {args.file}"
    if args.output:
        test_input += f"\n输出到: {args.output}"
    if args.no_page_numbers:
        test_input += "\n不包含页码"
    if args.no_titles:
        test_input += "\n不包含标题"
    if args.extract_notes:
        test_input += "\n包含演讲者笔记"
    if args.include_images:
        test_input += "\n包含图片引用"
    if args.add_toc:
        test_input += "\n添加目录"
    if args.style != 'default':
        test_input += f"\n使用{args.style}样式"
    
    print(f"🎯 测试输入: {test_input}")
    
    try:
        result = ppt_to_markdown_converter(test_input)
        print(f"📋 Agent 响应:\n{result}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")