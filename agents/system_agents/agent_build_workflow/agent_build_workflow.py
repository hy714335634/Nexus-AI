#!/usr/bin/env python3
"""
工作流编排器 Agent - 使用 agent_factory 创建并编排其他 agents
"""

import os
import time
import uuid
from time import sleep
import json
from typing import Any
from strands.multiagent import GraphBuilder,Swarm
from nexus_utils.agent_factory import create_agent_from_prompt_template
from nexus_utils.structured_output_model.project_intent_recognition import IntentRecognitionResult
from strands.session.file_session_manager import FileSessionManager
from tools.system_tools.agent_build_workflow.stage_tracker import (
    mark_stage_running,
    mark_stage_completed,
    mark_stage_failed,
)

# 导入其他 agents
from agents.system_agents.agent_build_workflow.requirements_analyzer_agent import requirements_analyzer
from agents.system_agents.agent_build_workflow.system_architect_agent import system_architect
from agents.system_agents.agent_build_workflow.agent_designer_agent import agent_designer
from agents.system_agents.agent_build_workflow.agent_deployer_agent import agent_deployer
from agents.system_agents.agent_build_workflow.agent_developer_manager_agent import agent_developer_manager
from strands.telemetry import StrandsTelemetry
from nexus_utils.workflow_report_generator import generate_workflow_summary_report
from nexus_utils.workflow_rule_extract import (
    get_base_rules,
    get_build_workflow_rules,
)

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
    nocallback=True,
    **agent_params
)


def _get_project_id():
    """获取当前项目ID"""
    return os.environ.get("NEXUS_STAGE_TRACKER_PROJECT_ID")


def _load_build_rules() -> str:
    """读取Base与Build工作流规则。"""
    base_rules = get_base_rules()
    build_rules = get_build_workflow_rules()
    return base_rules + "\n" + build_rules + "\n=====规则声明结束，请遵守以上规则=====\n"


def _create_stage_tracking_wrapper(agent, stage_name: str):
    """创建带阶段跟踪的Agent包装器
    
    直接修改Agent对象的__call__方法，添加阶段跟踪功能，然后返回Agent对象本身。
    这样可以保持Agent类型，满足strands GraphBuilder的要求。
    """
    # 检查是否已经包装过，避免重复包装
    if getattr(agent, f"_stage_tracking_wrapped_{stage_name}", False):
        return agent
    
    # 保存原始的__call__方法
    original_call = agent.__call__
    
    def wrapped_call(*args, **kwargs):
        """带阶段跟踪的Agent调用方法"""
        project_id = _get_project_id()
        
        if project_id:
            print(f"\n🔄 [{stage_name}] 标记阶段为运行中...")
            mark_stage_running(project_id, stage_name)
        
        try:
            # 调用原始的Agent方法
            result = original_call(*args, **kwargs)
            
            if project_id:
                print(f"✅ [{stage_name}] 标记阶段为已完成")
                mark_stage_completed(project_id, stage_name)
            
            return result
        except Exception as e:
            if project_id:
                print(f"❌ [{stage_name}] 标记阶段为失败: {str(e)}")
                mark_stage_failed(project_id, stage_name, str(e))
            raise
    
    # 替换Agent的__call__方法
    agent.__call__ = wrapped_call  # type: ignore[assignment]
    # 标记已包装，避免重复包装
    setattr(agent, f"_stage_tracking_wrapped_{stage_name}", True)
    
    # 返回Agent对象本身，而不是包装函数
    return agent


def analyze_user_intent(user_input: str):
    """分析用户意图"""
    print(f"\n{'='*80}")
    print(f"🔍 [INTENT] 开始分析用户意图")
    print(f"{'='*80}")
    
    try:
        # 使用意图分析 agent
        intent_structured_result = intent_analyzer.structured_output(
            IntentRecognitionResult,
            f"用户输入：{user_input}"
        )
        print(f"\n{'='*80}")
        print(f"📊 意图类型:\t{intent_structured_result.intent_type}")
        print(f"📊 提到的项目:\t{intent_structured_result.mentioned_project_name}")
        print(f"📊 项目存在:\t{intent_structured_result.project_exists}")
        print(f"📊 处理建议:\t{intent_structured_result.orchestrator_guidance}")
        print(f"{'='*80}\n")

        return intent_structured_result
        
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
    
    # 添加节点 - 使用包装器来跟踪阶段状态
    print("📋 添加工作流节点（带状态跟踪）...")
    
    # 所有阶段都使用包装器来跟踪状态
    builder.add_node(
        _create_stage_tracking_wrapper(orchestrator, "orchestrator"),
        "orchestrator"
    )
    
    # 其他阶段需要包装以跟踪状态
    builder.add_node(
        _create_stage_tracking_wrapper(requirements_analyzer, "requirements_analyzer"),
        "requirements_analyzer"
    )
    builder.add_node(
        _create_stage_tracking_wrapper(system_architect, "system_architect"),
        "system_architect"
    )
    builder.add_node(
        _create_stage_tracking_wrapper(agent_designer, "agent_designer"),
        "agent_designer"
    )
    builder.add_node(
        _create_stage_tracking_wrapper(agent_developer_manager, "agent_developer_manager"),
        "agent_developer_manager"
    )
    builder.add_node(
        _create_stage_tracking_wrapper(agent_deployer, "agent_deployer"),
        "agent_deployer"
    )

    # 添加边 - 定义工作流顺序
    print("🔗 配置工作流连接...")
    builder.add_edge("orchestrator", "requirements_analyzer")
    builder.add_edge("requirements_analyzer", "system_architect")
    builder.add_edge("system_architect", "agent_designer")
    builder.add_edge("agent_designer", "agent_developer_manager")
    builder.add_edge("agent_developer_manager", "agent_deployer")
    
    # 构建图
    graph = builder.build()
    print("✅ 工作流图构建完成（已启用阶段状态跟踪）")
    
    return graph


