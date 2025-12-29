#!/usr/bin/env python3
"""
工具构建工作流编排器 - 顺序调用版本

功能概述：
1. 接收用户工具构建需求
2. 读取Base与Tool Build工作流规则
3. 按顺序调用各个Agent完成工具构建流程
"""

from __future__ import annotations

import argparse
import os
import time
import uuid
import logging
from typing import Optional

from strands.session.file_session_manager import FileSessionManager
from strands.telemetry import StrandsTelemetry
from nexus_utils.agent_factory import create_agent_from_prompt_template
from nexus_utils.workflow_rule_extract import (
    get_base_rules,
    get_tool_build_workflow_rules,
)
from nexus_utils.config_loader import ConfigLoader

logger = logging.getLogger(__name__)
config = ConfigLoader()

# 设置环境变量
os.environ.setdefault("BYPASS_TOOL_CONSENT", "true")
otel_endpoint = config.get_with_env_override(
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "nexus_ai", "OTEL_EXPORTER_OTLP_ENDPOINT",
    default="http://localhost:4318"
)
os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", otel_endpoint)
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

# 创建 agent 的通用参数
agent_params = {
    "env": "production",
    "version": "latest",
    "model_id": "default",
    "enable_logging": True
}


def _load_tool_build_rules() -> str:
    """读取Base与Tool Build工作流规则。"""
    base_rules = get_base_rules()
    tool_build_rules = get_tool_build_workflow_rules()
    return base_rules + "\n" + tool_build_rules + "\n=====规则声明结束，请遵守以上规则=====\n"


def _create_agents_with_session(session_manager: Optional[FileSessionManager] = None):
    """创建带session管理的agents"""
    agent_kwargs = {**agent_params}
    if session_manager:
        agent_kwargs["session_manager"] = session_manager
    
    # 创建各个agent
    orchestrator = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/tool_build_workflow/orchestrator",
        **agent_kwargs
    )
    
    requirements_analyzer = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/tool_build_workflow/requirements_analyzer",
        **agent_kwargs
    )
    
    tool_designer = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/tool_build_workflow/tool_designer",
        **agent_kwargs
    )
    
    tool_developer = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/tool_build_workflow/tool_developer",
        **agent_kwargs
    )
    
    tool_validator = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/tool_build_workflow/tool_validator",
        **agent_kwargs
    )
    
    tool_documenter = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/tool_build_workflow/tool_documenter",
        **agent_kwargs
    )
    
    return {
        "orchestrator": orchestrator,
        "requirements_analyzer": requirements_analyzer,
        "tool_designer": tool_designer,
        "tool_developer": tool_developer,
        "tool_validator": tool_validator,
        "tool_documenter": tool_documenter,
    }


