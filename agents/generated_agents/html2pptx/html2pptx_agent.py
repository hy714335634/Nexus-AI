#!/usr/bin/env python3
"""
HTML2PPTX Agent

将HTML文档转换为PPTX格式的演示文稿，保留原始文档的结构、样式、图片和语义内容，
支持自定义模板，并能处理任意复杂度的HTML文档。

此Agent集成了多个专业工具：
- html_parser: 用于解析HTML文档结构和内容
- pptx_generator: 用于生成PowerPoint文档
- image_processor: 用于处理和嵌入图片资源
- cache_manager: 用于实现本地缓存机制
- style_mapper: 用于将HTML样式映射到PPT样式
- semantic_analyzer: 用于分析HTML的语义结构
- layout_optimizer: 用于优化PPT页面布局
"""

import os
import sys
import json
import argparse
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple

# 导入Strands SDK相关模块
from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry
from nexus_utils.config_loader import ConfigLoader
config = ConfigLoader()
# 设置环境变量
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
    "model_id": "default",
    "enable_logging": True
}

# 使用 agent_factory 创建 agent
html2pptx_agent = create_agent_from_prompt_template(
    agent_name="generated_agents_prompts/html2pptx/html2pptx_agent", 
    **agent_params
)

def convert_html_to_pptx(
    html_path: str, 
    output_path: Optional[str] = None, 
    template_path: Optional[str] = None,
    use_cache: bool = True,
    verbose: bool = False
) -> str:
    """
    将HTML文档转换为PPTX格式的演示文稿。

    Args:
        html_path (str): HTML文档路径
        output_path (str, optional): 输出PPTX文件路径，如果不提供则自动生成
        template_path (str, optional): PPT模板路径
        use_cache (bool): 是否使用缓存机制，默认为True
        verbose (bool): 是否输出详细信息，默认为False

    Returns:
        str: 生成的PPTX文件路径
    """
    # 验证输入文件
    if not os.path.exists(html_path):
        raise FileNotFoundError(f"HTML文件不存在: {html_path}")
    
    # 验证模板文件（如果提供）
    if template_path and not os.path.exists(template_path):
        raise FileNotFoundError(f"模板文件不存在: {template_path}")
    
    # 如果未提供输出路径，生成默认路径
    if not output_path:
        html_file = Path(html_path)
        output_path = str(html_file.with_suffix('.pptx'))
    
    # 构建转换请求
    conversion_request = f"""
    请将以下HTML文档转换为PPTX格式的演示文稿:
    
    HTML文件路径: {html_path}
    输出PPTX路径: {output_path}
    """
    
    # 添加可选参数
    if template_path:
        conversion_request += f"\nPPT模板路径: {template_path}"
    
    conversion_request += f"\n使用缓存: {'是' if use_cache else '否'}"
    
    # 调用Agent执行转换
    if verbose:
        print(f"正在将 {html_path} 转换为 {output_path}...")
        if template_path:
            print(f"使用模板: {template_path}")
    
    try:
        response = html2pptx_agent(conversion_request)
        
        # 验证输出文件是否生成
        if os.path.exists(output_path):
            if verbose:
                print(f"转换成功! 输出文件: {output_path}")
            return output_path
        else:
            raise FileNotFoundError(f"转换失败，输出文件未生成: {output_path}")
    
    except Exception as e:
        print(f"转换过程中发生错误: {str(e)}")
        raise
    
def analyze_html_structure(html_path: str, verbose: bool = False) -> Dict[str, Any]:
    """
    分析HTML文档结构，但不进行实际转换。

    Args:
        html_path (str): HTML文档路径
        verbose (bool): 是否输出详细信息，默认为False

    Returns:
        Dict[str, Any]: 文档结构分析结果
    """
    # 验证输入文件
    if not os.path.exists(html_path):
        raise FileNotFoundError(f"HTML文件不存在: {html_path}")
    
    # 构建分析请求
    analysis_request = f"""
    请分析以下HTML文档的结构，但不要进行转换:
    
    HTML文件路径: {html_path}
    
    我需要了解文档的结构、主要内容、图片数量、表格数量以及可能的幻灯片布局建议。
    """
    
    # 调用Agent执行分析
    if verbose:
        print(f"正在分析 {html_path} 的结构...")
    
    try:
        response = html2pptx_agent(analysis_request)
        
        # 尝试从响应中提取JSON数据
        try:
            # 查找响应中的JSON部分
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                analysis_result = json.loads(json_str)
                return analysis_result
            else:
                # 如果没有找到JSON，返回文本响应
                return {"analysis": response}
        
        except json.JSONDecodeError:
            # 如果JSON解析失败，返回文本响应
            return {"analysis": response}
    
    except Exception as e:
        print(f"分析过程中发生错误: {str(e)}")
        raise

