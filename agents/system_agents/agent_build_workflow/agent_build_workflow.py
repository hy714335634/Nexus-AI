#!/usr/bin/env python3
"""
工作流编排器 Agent - 使用 agent_factory 创建并编排其他 agents
"""

import os
import time
import uuid
import json
import re
from typing import Optional
from nexus_utils.agent_factory import create_agent_from_prompt_template
from nexus_utils.structured_output_model.project_intent_recognition import IntentRecognitionResult
from strands.session.file_session_manager import FileSessionManager
from tools.system_tools.agent_build_workflow.stage_tracker import (
    mark_stage_running,
    mark_stage_completed,
    mark_stage_failed,
)
from strands.telemetry import StrandsTelemetry
from nexus_utils.workflow_rule_extract import (
    get_base_rules,
    get_build_workflow_rules,
)

# 设置环境变量
os.environ.setdefault("BYPASS_TOOL_CONSENT", "true")
os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

# 创建 agent 的通用参数
agent_params = {
    "env": "production",
    "version": "latest", 
    "model_id": "default",
    "enable_logging": True
}


def _get_project_id():
    """获取当前项目ID"""
    return os.environ.get("NEXUS_STAGE_TRACKER_PROJECT_ID")


def _load_build_rules() -> str:
    """读取Base与Build工作流规则。"""
    base_rules = get_base_rules()
    build_rules = get_build_workflow_rules()
    return base_rules + "\n" + build_rules + "\n=====规则声明结束，请遵守以上规则=====\n"


def analyze_user_intent(user_input: str):
    """分析用户意图 - 通过JSON输出方式"""
    print(f"\n{'='*80}")
    print(f"🔍 [INTENT] 开始分析用户意图")
    print(f"{'='*80}")
    
    try:
        # 创建意图分析 agent（不使用session manager）
        intent_analyzer = create_agent_from_prompt_template(
            agent_name="system_agents_prompts/agent_build_workflow/agent_intent_analyzer",
            nocallback=True,
            **agent_params
        )
        
        # 构建包含JSON结构说明的提示
        intent_result_schema = IntentRecognitionResult.model_json_schema()
        intent_result_example = {
            "user_input": "用户原始输入内容",
            "intent_type": "new_project",  # 或 "existing_project" 或 "unclear"
            "mentioned_project_name": "项目名称（如果有）",
            "project_exists": False,
            "existing_project_info": None,  # 或 ExistingProjectInfo 对象
            "new_project_info": None,  # 或 NewProjectInfo 对象
            "orchestrator_guidance": "给orchestrator的处理建议"
        }
        
        intent_prompt = f"""用户输入：{user_input}

请分析用户意图，并输出JSON格式的结果。

JSON结构说明：
{json.dumps(intent_result_schema, ensure_ascii=False, indent=2)}

示例JSON：
{json.dumps(intent_result_example, ensure_ascii=False, indent=2)}

请直接输出JSON，不要包含其他文字说明。确保JSON格式正确，可以直接被解析。"""
        
        # 调用agent获取响应
        response = intent_analyzer(intent_prompt)
        
        # 从响应中提取JSON
        response_text = response.content if hasattr(response, 'content') else str(response)
        
        # 尝试提取JSON（可能包含在代码块中）
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            json_str = json_match.group(0)
        else:
            json_str = response_text
        
        # 解析JSON为IntentRecognitionResult对象
        intent_data = json.loads(json_str)
        intent_structured_result = IntentRecognitionResult(**intent_data)
        
        print(f"\n{'='*80}")
        print(f"📊 意图类型:\t{intent_structured_result.intent_type}")
        print(f"📊 提到的项目:\t{intent_structured_result.mentioned_project_name}")
        print(f"📊 项目存在:\t{intent_structured_result.project_exists}")
        print(f"📊 处理建议:\t{intent_structured_result.orchestrator_guidance}")
        print(f"{'='*80}\n")

        return intent_structured_result
        
    except Exception as e:
        print(f"❌ 意图分析失败: {e}")
        import traceback
        traceback.print_exc()
        # 返回默认结果
        return IntentRecognitionResult(
            user_input=user_input,
            intent_type="unclear",
            mentioned_project_name=None,
            project_exists=False,
            existing_project_info=None,
            orchestrator_guidance="需要进一步分析用户需求"
        )


