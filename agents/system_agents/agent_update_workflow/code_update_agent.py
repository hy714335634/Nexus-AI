#!/usr/bin/env python3
"""
Agent代码更新 Agent - 判断并生成新版本的 Agent 实现
"""

import os
from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry
from nexus_utils.config_loader import ConfigLoader
loader = ConfigLoader()
os.environ.setdefault("BYPASS_TOOL_CONSENT", "true")
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
    "version": "latest",
    "model_id": "default",
}

code_update_agent = create_agent_from_prompt_template(
    agent_name="system_agents_prompts/agent_update_workflow/code_update",
    **agent_params,
)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Agent代码更新 Agent 测试")
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        default="评估并生成新的 Agent 代码版本",
        help="测试输入内容",
    )
    args = parser.parse_args()

    print(f"✅ Code Update Agent 创建成功: {code_update_agent.name}")
    test_input = args.input
    print(f"🎯 测试输入: {test_input}")

    try:
        result = code_update_agent(test_input)
        print(f"📋 Agent 响应:\n{result}")
    except Exception as exc:
        print(f"❌ 测试失败: {exc}")
