#!/usr/bin/env python3
"""
文档处理Agent模板

专业的文档处理专家，能够处理各种格式的文档并进行智能分析。
支持文档解析、内容提取、格式转换、文本分析等功能。
"""

import os
from utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry

os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()


# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# 创建 agent 的通用参数
agent_params = {
    "env": "production",
    "version": "latest", 
    "model_id": "default"
}

# 使用 agent_factory 创建 agent
document_processor = create_agent_from_prompt_template(
    agent_name="template_prompts/document_processor_agent", 
    **agent_params
)

if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='文档处理Agent测试')
    parser.add_argument('-i', '--input', type=str, 
                       default="请分析这个文档的内容并提取关键信息",
                       help='测试输入内容')
    parser.add_argument('-f', '--file', type=str, 
                       help='要处理的文件路径')
    args = parser.parse_args()
    
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
