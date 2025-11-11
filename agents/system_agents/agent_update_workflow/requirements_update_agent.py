#!/usr/bin/env python3
"""
更新需求分析 Agent - 负责分析现有产物与用户更新需求
"""

import os
from nexus_utils.agent_factory import create_agent_from_prompt_template

os.environ.setdefault("BYPASS_TOOL_CONSENT", "true")

agent_params = {
    "env": "production",
    "version": "latest",
    "model_id": "default",
}

requirements_update_agent = create_agent_from_prompt_template(
    agent_name="system_agents_prompts/agent_update_workflow/requirements_update",
    **agent_params,
)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="更新需求分析 Agent 测试")
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        default="分析当前项目需求并给出更新建议",
        help="测试输入内容",
    )
    args = parser.parse_args()

    print(f"✅ Requirements Update Agent 创建成功: {requirements_update_agent.name}")
    test_input = args.input
    print(f"🎯 测试输入: {test_input}")

    try:
        result = requirements_update_agent(test_input)
        print(f"📋 Agent 响应:\n{result}")
    except Exception as exc:
        print(f"❌ 测试失败: {exc}")

