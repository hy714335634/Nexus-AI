#!/usr/bin/env python3
"""
Agent 代码开发者 Agent - 使用 agent_factory 创建
"""

import os
from strands import Agent
from nexus_utils.agent_factory import create_agent_from_prompt_template
from nexus_utils.config_loader import ConfigLoader
loader = ConfigLoader()

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"

def get_agent_code_developer(env: str = "production", version: str = None) -> Agent:
    if version is None:
        version = loader.get_nested("nexus_ai", "workflow_default_version", "agent_build")
    agent_code_developer = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/agent_build_workflow/agent_code_developer", 
        env=env,
        version=version
    )
    return agent_code_developer

if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Agent 代码开发者 Agent 测试')
    parser.add_argument('-i', '--input', type=str, 
                       default="根据设计方案和工具，编写完整的 Agent 代码实现",
                       help='测试输入内容')
    args = parser.parse_args()
    agent_code_developer = get_agent_code_developer()
    print(f"✅ Agent Code Developer Agent 创建成功: {agent_code_developer.name}")
    
    # 测试 agent 功能
    test_input = args.input
    print(f"🎯 测试输入: {test_input}")
    
    try:
        result = agent_code_developer(test_input)
        print(f"📋 Agent 响应:\n{result}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")