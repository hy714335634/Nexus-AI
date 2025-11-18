#!/usr/bin/env python3
"""AgentCore 部署协调 Agent."""

import os
from nexus_utils.agent_factory import create_agent_from_prompt_template
from nexus_utils.config_loader import ConfigLoader

loader = ConfigLoader()

os.environ.setdefault("BYPASS_TOOL_CONSENT", "true")

agent_params = {
    "env": "production",
    "version": loader.get_nested("nexus_ai", "workflow_default_version", "agent_build"),
    "model_id": "default",
}

agent_deployer = create_agent_from_prompt_template(
    agent_name="system_agents_prompts/agent_build_workflow/agent_deployer",
    **agent_params,
)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Agent Core 部署协调 Agent 测试")
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        default="请读取项目配置并将主Agent部署到AgentCore",
        help="测试输入内容",
    )
    args = parser.parse_args()
    print(f"✅ Agent Deployer 创建成功: {agent_deployer.name}")
    try:
        response = agent_deployer(args.input)
        print(f"📋 Agent 响应:\n{response}")
    except Exception as exc:  # pragma: no cover - CLI fallback
        print(f"❌ 测试失败: {exc}")
