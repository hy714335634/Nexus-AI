#!/usr/bin/env python3
"""
工作流编排器 Agent - 使用 agent_factory 创建并编排其他 agents
"""

import os
from strands.multiagent import GraphBuilder
from utils.agent_factory import create_agent_from_prompt_template

# 导入其他 agents
from agents.system_agents.agent_build_workflow.requirements_analyzer_agent import requirements_analyzer
from agents.system_agents.agent_build_workflow.system_architect_agent import system_architect
from agents.system_agents.agent_build_workflow.agent_designer_agent import agent_designer
from agents.system_agents.agent_build_workflow.prompt_engineer_agent import prompt_engineer
from agents.system_agents.agent_build_workflow.tool_developer_agent import tool_developer
from agents.system_agents.agent_build_workflow.agent_code_developer_agent import agent_code_developer
from agents.system_agents.agent_build_workflow.agent_developer_manager_agent import agent_developer_manager

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# 创建 agent 的通用参数
agent_params = {
    "env": "production",
    "version": "latest", 
    "model_id": "default"
}

# 使用 agent_factory 创建编排器 agent
orchestrator = create_agent_from_prompt_template(
    agent_name="system_agents_prompts/agent_build_workflow/orchestrator", 
    **agent_params
)


def create_build_workflow():
    """创建智能体构建工作流"""
    
    print("🔗 构建工作流图...")
    builder = GraphBuilder()
    
    # 添加节点
    builder.add_node(orchestrator, "orchestrator")
    builder.add_node(requirements_analyzer, "requirements_analyzer")
    builder.add_node(system_architect, "system_architect")
    builder.add_node(agent_designer, "agent_designer")
    builder.add_node(prompt_engineer, "prompt_engineer")
    builder.add_node(tool_developer, "tool_developer")
    builder.add_node(agent_code_developer, "agent_code_developer")
    builder.add_node(agent_developer_manager, "agent_developer_manager")
    
    # 添加边 - 定义工作流顺序
    builder.add_edge("orchestrator", "requirements_analyzer")
    builder.add_edge("requirements_analyzer", "system_architect")
    builder.add_edge("system_architect", "agent_designer")
    builder.add_edge("agent_designer", "tool_developer")
    builder.add_edge("tool_developer", "prompt_engineer")
    builder.add_edge("prompt_engineer", "agent_code_developer")
    builder.add_edge("agent_code_developer", "agent_developer_manager")
    
    # 构建图
    graph = builder.build()
    print("✅ 工作流图构建完成")
    
    return graph


def run_workflow(user_input: str):
    """运行工作流"""
    print(f"🎯 开始处理用户需求: {user_input}")
    
    # 创建工作流
    workflow = create_build_workflow()
    
    # 执行工作流
    print("⚡ 执行工作流...")
    result = workflow(user_input)
    
    print("🎉 工作流执行完成")
    return result


if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='工作流编排器 Agent 测试')
    parser.add_argument('-i', '--input', type=str, 
                       default="我需要一个agent，我会提供关于IT产品的描述和价格，它需要帮我根据aws服务和产品对照，生成完整的报价表单，并输出markdown格式。",
                       help='测试输入内容')
    args = parser.parse_args()
    
    print(f"✅ Orchestrator Agent 创建成功: {orchestrator.name}")
    print("🚀 创建并运行完整工作流...")
    
    # 运行完整工作流
    test_input = args.input
    print(f"🎯 测试输入: {test_input}")
    
    try:
        result = run_workflow(test_input)
        print(f"📋 工作流最终结果:\n{result}")
    except Exception as e:
        print(f"❌ 工作流执行失败: {e}")