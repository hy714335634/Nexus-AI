#!/usr/bin/env python3
"""
更新编排器 Agent - 负责初始化版本信息与调度更新流程
"""

import os
from nexus_utils.agent_factory import create_agent_from_prompt_template

os.environ.setdefault("BYPASS_TOOL_CONSENT", "true")

agent_params = {
    "env": "production",
    "version": "latest",
    "model_id": "default",
}

update_orchestrator = create_agent_from_prompt_template(
    agent_name="system_agents_prompts/agent_update_workflow/update_orchestrator",
    **agent_params,
)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="更新编排器 Agent 测试")
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        default="执行更新流程，初始化版本信息",
        help="测试输入内容",
    )
    args = parser.parse_args()

    print(f"✅ Update Orchestrator Agent 创建成功: {update_orchestrator.name}")
    test_input = args.input
    print(f"🎯 测试输入: {test_input}")

    try:
        result = update_orchestrator(test_input)
        print(f"📋 Agent 响应:\n{result}")
    except Exception as exc:
        print(f"❌ 测试失败: {exc}")

