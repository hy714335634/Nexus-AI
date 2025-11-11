#!/usr/bin/env python3
"""
面向 Agent Update Workflow 的版本管理工具。

核心能力：
1. 初始化项目更新版本目录与 status.yaml 中的版本记录
2. 记录各阶段文档输出与工件路径
3. 将内容写入 projects/<project_name>/<version_id>/ 下的受控文件
4. 维护更新版本的变更记录并在流程结束时收尾
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from strands import tool

BASE_PROJECT_DIR = Path("projects")
ALLOWED_STAGE_NAMES = [
    "orchestrator",
    "requirements_analysis",
    "tool_update",
    "prompt_update",
    "code_update",
]

STAGE_ALIAS: Dict[str, str] = {
    "requirements_update": "requirements_analysis",
    "requirements_update_stage": "requirements_analysis",
    "tool_update_stage": "tool_update",
    "prompt_update_stage": "prompt_update",
    "code_update_stage": "code_update",
    "orchestrator_stage": "orchestrator",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_join(base: Path, *parts: str) -> Path:
    candidate = base.joinpath(*parts).resolve()
    if not str(candidate).startswith(str(base.resolve())):
        raise ValueError("检测到越权访问: 目标路径不在允许目录内")
    return candidate


def _load_status(project_name: str) -> Dict[str, Any]:
    status_path = BASE_PROJECT_DIR / project_name / "status.yaml"
    if not status_path.exists():
        raise FileNotFoundError(f"未找到项目 {project_name} 的 status.yaml")
    with status_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return data


def _write_status(project_name: str, status_data: Dict[str, Any]) -> None:
    status_path = BASE_PROJECT_DIR / project_name / "status.yaml"
    with status_path.open("w", encoding="utf-8") as fh:
        yaml.dump(status_data, fh, allow_unicode=True, indent=2, sort_keys=False)


def _ensure_project_exists(project_name: str) -> None:
    project_root = BASE_PROJECT_DIR / project_name
    if not project_root.exists():
        raise FileNotFoundError(f"项目 {project_name} 不存在: {project_root}")


def _normalize_stage_name(stage_name: str) -> str:
    candidate = stage_name.strip().lower()
    normalized = STAGE_ALIAS.get(candidate, candidate)
    if normalized not in ALLOWED_STAGE_NAMES:
        raise ValueError(
            f"阶段 {stage_name} 不被允许，必须在 {ALLOWED_STAGE_NAMES + list(STAGE_ALIAS.keys())} 中选择"
        )
    return normalized


def _resolve_agent_entry(
    project_entry: Dict[str, Any],
    agent_name: Optional[str],
) -> Tuple[Dict[str, Any], str]:
    agents = project_entry.get("agents", [])
    if not isinstance(agents, list) or not agents:
        raise ValueError("status.yaml 中缺少 agents 列表，无法更新状态")

    if agent_name:
        for agent in agents:
            if agent.get("name") == agent_name:
                return agent, agent_name
        raise ValueError(f"在 status.yaml 中未找到 Agent {agent_name} 的记录")

    if len(agents) == 1:
        resolved_name = agents[0].get("name", "")
        return agents[0], resolved_name

    raise ValueError(
        "请提供 agent_name，以便在 status.yaml 中记录 update 版本进度"
    )


def _to_relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()

def _update_status_update_versions(
    status_data: Dict[str, Any],
    project_entry: Dict[str, Any],
    agent_entry: Dict[str, Any],
    agent_name: str,
    version_id: str,
    stage_payload: Dict[str, Any],
) -> None:
    update_versions = agent_entry.setdefault("update_versions", [])
    version_record = None
    for item in update_versions:
        if item.get("version_id") == version_id:
            version_record = item
            break
    if version_record is None:
        version_record = {
            "version_id": version_id,
            "created_at": _utc_now(),
            "stages": [],
        }
        update_versions.append(version_record)

    stages = version_record.setdefault("stages", [])
    stage_entry = None
    for entry in stages:
        if entry.get("stage") == stage_payload["stage"]:
            stage_entry = entry
            break
    if stage_entry is None:
        stage_entry = {}
        stages.append(stage_entry)

    stage_entry.update(stage_payload)
    agent_entry["last_updated"] = _utc_now()
    project_entry["last_updated"] = _utc_now()


def _get_project_entry(status_data: Dict[str, Any], project_name: str) -> Dict[str, Any]:
    project_list = status_data.get("project_info", [])
    if not isinstance(project_list, list):
        raise ValueError("status.yaml 中的 project_info 结构异常")
    for entry in project_list:
        if entry.get("name") == project_name:
            return entry
    raise ValueError(f"在 status.yaml 中未找到项目 {project_name} 的记录")


def _generate_version_id(project_entry: Dict[str, Any], prefix: str = "v") -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    candidate = f"{prefix}{timestamp}"
    existing = {
        ver.get("version_id")
        for ver in project_entry.get("versions", [])
        if isinstance(ver, dict)
    }
    suffix = 1
    unique_id = candidate
    while unique_id in existing:
        suffix += 1
        unique_id = f"{candidate}_{suffix}"
    return unique_id


def _initial_stage_state(version_id: str) -> List[Dict[str, Any]]:
    created_at = _utc_now()
    return [
        {
            "name": stage,
            "status": "pending",
            "doc_path": "",
            "summary": "",
            "artifacts": [],
            "updated_at": created_at,
        }
        for stage in ALLOWED_STAGE_NAMES
    ]


def _ensure_stage_entry(version_entry: Dict[str, Any], stage_name: str) -> Dict[str, Any]:
    stages = version_entry.setdefault("stages", [])
    for stage in stages:
        if stage.get("name") == stage_name:
            return stage
    new_stage = {
        "name": stage_name,
        "status": "pending",
        "doc_path": "",
        "summary": "",
        "artifacts": [],
        "updated_at": _utc_now(),
    }
    stages.append(new_stage)
    return new_stage


def _find_version_entry(project_entry: Dict[str, Any], version_id: str) -> Dict[str, Any]:
    for entry in project_entry.get("versions", []):
        if entry.get("version_id") == version_id:
            return entry
    raise ValueError(f"未在项目记录中找到版本 {version_id}")


@tool
def initialize_update_version(
    project_name: str,
    user_request: str = "",
    version_prefix: str = "v",
) -> str:
    """
    初始化更新版本目录与 status.yaml 记录。

    Args:
        project_name: 项目名称
        user_request: 用户更新请求概述
        version_prefix: 版本号前缀，默认 v

    Returns:
        JSON 字符串，包含 version_id、version_path、status_file 等信息
    """
    _ensure_project_exists(project_name)
    status_data = _load_status(project_name)
    project_entry = _get_project_entry(status_data, project_name)

    version_id = _generate_version_id(project_entry, prefix=version_prefix)
    version_path = _safe_join(BASE_PROJECT_DIR / project_name, version_id)
    version_path.mkdir(parents=True, exist_ok=True)

    created_at = _utc_now()
    version_entry = {
        "version_id": version_id,
        "created_at": created_at,
        "created_by": "update_orchestrator",
        "status": "in_progress",
        "user_request": user_request or "",
        "stages": _initial_stage_state(version_id),
        "artifacts": [],
        "summary": "",
        "change_log": [],
    }

    versions = project_entry.setdefault("versions", [])
    versions.append(version_entry)
    project_entry["current_version_id"] = version_id
    project_entry["last_updated"] = created_at

    _write_status(project_name, status_data)

    result = {
        "result": "success",
        "project_name": project_name,
        "version_id": version_id,
        "version_path": str(version_path),
        "status_file": str(BASE_PROJECT_DIR / project_name / "status.yaml"),
        "created_at": created_at,
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def register_version_stage(
    project_name: str,
    version_id: str,
    stage_name: str,
    status: str,
    agent_name: str = "",
    doc_path: str = "",
    summary: str = "",
    artifacts: Optional[List[str]] = None,
) -> str:
    """
    更新 status.yaml 中版本的阶段状态。

    Args:
        project_name: 项目名称
        version_id: 正在更新的版本号
        stage_name: 阶段名称（必须在允许列表中）
        status: 阶段状态，例如 pending/in_progress/completed/blocked
        doc_path: 阶段输出的相对路径
        summary: 阶段总结
        artifacts: 产生的制品相对路径列表
    """
    normalized_stage = _normalize_stage_name(stage_name)

    _ensure_project_exists(project_name)
    status_data = _load_status(project_name)
    project_entry = _get_project_entry(status_data, project_name)
    version_entry = _find_version_entry(project_entry, version_id)
    agent_entry, resolved_agent = _resolve_agent_entry(project_entry, agent_name or "")

    stage_entry = _ensure_stage_entry(version_entry, normalized_stage)
    stage_entry.update(
        {
            "status": status,
            "doc_path": doc_path or stage_entry.get("doc_path", ""),
            "summary": summary or stage_entry.get("summary", ""),
            "updated_at": _utc_now(),
        }
    )
    if artifacts is not None:
        stage_entry["artifacts"] = artifacts
    version_entry["last_stage_updated"] = normalized_stage
    project_entry["last_updated"] = _utc_now()

    stage_payload = {
        "stage": normalized_stage,
        "status": status,
        "doc_path": stage_entry.get("doc_path", ""),
        "summary": stage_entry.get("summary", ""),
        "artifacts": stage_entry.get("artifacts", []),
        "updated_at": stage_entry.get("updated_at"),
    }
    _update_status_update_versions(
        status_data,
        project_entry,
        agent_entry,
        resolved_agent,
        version_id,
        stage_payload,
    )

    _write_status(project_name, status_data)

    return json.dumps(
        {
            "result": "success",
            "project_name": project_name,
            "version_id": version_id,
            "stage": normalized_stage,
            "status": status,
            "doc_path": stage_entry.get("doc_path", ""),
            "artifacts": stage_entry.get("artifacts", []),
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
def write_version_file(
    project_name: str,
    version_id: str,
    relative_path: str,
    content: str,
) -> str:
    """
    将内容写入 projects/<project_name>/<version_id>/ 下指定相对路径。

    Args:
        project_name: 项目名称
        version_id: 版本ID，需已初始化
        relative_path: 相对于版本目录的文件路径，例如 requirements_analysis.json
        content: 要写入的文本内容
    """
    if not relative_path or relative_path.strip() == "":
        raise ValueError("relative_path 不能为空")

    _ensure_project_exists(project_name)
    version_root = _safe_join(BASE_PROJECT_DIR / project_name, version_id)
    if not version_root.exists():
        raise FileNotFoundError(f"版本目录不存在，请先初始化: {version_root}")

    target_path = _safe_join(version_root, relative_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with target_path.open("w", encoding="utf-8") as fh:
        fh.write(content)

    normalized_path = _to_relative_path(target_path)

    return json.dumps(
        {
            "result": "success",
            "project_name": project_name,
            "version_id": version_id,
            "file_path": normalized_path,
            "bytes_written": len(content.encode("utf-8")),
            "updated_at": _utc_now(),
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
def write_stage_document(
    project_name: str,
    version_id: str,
    stage_name: str,
    content: str,
    agent_name: str = "",
    filename: Optional[str] = None,
) -> str:
    """
    将阶段结构化内容写入版本目录，并返回文件路径。

    Args:
        project_name: 项目名称
        version_id: 版本ID
        stage_name: 阶段名称（可使用别名）
        content: JSON 字符串或可序列化的文本
        agent_name: 负责的Agent名称（用于记录status）
        filename: 自定义文件名，默认 stage_name.json
    """
    normalized_stage = _normalize_stage_name(stage_name)
    try:
        parsed = json.loads(content)
        serialized = json.dumps(parsed, ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        serialized = content

    file_name = filename or f"{normalized_stage}.json"
    result = json.loads(
        write_version_file(
            project_name, version_id, file_name, serialized
        )
    )
    doc_path = result["file_path"]

    register_version_stage(
        project_name=project_name,
        version_id=version_id,
        stage_name=normalized_stage,
        status="in_progress",
        agent_name=agent_name,
        doc_path=doc_path,
    )

    return json.dumps(
        {
            "result": "success",
            "project_name": project_name,
            "version_id": version_id,
            "stage": normalized_stage,
            "file_path": doc_path,
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
def get_stage_document(
    project_name: str,
    version_id: str,
    stage_name: str,
    filename: Optional[str] = None,
) -> str:
    """
    读取版本目录中指定阶段的JSON文件。
    """
    normalized_stage = _normalize_stage_name(stage_name)
    _ensure_project_exists(project_name)
    version_root = _safe_join(BASE_PROJECT_DIR / project_name, version_id)
    if not version_root.exists():
        raise FileNotFoundError(f"版本目录不存在: {version_root}")

    candidate = filename or f"{normalized_stage}.json"
    target_path = _safe_join(version_root, candidate)
    if not target_path.exists():
        raise FileNotFoundError(f"未找到阶段文件: {target_path}")

    with target_path.open("r", encoding="utf-8") as fh:
        content = fh.read()

    return json.dumps(
        {
            "result": "success",
            "project_name": project_name,
            "version_id": version_id,
            "stage": normalized_stage,
            "file_path": _to_relative_path(target_path),
            "content": content,
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
def append_change_log(
    project_name: str,
    version_id: str,
    title: str,
    description: str,
    stage: Optional[str] = None,
) -> str:
    """
    为指定版本记录变更条目，并写入 change_log.yaml。
    """
    if not title or not description:
        raise ValueError("title 与 description 均不能为空")

    _ensure_project_exists(project_name)
    status_data = _load_status(project_name)
    project_entry = _get_project_entry(status_data, project_name)
    version_entry = _find_version_entry(project_entry, version_id)

    log_entry = {
        "title": title,
        "description": description,
        "stage": stage,
        "created_at": _utc_now(),
    }
    change_log = version_entry.setdefault("change_log", [])
    change_log.append(log_entry)
    project_entry["last_updated"] = _utc_now()

    _write_status(project_name, status_data)

    # 同步写入 change_log.yaml
    version_root = _safe_join(BASE_PROJECT_DIR / project_name, version_id)
    change_log_path = version_root / "change_log.yaml"
    with change_log_path.open("w", encoding="utf-8") as fh:
        yaml.dump(change_log, fh, allow_unicode=True, indent=2, sort_keys=False)

    return json.dumps(
        {
            "result": "success",
            "project_name": project_name,
            "version_id": version_id,
            "log_entry": log_entry,
            "change_log_file": str(change_log_path),
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
def finalize_update_version(
    project_name: str,
    version_id: str,
    summary: str,
    status: str = "completed",
    artifacts: Optional[List[str]] = None,
) -> str:
    """
    在更新流程结束时，更新版本状态并写入 summary.yaml。
    """
    if status not in {"completed", "failed", "cancelled"}:
        raise ValueError("status 仅支持 completed/failed/cancelled")

    _ensure_project_exists(project_name)
    status_data = _load_status(project_name)
    project_entry = _get_project_entry(status_data, project_name)
    version_entry = _find_version_entry(project_entry, version_id)

    version_entry["status"] = status
    version_entry["summary"] = summary
    version_entry["closed_at"] = _utc_now()
    if artifacts is not None:
        version_entry["artifacts"] = artifacts
    project_entry["last_updated"] = _utc_now()

    _write_status(project_name, status_data)

    version_root = _safe_join(BASE_PROJECT_DIR / project_name, version_id)
    summary_path = version_root / "summary.yaml"
    summary_payload = {
        "project_name": project_name,
        "version_id": version_id,
        "status": status,
        "summary": summary,
        "artifacts": artifacts or [],
        "updated_at": _utc_now(),
    }
    with summary_path.open("w", encoding="utf-8") as fh:
        yaml.dump(summary_payload, fh, allow_unicode=True, indent=2, sort_keys=False)

    return json.dumps(
        {
            "result": "success",
            "project_name": project_name,
            "version_id": version_id,
            "status": status,
            "summary_file": str(summary_path),
        },
        ensure_ascii=False,
        indent=2,
    )

