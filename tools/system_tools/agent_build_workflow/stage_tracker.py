"""Stateless helpers for tracking build stage progress in DynamoDB.

This module has been updated to use StageService for stage tracking,
removing direct file system operations and using centralized stage management.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import re

from api.database.dynamodb_client import DynamoDBClient
from api.models.schemas import ProjectStatus, BuildStage, StageStatus

logger = logging.getLogger(__name__)


def _get_stage_service():
    """Lazy import to avoid circular dependency"""
    from api.services.stage_service import stage_service
    return stage_service

# Ordered list of workflow stages with display names.
STAGE_SEQUENCE: List[Tuple[str, str]] = [
    ("orchestrator", "工作流编排"),
    ("requirements_analyzer", "需求分析"),
    ("system_architect", "系统架构设计"),
    ("agent_designer", "Agent设计"),
    ("tools_developer", "工具开发"),
    ("prompt_engineer", "提示词工程"),
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

    # 使用新格式初始化阶段快照（通过 StageService）
    from api.models.schemas import build_initial_stage_snapshot
    snapshot = build_initial_stage_snapshot(include_agent_names=False)

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
    logger.info("Initialized project record %s with %d stages (new format)", project_id, snapshot.get('total', 0))


def mark_stage_running(project_id: str, stage_name: str) -> None:
    """
    Mark the given stage as running.

    Updated to use StageService instead of direct DynamoDB operations.
    Requirements: 7.2
    """
    try:
        # Convert stage_name to BuildStage enum
        stage_enum = _stage_name_to_enum(stage_name)
        if stage_enum is None:
            logger.warning("mark_stage_running: invalid stage %s for project %s", stage_name, project_id)
            return

        # Use StageService to update stage status
        stage_service = _get_stage_service()
        stage_service.update_stage_status(
            project_id=project_id,
            stage=stage_enum,
            status=StageStatus.RUNNING,
            started_at=_now()
        )
        logger.info("Project %s stage %s set to running", project_id, stage_name)
    except Exception as e:
        logger.error("Failed to mark stage running for project %s stage %s: %s", project_id, stage_name, str(e))
        raise


def mark_stage_completed(project_id: str, stage_name: str, output_data: Optional[Dict] = None) -> None:
    """
    Mark the given stage as completed and update project progress.

    Updated to use StageService instead of direct DynamoDB operations.
    Requirements: 7.3

    Args:
        project_id: Project ID
        stage_name: Stage name
        output_data: Optional output data from the stage
    """
    try:
        # Convert stage_name to BuildStage enum
        stage_enum = _stage_name_to_enum(stage_name)
        if stage_enum is None:
            logger.warning("mark_stage_completed: invalid stage %s for project %s", stage_name, project_id)
            return

        # Prepare kwargs for update
        kwargs = {
            "completed_at": _now()
        }
        if output_data:
            kwargs["output_data"] = output_data

        # Use StageService to update stage status
        stage_service = _get_stage_service()
        stage_service.update_stage_status(
            project_id=project_id,
            stage=stage_enum,
            status=StageStatus.COMPLETED,
            **kwargs
        )
        logger.info("Project %s stage %s completed", project_id, stage_name)
    except Exception as e:
        logger.error("Failed to mark stage completed for project %s stage %s: %s", project_id, stage_name, str(e))
        raise


def mark_stage_failed(project_id: str, stage_name: str, error_message: str) -> None:
    """
    Mark the given stage (and project) as failed.

    Updated to use StageService instead of direct DynamoDB operations.
    Requirements: 7.4

    Args:
        project_id: Project ID
        stage_name: Stage name
        error_message: Error message describing the failure
    """
    try:
        # Convert stage_name to BuildStage enum
        stage_enum = _stage_name_to_enum(stage_name)
        if stage_enum is None:
            logger.warning("mark_stage_failed: invalid stage %s for project %s", stage_name, project_id)
            # Still update project status to failed even if stage is invalid
            _update_project_status_to_failed(project_id, error_message)
            return

        # Use StageService to update stage status
        stage_service = _get_stage_service()
        stage_service.update_stage_status(
            project_id=project_id,
            stage=stage_enum,
            status=StageStatus.FAILED,
            completed_at=_now(),
            error_message=error_message
        )

        # Update project status to failed
        _update_project_status_to_failed(project_id, error_message)

        logger.error("Project %s stage %s failed: %s", project_id, stage_name, error_message)
    except Exception as e:
        logger.error("Failed to mark stage failed for project %s stage %s: %s", project_id, stage_name, str(e))
        raise


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
# Sub-stage tracking functions (for Developer Manager stage)
# Requirements: 7.2, 7.3, 7.4
# ---------------------------------------------------------------------------


def mark_sub_stage_running(project_id: str, sub_stage_name: str) -> None:
    """
    Mark a sub-stage as running within the agent_developer_manager stage.

    Args:
        project_id: Project ID
        sub_stage_name: Sub-stage name (tool_developer, prompt_engineer, agent_code_developer)

    Requirements: 7.2
    """
    try:
        stage_service = _get_stage_service()
        stage_service.update_sub_stage_status(
            project_id=project_id,
            sub_stage_name=sub_stage_name,
            status=StageStatus.RUNNING,
            started_at=_now()
        )
        logger.info("Project %s sub-stage %s set to running", project_id, sub_stage_name)
    except Exception as e:
        logger.error("Failed to mark sub-stage running for project %s sub-stage %s: %s",
                    project_id, sub_stage_name, str(e))
        raise


def mark_sub_stage_completed(project_id: str, sub_stage_name: str, artifacts: Optional[List[str]] = None) -> None:
    """
    Mark a sub-stage as completed within the agent_developer_manager stage.

    Args:
        project_id: Project ID
        sub_stage_name: Sub-stage name (tool_developer, prompt_engineer, agent_code_developer)
        artifacts: Optional list of artifact file paths generated by this sub-stage

    Requirements: 7.3
    """
    try:
        stage_service = _get_stage_service()
        stage_service.update_sub_stage_status(
            project_id=project_id,
            sub_stage_name=sub_stage_name,
            status=StageStatus.COMPLETED,
            completed_at=_now(),
            artifacts=artifacts or []
        )
        logger.info("Project %s sub-stage %s completed with %d artifacts",
                   project_id, sub_stage_name, len(artifacts or []))
    except Exception as e:
        logger.error("Failed to mark sub-stage completed for project %s sub-stage %s: %s",
                    project_id, sub_stage_name, str(e))
        raise


def mark_sub_stage_failed(project_id: str, sub_stage_name: str, error_message: str) -> None:
    """
    Mark a sub-stage as failed within the agent_developer_manager stage.

    Args:
        project_id: Project ID
        sub_stage_name: Sub-stage name (tool_developer, prompt_engineer, agent_code_developer)
        error_message: Error message describing the failure

    Requirements: 7.4
    """
    try:
        stage_service = _get_stage_service()
        stage_service.update_sub_stage_status(
            project_id=project_id,
            sub_stage_name=sub_stage_name,
            status=StageStatus.FAILED,
            completed_at=_now()
        )
        logger.error("Project %s sub-stage %s failed: %s", project_id, sub_stage_name, error_message)
    except Exception as e:
        logger.error("Failed to mark sub-stage failed for project %s sub-stage %s: %s",
                    project_id, sub_stage_name, str(e))
        raise


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _stage_name_to_enum(stage_name: str) -> Optional[BuildStage]:
    """
    Convert stage name string to BuildStage enum.

    Args:
        stage_name: Stage name string

    Returns:
        BuildStage enum or None if invalid
    """
    # Map stage names to BuildStage enum values
    # Support both workflow agent names and BuildStage enum values for compatibility
    stage_mapping = {
        # Workflow agent names (used in agent_build_workflow.py)
        "orchestrator": BuildStage.ORCHESTRATOR,
        "requirements_analyzer": BuildStage.REQUIREMENTS_ANALYSIS,
        "system_architect": BuildStage.SYSTEM_ARCHITECTURE,
        "agent_designer": BuildStage.AGENT_DESIGN,
        "prompt_engineer": BuildStage.PROMPT_ENGINEER,
        "tools_developer": BuildStage.TOOLS_DEVELOPER,
        "agent_code_developer": BuildStage.AGENT_CODE_DEVELOPER,
        "agent_developer_manager": BuildStage.AGENT_DEVELOPER_MANAGER,
        "agent_deployer": BuildStage.AGENT_DEPLOYER,
        # BuildStage enum values (for compatibility)
        "requirements_analysis": BuildStage.REQUIREMENTS_ANALYSIS,
        "system_architecture": BuildStage.SYSTEM_ARCHITECTURE,
        "agent_design": BuildStage.AGENT_DESIGN,
    }
    return stage_mapping.get(stage_name)


def _update_project_status_to_failed(project_id: str, error_message: str) -> None:
    """
    Update project status to FAILED.

    Args:
        project_id: Project ID
        error_message: Error message
    """
    try:
        db_client = DynamoDBClient()
        now = _now()
        db_client.projects_table.update_item(
            Key={"project_id": project_id},
            UpdateExpression="SET #status = :status, completed_at = :completed_at, error_info = :error_info, updated_at = :updated_at",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": ProjectStatus.FAILED.value,
                ":completed_at": now,
                ":error_info": {"error": error_message},
                ":updated_at": now
            }
        )
    except Exception as e:
        logger.error("Failed to update project status to failed for project %s: %s", project_id, str(e))
        raise


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
    "mark_sub_stage_running",
    "mark_sub_stage_completed",
    "mark_sub_stage_failed",
]
