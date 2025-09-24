#!/usr/bin/env python3
"""
API集成Agent模板

专业的API集成专家，能够与各种外部服务进行集成。
支持API调用、数据同步、格式转换、错误处理等功能。
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

# 创建 agent 的通用参数
agent_params = {
    "env": "production",
    "version": "latest", 
    "model_id": "default"
}

agent_config_path = "template_prompts/default"
# 使用 agent_factory 创建 agent
default_agent = create_agent_from_prompt_template(
    agent_name=agent_config_path, 
    **agent_params
)

if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Agent测试')
    parser.add_argument('-i', '--input', type=str, 
                       default="你是谁，你有什么能力，你具备哪些工具",
                       help='测试输入内容')
    args = parser.parse_args()
    
    print(f"✅ Default Agent 创建成功: {default_agent.name}")
    
    # 测试 agent 功能  
    test_input = args.input
    
    print(f"🎯 测试输入: {test_input}")
    
    try:
        result = default_agent(test_input)
        print(f"📋 Agent 响应:\n{result}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
