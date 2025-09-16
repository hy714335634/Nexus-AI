#!/usr/bin/env python3
"""
工作流编排器 Agent - 使用 agent_factory 创建并编排其他 agents
"""

import os
import time
import uuid
import json
from typing import Any
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
from utils.workflow_report_generator import generate_workflow_summary_report

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
        
        # 生成工作流总结报告
        print(f"\n{'='*80}")
        
        print(f"Status: {result.status}")  # COMPLETED, FAILED, etc.

        # See which nodes were executed and in what order
        for node in result.execution_order:
            print(f"Executed: {node.node_id}")

        # Get results from specific nodes
        orchestrator_result = result.results["orchestrator"].result
        print(f"Analysis: {orchestrator_result}")

        # Get performance metrics
        print(f"Total nodes: {result.total_nodes}")
        print(f"Completed nodes: {result.completed_nodes}")
        print(f"Failed nodes: {result.failed_nodes}")
        print(f"Execution time: {result.execution_time}ms")
        print(f"Token usage: {result.accumulated_usage}")
        print(f"{'='*80}")
        
        # 将result变量保存到本地json文件
        result_dict = {
            "total_nodes": result.total_nodes,
            "completed_nodes": result.completed_nodes,
            "failed_nodes": result.failed_nodes,
            "execution_time": result.execution_time,
            "accumulated_usage": result.accumulated_usage.__dict__ if hasattr(result.accumulated_usage, '__dict__') else str(result.accumulated_usage),
            "outputs": {k: str(v) for k, v in result.outputs.items()} if hasattr(result, 'outputs') else {}
        }
        with open('result.json', 'w', encoding='utf-8') as f:
            json.dump(result_dict, f, ensure_ascii=False, indent=4)
            print(f"📝 [SYSTEM] 已将result变量保存到本地json文件")

        report_path = generate_workflow_summary_report(result, './projects')
        
        return {
            "report_path": report_path,
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


""",
                       help='测试输入内容')
    parser.add_argument('-f', '--file', type=str, 
                       help='从文件中读取内容并添加到测试输入中')
    args = parser.parse_args()
    
    print(f"🎯 [SYSTEM] Orchestrator Agent 创建成功")
    print(f"🎯 [SYSTEM] Intent Analyzer Agent 创建成功")
    print(f"🎯 [SYSTEM] 所有工作流Agent创建成功")
    print(f"🎯 [SYSTEM] 开始创建并运行完整工作流...")
    
    # 运行完整工作流
    test_input = args.input
    
    # 如果指定了文件参数，读取文件内容并添加到test_input中
    if args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                file_content = f.read()
                test_input += f"\n\n从文件 {args.file} 读取的内容：\n{file_content}"
                print(f"📁 [SYSTEM] 已从文件 {args.file} 读取内容")
        except FileNotFoundError:
            print(f"❌ [SYSTEM] 文件 {args.file} 不存在")
            exit(1)
        except Exception as e:
            print(f"❌ [SYSTEM] 读取文件 {args.file} 失败: {e}")
            exit(1)
    
    print(f"📝 [SYSTEM] 测试输入: {test_input[:100]}...")
    
    try:
        result = run_workflow(test_input)
        # 将result持久化保存到本地文件，方便后续测试
        print(f"\n{'='*80}")
        print(f"🎉 [SYSTEM] 工作流执行完成")
        # print(f"📊 意图分析: {result['intent_analysis']}")
        # print(f"📊 工作流结果: {result['workflow_result']}")
        print(f"📊 工作流报告: {result['report_path']}")
        print(f"{'='*80}")
    except Exception as e:
        print(f"❌ [SYSTEM] 工作流执行失败: {e}")
        import traceback
        traceback.print_exc()