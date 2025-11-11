from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml

from nexus_utils.config_loader import get_config


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class WorkflowRuleError(Exception):
    """自定义异常：用于工作流规则提取相关错误。"""


@lru_cache(maxsize=1)
def _load_base_rule() -> Dict[str, Any]:
    config_loader = get_config()
    nexus_ai_config: Dict[str, Any] = config_loader.get("nexus_ai", {})

    base_rule_path = nexus_ai_config.get("base_rule_path")
    if not base_rule_path:
        raise WorkflowRuleError("默认配置缺少`base_rule_path`")

    base_rule_version = nexus_ai_config.get("base_rule_version", "latest")

    rule_file_path = (PROJECT_ROOT / base_rule_path).resolve()
    if not rule_file_path.exists():
        raise WorkflowRuleError(f"未找到Base规则文件: {rule_file_path}")

    with rule_file_path.open("r", encoding="utf-8") as f:
        rule_data = yaml.safe_load(f) or {}

    workflows = rule_data.get("workflows")
    if not isinstance(workflows, dict):
        raise WorkflowRuleError("规则文件缺少`workflows`配置或格式不正确")

    return {
        "version": base_rule_version,
        "workflows": workflows,
    }


def _merge_attributes(attributes: Dict[str, Any]) -> str:
    if not attributes:
        return ""

    merged_segments = []
    for value in attributes.values():
        if isinstance(value, str):
            segment = value.strip()
            if segment:
                merged_segments.append(segment)
    return "\n".join(merged_segments)


def _get_workflow_rules(workflow_key: str) -> str:
    base_rule = _load_base_rule()
    version = base_rule["version"]
    workflows = base_rule["workflows"]

    workflow_entries = workflows.get(workflow_key)
    if not isinstance(workflow_entries, list):
        raise WorkflowRuleError(f"未找到工作流 `{workflow_key}` 的规则定义")

    matched_entry = None
    for entry in workflow_entries:
        if entry.get("version") == version:
            matched_entry = entry
            break

    if matched_entry is None:
        # 如果未找到指定版本，回退到第一个配置
        matched_entry = workflow_entries[0] if workflow_entries else None

    if not matched_entry:
        raise WorkflowRuleError(f"工作流 `{workflow_key}` 未定义任何版本规则")

    attributes = matched_entry.get("attributes")
    if not isinstance(attributes, dict):
        raise WorkflowRuleError(f"工作流 `{workflow_key}` 的属性配置缺失或格式错误")

    return _merge_attributes(attributes)


def get_base_rules() -> str:
    """返回base工作流指定版本下所有属性规则的合并内容。"""
    return _get_workflow_rules("base")


def get_build_workflow_rules() -> str:
    """返回build工作流指定版本下所有属性规则的合并内容。"""
    return _get_workflow_rules("build")


def get_update_workflow_rules() -> str:
    """返回update工作流指定版本下所有属性规则的合并内容。"""
    return _get_workflow_rules("update")


def _run_cli() -> None:
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Nexus-AI工作流规则提取测试入口"
    )
    parser.add_argument(
        "workflow",
        nargs="?",
        choices=["base", "build", "update"],
        default="base",
        help="要查看的工作流规则（默认: base）",
    )
    args = parser.parse_args()

    extractor_map = {
        "base": get_base_rules,
        "build": get_build_workflow_rules,
        "update": get_update_workflow_rules,
    }

    try:
        content = extractor_map[args.workflow]()
    except WorkflowRuleError as exc:
        print(f"❌ 提取失败: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"✅ {args.workflow} workflow rules:\n")
    print(content)


if __name__ == "__main__":
    _run_cli()