def run_workflow(user_input: str, session_id="default"):
    print(f"\n{'='*80}", flush=True)
    print(f"🎯 [WORKFLOW] 开始工作流执行", flush=True)
    print(f"{'='*80}", flush=True)

    # 第一步：分析用户意图
    print(f"🔍 [STEP 1] 分析用户意图...", flush=True)
    intent_structured_result = analyze_user_intent(user_input)

    # 创建工作流
    print(f"\n🏗️ [STEP 2] 创建构建工作流...", flush=True)
    workflow = create_build_workflow()
    
    # 执行工作流
    print(f"\n{'='*80}", flush=True)
    print(f"⚡ [STEP 3] 执行工作流", flush=True)
    print(f"📝 输入内容: {user_input[:100]}...", flush=True)
    print(f"{'='*80}", flush=True)
    
    try:
        print("🚀 开始执行工作流...", flush=True)
        print("📋 预计执行阶段:", flush=True)
        print("  1️⃣ orchestrator - 工作流编排", flush=True)
        print("  2️⃣ requirements_analyzer - 需求分析", flush=True)
        print("  3️⃣ system_architect - 系统架构设计", flush=True)
        print("  4️⃣ agent_designer - Agent设计", flush=True)
        print("  5️⃣ agent_developer_manager - 开发管理", flush=True)
        print(f"{'='*60}", flush=True)

        # 执行工作流并监控进度
        import time
        start_time = time.time()

        # 加载规则作为上下文
        rules = _load_build_rules()
        
        # 构建工作流输入，包含规则、意图识别结果和用户输入
        workflow_input = (
            f"# Build Workflow Kickoff\n"
            f"## 规则上下文\n{rules}\n"
            f"## 意图识别结果\n{intent_structured_result}\n"
            f"## 用户原始输入\n{user_input}\n"
            f"请按顺序完成构建流程，遵守以上规则。"
        )

        result = workflow(workflow_input)

        end_time = time.time()
        execution_duration = end_time - start_time
        print(f"\n⏱️ 实际执行时间: {execution_duration:.2f}秒")

        print("✅ 工作流执行完成")
        
        # 生成工作流总结报告
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
        

        report_path = generate_workflow_summary_report(result, './projects')
        print(f"📄 报告路径: {report_path}")
        print(f"{'='*80}")

        return {
            "report_path": report_path,
            "intent_analysis": intent_structured_result,
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

请创建一个用于AWS产品报价的Agent，我需要他帮我完成AWS产品报价工作，我会提供自然语言描述的资源和配置要求，请分析并推荐合理AWS服务和配置，然后进行实时的报价并生成报告。
具体要求如下：
1.至少需要支持EC2、EBS、S3、网络流量、ELB、RDS、ElastiCache、Opensearch这几个产品，能够获取实时且真实的按需和预留实例价格
2.在用户提出的描述不清晰时，需要能够根据用户需求推测合理配置
3.在推荐配置和获取价格时，应通过API或SDK获取当前支持的实例类型和真实价格，因为不同区域支持的机型有所区别
4.在同系列同配置情况下，优先推荐最新一代实例
5、能够支持根据客户指定区域进行报价，包括中国区
6、能够按照销售的思维分析用户提供的数据，生成清晰且有逻辑的报价方案

如果价格获取失败或无法获取，请在对应资源报价中注明。
""",
                       help='测试输入内容')
    parser.add_argument('-f', '--file', type=str, 
                       help='从文件中读取内容并添加到测试输入中')
    args = parser.parse_args()
    
    print(f"🎯 [SYSTEM] Orchestrator Agent 创建成功", flush=True)
    print(f"🎯 [SYSTEM] Intent Analyzer Agent 创建成功", flush=True)
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
    
    print(f"📝 [SYSTEM] 测试输入: {test_input[:100]}...")
    
    try:
        result = run_workflow(test_input)
        # 将result持久化保存到本地文件，方便后续测试
        print(f"\n{'='*80}")
        print(f"🎉 [SYSTEM] 工作流执行完成")
        print(f"📊 工作流报告: {result['report_path']}")
        print(f"{'='*80}")
    except Exception as e:
        print(f"❌ [SYSTEM] 工作流执行失败: {e}")
        import traceback
        traceback.print_exc()

