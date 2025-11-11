#!/usr/bin/env python3
"""
提示词版本管理工具，面向 Agent Update Workflow 提供以下能力：

1. 读取指定项目 Agent 的提示词版本信息
2. 在原有 YAML 文件中新增版本配置，禁止修改其他版本内容
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import yaml
from strands import tool

PROMPT_ROOT = Path("prompts") / "generated_agents_prompts"


class _LiteralDumper(yaml.SafeDumper):
    """
    自定义YAML Dumper：字符串包含换行时使用'|'保持多行格式。
    """


def _str_representer(dumper: yaml.SafeDumper, data: str):
    style = "|" if "\n" in data else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


_LiteralDumper.add_representer(str, _str_representer)


def _prompt_path(project_name: str, agent_name: str) -> Path:
    if not project_name or "/" in project_name or "\\" in project_name or ".." in project_name:
        raise ValueError("project_name 不合法")
    if not agent_name or "/" in agent_name or "\\" in agent_name or ".." in agent_name:
        raise ValueError("agent_name 不合法")
    base_dir = PROMPT_ROOT / project_name
    primary = base_dir / f"{agent_name}.yaml"
    if primary.exists():
        return primary

    suffix_candidates = [
        base_dir / f"{agent_name}_prompt.yaml",
        base_dir / f"{agent_name}_agent.yaml",
    ]
    for candidate in suffix_candidates:
        if candidate.exists():
            return candidate

    for candidate in sorted(base_dir.glob(f"{agent_name}*.yaml")):
        return candidate

    return primary


def _load_prompt(project_name: str, agent_name: str) -> Dict[str, Any]:
    prompt_file = _prompt_path(project_name, agent_name)
    if not prompt_file.exists():
        raise FileNotFoundError(f"未找到提示词文件: {prompt_file}")
    with prompt_file.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return data


def _write_prompt(project_name: str, agent_name: str, data: Dict[str, Any]) -> None:
    prompt_file = _prompt_path(project_name, agent_name)
    prompt_file.parent.mkdir(parents=True, exist_ok=True)
    with prompt_file.open("w", encoding="utf-8") as fh:
        yaml.dump(
            data,
            fh,
            allow_unicode=True,
            indent=2,
            sort_keys=False,
            Dumper=_LiteralDumper,
        )


@tool
def read_prompt_versions(project_name: str, agent_name: str) -> str:
    """
    读取指定 Agent 的提示词版本信息。
    """
    prompt_data = _load_prompt(project_name, agent_name)
    versions = prompt_data.get("agent", {}).get("versions", [])
    result = {
        "project_name": project_name,
        "agent_name": agent_name,
        "version_count": len(versions),
        "versions": versions,
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def append_prompt_version(
    project_name: str,
    agent_name: str,
    version_id: str,
    version_payload: str,
) -> str:
    """
    在提示词 YAML 中追加新的版本节点。

    Args:
        project_name: 项目名称
        agent_name: Agent 名称
        version_id: 新的版本号，将写入 versions[].version
        version_payload: JSON 字符串，描述版本字段（除 version 外的其他字段）
    """
    if not version_id:
        raise ValueError("version_id 不能为空")

    try:
        payload = json.loads(version_payload) if version_payload else {}
    except json.JSONDecodeError as exc:
        raise ValueError("version_payload 需要为合法 JSON 字符串") from exc

    prompt_data = _load_prompt(project_name, agent_name)
    agent_block = prompt_data.setdefault("agent", {})
    versions = agent_block.setdefault("versions", [])

    for ver in versions:
        if ver.get("version") == version_id:
            raise ValueError(f"提示词版本 {version_id} 已存在，禁止覆盖")

    new_entry: Dict[str, Any] = {"version": version_id}
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key == "version":
                continue
            new_entry[key] = value

    versions.append(new_entry)
    _write_prompt(project_name, agent_name, prompt_data)

    result = {
        "project_name": project_name,
        "agent_name": agent_name,
        "version_id": version_id,
        "prompt_file": str(_prompt_path(project_name, agent_name)),
        "total_versions": len(versions),
    }
    return json.dumps(result, ensure_ascii=False, indent=2)

