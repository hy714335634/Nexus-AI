"""Celery tasks for agent workflow execution."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional
import re

from api.core.celery_app import celery_app
from api.database.dynamodb_client import DynamoDBClient
from api.services import AgentCLIBuildService
from tools.system_tools.agent_build_workflow.stage_tracker import (
    STAGE_SEQUENCE,
    mark_stage_completed,
    mark_stage_failed,
    mark_stage_running,
)

logger = logging.getLogger(__name__)


_JOB_ID_PATTERN = re.compile(r"^job_[0-9a-f]{8,}$", re.IGNORECASE)


@celery_app.task(bind=True, name="api.tasks.agent_build_tasks.build_agent")
def build_agent(
    self,
    *,
    project_id: str,
    requirement: str,
    session_id: str,
    user_id: Optional[str] = None,
    user_name: Optional[str] = None,
    agent_name: Optional[str] = None,
    **kwargs: Any,
) -> dict:
    """Execute the legacy CLI workflow asynchronously with stage tracking."""

    logger.info("Starting agent build task", extra={"session_id": session_id, "project_id": project_id})

    service = AgentCLIBuildService()
    start_time = datetime.now(timezone.utc)

    try:
        output = service.run_build(
            requirement,
            session_id=session_id,
            project_id=project_id,
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        finish_time = datetime.now(timezone.utc)
        _persist_task_snapshot(
            project_id,
            latest_task=_build_task_snapshot(
                task_id=getattr(self.request, "id", None),
                status="failed",
                started_at=start_time,
                finished_at=finish_time,
                error=str(exc),
            ),
            metrics_payload=None,
            project_name=agent_name,
        )
        # 不需要在这里标记失败，因为 workflow 内部已经处理了
        logger.exception("Agent build task failed", extra={"project_id": project_id})
        raise

    finish_time = datetime.now(timezone.utc)
    workflow_payload = output.workflow or {}
    usage = workflow_payload.get("accumulated_usage") if isinstance(workflow_payload, dict) else None

    metrics_payload = {
        "total_duration_seconds": output.execution_time,
        "input_tokens": _coerce_int(_extract_usage_value(usage, "inputTokens")),
        "output_tokens": _coerce_int(_extract_usage_value(usage, "outputTokens")),
        "tool_calls": _coerce_int(workflow_payload.get("tool_calls")),
        "report_path": output.report_path,
    }

    if agent_name is None and "agent_name" in kwargs:
        agent_name = kwargs.pop("agent_name")

    resolved_agent_name = _best_agent_name(agent_name, output)

    latest_task_metadata: Dict[str, Any] = {
        "execution_time_seconds": output.execution_time,
        "total_nodes": workflow_payload.get("total_nodes"),
        "completed_nodes": workflow_payload.get("completed_nodes"),
        "failed_nodes": workflow_payload.get("failed_nodes"),
    }
    if resolved_agent_name:
        latest_task_metadata["project_name"] = resolved_agent_name

    latest_task_payload = _build_task_snapshot(
        task_id=getattr(self.request, "id", None),
        status=_safe_lower(workflow_payload.get("status")) or "completed",
        started_at=start_time,
        finished_at=finish_time,
        metadata=latest_task_metadata,
    )

    _persist_task_snapshot(
        project_id,
        latest_task=latest_task_payload,
        metrics_payload=metrics_payload,
        project_name=resolved_agent_name,
    )

    payload = output.to_dict()
    payload.update({
        "project_id": project_id,
        "user_id": user_id,
        "user_name": user_name,
        "agent_name": resolved_agent_name,
    })

    logger.info("Agent build task completed", extra={"session_id": session_id, "project_id": project_id})

    return payload


def _build_task_snapshot(
    *,
    task_id: Optional[str],
    status: str,
    started_at: datetime,
    finished_at: datetime,
    error: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    snapshot: Dict[str, Any] = {
        "task_id": task_id or "",
        "status": status,
        "started_at": _isoformat(started_at),
        "finished_at": _isoformat(finished_at),
    }
    if error:
        snapshot["error"] = error
    if metadata:
        snapshot["metadata"] = {k: v for k, v in metadata.items() if v is not None}
    return snapshot


def _persist_task_snapshot(
    project_id: str,
    *,
    latest_task: Optional[Dict[str, Any]],
    metrics_payload: Optional[Dict[str, Any]],
    project_name: Optional[str] = None,
) -> None:
    db_client = DynamoDBClient()
    update_expression = "SET updated_at = :updated_at"
    values: Dict[str, Any] = {
        ":updated_at": _isoformat(datetime.now(timezone.utc)),
    }
    expression_names: Dict[str, str] = {}

    if latest_task:
        update_expression += ", latest_task = :latest_task"
        values[":latest_task"] = _to_dynamo(latest_task)

    if metrics_payload:
        cleaned_metrics = {k: v for k, v in metrics_payload.items() if v is not None}
        if cleaned_metrics:
            update_expression += ", #metrics_payload = :metrics_payload"
            expression_names["#metrics_payload"] = "metrics_payload"
            values[":metrics_payload"] = _to_dynamo(cleaned_metrics)

    if project_name:
        update_expression += ", project_name = :project_name"
        values[":project_name"] = project_name

    update_kwargs: Dict[str, Any] = {
        "Key": {"project_id": project_id},
        "UpdateExpression": update_expression,
        "ExpressionAttributeValues": values,
    }
    if expression_names:
        update_kwargs["ExpressionAttributeNames"] = expression_names

    db_client.projects_table.update_item(**update_kwargs)


def _extract_usage_value(usage: Any, key: str) -> Optional[int]:
    if isinstance(usage, dict):
        value = usage.get(key) or usage.get(_camel_to_snake(key))
        return _coerce_int(value)
    return None


def _best_agent_name(initial: Optional[str], output: Any) -> Optional[str]:
    candidates: list[Optional[str]] = [initial]

    intent_payload = output.intent or {}
    workflow_payload = output.workflow or {}

    for key in ("project_name", "mentioned_project_name", "suggested_project_name", "title"):
        value = intent_payload.get(key)
        if isinstance(value, str):
            candidates.append(value)

    existing_info = intent_payload.get("existing_project_info")
    if isinstance(existing_info, dict):
        value = existing_info.get("project_name")
        if isinstance(value, str):
            candidates.append(value)

    new_info = intent_payload.get("new_project_info")
    if isinstance(new_info, dict):
        value = new_info.get("suggested_project_name")
        if isinstance(value, str):
            candidates.append(value)

    workflow_name = workflow_payload.get("project_name")
    if isinstance(workflow_name, str):
        candidates.append(workflow_name)

    for candidate in candidates:
        sanitized = _sanitize_agent_name(candidate)
        if sanitized:
            return sanitized
    return None


def _sanitize_agent_name(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if _JOB_ID_PATTERN.match(candidate):
        return None
    return candidate


def _camel_to_snake(value: str) -> str:
    chars = []
    for character in value:
        if character.isupper():
            chars.append("_")
            chars.append(character.lower())
        else:
            chars.append(character)
    return "".join(chars).lstrip("_")


def _to_dynamo(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _to_dynamo(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_to_dynamo(item) for item in value if item is not None]
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    return value


def _isoformat(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _coerce_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, (int, bool)):
        return int(value)
    if isinstance(value, Decimal):
        return int(value)
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return None


def _safe_lower(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    lowered = value.strip().lower()
    return lowered or None


__all__ = ["build_agent"]