def run_tool_build_workflow(user_input: str, session_id: Optional[str] = None):
    """
    执行工具构建工作流
    
    Args:
        user_input: 用户工具构建需求描述
        session_id: 可选的session_id，如果未提供则自动生成
        
    Returns:
        dict: 工作流执行结果
    """
    print(f"\n{'='*80}", flush=True)
    print(f"🎯 [TOOL BUILD WORKFLOW] 开始工具构建工作流执行", flush=True)
    print(f"{'='*80}", flush=True)

    # 第一步：生成或使用session_id，创建session manager
    if session_id is None:
        session_id = str(uuid.uuid4())
        print(f"🔑 [STEP 1] 生成新的session_id: {session_id}", flush=True)
    else:
        print(f"🔑 [STEP 1] 使用指定的session_id: {session_id}", flush=True)
    
    # 创建session manager
    session_manager = FileSessionManager(
        session_id=session_id,
        storage_dir="./.cache/session_cache"
    )
    
    # 第二步：创建带session的agents
    print(f"\n🏗️ [STEP 2] 创建工具构建工作流agents（带session管理）...", flush=True)
    agents = _create_agents_with_session(session_manager)
    
    # 第三步：加载规则
    print(f"\n📘 [STEP 3] 加载工作流规则...", flush=True)
    rules = _load_tool_build_rules()
    
    # 第四步：执行工作流
    print(f"\n{'='*80}", flush=True)
    print(f"⚡ [STEP 4] 执行工具构建工作流", flush=True)
    print(f"📝 用户需求: {user_input[:100]}...", flush=True)
    print(f"🔑 Session ID: {session_id}", flush=True)
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

        # 构建工作流输入
        workflow_input = (
            f"# Tool Build Workflow Kickoff\n"
            f"## 必须严格遵守的规则:\n{rules}\n"
            f"## 用户工具构建需求\n{user_input}\n"
            f"请按顺序完成工具构建流程，遵守以上规则。"
        )

        # 顺序调用各个agent
        base_context = workflow_input
        current_context = workflow_input
        execution_results = {}  # 存储AgentResult对象
        execution_order = []

        # 1. Orchestrator
        print(f"\n{'='*60}")
        print(f"🔄 [1/6] 执行 orchestrator...")
        print(f"{'='*60}")
        orchestrator_result = agents["orchestrator"](current_context)
        execution_results["orchestrator"] = orchestrator_result
        execution_order.append("orchestrator")
        orchestrator_content = str(orchestrator_result.content) if hasattr(orchestrator_result, 'content') else str(orchestrator_result)
        current_context = base_context + "\n===\nOrchestrator Agent: " + orchestrator_content + "\n===\n"

        # 2. Requirements Analyzer
        print(f"\n{'='*60}")
        print(f"🔄 [2/6] 执行 requirements_analyzer...")
        print(f"{'='*60}")
        requirements_result = agents["requirements_analyzer"](current_context)
        execution_results["requirements_analyzer"] = requirements_result
        execution_order.append("requirements_analyzer")
        requirements_content = str(requirements_result.content) if hasattr(requirements_result, 'content') else str(requirements_result)
        current_context = current_context + "\n===\nRequirements Analyzer Agent: " + requirements_content + "\n===\n"
        
        # 3. Tool Designer
        print(f"\n{'='*60}")
        print(f"🔄 [3/6] 执行 tool_designer...")
        print(f"{'='*60}")
        designer_result = agents["tool_designer"](current_context)
        execution_results["tool_designer"] = designer_result
        execution_order.append("tool_designer")
        designer_content = str(designer_result.content) if hasattr(designer_result, 'content') else str(designer_result)
        current_context = current_context + "\n===\nTool Designer Agent: " + designer_content + "\n===\n"
        
        # 4. Tool Developer
        print(f"\n{'='*60}")
        print(f"🔄 [4/6] 执行 tool_developer...")
        print(f"{'='*60}")
        developer_result = agents["tool_developer"](current_context)
        execution_results["tool_developer"] = developer_result
        execution_order.append("tool_developer")
        developer_content = str(developer_result.content) if hasattr(developer_result, 'content') else str(developer_result)
        current_context = current_context + "\n===\nTool Developer Agent: " + developer_content + "\n===\n"
        
        # 5. Tool Validator
        print(f"\n{'='*60}")
        print(f"🔄 [5/6] 执行 tool_validator...")
        print(f"{'='*60}")
        validator_result = agents["tool_validator"](current_context)
        execution_results["tool_validator"] = validator_result
        execution_order.append("tool_validator")
        validator_content = str(validator_result.content) if hasattr(validator_result, 'content') else str(validator_result)
        current_context = current_context + "\n===\nTool Validator Agent: " + validator_content + "\n===\n"
        
        # 6. Tool Documenter
        print(f"\n{'='*60}")
        print(f"🔄 [6/6] 执行 tool_documenter...")
        print(f"{'='*60}")
        documenter_result = agents["tool_documenter"](current_context)
        execution_results["tool_documenter"] = documenter_result
        execution_order.append("tool_documenter")

        end_time = time.time()
        execution_duration = end_time - start_time
        print(f"\n⏱️ 实际执行时间: {execution_duration:.2f}秒")

        print("✅ 工具构建工作流执行完成")

        # 生成工作流总结
        print(f"\n{'='*80}")
        print(f"📊 [RESULTS] 工具构建工作流执行结果")
        print(f"{'='*80}")

        print(f"📈 状态: COMPLETED")
        print(f"📊 总节点数: {len(execution_order)}")
        print(f"✅ 完成节点数: {len(execution_order)}")
        print(f"❌ 失败节点数: 0")
        print(f"⏱️ 执行时间: {execution_duration:.2f}秒")

        # 显示执行顺序
        print(f"\n📋 执行顺序:")
        for i, node_name in enumerate(execution_order, 1):
            print(f"  {i}. {node_name}")

        print(f"{'='*80}")

        return {
            "session_id": session_id,
            "execution_results": execution_results,
            "execution_order": execution_order,
            "execution_time": execution_duration,
            "status": "COMPLETED"
        }
    except Exception as e:
        print(f"❌ 工具构建工作流执行失败: {e}")
        import traceback
        traceback.print_exc()
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Tool Build Workflow - 工具构建工作流")
    parser.add_argument("-i", "--input", type=str, 
                       default="我需要一个工具，能够从指定的URL下载文件并保存到本地",
                       help="用户工具构建需求描述")
    parser.add_argument("-f", "--file", type=str, 
                       help="从文件中读取需求描述")
    parser.add_argument("-s", "--session_id", type=str, default=None,
                       help="可选的session_id，用于恢复之前的会话")
    args = parser.parse_args()
    
    print(f"🎯 [SYSTEM] 开始执行工具构建工作流...", flush=True)
    
    # 构建用户输入
    user_input = args.input
    
    # 如果指定了文件参数，读取文件内容并添加到user_input中
    if args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                file_content = f.read()
                user_input += f"\n\n从文件 {args.file} 读取的内容：\n{file_content}"
                print(f"📁 [SYSTEM] 已从文件 {args.file} 读取内容")
        except FileNotFoundError:
            print(f"❌ [SYSTEM] 文件 {args.file} 不存在")
            exit(1)
        except Exception as e:
            print(f"❌ [SYSTEM] 读取文件 {args.file} 失败: {e}")
            exit(1)
    
    print(f"📝 [SYSTEM] 用户需求: {user_input[:100]}...")
    if args.session_id:
        print(f"🔑 [SYSTEM] 使用指定的session_id: {args.session_id}")
    
    try:
        result = run_tool_build_workflow(user_input, session_id=args.session_id)
        print(f"\n{'='*80}")
        print(f"🎉 [SYSTEM] 工具构建工作流执行完成")
        print(f"🔑 Session ID: {result['session_id']}")
        print(f"📊 执行状态: {result['status']}")
        print(f"⏱️ 执行时间: {result['execution_time']:.2f}秒")
        print(f"{'='*80}")
    except Exception as e:
        print(f"❌ [SYSTEM] 工具构建工作流执行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
