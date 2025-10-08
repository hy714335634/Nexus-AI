"""Stateless helpers for tracking build stage progress in DynamoDB."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import re

from api.database.dynamodb_client import DynamoDBClient
from api.models.schemas import ProjectStatus

logger = logging.getLogger(__name__)

# Ordered list of workflow stages with display names.
STAGE_SEQUENCE: List[Tuple[str, str]] = [
    ("orchestrator", "工作流编排"),
    ("requirements_analyzer", "需求分析"),
    ("system_architect", "系统架构设计"),
    ("agent_designer", "Agent设计"),
    ("prompt_engineer", "提示词工程"),
    ("tools_developer", "工具开发"),
    ("agent_code_developer", "代码开发"),
    ("agent_developer_manager", "开发管理"),
    ("agent_deployer", "Agent部署"),
]

_JOB_ID_PATTERN = re.compile(r"^job_[0-9a-f]{8,}$", re.IGNORECASE)


def initialize_project_record(
    project_id: str,
    *,
    requirement: str = "",
    user_id: Optional[str] = None,
    user_name: Optional[str] = None,
    project_name: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> None:
    """Create or overwrite the project record with a fresh stage snapshot."""

    db_client = DynamoDBClient()
    now = _now()

    snapshot = _default_snapshot()

    normalized_tags = [tag.strip() for tag in (tags or []) if isinstance(tag, str) and tag.strip()]
    resolved_project_name = _resolve_project_name(project_name, requirement, project_id)

    item = {
        "project_id": project_id,
        "project_name": resolved_project_name,
        "requirement": requirement,
        "user_id": user_id,
        "user_name": user_name,
        "tags": normalized_tags or None,
        "status": ProjectStatus.BUILDING.value,
        "progress_percentage": Decimal("0"),
        "created_at": now,
        "updated_at": now,
        "stages_snapshot": snapshot,
    }

    db_client.projects_table.put_item(Item=_convert(item))
    logger.info("Initialized project record %s with %d stages", project_id, len(STAGE_SEQUENCE))


def mark_stage_running(project_id: str, stage_name: str) -> None:
    """Mark the given stage as running."""

    snapshot = _load_snapshot(project_id)
    stage = _ensure_stage_entry(snapshot, stage_name)
    if stage is None:
        logger.warning("mark_stage_running: stage %s not found for project %s", stage_name, project_id)
        return

    stage["status"] = "running"
    stage.setdefault("started_at", _now())
    stage.pop("completed_at", None)
    stage.pop("error", None)

    _write_snapshot(project_id, snapshot)
    logger.debug("Project %s stage %s set to running", project_id, stage_name)


def mark_stage_completed(project_id: str, stage_name: str) -> None:
    """Mark the given stage as completed and update project progress."""

    snapshot = _load_snapshot(project_id)
    stage = _ensure_stage_entry(snapshot, stage_name)
    if stage is None:
        logger.warning("mark_stage_completed: stage %s not found for project %s", stage_name, project_id)
        return

    stage.setdefault("started_at", _now())
    stage["status"] = "completed"
    stage["completed_at"] = _now()
    stage.pop("error", None)

    project_status = None
    if _is_project_completed(snapshot):
        project_status = ProjectStatus.COMPLETED.value

    _write_snapshot(project_id, snapshot, project_status=project_status)
    logger.info("Project %s stage %s completed", project_id, stage_name)


def mark_stage_failed(project_id: str, stage_name: str, error_message: str) -> None:
    """Mark the given stage (and project) as failed."""

    snapshot = _load_snapshot(project_id)
    stage = _ensure_stage_entry(snapshot, stage_name)
    if stage is not None:
        stage.setdefault("started_at", _now())
        stage["status"] = "failed"
        stage["completed_at"] = _now()
        stage["error"] = error_message

    _write_snapshot(
        project_id,
        snapshot,
        project_status=ProjectStatus.FAILED.value,
        error_info={"error": error_message},
    )
    logger.error("Project %s stage %s failed: %s", project_id, stage_name, error_message)


def mark_project_completed(project_id: str) -> None:
    """Force the project to completed, ensuring all stages are marked complete."""

    snapshot = _load_snapshot(project_id)
    for stage in snapshot.get("stages", []):
        if stage.get("status") != "completed":
            stage.setdefault("started_at", _now())
            stage["status"] = "completed"
            stage["completed_at"] = _now()
            stage.pop("error", None)

    _write_snapshot(project_id, snapshot, project_status=ProjectStatus.COMPLETED.value)
    logger.info("Project %s marked as completed", project_id)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_snapshot(project_id: str) -> Dict[str, any]:
    db_client = DynamoDBClient()
    response = db_client.projects_table.get_item(Key={"project_id": project_id})
    item = response.get("Item") or {}
    snapshot = item.get("stages_snapshot")
    if isinstance(snapshot, dict):
        return snapshot
    return _default_snapshot()


def _ensure_stage_entry(snapshot: Dict[str, any], stage_name: str) -> Optional[Dict[str, any]]:
    stages = snapshot.setdefault("stages", [])
    for stage in stages:
        if stage.get("name") == stage_name:
            return stage

    # Stage not found, append a default entry.
    for idx, (name, display) in enumerate(STAGE_SEQUENCE):
        if name == stage_name:
            entry = {
                "name": name,
                "display_name": display,
                "order": idx + 1,
                "status": "pending",
            }
            stages.append(entry)
            return entry

    return None


def _write_snapshot(
    project_id: str,
    snapshot: Dict[str, any],
    *,
    project_status: Optional[str] = None,
    error_info: Optional[Dict[str, str]] = None,
) -> None:
    db_client = DynamoDBClient()

    total = snapshot.get("total") or len(snapshot.get("stages", [])) or len(STAGE_SEQUENCE)
    completed = sum(1 for stage in snapshot.get("stages", []) if stage.get("status") == "completed")
    snapshot["total"] = total
    snapshot["completed"] = completed

    progress = (completed / total * 100) if total else 0
    now = _now()

    update_expression = "SET stages_snapshot = :snapshot, progress_percentage = :progress, updated_at = :updated_at"
    expression_values = {
        ":snapshot": _convert(snapshot),
        ":progress": Decimal(str(round(progress, 2))),
        ":updated_at": now,
    }
    expression_names = {}

    if project_status:
        update_expression += ", #status = :status"
        expression_names["#status"] = "status"
        expression_values[":status"] = project_status
        if project_status == ProjectStatus.COMPLETED.value:
            update_expression += ", completed_at = :completed_at"
            expression_values[":completed_at"] = now
        elif project_status == ProjectStatus.FAILED.value:
            update_expression += ", completed_at = :completed_at, error_info = :error_info"
            expression_values[":completed_at"] = now
            expression_values[":error_info"] = error_info or {"error": "workflow failed"}

    update_kwargs = {
        "Key": {"project_id": project_id},
        "UpdateExpression": update_expression,
        "ExpressionAttributeValues": expression_values,
    }
    if expression_names:
        update_kwargs["ExpressionAttributeNames"] = expression_names

    db_client.projects_table.update_item(**update_kwargs)
    logger.debug(
        "Project %s snapshot updated: %.2f%% complete (status=%s)",
        project_id,
        float(progress),
        project_status or "unchanged",
    )


def _default_snapshot() -> Dict[str, any]:
    return {
        "total": len(STAGE_SEQUENCE),
        "completed": 0,
        "stages": [
            {
                "name": stage_name,
                "display_name": display_name,
                "order": idx + 1,
                "status": "pending",
            }
            for idx, (stage_name, display_name) in enumerate(STAGE_SEQUENCE)
        ],
    }


def _is_project_completed(snapshot: Dict[str, any]) -> bool:
    stages = snapshot.get("stages", [])
    return bool(stages) and all(stage.get("status") == "completed" for stage in stages)


def _resolve_project_name(
    provided_name: Optional[str],
    requirement: str,
    project_id: str,
) -> Optional[str]:
    candidate = _sanitize_project_name(provided_name)
    if candidate:
        return candidate

    requirement_title = _extract_requirement_title(requirement)
    if requirement_title:
        return requirement_title

    return None


def _sanitize_project_name(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if _JOB_ID_PATTERN.match(candidate):
        return None
    return candidate


def _extract_requirement_title(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    # Focus on the first line and cap the length to keep UI concise.
    first_line = value.strip().splitlines()[0].strip()
    if not first_line:
        return None
    if len(first_line) > 80:
        first_line = first_line[:77].rstrip() + "…"
    if _JOB_ID_PATTERN.match(first_line):
        return None
    return first_line


def _convert(value):
    if isinstance(value, dict):
        return {k: _convert(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_convert(v) for v in value if v is not None]
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, int):
        return Decimal(str(value))
    return value


def _now() -> str:
    return datetime.utcnow().replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = [
    "STAGE_SEQUENCE",
    "initialize_project_record",
    "mark_stage_running",
    "mark_stage_completed",
    "mark_stage_failed",
    "mark_project_completed",
]
