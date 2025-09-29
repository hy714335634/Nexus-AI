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
            # Reuse the CLI helpers to stay faithful to the original behaviour.
            intent_result = cli_workflow.analyze_user_intent(requirement)
            workflow = cli_workflow.create_build_workflow()

            start_time = time.time()
            workflow_result = self._execute_workflow_with_retry(workflow, intent_result)
            execution_time = time.time() - start_time

            report_path = generate_workflow_summary_report(workflow_result, "./projects")
        finally:
            if previous_tracker_id is None:
                os.environ.pop("NEXUS_STAGE_TRACKER_PROJECT_ID", None)
            else:
                os.environ["NEXUS_STAGE_TRACKER_PROJECT_ID"] = previous_tracker_id

        intent_payload = {
            "intent_type": self._json_safe(getattr(intent_result, "intent_type", None)),
            "mentioned_project_name": self._json_safe(getattr(intent_result, "mentioned_project_name", None)),
            "project_exists": self._json_safe(getattr(intent_result, "project_exists", None)),
            "orchestrator_guidance": self._json_safe(getattr(intent_result, "orchestrator_guidance", None)),
        }

        workflow_payload = {
            "status": self._json_safe(getattr(workflow_result, "status", None)),
            "total_nodes": self._json_safe(getattr(workflow_result, "total_nodes", None)),
            "completed_nodes": self._json_safe(getattr(workflow_result, "completed_nodes", None)),
            "failed_nodes": self._json_safe(getattr(workflow_result, "failed_nodes", None)),
            "execution_time_ms": self._json_safe(getattr(workflow_result, "execution_time", None)),
            "execution_order": [
                self._json_safe(getattr(node, "node_id", node))
                for node in getattr(workflow_result, "execution_order", [])
            ],
            "accumulated_usage": self._json_safe(getattr(workflow_result, "accumulated_usage", None)),
        }

        return AgentWorkflowOutput(
            session_id=session,
            report_path=report_path,
            execution_time=execution_time,
            intent=intent_payload,
            workflow=workflow_payload,
        )

    def _execute_workflow_with_retry(self, workflow: Any, intent_result: Any) -> Any:
        """Execute workflow with exponential backoff on max_tokens limit errors."""

        delays = [0, 120, 240, 480]  # seconds
        last_exception: Optional[Exception] = None

        for attempt, delay in enumerate(delays, start=1):
            if delay:
                logger.info(
                    "Workflow retry attempt %s after sleeping %ss due to max_tokens limit",
                    attempt,
                    delay,
                )
                time.sleep(delay)

            try:
                return workflow(str(intent_result))
            except Exception as exc:  # pragma: no cover - retry loop
                message = str(exc)
                if "max_tokens limit" not in message:
                    raise
                last_exception = exc
                if attempt == len(delays):
                    break
                logger.warning(
                    "Max tokens limit reached (attempt %s/%s), will retry with backoff",
                    attempt,
                    len(delays),
                )

        # All retries exhausted
        if last_exception:
            raise last_exception
        raise RuntimeError("Workflow retry loop exited unexpectedly")

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
