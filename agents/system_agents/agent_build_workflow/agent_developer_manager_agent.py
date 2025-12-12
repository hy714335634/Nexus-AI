#!/usr/bin/env python3
"""
Agent 开发管理者 Agent - 使用 agent_factory 创建
"""

import os
from nexus_utils.agent_factory import create_agent_from_prompt_template
from nexus_utils.config_loader import ConfigLoader
from strands.telemetry import StrandsTelemetry
loader = ConfigLoader()

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"
otel_endpoint = loader.get_with_env_override(
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "nexus_ai", "OTEL_EXPORTER_OTLP_ENDPOINT",
    default="http://localhost:4318"
)
os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", otel_endpoint)
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

agent_params = {
    "env": "production",
    "version": loader.get_nested("nexus_ai", "workflow_default_version", "agent_build"),
    "model_id": "default",
}

agent_developer_manager = create_agent_from_prompt_template(
    agent_name="system_agents_prompts/agent_build_workflow/agent_developer_manager",
    **agent_params,
)

if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Agent 开发管理者 Agent 测试')
    parser.add_argument('-i', '--input', type=str, 
                       default="管理整个 Agent 开发流程，确保质量和完整性",
                       help='测试输入内容')
    args = parser.parse_args()
    print(f"✅ Agent Developer Manager Agent 创建成功: {agent_developer_manager.name}")
    
    # 测试 agent 功能
    test_input = args.input
    print(f"🎯 测试输入: {test_input}")
    
    try:
        result = agent_developer_manager(test_input)
        print(f"📋 Agent 响应:\n{result}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")