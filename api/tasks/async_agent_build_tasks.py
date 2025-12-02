"""
Async agent build tasks without Celery dependency.
Uses Python's threading and concurrent.futures for background execution.
"""

from __future__ import annotations

import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional, Callable
import re

from api.database.dynamodb_client import DynamoDBClient
from api.services import AgentCLIBuildService

logger = logging.getLogger(__name__)

# Thread pool for executing tasks
_executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="agent_build_")

# In-memory task status storage (for development)
_task_status: Dict[str, Dict[str, Any]] = {}
_status_lock = threading.Lock()

_JOB_ID_PATTERN = re.compile(r"^job_[0-9a-f]{8,}$", re.IGNORECASE)


class AsyncTaskResult:
    """Represents the result of an async task"""

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.id = task_id  # Celery compatibility

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the task"""
        with _status_lock:
            return _task_status.get(self.task_id, {
                "task_id": self.task_id,
                "status": "PENDING",
                "result": None,
                "error": None
            })

    @property
    def state(self) -> str:
        """Get the current state (Celery compatibility)"""
        return self.get_status().get("status", "PENDING")

    @property
    def result(self) -> Any:
        """Get the result if completed"""
        return self.get_status().get("result")

    @property
    def ready(self) -> bool:
        """Check if task is completed"""
        state = self.state
        return state in ("SUCCESS", "FAILURE")


def _update_task_status(task_id: str, status: str, result: Any = None, error: str = None):
    """Update task status in memory"""
    with _status_lock:
        _task_status[task_id] = {
            "task_id": task_id,
            "status": status,
            "result": result,
            "error": error,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }


def build_agent(
    *,
    project_id: str,
    requirement: str,
    session_id: str,
    user_id: Optional[str] = None,
    user_name: Optional[str] = None,
    agent_name: Optional[str] = None,
    callback: Optional[Callable] = None,
    **kwargs: Any,
) -> AsyncTaskResult:
    """
    Execute the agent build workflow asynchronously without Celery.

    Args:
        project_id: Project identifier
        requirement: User requirement description
        session_id: Session identifier
        user_id: User identifier (optional)
        user_name: User display name (optional)
        agent_name: Agent name (optional)
        callback: Optional callback function to call on completion
        **kwargs: Additional arguments

    Returns:
        AsyncTaskResult: Task result object for status tracking
    """
    task_id = str(uuid.uuid4())

    # Update initial status
    _update_task_status(task_id, "PENDING")

    # Submit task to thread pool
    future = _executor.submit(
        _execute_build_agent,
        task_id=task_id,
        project_id=project_id,
        requirement=requirement,
        session_id=session_id,
        user_id=user_id,
        user_name=user_name,
        agent_name=agent_name,
        callback=callback,
        **kwargs
    )

    logger.info(f"Submitted agent build task {task_id} for project {project_id}")

    return AsyncTaskResult(task_id)


def _execute_build_agent(
    task_id: str,
    project_id: str,
    requirement: str,
    session_id: str,
    user_id: Optional[str],
    user_name: Optional[str],
    agent_name: Optional[str],
    callback: Optional[Callable],
    **kwargs: Any,
) -> dict:
    """Internal function to execute the build workflow"""

    logger.info(f"Starting agent build task {task_id}", extra={"session_id": session_id, "project_id": project_id})

    # Update status to STARTED
    _update_task_status(task_id, "STARTED")

    service = AgentCLIBuildService()
    start_time = datetime.now(timezone.utc)

    try:
        output = service.run_build(
            requirement,
            session_id=session_id,
            project_id=project_id,
        )
    except Exception as exc:
        finish_time = datetime.now(timezone.utc)
        error_msg = str(exc)

        _persist_task_snapshot(
            project_id,
            latest_task=_build_task_snapshot(
                task_id=task_id,
                status="failed",
                started_at=start_time,
                finished_at=finish_time,
                error=error_msg,
            ),
            metrics_payload=None,
            project_name=agent_name,
        )

        # Update project status to failed (if not already updated by mark_stage_failed)
        from api.database.dynamodb_client import DynamoDBClient
        from api.models.schemas import ProjectStatus
        db_client = DynamoDBClient()
        try:
            # Check current status to avoid overwriting if already failed
            project = db_client.get_project(project_id)
            if project.get('status') != ProjectStatus.FAILED.value:
                db_client.update_project_status(
                    project_id,
                    ProjectStatus.FAILED,
                    completed_at=finish_time,
                    error_info={"error": error_msg, "type": "task_exception"}
                )
                logger.info(f"Updated project {project_id} status to failed")
        except Exception as db_exc:
            logger.error(f"Failed to update project status: {db_exc}")

        # Update status to FAILURE
        _update_task_status(task_id, "FAILURE", error=error_msg)

        logger.exception(f"Agent build task {task_id} failed", extra={"project_id": project_id})

        if callback:
            try:
                callback(success=False, error=error_msg)
            except Exception as cb_exc:
                logger.error(f"Callback error: {cb_exc}")

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
        task_id=task_id,
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

    # Update project status to completed
    from api.database.dynamodb_client import DynamoDBClient
    from api.models.schemas import ProjectStatus
    db_client = DynamoDBClient()
    db_client.update_project_status(
        project_id,
        ProjectStatus.COMPLETED,
        completed_at=finish_time
    )
    logger.info(f"Updated project {project_id} status to completed")

    payload = output.to_dict()
    payload.update({
        "project_id": project_id,
        "user_id": user_id,
        "user_name": user_name,
        "agent_name": resolved_agent_name,
    })

    # Update status to SUCCESS
    _update_task_status(task_id, "SUCCESS", result=payload)

    logger.info(f"Agent build task {task_id} completed", extra={"session_id": session_id, "project_id": project_id})

    if callback:
        try:
            callback(success=True, result=payload)
        except Exception as cb_exc:
            logger.error(f"Callback error: {cb_exc}")

    return payload


def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Get the status of a task by ID.

    Args:
        task_id: Task identifier

    Returns:
        Dict with task status information
    """
    with _status_lock:
        return _task_status.get(task_id, {
            "task_id": task_id,
            "status": "UNKNOWN",
            "result": None,
            "error": "Task not found"
        })


# Helper functions from original Celery tasks

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


__all__ = ["build_agent", "get_task_status", "AsyncTaskResult"]
