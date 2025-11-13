#!/usr/bin/env python3
"""
工具设计 Agent - 使用 agent_factory 创建
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
tool_designer = create_agent_from_prompt_template(
    agent_name="system_agents_prompts/tool_build_workflow/tool_designer", 
    **agent_params
)

if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='工具设计 Agent 测试')
    parser.add_argument('-i', '--input', type=str, 
                       default="设计工具结构和接口",
                       help='测试输入内容')
    args = parser.parse_args()
    
    print(f"✅ Tool Designer Agent 创建成功: {tool_designer.name}")
    
    # 测试 agent 功能
    test_input = args.input
    print(f"🎯 测试输入: {test_input}")
    
    try:
        result = tool_designer(test_input)
        print(f"📋 Agent 响应:\n{result}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")

