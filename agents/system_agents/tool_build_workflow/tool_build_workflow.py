#!/usr/bin/env python3
"""
工具构建工作流编排器 - 使用 agent_factory 创建并编排其他 agents
"""

import os
import time
import json
import argparse
from strands.multiagent import GraphBuilder
from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry
from nexus_utils.workflow_rule_extract import (
    get_base_rules,
    get_tool_build_workflow_rules,
)

# 导入其他 agents
from agents.system_agents.tool_build_workflow.tool_build_orchestrator_agent import tool_build_orchestrator
from agents.system_agents.tool_build_workflow.requirements_analyzer_agent import requirements_analyzer
from agents.system_agents.tool_build_workflow.tool_designer_agent import tool_designer
from agents.system_agents.tool_build_workflow.tool_developer_agent import tool_developer
from agents.system_agents.tool_build_workflow.tool_validator_agent import tool_validator
from agents.system_agents.tool_build_workflow.tool_documenter_agent import tool_documenter

strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()


def _prepare_environment() -> None:
    """设置工作流运行所需环境变量。"""
    os.environ.setdefault("BYPASS_TOOL_CONSENT", "true")
    os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")


def _load_tool_build_rules() -> str:
    """读取Base与Tool Build工作流规则。"""
    base_rules = get_base_rules()
    tool_build_rules = get_tool_build_workflow_rules()
    return base_rules + "\n" + tool_build_rules + "\n=====规则声明结束，请遵守以上规则=====\n"


def initialize_tool_build_workflow(user_input: str) -> GraphBuilder:
    """
    初始化Tool Build Workflow编排骨架。

    Args:
        user_input: 用户功能需求描述

    Returns:
        GraphBuilder: 用于后续构建Strands工作流的图构造器
    """
    _prepare_environment()
    rules = _load_tool_build_rules()

    print("🎯 初始化Tool Build Workflow")
    print(f"📝 用户需求: {user_input}")
    print("\n📘 规则:" + rules)

    builder = GraphBuilder()
    
    # 添加节点
    print("📋 添加工作流节点...")
    builder.add_node(tool_build_orchestrator, "orchestrator")
    builder.add_node(requirements_analyzer, "requirements_analyzer")
    builder.add_node(tool_designer, "tool_designer")
    builder.add_node(tool_developer, "tool_developer")
    builder.add_node(tool_validator, "tool_validator")
    builder.add_node(tool_documenter, "tool_documenter")

    # 添加边 - 定义工作流顺序
    print("🔗 配置工作流连接...")
    builder.add_edge("orchestrator", "requirements_analyzer")
    builder.add_edge("requirements_analyzer", "tool_designer")
    builder.add_edge("tool_designer", "tool_developer")
    builder.add_edge("tool_developer", "tool_validator")
    builder.add_edge("tool_validator", "tool_documenter")

    return builder


def run_tool_build_workflow(user_input: str):
    """
    构建并执行工具构建工作流。
    
    Args:
        user_input: 用户自然语言描述的功能需求
        
    Returns:
        dict: 工作流执行结果
    """
    builder = initialize_tool_build_workflow(user_input)
    workflow = builder.build()

    rules = _load_tool_build_rules()
    
    kickoff_payload = (
        f"# Tool Build Workflow Kickoff\n"
        f"- user_request: {user_input}\n"
        f"- workflow_rules:\n{rules}\n"
        "请按顺序完成工具构建流程，遵守上述规则。"
    )

    print(f"\n{'='*80}", flush=True)
    print(f"⚡ [STEP 2] 执行工作流", flush=True)
    print(f"📝 用户需求: {user_input[:100]}...", flush=True)
    print(f"{'='*80}", flush=True)
    
    try:
        print("🚀 开始执行工作流...", flush=True)
        print("📋 预计执行阶段:", flush=True)
        print("  1️⃣ orchestrator - 工作流编排和项目初始化", flush=True)
        print("  2️⃣ requirements_analyzer - 需求分析", flush=True)
        print("  3️⃣ tool_designer - 工具设计", flush=True)
        print("  4️⃣ tool_developer - 工具开发", flush=True)
        print("  5️⃣ tool_validator - 工具验证", flush=True)
        print("  6️⃣ tool_documenter - 文档生成", flush=True)
        print(f"{'='*60}", flush=True)

        # 执行工作流并监控进度
        start_time = time.time()

        result = workflow(kickoff_payload)

        end_time = time.time()
        execution_duration = end_time - start_time
        print(f"\n⏱️ 实际执行时间: {execution_duration:.2f}秒")

        print("✅ 工作流执行完成")
        
        # 输出工作流执行结果
        print(f"\n{'='*80}")
        print(f"📊 [RESULTS] 工作流执行结果")
        print(f"{'='*80}")

        print(f"📈 状态: {result.status}")  # COMPLETED, FAILED, etc.
        print(f"📊 总节点数: {result.total_nodes}")
        print(f"✅ 完成节点数: {result.completed_nodes}")
        print(f"❌ 失败节点数: {result.failed_nodes}")
        print(f"⏱️ 执行时间: {result.execution_time}ms")
        print(f"🔢 Token使用: {result.accumulated_usage}")

        # See which nodes were executed and in what order
        for node in result.execution_order:
            print(f"Executed: {node.node_id}")

        print(f"{'='*80}")

        return {
            "workflow_result": result,
            "execution_time": execution_duration
        }
    except Exception as e:
        print(f"❌ 工作流执行失败: {e}")
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Tool Build Workflow 工具构建工作流")
    parser.add_argument("-i", "--input", type=str, 
                       default="我需要一个工具，能够从指定的URL下载文件并保存到本地",
                       help="用户功能需求描述")
    parser.add_argument("-f", "--file", type=str, 
                       help="从文件中读取需求描述")
    args = parser.parse_args()
    
    print(f"🎯 [SYSTEM] Tool Build Orchestrator Agent 创建成功", flush=True)
    print(f"🎯 [SYSTEM] 所有工作流Agent创建成功", flush=True)
    print(f"🎯 [SYSTEM] 开始创建并运行完整工作流...", flush=True)
    
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
    
    print(f"📝 [SYSTEM] 用户需求: {test_input[:100]}...")
    
    try:
        result = run_tool_build_workflow(test_input)
        print(f"\n{'='*80}")
        print(f"🎉 [SYSTEM] 工具构建工作流执行完成")
        print(f"{'='*80}")
        print("\n🎯 最终状态:", result["workflow_result"].status)
    except Exception as e:
        print(f"❌ [SYSTEM] 工作流执行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

