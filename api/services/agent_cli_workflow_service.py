"""Simple wrapper around the legacy agent build CLI workflow."""

from __future__ import annotations

import logging
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
            # Run the complete workflow (which includes intent analysis internally)
            workflow_result = cli_workflow.run_workflow(requirement, session_id=session)

            # Extract data from workflow result
            intent_result = workflow_result.get("intent_analysis")
            execution_time = workflow_result.get("execution_time", 0)
            report_path = workflow_result.get("report_path", "")
            execution_order = workflow_result.get("execution_order", [])
            status = workflow_result.get("status", "UNKNOWN")

        finally:
            if previous_tracker_id is None:
                os.environ.pop("NEXUS_STAGE_TRACKER_PROJECT_ID", None)
            else:
                os.environ["NEXUS_STAGE_TRACKER_PROJECT_ID"] = previous_tracker_id

        # Build intent payload
        intent_payload = {}
        if intent_result:
            intent_payload = {
                "intent_type": self._json_safe(getattr(intent_result, "intent_type", None)),
                "mentioned_project_name": self._json_safe(getattr(intent_result, "mentioned_project_name", None)),
                "project_exists": self._json_safe(getattr(intent_result, "project_exists", None)),
                "orchestrator_guidance": self._json_safe(getattr(intent_result, "orchestrator_guidance", None)),
                "existing_project_info": self._json_safe(getattr(intent_result, "existing_project_info", None)),
                "new_project_info": self._json_safe(getattr(intent_result, "new_project_info", None)),
            }

            new_project_info = getattr(intent_result, "new_project_info", None)
            if new_project_info is not None:
                suggested_name = getattr(new_project_info, "suggested_project_name", None)
                if suggested_name:
                    intent_payload["suggested_project_name"] = self._json_safe(suggested_name)

        # Build workflow payload
        workflow_payload = {
            "status": status,
            "total_nodes": len(execution_order),
            "completed_nodes": len(execution_order) if status == "COMPLETED" else 0,
            "failed_nodes": 0 if status == "COMPLETED" else 1,
            "execution_time_ms": int(execution_time * 1000) if execution_time else 0,
            "execution_order": [str(node) for node in execution_order],
            "accumulated_usage": None,
        }

        return AgentWorkflowOutput(
            session_id=session,
            report_path=report_path,
            execution_time=execution_time,
            intent=intent_payload,
            workflow=workflow_payload,
        )

    def _json_safe(self, value: Any) -> Any:
        """Best-effort conversion of SDK objects to JSON-serialisable primitives."""

        if value is None or isinstance(value, (str, int, float, bool)):
            return value

        if isinstance(value, dict):
            return {k: self._json_safe(v) for k, v in value.items()}

        if isinstance(value, (list, tuple, set)):
            return [self._json_safe(v) for v in value]

        # Enums or objects with value/name attributes
        for attr in ("value", "name", "status"):
            if hasattr(value, attr):
                candidate = getattr(value, attr)
                if isinstance(candidate, (str, int, float, bool)):
                    return candidate

        # Dataclasses or objects exposing dict representations
        if hasattr(value, "to_dict"):
            try:
                return self._json_safe(value.to_dict())
            except Exception:  # pragma: no cover - defensive
                pass

        if hasattr(value, "__dict__"):
            return self._json_safe(vars(value))

        return str(value)


__all__ = ["AgentCLIBuildService", "AgentWorkflowOutput"]
logger = logging.getLogger(__name__)
