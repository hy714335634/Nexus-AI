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

# 创建 agent 的通用参数生成方法
def create_default_agent(env: str = "production", version: str = "latest", model_id: str = "default"):
    agent_params = {
        "env": env,
        "version": version, 
        "model_id": model_id,
        "enable_logging": True
    }
    return create_agent_from_prompt_template(
        agent_name=agent_config_path, 
        **agent_params
    )

agent_config_path = "template_prompts/default"
# 使用 agent_factory 创建 agent
default_agent = create_default_agent()

if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Agent测试')
    parser.add_argument('-i', '--input', type=str, 
                       default="你是谁，你有什么能力，你具备哪些工具",
                       help='测试输入内容')
    parser.add_argument('-e', '--env', type=str,
                       default="production",
                       help='指定Agent运行环境 (默认: production)')
    parser.add_argument('-v', '--version', type=str,
                       default="latest",
                       help='指定Agent版本 (默认: latest)')
    args = parser.parse_args()

    default_agent = create_default_agent(env=args.env, version=args.version)

    print(f"✅ Default Agent 创建成功: {default_agent.name}")
    
    # 测试 agent 功能  
    test_input = args.input
    
    print(f"🎯 测试输入: {test_input}")
    
    try:
        result = default_agent(test_input)
        print(f"📋 Agent 响应:\n{result}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
