"""Simple wrapper around the legacy agent build CLI workflow."""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from strands.telemetry import StrandsTelemetry

from nexus_utils.workflow_report_generator import generate_workflow_summary_report

from agents.system_agents.agent_build_workflow import agent_build_workflow as cli_workflow


@dataclass
class AgentWorkflowOutput:
    """Structured payload returned by :func:`AgentCLIBuildService.run_build`."""

    session_id: str
    report_path: str
    execution_time: float
    intent: Dict[str, Any]
    workflow: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "report_path": self.report_path,
            "execution_time": self.execution_time,
            "intent": self.intent,
            "workflow": self.workflow,
        }


class AgentCLIBuildService:
    """Runs the existing CLI workflow and exposes a Python-friendly API."""

    _telemetry_initialized = False

    def _ensure_environment(self) -> None:
        """Align environment/telemetry settings with the CLI script."""

        os.environ.setdefault("BYPASS_TOOL_CONSENT", "true")
        os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")

        if not self.__class__._telemetry_initialized:
            telemetry = StrandsTelemetry()
            telemetry.setup_otlp_exporter()
            self.__class__._telemetry_initialized = True

    def run_build(
        self,
        requirement: str,
        *,
        session_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> AgentWorkflowOutput:
        session = session_id or str(uuid.uuid4())
        project_identifier = project_id or session

        self._ensure_environment()

        # Stage tracker relies on this environment variable to synchronise with DynamoDB.
        previous_tracker_id = os.environ.get("NEXUS_STAGE_TRACKER_PROJECT_ID")
        os.environ["NEXUS_STAGE_TRACKER_PROJECT_ID"] = project_identifier

        try:
            # Reuse the CLI helpers to stay faithful to the original behaviour.
            intent_result = cli_workflow.analyze_user_intent(requirement)
            workflow = cli_workflow.create_build_workflow()

            start_time = time.time()
            workflow_result = workflow(str(intent_result))
            execution_time = time.time() - start_time

            report_path = generate_workflow_summary_report(workflow_result, "./projects")
        finally:
            if previous_tracker_id is None:
                os.environ.pop("NEXUS_STAGE_TRACKER_PROJECT_ID", None)
            else:
                os.environ["NEXUS_STAGE_TRACKER_PROJECT_ID"] = previous_tracker_id

        intent_payload = {
            "intent_type": intent_result.intent_type,
            "mentioned_project_name": intent_result.mentioned_project_name,
            "project_exists": intent_result.project_exists,
            "orchestrator_guidance": intent_result.orchestrator_guidance,
        }

        workflow_payload = {
            "status": getattr(workflow_result, "status", None),
            "total_nodes": getattr(workflow_result, "total_nodes", None),
            "completed_nodes": getattr(workflow_result, "completed_nodes", None),
            "failed_nodes": getattr(workflow_result, "failed_nodes", None),
            "execution_time_ms": getattr(workflow_result, "execution_time", None),
            "execution_order": [
                getattr(node, "node_id", str(node)) for node in getattr(workflow_result, "execution_order", [])
            ],
        }

        return AgentWorkflowOutput(
            session_id=session,
            report_path=report_path,
            execution_time=execution_time,
            intent=intent_payload,
            workflow=workflow_payload,
        )


__all__ = ["AgentCLIBuildService", "AgentWorkflowOutput"]
