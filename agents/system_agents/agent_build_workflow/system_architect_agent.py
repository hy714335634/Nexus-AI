#!/usr/bin/env python3
"""
系统架构师 Agent - 使用 agent_factory 创建
"""

import os
from nexus_utils.agent_factory import create_agent_from_prompt_template

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# 创建 agent 的通用参数
agent_params = {
    "env": "production",
    "version": "latest", 
    "model_id": "default"
}

# 使用 agent_factory 创建 agent
system_architect = create_agent_from_prompt_template(
    agent_name="system_agents_prompts/agent_build_workflow/system_architect", 
    **agent_params
)

if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='系统架构师 Agent 测试')
    parser.add_argument('-i', '--input', type=str, 
                       default="根据需求分析结果，设计系统架构和技术选型",
                       help='测试输入内容')
    args = parser.parse_args()
    
    print(f"✅ System Architect Agent 创建成功: {system_architect.name}")
    
    # 测试 agent 功能
    test_input = args.input
    print(f"🎯 测试输入: {test_input}")
    
    try:
        result = system_architect(test_input)
        print(f"📋 Agent 响应:\n{result}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")