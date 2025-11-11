#!/usr/bin/env python3
"""
文档处理Agent模板

专业的文档处理专家，能够处理各种格式的文档并进行智能分析。
支持文档解析、内容提取、格式转换、文本分析等功能。
"""

import os
from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry

os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()


# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# 创建 agent 的通用参数生成方法
def create_document_processor_agent(env: str = "production", version: str = "latest", model_id: str = "default"):
    agent_params = {
        "env": env,
        "version": version, 
        "model_id": model_id
    }
    return create_agent_from_prompt_template(
        agent_name=agent_config_path, 
        **agent_params
    )

agent_config_path = "template_prompts/document_processor_agent"

# 使用 agent_factory 创建 agent
document_processor = create_document_processor_agent()

if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='文档处理Agent测试')
    parser.add_argument('-i', '--input', type=str, 
                       default="请分析这个文档的内容并提取关键信息",
                       help='测试输入内容')
    parser.add_argument('-f', '--file', type=str, 
                       help='要处理的文件路径')
    parser.add_argument('-e', '--env', type=str,
                       default="production",
                       help='指定Agent运行环境 (默认: production)')
    parser.add_argument('-v', '--version', type=str,
                       default="latest",
                       help='指定Agent版本 (默认: latest)')
    args = parser.parse_args()

    document_processor = create_document_processor_agent(env=args.env, version=args.version)

    print(f"✅ Document Processor Agent 创建成功: {document_processor.name}")
    
    # 测试 agent 功能
    test_input = args.input
    if args.file:
        test_input += f"\n文件路径: {args.file}"
    
    print(f"🎯 测试输入: {test_input}")
    
    try:
        result = document_processor(test_input)
        print(f"📋 Agent 响应:\n{result}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