def suggest_ppt_structure(html_path: str, max_slides: int = 10, verbose: bool = False) -> Dict[str, Any]:
    """
    根据HTML文档内容建议PPT幻灯片结构。

    Args:
        html_path (str): HTML文档路径
        max_slides (int): 最大幻灯片数量，默认为10
        verbose (bool): 是否输出详细信息，默认为False

    Returns:
        Dict[str, Any]: 幻灯片结构建议
    """
    # 验证输入文件
    if not os.path.exists(html_path):
        raise FileNotFoundError(f"HTML文件不存在: {html_path}")
    
    # 构建请求
    suggestion_request = f"""
    请根据以下HTML文档内容建议PPT幻灯片结构:
    
    HTML文件路径: {html_path}
    最大幻灯片数量: {max_slides}
    
    我需要了解如何最佳地将文档内容组织成幻灯片，包括标题页、目录页、内容页和结束页的建议。
    """
    
    # 调用Agent执行分析
    if verbose:
        print(f"正在为 {html_path} 生成幻灯片结构建议...")
    
    try:
        response = html2pptx_agent(suggestion_request)
        
        # 尝试从响应中提取JSON数据
        try:
            # 查找响应中的JSON部分
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                suggestion_result = json.loads(json_str)
                return suggestion_result
            else:
                # 如果没有找到JSON，返回文本响应
                return {"suggestion": response}
        
        except json.JSONDecodeError:
            # 如果JSON解析失败，返回文本响应
            return {"suggestion": response}
    
    except Exception as e:
        print(f"生成建议过程中发生错误: {str(e)}")
        raise

def clear_cache(verbose: bool = False) -> bool:
    """
    清理本地缓存。

    Args:
        verbose (bool): 是否输出详细信息，默认为False

    Returns:
        bool: 清理是否成功
    """
    # 构建请求
    clear_request = """
    请清理HTML2PPTX转换过程中使用的所有本地缓存。
    """
    
    # 调用Agent执行清理
    if verbose:
        print("正在清理本地缓存...")
    
    try:
        response = html2pptx_agent(clear_request)
        
        if "成功" in response or "已清理" in response:
            if verbose:
                print("缓存清理成功!")
            return True
        else:
            if verbose:
                print("缓存清理可能未完全成功。")
            return False
    
    except Exception as e:
        print(f"清理缓存过程中发生错误: {str(e)}")
        return False

def main():
    """命令行入口函数"""
    parser = argparse.ArgumentParser(description='HTML2PPTX - 将HTML文档转换为PPTX格式的演示文稿')
    
    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # convert命令
    convert_parser = subparsers.add_parser('convert', help='转换HTML文档为PPTX')
    convert_parser.add_argument('-i', '--input', required=True, help='输入HTML文件路径')
    convert_parser.add_argument('-o', '--output', help='输出PPTX文件路径')
    convert_parser.add_argument('-t', '--template', help='PPT模板路径')
    convert_parser.add_argument('--no-cache', action='store_true', help='禁用缓存')
    convert_parser.add_argument('-v', '--verbose', action='store_true', help='输出详细信息')
    
    # analyze命令
    analyze_parser = subparsers.add_parser('analyze', help='分析HTML文档结构')
    analyze_parser.add_argument('-i', '--input', required=True, help='输入HTML文件路径')
    analyze_parser.add_argument('-v', '--verbose', action='store_true', help='输出详细信息')
    
    # suggest命令
    suggest_parser = subparsers.add_parser('suggest', help='建议PPT幻灯片结构')
    suggest_parser.add_argument('-i', '--input', required=True, help='输入HTML文件路径')
    suggest_parser.add_argument('-m', '--max-slides', type=int, default=10, help='最大幻灯片数量')
    suggest_parser.add_argument('-v', '--verbose', action='store_true', help='输出详细信息')
    
    # clear-cache命令
    clear_cache_parser = subparsers.add_parser('clear-cache', help='清理本地缓存')
    clear_cache_parser.add_argument('-v', '--verbose', action='store_true', help='输出详细信息')
    
    # 解析参数
    args = parser.parse_args()
    
    # 如果没有指定命令，显示帮助
    if not args.command:
        parser.print_help()
        return
    
    # 执行相应的命令
    try:
        if args.command == 'convert':
            output_path = convert_html_to_pptx(
                html_path=args.input,
                output_path=args.output,
                template_path=args.template,
                use_cache=not args.no_cache,
                verbose=args.verbose
            )
            print(f"转换成功! 输出文件: {output_path}")
        
        elif args.command == 'analyze':
            result = analyze_html_structure(
                html_path=args.input,
                verbose=args.verbose
            )
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        elif args.command == 'suggest':
            result = suggest_ppt_structure(
                html_path=args.input,
                max_slides=args.max_slides,
                verbose=args.verbose
            )
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        elif args.command == 'clear-cache':
            success = clear_cache(verbose=args.verbose)
            if success:
                print("缓存清理成功!")
            else:
                print("缓存清理可能未完全成功。")
    
    except Exception as e:
        print(f"错误: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()