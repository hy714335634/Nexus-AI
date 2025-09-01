#!/usr/bin/env python3
"""
数据分析Agent模板

专业的数据分析专家，能够处理各种数据格式并进行统计分析。
支持数据预处理、统计分析、图表生成、报告输出等功能。
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
data_analyzer = create_agent_from_prompt_template(
    agent_name="template_prompts/data_analyzer_agent", 
    **agent_params
)

if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='数据分析Agent测试')
    parser.add_argument('-i', '--input', type=str, 
                       default="请分析这个数据集并生成统计报告",
                       help='测试输入内容')
    parser.add_argument('-f', '--file', type=str, 
                       help='要分析的数据文件路径')
    args = parser.parse_args()
    
    print(f"✅ Data Analyzer Agent 创建成功: {data_analyzer.name}")
    
    # 测试 agent 功能
    test_input = args.input
    if args.file:
        test_input += f"\n数据文件路径: {args.file}"
    
    print(f"🎯 测试输入: {test_input}")
    
    try:
        result = data_analyzer(test_input)
        print(f"📋 Agent 响应:\n{result}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
