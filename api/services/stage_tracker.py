"""Utility helpers for tracking build stage progress in DynamoDB."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from api.database.dynamodb_client import DynamoDBClient
from api.models.schemas import ProjectStatus


class StageTracker:
    """Lightweight stage tracking utility stored inside DynamoDB projects table."""

    STAGES: List[Tuple[str, str]] = [
        ("orchestrator", "工作流编排"),
        ("requirements_analyzer", "需求分析"),
        ("system_architect", "系统架构设计"),
        ("agent_designer", "Agent设计"),
        ("agent_developer_manager", "开发管理"),
    ]

    def __init__(self, project_id: str, *, db_client: Optional[DynamoDBClient] = None) -> None:
        self.project_id = project_id
        self.db_client = db_client or DynamoDBClient()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def initialize(
        self,
        *,
        requirement: str,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
    ) -> None:
        """Create/overwrite the project record with a fresh stage snapshot."""

        now = self._now()
        snapshot = {
            "total": len(self.STAGES),
            "completed": 0,
            "stages": [
                {
                    "name": stage_name,
                    "display_name": display_name,
                    "order": idx + 1,
                    "status": "pending",
                }
                for idx, (stage_name, display_name) in enumerate(self.STAGES)
            ],
        }

        item = {
            "project_id": self.project_id,
            "requirement": requirement,
            "user_id": user_id,
            "user_name": user_name,
            "status": ProjectStatus.BUILDING.value,
            "progress_percentage": Decimal("0"),
            "created_at": now,
            "updated_at": now,
            "stages_snapshot": snapshot,
        }

        self.db_client.projects_table.put_item(Item=self._convert(item))

    def mark_stage_running(self, stage_name: str) -> None:
        snapshot = self._load_snapshot()
        stage = self._find_stage(snapshot, stage_name)
        if not stage:
            return
        stage["status"] = "running"
        stage["started_at"] = self._now()
        stage.pop("completed_at", None)
        stage.pop("error", None)
        self._write_snapshot(snapshot)

    def mark_stage_completed(self, stage_name: str) -> None:
        snapshot = self._load_snapshot()
        stage = self._find_stage(snapshot, stage_name)
        if not stage:
            return
        stage["status"] = "completed"
        stage.setdefault("started_at", self._now())
        stage["completed_at"] = self._now()
        stage.pop("error", None)
        self._write_snapshot(snapshot)

    def mark_stage_failed(self, stage_name: str, error_message: str) -> None:
        snapshot = self._load_snapshot()
        stage = self._find_stage(snapshot, stage_name)
        if stage:
            stage["status"] = "failed"
            stage["error"] = error_message
            stage.setdefault("started_at", self._now())
            stage["completed_at"] = self._now()
        self._write_snapshot(snapshot, project_status=ProjectStatus.FAILED.value, error_info={"error": error_message})

    def mark_project_completed(self) -> None:
        snapshot = self._load_snapshot()
        for stage in snapshot.get("stages", []):
            if stage.get("status") != "completed":
                stage["status"] = "completed"
                stage.setdefault("started_at", self._now())
                stage["completed_at"] = self._now()
                stage.pop("error", None)
        self._write_snapshot(snapshot, project_status=ProjectStatus.COMPLETED.value)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _load_snapshot(self) -> Dict[str, any]:
        response = self.db_client.projects_table.get_item(Key={"project_id": self.project_id})
        item = response.get("Item") or {}
        snapshot = item.get("stages_snapshot")
        if isinstance(snapshot, dict):
            return snapshot
        return {
            "total": len(self.STAGES),
            "completed": 0,
            "stages": [
                {
                    "name": stage_name,
                    "display_name": display_name,
                    "order": idx + 1,
                    "status": "pending",
                }
                for idx, (stage_name, display_name) in enumerate(self.STAGES)
            ],
        }

    def _write_snapshot(
        self,
        snapshot: Dict[str, any],
        *,
        project_status: Optional[str] = None,
        error_info: Optional[Dict[str, str]] = None,
    ) -> None:
        total = snapshot.get("total") or len(snapshot.get("stages", [])) or len(self.STAGES)
        completed = sum(1 for stage in snapshot.get("stages", []) if stage.get("status") == "completed")
        snapshot["total"] = total
        snapshot["completed"] = completed
        progress = (completed / total * 100) if total else 0

        now = self._now()

        update_expression = "SET stages_snapshot = :snapshot, progress_percentage = :progress, updated_at = :updated_at"
        expression_values = {
            ":snapshot": self._convert(snapshot),
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
            "Key": {"project_id": self.project_id},
            "UpdateExpression": update_expression,
            "ExpressionAttributeValues": expression_values,
        }
        if expression_names:
            update_kwargs["ExpressionAttributeNames"] = expression_names

        self.db_client.projects_table.update_item(**update_kwargs)

    def _find_stage(self, snapshot: Dict[str, any], stage_name: str) -> Optional[Dict[str, any]]:
        for stage in snapshot.get("stages", []):
            if stage.get("name") == stage_name:
                return stage
        return None

    @staticmethod
    def _convert(value):
        if isinstance(value, dict):
            return {k: StageTracker._convert(v) for k, v in value.items() if v is not None}
        if isinstance(value, list):
            return [StageTracker._convert(v) for v in value if v is not None]
        if isinstance(value, float):
            return Decimal(str(value))
        if isinstance(value, int):
            return Decimal(str(value))
        return value

    @staticmethod
    def _now() -> str:
        return datetime.utcnow().replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = ["StageTracker"]