def _create_agents_with_session(session_manager: Optional[FileSessionManager] = None):
    """创建带session管理的agents"""
    agent_kwargs = {**agent_params}
    if session_manager:
        agent_kwargs["session_manager"] = session_manager
    
    # 创建各个agent
    orchestrator_agent = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/agent_build_workflow/orchestrator",
        **agent_kwargs
    )
    
    requirements_analyzer_agent = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/agent_build_workflow/requirements_analyzer",
        **agent_kwargs
    )
    
    system_architect_agent = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/agent_build_workflow/system_architect",
        **agent_kwargs
    )
    
    agent_designer_agent = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/agent_build_workflow/agent_designer",
        **agent_kwargs
    )
    
    # 创建开发团队的agents
    tool_developer_agent = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/agent_build_workflow/tool_developer",
        **agent_kwargs
    )
    
    prompt_engineer_agent = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/agent_build_workflow/prompt_engineer",
        **agent_kwargs
    )
    
    agent_code_developer_agent = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/agent_build_workflow/agent_code_developer",
        **agent_kwargs
    )
    
    # agent_webapp_developer_agent = create_agent_from_prompt_template(
    #     agent_name="system_agents_prompts/agent_build_workflow/agent_webapp_developer",
    #     **agent_kwargs
    # )
    
    agent_developer_manager_agent = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/agent_build_workflow/agent_developer_manager",
        **agent_kwargs
    )
    
    agent_deployer_agent = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/agent_build_workflow/agent_deployer",
        **agent_kwargs
    )
    
    return {
        "orchestrator": orchestrator_agent,
        "requirements_analyzer": requirements_analyzer_agent,
        "system_architect": system_architect_agent,
        "agent_designer": agent_designer_agent,
        "tool_developer": tool_developer_agent,
        "prompt_engineer": prompt_engineer_agent,
        "agent_code_developer": agent_code_developer_agent,
        # "agent_webapp_developer": agent_webapp_developer_agent,
        "agent_developer_manager": agent_developer_manager_agent,
        "agent_deployer": agent_deployer_agent,
    }


