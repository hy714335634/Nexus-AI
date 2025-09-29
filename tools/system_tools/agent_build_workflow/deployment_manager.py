#!/usr/bin/env python3
"""Utilities to deploy generated agents to Amazon Bedrock AgentCore."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

from strands import tool

from api.services.agent_deployment_service import (
    AgentDeploymentService,
    AgentDeploymentError,
)
from tools.system_tools.agent_build_workflow.stage_tracker import (
    mark_stage_completed,
    mark_stage_failed,
    mark_stage_running,
)

logger = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parents[3]


def _current_project_id() -> Optional[str]:
    return os.environ.get("NEXUS_STAGE_TRACKER_PROJECT_ID")


@tool
def deploy_agent_to_agentcore(
    project_name: str,
    agent_name: Optional[str] = None,
    agent_script_path: Optional[str] = None,
    project_id: Optional[str] = None,
    requirements_path: Optional[str] = None,
    region: Optional[str] = None,
) -> str:
    """部署生成的Agent到Amazon Bedrock AgentCore并返回部署详情。"""

    tracker_project_id = project_id or _current_project_id()

    if tracker_project_id:
        mark_stage_running(tracker_project_id, "agent_deployer")

    service = AgentDeploymentService()

    agent_script_path = _normalize_input_path(agent_script_path)
    requirements_path = _normalize_input_path(requirements_path)

    try:
        result = service.deploy_to_agentcore(
            project_name=project_name,
            project_id=tracker_project_id,
            agent_script_path=agent_script_path,
            requirements_path=requirements_path,
            region=region,
            agent_name_override=agent_name,
        )
    except AgentDeploymentError as exc:
        if tracker_project_id:
            mark_stage_failed(tracker_project_id, "agent_deployer", str(exc))
        logger.exception("AgentCore deployment failed for project %s", project_name)
        raise
    except Exception as exc:  # pragma: no cover - defensive safety
        if tracker_project_id:
            mark_stage_failed(tracker_project_id, "agent_deployer", str(exc))
        logger.exception("Unexpected error during AgentCore deployment")
        raise
    else:
        if tracker_project_id:
            mark_stage_completed(tracker_project_id, "agent_deployer")

    payload = result.to_dict()
    return json.dumps(payload, ensure_ascii=False, indent=2)


__all__ = ["deploy_agent_to_agentcore"]


def _normalize_input_path(path_value: Optional[str]) -> Optional[str]:
    if not path_value:
        return None

    candidate = Path(path_value)
    if not candidate.is_absolute():
        candidate = REPO_ROOT / candidate

    if candidate.exists():
        return str(candidate)

    logger.warning("Provided path does not exist, ignoring override: %s", path_value)
    return None
