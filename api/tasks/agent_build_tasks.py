"""Celery tasks for agent workflow execution."""

from __future__ import annotations

import logging
from typing import Optional

from api.core.celery_app import celery_app
from api.services import AgentCLIBuildService, StageTracker

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="api.tasks.agent_build_tasks.build_agent")
def build_agent(
    self,
    *,
    project_id: str,
    requirement: str,
    session_id: str,
    user_id: Optional[str] = None,
    user_name: Optional[str] = None,
) -> dict:
    """Execute the legacy CLI workflow asynchronously with stage tracking."""

    logger.info("Starting agent build task", extra={"session_id": session_id, "project_id": project_id})

    tracker = StageTracker(project_id)
    orchestrator_stage = StageTracker.STAGES[0][0]
    tracker.mark_stage_running(orchestrator_stage)

    service = AgentCLIBuildService()

    try:
        output = service.run_build(
            requirement,
            session_id=session_id,
            project_id=project_id,
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        tracker.mark_stage_failed(orchestrator_stage, str(exc))
        logger.exception("Agent build task failed", extra={"project_id": project_id})
        raise

    tracker.mark_stage_completed(orchestrator_stage)

    payload = output.to_dict()
    payload.update({
        "project_id": project_id,
        "user_id": user_id,
        "user_name": user_name,
    })

    logger.info("Agent build task completed", extra={"session_id": session_id, "project_id": project_id})

    return payload


__all__ = ["build_agent"]
