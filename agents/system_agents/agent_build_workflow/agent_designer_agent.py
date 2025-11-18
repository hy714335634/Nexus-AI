#!/usr/bin/env python3
"""
Agent 设计师 Agent - 使用 agent_factory 创建
"""

import os
from nexus_utils.agent_factory import create_agent_from_prompt_template
from nexus_utils.config_loader import ConfigLoader

loader = ConfigLoader()

# 设置环境变量
os.environ.setdefault("BYPASS_TOOL_CONSENT", "true")

agent_params = {
    "env": "production",
    "version": loader.get_nested("nexus_ai", "workflow_default_version", "agent_build"),
    "model_id": "default",
}

agent_designer = create_agent_from_prompt_template(
    agent_name="system_agents_prompts/agent_build_workflow/agent_designer",
    **agent_params,
)

if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Agent 设计师 Agent 测试')
    parser.add_argument('-i', '--input', type=str, 
                       default="根据系统架构设计，设计具体的 Agent 实现方案",
                       help='测试输入内容')
    args = parser.parse_args()
    print(f"✅ Agent Designer Agent 创建成功: {agent_designer.name}")
    
    # 测试 agent 功能
    test_input = args.input
    print(f"🎯 测试输入: {test_input}")
    
    try:
        result = agent_designer(test_input)
        print(f"📋 Agent 响应:\n{result}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")