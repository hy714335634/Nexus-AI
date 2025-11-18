#!/usr/bin/env python3
"""
需求分析师 Agent - 使用 agent_factory 创建
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

requirements_analyzer = create_agent_from_prompt_template(
    agent_name="system_agents_prompts/agent_build_workflow/requirements_analyzer",
    **agent_params,
)

if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='需求分析师 Agent 测试')
    parser.add_argument('-i', '--input', type=str, 
                       default="我需要一个agent，我会提供关于IT产品的描述和价格，它需要帮我根据aws服务和产品对照，生成完整的报价表单，并输出markdown格式。",
                       help='测试输入内容')
    args = parser.parse_args()
    print(f"✅ Requirements Analyzer Agent 创建成功: {requirements_analyzer.name}")
    
    # 测试 agent 功能
    test_input = args.input
    print(f"🎯 测试输入: {test_input}")
    
    try:
        result = requirements_analyzer(test_input)
        print(f"📋 Agent 响应:\n{result}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")