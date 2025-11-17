#!/usr/bin/env python3
"""
工具开发者 Agent - 使用 agent_factory 创建
"""

import os
from strands import Agent
from nexus_utils.agent_factory import create_agent_from_prompt_template
from nexus_utils.config_loader import ConfigLoader
loader = ConfigLoader()

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"

def get_tool_developer(env: str = "production",version: str = None) -> Agent:
    if version is None:
        version = loader.get_nested("nexus_ai", "workflow_default_version", "agent_build")
    tool_developer = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/agent_build_workflow/tool_developer", 
        env=env,
        version=version
    )
    return tool_developer

if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='工具开发者 Agent 测试')
    parser.add_argument('-i', '--input', type=str, 
                       default="根据 Agent 需求，开发必要的工具和函数",
                       help='测试输入内容')
    args = parser.parse_args()
    tool_developer = get_tool_developer()
    print(f"✅ Tool Developer Agent 创建成功: {tool_developer.name}")
    
    # 测试 agent 功能
    test_input = args.input
    print(f"🎯 测试输入: {test_input}")
    
    try:
        result = tool_developer(test_input)
        print(f"📋 Agent 响应:\n{result}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")