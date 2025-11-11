#!/usr/bin/env python3
"""
Agent Update Workflow 初始版本

功能概述：
1. 接收用户请求与项目ID
2. 读取Base与Update工作流规则
3. 初始化Strands Graph以及后续可扩展的Agent编排能力
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict

from strands.multiagent import GraphBuilder

from strands.telemetry import StrandsTelemetry
from nexus_utils.workflow_rule_extract import (
    get_base_rules,
    get_update_workflow_rules,
)

from agents.system_agents.agent_update_workflow.update_orchestrator_agent import (
    update_orchestrator,
)
from agents.system_agents.agent_update_workflow.requirements_update_agent import (
    requirements_update_agent,
)
from agents.system_agents.agent_update_workflow.tool_update_agent import (
    tool_update_agent,
)
from agents.system_agents.agent_update_workflow.prompt_update_agent import (
    prompt_update_agent,
)
from agents.system_agents.agent_update_workflow.code_update_agent import (
    code_update_agent,
)
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()


def _prepare_environment() -> None:
    """设置工作流运行所需环境变量。"""
    os.environ.setdefault("BYPASS_TOOL_CONSENT", "true")
    os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")


def _load_update_rules() -> Dict[str, str]:
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

def initialize_update_workflow(user_request: str, project_id: str) -> GraphBuilder:
    """
    初始化Update Workflow编排骨架。

    Args:
        user_request: 用户最新输入内容
        project_id: 需要更新的项目ID

    Returns:
        GraphBuilder: 用于后续构建Strands工作流的图构造器
    """
    _prepare_environment()
    rules = _load_update_rules()

    print("🎯 初始化Update Workflow")
    print(f"📝 用户请求: {user_request}")
    print(f"📁 项目ID: {project_id}")
    print("\n📘 规则:" + rules)

    builder = GraphBuilder()
    builder.add_node(update_orchestrator, "update_orchestrator")
    builder.add_node(requirements_update_agent, "requirements_update")
    builder.add_node(tool_update_agent, "tool_update")
    builder.add_node(prompt_update_agent, "prompt_update")
    builder.add_node(code_update_agent, "code_update")

    builder.add_edge("update_orchestrator", "requirements_update")
    builder.add_edge("requirements_update", "tool_update")
    builder.add_edge("tool_update", "prompt_update")
    builder.add_edge("prompt_update", "code_update")

    return builder


def _validate_inputs(user_request: str, project_id: str) -> None:
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


def run_update_workflow(user_request: str, project_id: str):
    """
    构建并执行更新工作流。
    """
    _validate_inputs(user_request, project_id)

    builder = initialize_update_workflow(user_request, project_id)
    workflow = builder.build()

    project_context = _load_project_config(project_id)
    project_context_json = json.dumps(project_context, ensure_ascii=False, indent=2)

    kickoff_payload = (
        f"# Update Workflow Kickoff\n"
        f"- project_id: {project_id}\n"
        f"- user_request: {user_request}\n"
        f"- project_config_context:\n{project_context_json}\n"
        "请按顺序完成更新流程，保持输出为JSON。"
    )

    result = workflow(kickoff_payload)
    print("\n✅ Update Workflow 执行完成")
    print(f"📊 节点总数: {result.total_nodes}")
    print(f"✅ 完成节点: {result.completed_nodes}")
    print(f"❌ 失败节点: {result.failed_nodes}")
    print(f"⏱️ 执行耗时: {result.execution_time}ms")
    for node in result.execution_order:
        print(f"➡️ 执行节点: {node.node_id}")

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent Update Workflow 初始化脚本")
    parser.add_argument("-i", "--user_request", type=str, help="用户最新请求内容")
    parser.add_argument("-j", "--project_id", type=str, help="需要更新的项目ID")
    args = parser.parse_args()

    try:
        result = run_update_workflow(args.user_request or "", args.project_id or "")
    except ValueError as exc:
        print(f"❌ 参数校验失败: {exc}")
        print("✅ 示例: python agent_update_workflow.py -i \"更新需求\" -j project_x")
        return

    print("\n🎯 最终状态:", result.status)


if __name__ == "__main__":
    main()
