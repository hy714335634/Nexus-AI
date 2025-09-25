#!/usr/bin/env python3
"""
医学文档翻译Agent

专业的医学文档翻译专家，能够精准翻译医学专业文档，支持Word文档处理、
医学词库管理、智能翻译、质量控制和批量处理等功能。
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Union
from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# 设置遥测
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

# 创建 agent 的通用参数
agent_params = {
    "env": "production",
    "version": "latest", 
    "model_id": "us.anthropic.claude-3-opus-20240229-v1:0"  # 使用Claude Opus以获得最佳医学翻译能力
}

# 使用 agent_factory 创建 agent
medical_translator = create_agent_from_prompt_template(
    agent_name="generated_agents_prompts/medical_document_translation_agent/medical_translator", 
    **agent_params
)

def translate_medical_document(
    file_path: str,
    source_lang: str,
    target_lang: str,
    glossary_name: Optional[str] = None,
    domain: str = "general",
    expand_abbreviations: bool = True,
    output_path: Optional[str] = None
) -> str:
    """
    翻译单个医学文档
    
    Args:
        file_path (str): 要翻译的文档路径
        source_lang (str): 源语言代码 (如 'en', 'zh')
        target_lang (str): 目标语言代码 (如 'zh', 'en')
        glossary_name (Optional[str]): 词库名称 (可选)
        domain (str): 医学领域 (默认为'general')
        expand_abbreviations (bool): 是否展开医学缩写 (默认为True)
        output_path (Optional[str]): 输出文件路径 (可选，默认为原文件名+目标语言代码)
        
    Returns:
        str: 翻译结果信息
    """
    # 构建输入提示
    input_text = f"请将以下医学文档从{source_lang}翻译成{target_lang}。\n\n"
    input_text += f"文档路径: {file_path}\n"
    
    if glossary_name:
        input_text += f"使用词库: {glossary_name}\n"
    
    input_text += f"医学领域: {domain}\n"
    input_text += f"是否展开缩写: {'是' if expand_abbreviations else '否'}\n"
    
    if output_path:
        input_text += f"输出路径: {output_path}\n"
    
    # 调用Agent处理翻译请求
    try:
        result = medical_translator(input_text)
        return result
    except Exception as e:
        logger.error(f"翻译文档时出错: {e}")
        return f"翻译文档时出错: {str(e)}"

def batch_translate_documents(
    file_paths: List[str],
    source_lang: str,
    target_lang: str,
    glossary_name: Optional[str] = None,
    domain: str = "general",
    expand_abbreviations: bool = True,
    output_dir: Optional[str] = None,
    task_name: Optional[str] = None
) -> str:
    """
    批量翻译多个医学文档
    
    Args:
        file_paths (List[str]): 要翻译的文档路径列表
        source_lang (str): 源语言代码 (如 'en', 'zh')
        target_lang (str): 目标语言代码 (如 'zh', 'en')
        glossary_name (Optional[str]): 词库名称 (可选)
        domain (str): 医学领域 (默认为'general')
        expand_abbreviations (bool): 是否展开医学缩写 (默认为True)
        output_dir (Optional[str]): 输出目录 (可选)
        task_name (Optional[str]): 任务名称 (可选)
        
    Returns:
        str: 批量翻译结果信息
    """
    # 构建输入提示
    input_text = f"请批量翻译以下医学文档从{source_lang}到{target_lang}。\n\n"
    input_text += f"文档列表:\n"
    
    for i, path in enumerate(file_paths):
        input_text += f"{i+1}. {path}\n"
    
    input_text += f"\n源语言: {source_lang}\n"
    input_text += f"目标语言: {target_lang}\n"
    
    if glossary_name:
        input_text += f"使用词库: {glossary_name}\n"
    
    input_text += f"医学领域: {domain}\n"
    input_text += f"是否展开缩写: {'是' if expand_abbreviations else '否'}\n"
    
    if output_dir:
        input_text += f"输出目录: {output_dir}\n"
    
    if task_name:
        input_text += f"任务名称: {task_name}\n"
    
    # 调用Agent处理批量翻译请求
    try:
        result = medical_translator(input_text)
        return result
    except Exception as e:
        logger.error(f"批量翻译文档时出错: {e}")
        return f"批量翻译文档时出错: {str(e)}"

def manage_medical_glossary(
    action: str,
    glossary_name: str,
    file_path: Optional[str] = None,
    source_lang_column: Optional[str] = None,
    target_lang_column: Optional[str] = None,
    category_column: Optional[str] = None,
    output_format: Optional[str] = None,
    output_path: Optional[str] = None
) -> str:
    """
    管理医学词库
    
    Args:
        action (str): 操作类型 ('import', 'export', 'search', 'add', 'delete')
        glossary_name (str): 词库名称
        file_path (Optional[str]): 词库文件路径 (导入操作必需)
        source_lang_column (Optional[str]): 源语言列名 (导入操作必需)
        target_lang_column (Optional[str]): 目标语言列名 (导入操作必需)
        category_column (Optional[str]): 分类列名 (可选)
        output_format (Optional[str]): 导出格式 (导出操作必需，'json', 'csv', 'excel')
        output_path (Optional[str]): 导出路径 (导出操作可选)
        
    Returns:
        str: 操作结果信息
    """
    # 构建输入提示
    input_text = f"请{action}医学词库。\n\n"
    input_text += f"词库名称: {glossary_name}\n"
    
    if action == "import" and file_path:
        input_text += f"词库文件路径: {file_path}\n"
        if source_lang_column:
            input_text += f"源语言列名: {source_lang_column}\n"
        if target_lang_column:
            input_text += f"目标语言列名: {target_lang_column}\n"
        if category_column:
            input_text += f"分类列名: {category_column}\n"
    
    elif action == "export":
        if output_format:
            input_text += f"导出格式: {output_format}\n"
        if output_path:
            input_text += f"导出路径: {output_path}\n"
    
    # 调用Agent处理词库管理请求
    try:
        result = medical_translator(input_text)
        return result
    except Exception as e:
        logger.error(f"管理医学词库时出错: {e}")
        return f"管理医学词库时出错: {str(e)}"

def generate_quality_report(
    source_file_path: str,
    translated_file_path: str,
    source_lang: str,
    target_lang: str,
    glossary_name: Optional[str] = None,
    domain: str = "general"
) -> str:
    """
    生成翻译质量报告
    
    Args:
        source_file_path (str): 源文档路径
        translated_file_path (str): 翻译文档路径
        source_lang (str): 源语言代码
        target_lang (str): 目标语言代码
        glossary_name (Optional[str]): 词库名称 (可选)
        domain (str): 医学领域 (默认为'general')
        
    Returns:
        str: 质量报告
    """
    # 构建输入提示
    input_text = f"请生成医学文档翻译的质量报告。\n\n"
    input_text += f"源文档路径: {source_file_path}\n"
    input_text += f"翻译文档路径: {translated_file_path}\n"
    input_text += f"源语言: {source_lang}\n"
    input_text += f"目标语言: {target_lang}\n"
    
    if glossary_name:
        input_text += f"使用词库: {glossary_name}\n"
    
    input_text += f"医学领域: {domain}\n"
    
    # 调用Agent生成质量报告
    try:
        result = medical_translator(input_text)
        return result
    except Exception as e:
        logger.error(f"生成质量报告时出错: {e}")
        return f"生成质量报告时出错: {str(e)}"

def get_batch_task_progress(task_id: str) -> str:
    """
    获取批量翻译任务进度
    
    Args:
        task_id (str): 任务ID
        
    Returns:
        str: 任务进度信息
    """
    # 构建输入提示
    input_text = f"请获取批量翻译任务的进度。\n\n"
    input_text += f"任务ID: {task_id}\n"
    
    # 调用Agent获取任务进度
    try:
        result = medical_translator(input_text)
        return result
    except Exception as e:
        logger.error(f"获取任务进度时出错: {e}")
        return f"获取任务进度时出错: {str(e)}"

if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='医学文档翻译Agent')
    parser.add_argument('--mode', type=str, required=True, 
                      choices=['translate', 'batch', 'glossary', 'report', 'progress'],
                      help='操作模式: translate(单文档翻译), batch(批量翻译), glossary(词库管理), report(质量报告), progress(任务进度)')
    
    # 单文档翻译参数
    parser.add_argument('--file', type=str, help='要翻译的文档路径')
    parser.add_argument('--source_lang', type=str, help='源语言代码 (如 en, zh)')
    parser.add_argument('--target_lang', type=str, help='目标语言代码 (如 zh, en)')
    parser.add_argument('--glossary', type=str, help='词库名称')
    parser.add_argument('--domain', type=str, default='general', help='医学领域')
    parser.add_argument('--expand_abbreviations', action='store_true', help='是否展开医学缩写')
    parser.add_argument('--output', type=str, help='输出文件路径')
    
    # 批量翻译参数
    parser.add_argument('--files', type=str, help='要翻译的文档路径列表，用逗号分隔')
    parser.add_argument('--output_dir', type=str, help='输出目录')
    parser.add_argument('--task_name', type=str, help='任务名称')
    
    # 词库管理参数
    parser.add_argument('--glossary_action', type=str, 
                      choices=['import', 'export', 'search', 'add', 'delete'],
                      help='词库操作类型')
    parser.add_argument('--glossary_name', type=str, help='词库名称')
    parser.add_argument('--glossary_file', type=str, help='词库文件路径')
    parser.add_argument('--source_column', type=str, help='源语言列名')
    parser.add_argument('--target_column', type=str, help='目标语言列名')
    parser.add_argument('--category_column', type=str, help='分类列名')
    parser.add_argument('--output_format', type=str, 
                      choices=['json', 'csv', 'excel'],
                      help='导出格式')
    
    # 质量报告参数
    parser.add_argument('--source_file', type=str, help='源文档路径')
    parser.add_argument('--translated_file', type=str, help='翻译文档路径')
    
    # 任务进度参数
    parser.add_argument('--task_id', type=str, help='任务ID')
    
    args = parser.parse_args()
    
    print(f"✅ Medical Document Translation Agent 创建成功")
    
    # 根据操作模式执行相应功能
    if args.mode == 'translate':
        if not args.file or not args.source_lang or not args.target_lang:
            print("❌ 单文档翻译模式需要提供 --file, --source_lang 和 --target_lang 参数")
            exit(1)
        
        result = translate_medical_document(
            file_path=args.file,
            source_lang=args.source_lang,
            target_lang=args.target_lang,
            glossary_name=args.glossary,
            domain=args.domain,
            expand_abbreviations=args.expand_abbreviations,
            output_path=args.output
        )
        # print(f"📋 翻译结果:\n{result}")
    
    elif args.mode == 'batch':
        if not args.files or not args.source_lang or not args.target_lang:
            print("❌ 批量翻译模式需要提供 --files, --source_lang 和 --target_lang 参数")
            exit(1)
        
        file_paths = [path.strip() for path in args.files.split(',')]
        result = batch_translate_documents(
            file_paths=file_paths,
            source_lang=args.source_lang,
            target_lang=args.target_lang,
            glossary_name=args.glossary,
            domain=args.domain,
            expand_abbreviations=args.expand_abbreviations,
            output_dir=args.output_dir,
            task_name=args.task_name
        )
        print(f"📋 批量翻译结果:\n{result}")
    
    elif args.mode == 'glossary':
        if not args.glossary_action or not args.glossary_name:
            print("❌ 词库管理模式需要提供 --glossary_action 和 --glossary_name 参数")
            exit(1)
        
        if args.glossary_action == 'import' and (not args.glossary_file or not args.source_column or not args.target_column):
            print("❌ 词库导入操作需要提供 --glossary_file, --source_column 和 --target_column 参数")
            exit(1)
        
        if args.glossary_action == 'export' and not args.output_format:
            print("❌ 词库导出操作需要提供 --output_format 参数")
            exit(1)
        
        result = manage_medical_glossary(
            action=args.glossary_action,
            glossary_name=args.glossary_name,
            file_path=args.glossary_file,
            source_lang_column=args.source_column,
            target_lang_column=args.target_column,
            category_column=args.category_column,
            output_format=args.output_format,
            output_path=args.output
        )
        print(f"📋 词库管理结果:\n{result}")
    
    elif args.mode == 'report':
        if not args.source_file or not args.translated_file or not args.source_lang or not args.target_lang:
            print("❌ 质量报告模式需要提供 --source_file, --translated_file, --source_lang 和 --target_lang 参数")
            exit(1)
        
        result = generate_quality_report(
            source_file_path=args.source_file,
            translated_file_path=args.translated_file,
            source_lang=args.source_lang,
            target_lang=args.target_lang,
            glossary_name=args.glossary,
            domain=args.domain
        )
        print(f"📋 质量报告:\n{result}")
    
    elif args.mode == 'progress':
        if not args.task_id:
            print("❌ 任务进度模式需要提供 --task_id 参数")
            exit(1)
        
        result = get_batch_task_progress(task_id=args.task_id)
        print(f"📋 任务进度:\n{result}")