#!/usr/bin/env python3
"""
Agent Update Workflow - 顺序调用版本

功能概述：
1. 接收用户请求与项目ID
2. 读取Base与Update工作流规则
3. 按顺序调用各个Agent完成更新流程
"""

from __future__ import annotations

import argparse
import json
import os
import time
import uuid
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from strands.session.file_session_manager import FileSessionManager
from strands.telemetry import StrandsTelemetry
from nexus_utils.agent_factory import create_agent_from_prompt_template
from nexus_utils.workflow_rule_extract import (
    get_base_rules,
    get_update_workflow_rules,
)
from nexus_utils.config_loader import ConfigLoader
from api.database.dynamodb_client import DynamoDBClient
from tools.system_tools.agent_build_workflow.stage_tracker import (
    mark_stage_running,
    mark_stage_completed,
    mark_stage_failed,
)

logger = logging.getLogger(__name__)
loader = ConfigLoader()

# 设置环境变量
os.environ.setdefault("BYPASS_TOOL_CONSENT", "true")
otel_endpoint = loader.get_with_env_override(
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


def _load_update_rules() -> str:
    """读取Base与Update工作流规则。"""
    base_rules = get_base_rules()
    update_rules = get_update_workflow_rules()
    return base_rules + "\n" + update_rules + "\n=====规则声明结束，请遵守以上规则=====\n"


def _load_project_config(project_id: str) -> Dict[str, Any]:
    """
    读取项目 project_config.json，并返回简化上下文。
    """
    project_root = Path("projects") / project_id
    config_path = project_root / "project_config.json"

    if config_path.exists():
        try:
            with config_path.open("r", encoding="utf-8") as fh:
                config_data = json.load(fh)
            return {
                "project_config_path": str(config_path),
                "project_config": config_data,
            }
        except json.JSONDecodeError as exc:
            return {
                "project_config_path": str(config_path),
                "error": f"project_config.json 解析失败: {exc}",
            }

    return {
        "project_config_path": str(config_path),
        "error": "未找到 project_config.json，后续Agent需自行确认项目配置。",
    }


def _create_agents_with_session(session_manager: Optional[FileSessionManager] = None):
    """创建带session管理的agents"""
    agent_kwargs = {**agent_params}
    if session_manager:
        agent_kwargs["session_manager"] = session_manager
    
    # 创建各个agent
    update_orchestrator = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/agent_update_workflow/update_orchestrator",
        **agent_kwargs
    )
    
    requirements_update = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/agent_update_workflow/requirements_update",
        **agent_kwargs
    )
    
    tool_update = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/agent_update_workflow/tool_update",
        **agent_kwargs
    )
    
    prompt_update = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/agent_update_workflow/prompt_update",
        **agent_kwargs
    )
    
    code_update = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/agent_update_workflow/code_update",
        **agent_kwargs
    )
    
    return {
        "update_orchestrator": update_orchestrator,
        "requirements_update": requirements_update,
        "tool_update": tool_update,
        "prompt_update": prompt_update,
        "code_update": code_update,
    }


def _validate_inputs(user_request: str, project_id: str) -> None:
    """验证输入参数"""
    missing: list[str] = []
    if not user_request or not user_request.strip():
        missing.append("user_request")
    if not project_id or not project_id.strip():
        missing.append("project_id")

    if missing:
        raise ValueError(
            "缺少必要参数: "
            + ", ".join(missing)
            + "。请在命令行提供 -i/--user_request 与 -j/--project_id。"
        )


