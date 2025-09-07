#!/usr/bin/env python3
"""
多模态内容分析Agent模板

专业的多模态内容分析专家，能够处理各种类型的文件（图片、文档、文本等）
并进行智能分析和问答。支持多轮对话，用户可指定本地文件路径进行分析。
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
multimodal_analyzer = create_agent_from_prompt_template(
    agent_name="system_agents_prompts/multimodal_analysis/multimodal_analyzer_agent", 
    **agent_params
)

if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='多模态内容分析Agent测试')
    parser.add_argument('-f', '--file', type=str, 
                       default="请分析这个图片文件的内容",
                       help='要分析的文件路径或描述')
    parser.add_argument('-q', '--question', type=str, 
                       default="这个文件包含什么信息？",
                       help='关于文件的具体问题')
    parser.add_argument('-c', '--context', type=str, 
                       default="",
                       help='分析上下文或背景信息')
    args = parser.parse_args()
    
    print(f"✅ Multimodal Analyzer Agent 创建成功: {multimodal_analyzer.name}")
    
    # 构建测试输入
    test_input = f"""
文件分析请求: {args.file}
具体问题: {args.question}
分析上下文: {args.context}

请对指定文件进行多模态内容分析并回答相关问题。
"""
    
    print(f"🎯 测试输入: {test_input}")
    
    try:
        result = multimodal_analyzer(test_input)
        print(f"📋 Agent 响应:\n{result}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
