#!/usr/bin/env python3
"""
工作流编排器 Agent - 使用 agent_factory 创建并编排其他 agents
"""

import os
import uuid
import json
from strands.multiagent import GraphBuilder
from utils.agent_factory import create_agent_from_prompt_template
from utils.structured_output_model.project_intent_recognition import IntentRecognitionResult

# 导入其他 agents
from agents.system_agents.agent_build_workflow.requirements_analyzer_agent import requirements_analyzer
from agents.system_agents.agent_build_workflow.system_architect_agent import system_architect
from agents.system_agents.agent_build_workflow.agent_designer_agent import agent_designer
from agents.system_agents.agent_build_workflow.prompt_engineer_agent import prompt_engineer
from agents.system_agents.agent_build_workflow.tool_developer_agent import tool_developer
from agents.system_agents.agent_build_workflow.agent_code_developer_agent import agent_code_developer
from agents.system_agents.agent_build_workflow.agent_developer_manager_agent import agent_developer_manager
from strands.session.file_session_manager import FileSessionManager
from strands.telemetry import StrandsTelemetry

os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# 创建 agent 的通用参数
agent_params = {
    "env": "production",
    "version": "latest", 
    "model_id": "default"
}

# 使用 agent_factory 创建 agents
orchestrator = create_agent_from_prompt_template(
    agent_name="system_agents_prompts/agent_build_workflow/orchestrator", 
    **agent_params
)

# 创建意图分析 agent
intent_analyzer = create_agent_from_prompt_template(
    agent_name="system_agents_prompts/agent_build_workflow/agent_intent_analyzer",
    **agent_params
)

def create_conversation_manager(session_id="default",session_dir="/Users/qangz/Downloads/99.Project/Nexus-AI/.sessions"):
    # Create a session manager with a unique session ID
    sid = session_id if session_id!="default" else uuid.uuid4()
    session_manager = FileSessionManager(
        session_id=str(sid),
        storage_dir=session_dir
    )
    return session_manager


def analyze_user_intent(user_input: str):
    """分析用户意图"""
    print(f"🔍 分析用户意图: {user_input}")
    
    try:
        # 使用意图分析 agent
        result = intent_analyzer.structured_output(
            IntentRecognitionResult,
            f"用户输入：{user_input}"
        )
        
        print(f"📊 意图分析结果:")
        print(f"  - 意图类型: {result.intent_type}")
        print(f"  - 提到的项目: {result.mentioned_project_name}")
        print(f"  - 项目存在: {result.project_exists}")
        print(f"  - 处理建议: {result.orchestrator_guidance}")
        
        return result
        
    except Exception as e:
        print(f"❌ 意图分析失败: {e}")
        # 返回默认结果
        return IntentRecognitionResult(
            user_input=user_input,
            intent_type="unclear",
            mentioned_project_name=None,
            project_exists=False,
            existing_project_info=None,
            orchestrator_guidance="需要进一步分析用户需求"
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
    builder.add_edge("orchestrator", "system_architect")
    builder.add_edge("orchestrator", "agent_designer")
    builder.add_edge("orchestrator", "agent_developer_manager")

    builder.add_edge("requirements_analyzer", "system_architect")
    builder.add_edge("system_architect", "agent_designer")
    builder.add_edge("system_architect", "agent_developer_manager")

    builder.add_edge("agent_developer_manager", "tool_developer")
    builder.add_edge("agent_developer_manager", "prompt_engineer")
    builder.add_edge("agent_developer_manager", "agent_code_developer")

    
    # 构建图
    graph = builder.build()
    print("✅ 工作流图构建完成")
    
    return graph


def run_workflow(user_input: str):
    """运行工作流"""
    print(f"🎯 开始处理用户需求: {user_input}")
    
    # 第一步：分析用户意图
    intent_result = analyze_user_intent(user_input)

    workflow = create_build_workflow()
    result = workflow(str(intent_result))

    print("🎉 工作流执行完成")
    return {
        "intent_analysis": intent_result,
        "workflow_result": result
    }


if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='工作流编排器 Agent 测试')
    parser.add_argument('-i', '--input', type=str, 
                       default="我需要一个agent，我会提供关于IT产品的描述和价格，它需要帮我根据aws服务和产品对照，生成完整的报价表单，并输出markdown格式。",
                       help='测试输入内容')
    args = parser.parse_args()
    
    print(f"✅ Orchestrator Agent 创建成功: {orchestrator.name}")
    print(f"✅ Intent Analyzer Agent 创建成功: {intent_analyzer.name}")
    print("🚀 创建并运行完整工作流...")
    
    session_manager = create_conversation_manager()
    
    # 运行完整工作流
    test_input = args.input
    print(f"🎯 测试输入: {test_input}")
    
    try:
        result = run_workflow(test_input)
        print(f"📋 工作流最终结果:")
        print(f"意图分析: {result['intent_analysis']}")
        print(f"工作流结果: {result['workflow_result']}")
    except Exception as e:
        print(f"❌ 工作流执行失败: {e}")
        import traceback
        traceback.print_exc()