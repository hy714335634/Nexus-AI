#!/usr/bin/env python3
"""
提示词工程师 Agent - 使用 agent_factory 创建
"""

import os
from strands import Agent
from nexus_utils.agent_factory import create_agent_from_prompt_template
from nexus_utils.config_loader import ConfigLoader
loader = ConfigLoader()

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"

def get_prompt_engineer(env: str = "production", version: str = None) -> Agent:
    if version is None:
        version = loader.get_nested("nexus_ai", "workflow_default_version", "agent_build")
    prompt_engineer = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/agent_build_workflow/prompt_engineer", 
        env=env,
        version=version
    )
    return prompt_engineer

if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='提示词工程师 Agent 测试')
    parser.add_argument('-i', '--input', type=str, 
                       default="根据 Agent 设计方案，编写高质量的提示词模板",
                       help='测试输入内容')
    args = parser.parse_args()
    prompt_engineer = get_prompt_engineer()
    print(f"✅ Prompt Engineer Agent 创建成功: {prompt_engineer.name}")
    
    # 测试 agent 功能
    test_input = args.input
    print(f"🎯 测试输入: {test_input}")
    
    try:
        result = prompt_engineer(test_input)
        print(f"📋 Agent 响应:\n{result}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")