def run_workflow(user_input: str, session_id: Optional[str] = None):
    """
    执行构建工作流
    
    Args:
        user_input: 用户输入内容
        session_id: 可选的session_id，如果未提供则自动生成
    """
    print(f"\n{'='*80}", flush=True)
    print(f"🎯 [WORKFLOW] 开始工作流执行", flush=True)
    print(f"{'='*80}", flush=True)

    # 第一步：分析用户意图（不使用session）
    print(f"🔍 [STEP 1] 分析用户意图...", flush=True)
    intent_structured_result = analyze_user_intent(user_input)

    # 第二步：生成或使用session_id，创建session manager
    if session_id is None:
        session_id = str(uuid.uuid4())
        print(f"🔑 [STEP 2] 生成新的session_id: {session_id}", flush=True)
    else:
        print(f"🔑 [STEP 2] 使用指定的session_id: {session_id}", flush=True)
    
    # 创建session manager
    session_manager = FileSessionManager(
        session_id=session_id,
        storage_dir="./.cache/session_cache"
    )
    
    # 第三步：创建带session的agents
    print(f"\n🏗️ [STEP 3] 创建构建工作流agents（带session管理）...", flush=True)
    agents = _create_agents_with_session(session_manager)
    
    # 第四步：执行工作流
    print(f"\n{'='*80}", flush=True)
    print(f"⚡ [STEP 4] 执行工作流", flush=True)
    print(f"📝 输入内容: {user_input[:100]}...", flush=True)
    print(f"🔑 Session ID: {session_id}", flush=True)
    print(f"{'='*80}", flush=True)
    
    try:
        print("🚀 开始执行工作流...", flush=True)
        print("📋 预计执行阶段:", flush=True)
        print("  1️⃣ orchestrator - 工作流编排", flush=True)
        print("  2️⃣ requirements_analyzer - 需求分析", flush=True)
        print("  3️⃣ system_architect - 系统架构设计", flush=True)
        print("  4️⃣ agent_designer - Agent设计", flush=True)
        print("  5️⃣ tool_developer - 工具开发", flush=True)
        print("  6️⃣ prompt_engineer - 提示词开发", flush=True)
        print("  7️⃣ agent_code_developer - Agent脚本开发", flush=True)
        print("  8️⃣ agent_developer_manager - 开发管理", flush=True)
        print("  9️⃣ agent_deployer - Agent部署", flush=True)
        print(f"{'='*60}", flush=True)

        # 执行工作流并监控进度
        start_time = time.time()

        # 加载规则作为上下文
        rules = _load_build_rules()
        
        # 构建工作流输入，包含规则、意图识别结果和用户输入
        workflow_input = (
            f"# Build Workflow Kickoff\n"
            f"## 必须严格遵守的规则:\n{rules}\n"
            f"## 意图识别结果\n{json.dumps(intent_structured_result.model_dump(), ensure_ascii=False, indent=2)}\n"
            f"## 用户原始输入\n{user_input}\n"
            f"请按顺序完成构建流程，遵守以上规则。"
        )

        # 顺序调用各个agent
        base_context = workflow_input
        current_context = workflow_input
        execution_results = {}  # 存储AgentResult对象
        execution_order = []
        project_id = _get_project_id()
        # 1. Orchestrator
        print(f"\n{'='*60}")
        print(f"🔄 [1/9] 执行 orchestrator...")
        print(f"{'='*60}")
        try:
            mark_stage_running(project_id, 'orchestrator')
            orchestrator_result = agents["orchestrator"](current_context)
            execution_results["orchestrator"] = orchestrator_result
            execution_order.append("orchestrator")
            orchestrator_content = str(orchestrator_result.content) if hasattr(orchestrator_result, 'content') else str(orchestrator_result)
            current_context = base_context + "\n===\nOrchestrator Agent: " + orchestrator_content + "\n===\n"
            mark_stage_completed(project_id, 'orchestrator')
        except Exception as e:
            mark_stage_failed(project_id, 'orchestrator', str(e))
            raise

        # 2. Requirements Analyzer
        print(f"\n{'='*60}")
        print(f"🔄 [2/9] 执行 requirements_analyzer...")
        print(f"{'='*60}")
        try:
            mark_stage_running(project_id, 'requirements_analysis')
            requirements_result = agents["requirements_analyzer"](current_context)
            execution_results["requirements_analyzer"] = requirements_result
            execution_order.append("requirements_analyzer")
            requirements_content = str(requirements_result.content) if hasattr(requirements_result, 'content') else str(requirements_result)
            current_context = base_context + "\n===\nRequirements Analyzer Agent: " + requirements_content + "\n===\n"
            mark_stage_completed(project_id, 'requirements_analysis')
        except Exception as e:
            mark_stage_failed(project_id, 'requirements_analysis', str(e))
            raise
        
        # 3. System Architect
        print(f"\n{'='*60}")
        print(f"🔄 [3/9] 执行 system_architect...")
        print(f"{'='*60}")
        try:
            mark_stage_running(project_id, 'system_architecture')
            architect_result = agents["system_architect"](current_context)
            execution_results["system_architect"] = architect_result
            execution_order.append("system_architect")
            architect_content = str(architect_result.content) if hasattr(architect_result, 'content') else str(architect_result)
            current_context = base_context + "\n===\nSystem Architect Agent: " + architect_content + "\n===\n"
            mark_stage_completed(project_id, 'system_architecture')
        except Exception as e:
            mark_stage_failed(project_id, 'system_architecture', str(e))
            raise
        
        # 4. Agent Designer
        print(f"\n{'='*60}")
        print(f"🔄 [4/9] 执行 agent_designer...")
        print(f"{'='*60}")
        try:
            mark_stage_running(project_id, 'agent_design')
            designer_result = agents["agent_designer"](current_context)
            execution_results["agent_designer"] = designer_result
            execution_order.append("agent_designer")
            designer_content = str(designer_result.content) if hasattr(designer_result, 'content') else str(designer_result)
            current_context = base_context + "\n===\nAgent Designer Agent: " + designer_content + "\n===\n"
            mark_stage_completed(project_id, 'agent_design')
        except Exception as e:
            mark_stage_failed(project_id, 'agent_design', str(e))
            raise
        
        # 5. Tool Developer
        print(f"\n{'='*60}")
        print(f"🔄 [5/9] 执行 tool_developer...")
        print(f"{'='*60}")
        try:
            mark_stage_running(project_id, 'tools_developer')
            tool_developer_result = agents["tool_developer"](current_context)
            execution_results["tool_developer"] = tool_developer_result
            execution_order.append("tool_developer")
            tool_developer_content = str(tool_developer_result.content) if hasattr(tool_developer_result, 'content') else str(tool_developer_result)
            current_context = current_context + "\n===\nTool Developer Agent: " + tool_developer_content + "\n===\n"
            mark_stage_completed(project_id, 'tools_developer')
        except Exception as e:
            mark_stage_failed(project_id, 'tools_developer', str(e))
            raise
        
        # 6. Prompt Engineer
        print(f"\n{'='*60}")
        print(f"🔄 [6/9] 执行 prompt_engineer...")
        print(f"{'='*60}")
        try:
            mark_stage_running(project_id, 'prompt_engineer')
            prompt_engineer_result = agents["prompt_engineer"](current_context)
            execution_results["prompt_engineer"] = prompt_engineer_result
            execution_order.append("prompt_engineer")
            prompt_engineer_content = str(prompt_engineer_result.content) if hasattr(prompt_engineer_result, 'content') else str(prompt_engineer_result)
            current_context = current_context + "\n===\nPrompt Engineer Agent: " + prompt_engineer_content + "\n===\n"
            mark_stage_completed(project_id, 'prompt_engineer')
        except Exception as e:
            mark_stage_failed(project_id, 'prompt_engineer', str(e))
            raise
        
        # 7. Agent Code Developer
        print(f"\n{'='*60}")
        print(f"🔄 [7/9] 执行 agent_code_developer...")
        print(f"{'='*60}")
        try:
            mark_stage_running(project_id, 'agent_code_developer')
            agent_code_developer_result = agents["agent_code_developer"](current_context)
            execution_results["agent_code_developer"] = agent_code_developer_result
            execution_order.append("agent_code_developer")
            agent_code_developer_content = str(agent_code_developer_result.content) if hasattr(agent_code_developer_result, 'content') else str(agent_code_developer_result)
            current_context = current_context + "\n===\nAgent Code Developer Agent: " + agent_code_developer_content + "\n===\n"
            mark_stage_completed(project_id, 'agent_code_developer')
        except Exception as e:
            mark_stage_failed(project_id, 'agent_code_developer', str(e))
            raise

        # # 8. Streamlit Web App Developer
        # print(f"\n{'='*60}")
        # print(f"🔄 [8/9] 执行 agent_webapp_developer...")
        # print(f"{'='*60}")
        # streamlit_webapp_developer_result = _call_agent_with_stage_tracking(
        #     agents["agent_webapp_developer"], "agent_webapp_developer", current_context
        # )
        # execution_results["agent_webapp_developer"] = streamlit_webapp_developer_result
        # execution_order.append("agent_webapp_developer")
        # streamlit_webapp_developer_content = str(streamlit_webapp_developer_result.content) if hasattr(streamlit_webapp_developer_result, 'content') else str(streamlit_webapp_developer_result)
        # current_context = current_context + "\n===\nStreamlit Web App Developer Agent: " + streamlit_webapp_developer_content + "\n===\n"
        
        # 8. Agent Developer Manager
        print(f"\n{'='*60}")
        print(f"🔄 [8/9] 执行 agent_developer_manager...")
        print(f"{'='*60}")
        try:
            mark_stage_running(project_id, 'agent_developer_manager')
            developer_manager_result = agents["agent_developer_manager"](current_context)
            execution_results["agent_developer_manager"] = developer_manager_result
            execution_order.append("agent_developer_manager")
            developer_manager_content = str(developer_manager_result.content) if hasattr(developer_manager_result, 'content') else str(developer_manager_result)
            current_context = base_context + "\n===\nAgent Developer Manager Agent: " + developer_manager_content + "\n===\n"
            mark_stage_completed(project_id, 'agent_developer_manager')
        except Exception as e:
            mark_stage_failed(project_id, 'agent_developer_manager', str(e))
            raise
        
        # 9. Agent Deployer
        print(f"\n{'='*60}")
        print(f"🔄 [9/9] 跳过 agent_deployer...")
        print(f"{'='*60}")
        try:
            mark_stage_running(project_id, 'agent_deployer')
            deployer_result = agents["agent_deployer"](current_context)
            execution_results["agent_deployer"] = deployer_result
            execution_order.append("agent_deployer")
            mark_stage_completed(project_id, 'agent_deployer')
        except Exception as e:
            mark_stage_failed(project_id, 'agent_deployer', str(e))
            raise

        end_time = time.time()
        execution_duration = end_time - start_time
        print(f"\n⏱️ 实际执行时间: {execution_duration:.2f}秒")

        print("✅ 工作流执行完成")

        # 更新项目状态为 COMPLETED
        from api.database.dynamodb_client import DynamoDBClient
        from api.models.schemas import ProjectStatus
        from datetime import datetime, timezone
        db_client = DynamoDBClient()
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        db_client.update_project_status(
            project_id,
            ProjectStatus.COMPLETED,
            completed_at=now,
            updated_at=now
        )
        print(f"✅ 项目状态已更新为 COMPLETED")

        # 生成工作流总结报告
        print(f"\n{'='*80}")
        print(f"📊 [RESULTS] 工作流执行结果")
        print(f"{'='*80}")

        print(f"📈 状态: COMPLETED")
        print(f"📊 总节点数: {len(execution_order)}")
        print(f"✅ 完成节点数: {len(execution_order)}")
        print(f"❌ 失败节点数: 0")
        print(f"⏱️ 执行时间: {execution_duration:.2f}秒")

        # 显示执行顺序
        for i, node_name in enumerate(execution_order, 1):
            print(f"  {i}. {node_name}")

        print(f"{'='*80}")

        # 生成工作流总结报告
        from nexus_utils.workflow_report_generator import generate_sequential_workflow_report
        report_path = generate_sequential_workflow_report(
            execution_results=execution_results,
            execution_order=execution_order,
            execution_time=execution_duration,
            intent_analysis=intent_structured_result,
            default_project_root_path='./projects'
        )
        if report_path:
            print(f"📄 报告路径: {report_path}")
        print(f"{'='*80}")

        return {
            "session_id": session_id,
            "intent_analysis": intent_structured_result,
            "execution_results": execution_results,
            "execution_order": execution_order,
            "execution_time": execution_duration,
            "status": "COMPLETED",
            "report_path": report_path
        }
    except Exception as e:
        print(f"❌ 工作流执行失败: {e}")
        import traceback
        traceback.print_exc()
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
    parser.add_argument('-s', '--session_id', type=str,
                       default=None,
                       help='可选的session_id，用于恢复之前的会话')
    args = parser.parse_args()
    
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
    if args.session_id:
        print(f"🔑 [SYSTEM] 使用指定的session_id: {args.session_id}")
    
    try:
        result = run_workflow(test_input, session_id=args.session_id)
        # 将result持久化保存到本地文件，方便后续测试
        print(f"\n{'='*80}")
        print(f"🎉 [SYSTEM] 工作流执行完成")
        print(f"🔑 Session ID: {result['session_id']}")
        print(f"📊 执行状态: {result['status']}")
        print(f"⏱️ 执行时间: {result['execution_time']:.2f}秒")
        print(f"{'='*80}")
    except Exception as e:
        print(f"❌ [SYSTEM] 工作流执行失败: {e}")
        import traceback
        traceback.print_exc()

