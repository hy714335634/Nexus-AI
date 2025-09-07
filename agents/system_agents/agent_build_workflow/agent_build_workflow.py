#!/usr/bin/env python3
"""
工作流编排器 Agent - 使用 agent_factory 创建并编排其他 agents
"""

import os
import time
import uuid
from strands.multiagent import GraphBuilder,Swarm
from utils.agent_factory import create_agent_from_prompt_template
from utils.structured_output_model.project_intent_recognition import IntentRecognitionResult
from strands.session.file_session_manager import FileSessionManager

# 导入其他 agents
from agents.system_agents.agent_build_workflow.requirements_analyzer_agent import requirements_analyzer
from agents.system_agents.agent_build_workflow.system_architect_agent import system_architect
from agents.system_agents.agent_build_workflow.agent_designer_agent import agent_designer
from agents.system_agents.agent_build_workflow.prompt_engineer_agent import prompt_engineer
from agents.system_agents.agent_build_workflow.tool_developer_agent import tool_developer
from agents.system_agents.agent_build_workflow.agent_code_developer_agent import agent_code_developer
from agents.system_agents.agent_build_workflow.agent_developer_manager_agent import agent_developer_manager
from strands.telemetry import StrandsTelemetry

os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# 创建 agent 的通用参数（不启用日志，因为Graph不支持）
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

# 创建意图分析 agent
intent_analyzer = create_agent_from_prompt_template(
    agent_name="system_agents_prompts/agent_build_workflow/agent_intent_analyzer",
    **agent_params
)


def analyze_user_intent(user_input: str):
    """分析用户意图"""
    print(f"\n{'='*80}")
    print(f"🔍 [INTENT] 开始分析用户意图")
    print(f"{'='*80}")
    
    try:
        # 使用意图分析 agent
        result = intent_analyzer.structured_output(
            IntentRecognitionResult,
            f"用户输入：{user_input}"
        )
        
        print(f"📊 意图类型:\t{result.intent_type}")
        print(f"📊 提到的项目:\t{result.mentioned_project_name}")
        print(f"📊 项目存在:\t{result.project_exists}")
        print(f"📊 处理建议:\t{result.orchestrator_guidance}")
        
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
    
    print(f"\n{'='*80}")
    print(f"🏗️  [WORKFLOW] 创建工作流")
    print(f"{'='*80}")
    
    developer_swarm = Swarm(
        [prompt_engineer, tool_developer, agent_code_developer],
        max_handoffs=20,
        max_iterations=20,
        execution_timeout=3600.0,  # 60 minutes
        node_timeout=1200.0,       # 20 minutes per agent
        repetitive_handoff_detection_window=8,  # There must be >= 3 unique agents in the last 8 handoffs
        repetitive_handoff_min_unique_agents=3
    )


    builder = GraphBuilder()
    
    # 添加节点
    print("📋 添加工作流节点...")
    builder.add_node(orchestrator, "orchestrator")
    builder.add_node(requirements_analyzer, "requirements_analyzer")
    builder.add_node(system_architect, "system_architect")
    builder.add_node(agent_designer, "agent_designer")
    # builder.add_node(developer_swarm, "developer_swarm")
    # builder.add_node(prompt_engineer, "prompt_engineer")
    # builder.add_node(tool_developer, "tool_developer")
    # builder.add_node(agent_code_developer, "agent_code_developer")
    builder.add_node(agent_developer_manager, "agent_developer_manager")
    
    # 添加边 - 定义工作流顺序
    print("🔗 配置工作流连接...")
    builder.add_edge("orchestrator", "requirements_analyzer")
    builder.add_edge("requirements_analyzer", "system_architect")
    builder.add_edge("system_architect", "agent_designer")
    builder.add_edge("agent_designer", "agent_developer_manager")
    # builder.add_edge("orchestrator", "agent_developer_manager")
    # builder.add_edge("developer_swarm", "agent_developer_manager")
    # builder.add_edge("agent_designer", "tool_developer")
    # builder.add_edge("tool_developer", "prompt_engineer")
    # builder.add_edge("prompt_engineer", "agent_code_developer")
    # builder.add_edge("agent_code_developer", "agent_developer_manager")
    
    # 构建图
    graph = builder.build()
    print("✅ 工作流图构建完成")
    
    return graph


def run_workflow(user_input: str, session_id="default"):
    # 第一步：分析用户意图
    intent_result = analyze_user_intent(user_input)


    # 创建工作流
    workflow = create_build_workflow()
    
    # 执行工作流
    print(f"\n{'='*80}")
    print(f"⚡ [EXECUTION] 执行工作流")
    print(f"{'='*80}")
    
    try:
        result = workflow(str(intent_result))
        print("✅ 工作流执行完成")
        return {
            "intent_analysis": intent_result,
            "workflow_result": result
        }
    except Exception as e:
        print(f"❌ 工作流执行失败: {e}")
        raise


if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='工作流编排器 Agent 测试')
    parser.add_argument('-i', '--input', type=str, 
                       default="""
请创建一个Agent帮我完成AWS产品报价工作，我会提供tsv格式的其他云平台账单或IDC配置清单，请找到正确的AWS配置并告诉我真实价格，具体要求如下：
1、需要至少支持计算、存储、网络、数据库四个核心产品
2、在用户提出的描述不清晰时，需要能够根据用户需求推测合理配置
3、需要使用真实价格数据，通过aws接口获取真实数据
4、能够支持根据客户指定区域进行报价
5、能够按照销售的思维分析用户提供的数据，生成清晰且有逻辑的报价方案
6、报价文档尽量使用中文
""",
                       help='测试输入内容')
    args = parser.parse_args()
    
    print(f"🎯 [SYSTEM] Orchestrator Agent 创建成功")
    print(f"🎯 [SYSTEM] Intent Analyzer Agent 创建成功")
    print(f"🎯 [SYSTEM] 所有工作流Agent创建成功")
    print(f"🎯 [SYSTEM] 开始创建并运行完整工作流...")
    
    # 运行完整工作流
    test_input = args.input
    
    print(f"📝 [SYSTEM] 测试输入: {test_input[:100]}...")
    
    try:
        result = run_workflow(test_input)
        print(f"\n{'='*80}")
        print(f"🎉 [SYSTEM] 工作流执行完成")
        print(f"📊 意图分析: {result['intent_analysis']}")
        print(f"📊 工作流结果: {result['workflow_result']}")
        print(f"{'='*80}")
    except Exception as e:
        print(f"❌ [SYSTEM] 工作流执行失败: {e}")
        import traceback
        traceback.print_exc()