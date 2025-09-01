#!/usr/bin/env python3
"""
简化的工作流编排器 - 使用 agent_factory 动态创建 agents
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


# 定义 agent 创建的通用参数
agent_params = {
    "env": "production",
    "version": "latest", 
    "model_id": "default"
}

# 使用agent_factory创建agent
requirements_analyzer = create_agent_from_prompt_template(
    agent_name="template_prompts/template_requirements_analyzer", **agent_params
)


if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', type=str, 
                       default="你是谁，你有什么能力，你具备哪些工具",
                       help='测试输入内容')
    args = parser.parse_args()
    
    print(f"✅ Agent 创建成功: {requirements_analyzer.name}")
    
    # 运行完整工作流
    test_input = args.input
    print(f"🎯 测试输入: {test_input}")
    
    requirements_analyzer(test_input)
