#!/usr/bin/env python3
"""
内容生成Agent模板

专业的内容生成专家，能够根据需求生成各种类型的内容。
支持文章写作、报告生成、创意内容、营销文案等功能。
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
content_generator = create_agent_from_prompt_template(
    agent_name="template_prompts/content_generator_agent", 
    **agent_params
)

if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='内容生成Agent测试')
    parser.add_argument('-i', '--input', type=str, 
                       default="请根据主题生成一篇高质量的文章",
                       help='测试输入内容')
    parser.add_argument('-t', '--type', type=str, 
                       default="article",
                       help='内容类型 (article, report, marketing, creative)')
    args = parser.parse_args()
    
    print(f"✅ Content Generator Agent 创建成功: {content_generator.name}")
    
    # 测试 agent 功能
    test_input = args.input
    if args.type:
        test_input += f"\n内容类型: {args.type}"
    
    print(f"🎯 测试输入: {test_input}")
    
    try:
        result = content_generator(test_input)
        print(f"📋 Agent 响应:\n{result}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