def run_update_workflow(user_request: str, project_id: str, session_id: Optional[str] = None):
    """
    执行更新工作流
    
    Args:
        user_request: 用户更新请求内容
        project_id: 需要更新的项目ID
        session_id: 可选的session_id，如果未提供则自动生成
    """
    print(f"\n{'='*80}", flush=True)
    print(f"🎯 [UPDATE WORKFLOW] 开始更新工作流执行", flush=True)
    print(f"{'='*80}", flush=True)

    # 验证输入
    _validate_inputs(user_request, project_id)

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
    print(f"\n🏗️ [STEP 2] 创建更新工作流agents（带session管理）...", flush=True)
    agents = _create_agents_with_session(session_manager)
    
    # 第三步：加载规则和项目配置
    print(f"\n📘 [STEP 3] 加载规则和项目配置...", flush=True)
    rules = _load_update_rules()
    project_context = _load_project_config(project_id)
    project_context_json = json.dumps(project_context, ensure_ascii=False, indent=2)
    
    # 第四步：执行工作流
    print(f"\n{'='*80}", flush=True)
    print(f"⚡ [STEP 4] 执行更新工作流", flush=True)
    print(f"📝 用户请求: {user_request[:100]}...", flush=True)
    print(f"📁 项目ID: {project_id}", flush=True)
    print(f"🔑 Session ID: {session_id}", flush=True)
    print(f"{'='*80}", flush=True)
    
    try:
        print("🚀 开始执行更新工作流...", flush=True)
        print("📋 预计执行阶段:", flush=True)
        print("  1️⃣ update_orchestrator - 更新编排", flush=True)
        print("  2️⃣ requirements_update - 需求更新分析", flush=True)
        print("  3️⃣ tool_update - 工具代码更新", flush=True)
        print("  4️⃣ prompt_update - 提示词更新", flush=True)
        print("  5️⃣ code_update - Agent代码更新", flush=True)
        print(f"{'='*60}", flush=True)

        # 执行工作流并监控进度
        start_time = time.time()
        
        # 构建工作流输入
        workflow_input = (
            f"# Update Workflow Kickoff\n"
            f"## 必须严格遵守的规则:\n{rules}\n"
            f"## 项目信息\n"
            f"- project_id: {project_id}\n"
            f"- project_config_context:\n{project_context_json}\n"
            f"## 用户更新请求\n{user_request}\n"
            f"请按顺序完成更新流程，遵守以上规则。"
        )

        # 顺序调用各个agent
        base_context = workflow_input
        current_context = workflow_input
        execution_results = {}  # 存储AgentResult对象
        execution_order = []
        
        mode = "remote"
        db_client = DynamoDBClient()
        
        # 检查 AgentProjects 表是否存在
        if not db_client.table_exists('AgentProjects'):
            logger.warning(f"AgentProjects表不存在，当前模式为local")
            print(f"ℹ️ AgentProjects表不存在，当前模式为local", flush=True)
            mode = "local"
        else:
            logger.info(f"AgentProjects表存在，当前模式为remote")
            print(f"ℹ️ AgentProjects表存在，当前模式为remote", flush=True)

        # 1. Update Orchestrator
        print(f"\n{'='*60}")
        print(f"🔄 [1/5] 执行 update_orchestrator...")
        print(f"{'='*60}")
        try:
            mark_stage_running(project_id, 'update_orchestrator') if mode == "remote" else None
            orchestrator_result = agents["update_orchestrator"](current_context)
            execution_results["update_orchestrator"] = orchestrator_result
            execution_order.append("update_orchestrator")
            orchestrator_content = str(orchestrator_result.content) if hasattr(orchestrator_result, 'content') else str(orchestrator_result)
            current_context = base_context + "\n===\nUpdate Orchestrator Agent: " + orchestrator_content + "\n===\n"
            mark_stage_completed(project_id, 'update_orchestrator') if mode == "remote" else None
        except Exception as e:
            mark_stage_failed(project_id, 'update_orchestrator', str(e)) if mode == "remote" else None
            raise

        # 2. Requirements Update
        print(f"\n{'='*60}")
        print(f"🔄 [2/5] 执行 requirements_update...")
        print(f"{'='*60}")
        try:
            mark_stage_running(project_id, 'requirements_update') if mode == "remote" else None
            requirements_result = agents["requirements_update"](current_context)
            execution_results["requirements_update"] = requirements_result
            execution_order.append("requirements_update")
            requirements_content = str(requirements_result.content) if hasattr(requirements_result, 'content') else str(requirements_result)
            current_context = base_context + "\n===\nRequirements Update Agent: " + requirements_content + "\n===\n"
            mark_stage_completed(project_id, 'requirements_update') if mode == "remote" else None
        except Exception as e:
            mark_stage_failed(project_id, 'requirements_update', str(e)) if mode == "remote" else None
            raise
        
        # 3. Tool Update
        print(f"\n{'='*60}")
        print(f"🔄 [3/5] 执行 tool_update...")
        print(f"{'='*60}")
        try:
            mark_stage_running(project_id, 'tool_update') if mode == "remote" else None
            tool_result = agents["tool_update"](current_context)
            execution_results["tool_update"] = tool_result
            execution_order.append("tool_update")
            tool_content = str(tool_result.content) if hasattr(tool_result, 'content') else str(tool_result)
            current_context = current_context + "\n===\nTool Update Agent: " + tool_content + "\n===\n"
            mark_stage_completed(project_id, 'tool_update') if mode == "remote" else None
        except Exception as e:
            mark_stage_failed(project_id, 'tool_update', str(e)) if mode == "remote" else None
            raise
        
        # 4. Prompt Update
        print(f"\n{'='*60}")
        print(f"🔄 [4/5] 执行 prompt_update...")
        print(f"{'='*60}")
        try:
            mark_stage_running(project_id, 'prompt_update') if mode == "remote" else None
            prompt_result = agents["prompt_update"](current_context)
            execution_results["prompt_update"] = prompt_result
            execution_order.append("prompt_update")
            prompt_content = str(prompt_result.content) if hasattr(prompt_result, 'content') else str(prompt_result)
            current_context = current_context + "\n===\nPrompt Update Agent: " + prompt_content + "\n===\n"
            mark_stage_completed(project_id, 'prompt_update') if mode == "remote" else None
        except Exception as e:
            mark_stage_failed(project_id, 'prompt_update', str(e)) if mode == "remote" else None
            raise
        
        # 5. Code Update
        print(f"\n{'='*60}")
        print(f"🔄 [5/5] 执行 code_update...")
        print(f"{'='*60}")
        try:
            mark_stage_running(project_id, 'code_update') if mode == "remote" else None
            code_result = agents["code_update"](current_context)
            execution_results["code_update"] = code_result
            execution_order.append("code_update")
            code_content = str(code_result.content) if hasattr(code_result, 'content') else str(code_result)
            current_context = current_context + "\n===\nCode Update Agent: " + code_content + "\n===\n"
            mark_stage_completed(project_id, 'code_update') if mode == "remote" else None
        except Exception as e:
            mark_stage_failed(project_id, 'code_update', str(e)) if mode == "remote" else None
            raise

        end_time = time.time()
        execution_duration = end_time - start_time
        print(f"\n⏱️ 实际执行时间: {execution_duration:.2f}秒")

        print("✅ 更新工作流执行完成")

        # 更新项目状态为 COMPLETED
        if mode == "remote":
            from api.models.schemas import ProjectStatus
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            db_client.update_project_status(
                project_id,
                ProjectStatus.COMPLETED,
                completed_at=now
            )
            print(f"✅ 项目状态已更新为 COMPLETED")

        # 生成工作流总结报告
        print(f"\n{'='*80}")
        print(f"📊 [RESULTS] 更新工作流执行结果")
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
            intent_analysis=None,  # 更新工作流不需要意图分析
            default_project_root_path=f'./projects/{project_id}'
        )
        if report_path:
            print(f"📄 报告路径: {report_path}")
        print(f"{'='*80}")

        return {
            "session_id": session_id,
            "project_id": project_id,
            "execution_results": execution_results,
            "execution_order": execution_order,
            "execution_time": execution_duration,
            "status": "COMPLETED",
            "report_path": report_path
        }
    except Exception as e:
        print(f"❌ 更新工作流执行失败: {e}")
        import traceback
        traceback.print_exc()
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent Update Workflow - 顺序调用版本")
    parser.add_argument("-i", "--user_request", type=str, help="用户更新请求内容")
    parser.add_argument("-j", "--project_id", type=str, help="需要更新的项目ID")
    parser.add_argument("-f", "--file", type=str, help="从文件中读取更新请求内容")
    parser.add_argument("-s", "--session_id", type=str, default=None, help="可选的session_id")
    args = parser.parse_args()

    print(f"🎯 [SYSTEM] 开始执行Agent更新工作流...", flush=True)
    
    # 构建用户请求
    user_request = args.user_request or ""
    
    # 如果指定了文件参数，读取文件内容并添加到user_request中
    if args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                file_content = f.read()
                user_request += f"\n\n从文件 {args.file} 读取的内容：\n{file_content}"
                print(f"📁 [SYSTEM] 已从文件 {args.file} 读取内容")
        except FileNotFoundError:
            print(f"❌ [SYSTEM] 文件 {args.file} 不存在")
            exit(1)
        except Exception as e:
            print(f"❌ [SYSTEM] 读取文件 {args.file} 失败: {e}")
            exit(1)

    try:
        result = run_update_workflow(
            user_request=user_request,
            project_id=args.project_id or "",
            session_id=args.session_id
        )
        print(f"\n{'='*80}")
        print(f"🎉 [SYSTEM] 更新工作流执行完成")
        print(f"🔑 Session ID: {result['session_id']}")
        print(f"📁 Project ID: {result['project_id']}")
        print(f"📊 执行状态: {result['status']}")
        print(f"⏱️ 执行时间: {result['execution_time']:.2f}秒")
        print(f"{'='*80}")
    except ValueError as exc:
        print(f"❌ 参数校验失败: {exc}")
        print("✅ 示例: python agent_update_workflow.py -i \"更新需求\" -j project_x")
    except Exception as e:
        print(f"❌ [SYSTEM] 更新工作流执行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
