"""Service helpers for project build dashboard aggregation."""

from __future__ import annotations

import json
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import yaml

from api.core.exceptions import ResourceNotFoundError
from api.database.dynamodb_client import DynamoDBClient
from api.models.schemas import (
    BuildDashboardData,
    BuildDashboardMetrics,
    BuildDashboardStage,
    BuildDashboardTaskSnapshot,
    ProjectStatus,
    StageStatus,
)

DEFAULT_PROJECT_ROOT = Path("./projects")


class BuildDashboardService:
    """Aggregates project build data from DynamoDB snapshots and project artifacts."""

    def __init__(
        self,
        db_client: Optional[DynamoDBClient] = None,
        *,
        project_root: Optional[Union[str, Path]] = None,
    ) -> None:
        self._db_client = db_client or DynamoDBClient()
        root_candidate = Path(project_root) if project_root is not None else DEFAULT_PROJECT_ROOT
        if not root_candidate.is_absolute():
            root_candidate = Path.cwd() / root_candidate
        self._project_root = root_candidate.resolve()

    def get_build_dashboard(self, project_id: str) -> BuildDashboardData:
        """Return a consolidated build dashboard payload for the given project."""

        project_record = self._db_client.get_project(project_id)
        if not project_record:
            raise ResourceNotFoundError("Project", project_id)

        requirement = _coerce_str(project_record.get("requirement"))
        project_name = _coerce_str(project_record.get("project_name"))
        status = _coerce_project_status(project_record.get("status"))
        progress = _coerce_float(project_record.get("progress_percentage"))
        updated_at = _parse_datetime(project_record.get("updated_at"))
        error_info = _normalize(project_record.get("error_info"))

        snapshot = _normalize(project_record.get("stages_snapshot")) or {}
        stages_payload = snapshot.get("stages") or []

        stage_map: Dict[str, BuildDashboardStage] = {}
        for entry in stages_payload:
            stage = _build_stage_model(entry)
            stage_map[stage.name] = stage

        next_order = max((stage.order for stage in stage_map.values() if stage.order), default=0) + 1

        project_dir = self._resolve_project_directory(project_record)

        summary_metrics: Optional[Dict[str, Any]] = None
        summary_stage_updates: Dict[str, Dict[str, Any]] = {}
        summary_generated_at: Optional[datetime] = None
        status_info: Dict[str, Any] = {}
        config_info: Dict[str, Any] = {}

        if project_dir:
            summary_metrics, summary_stage_updates, summary_generated_at = _parse_workflow_summary_report(
                project_dir / "workflow_summary_report.md"
            )
            status_info = _parse_status_yaml(project_dir / "status.yaml")
            config_info = _parse_project_config(project_dir / "project_config.json")

        metrics_from_record = _extract_metrics(project_record)
        metrics_dict: Dict[str, Any] = {}
        if metrics_from_record:
            metrics_dict.update(metrics_from_record.model_dump(exclude_none=True))

        metrics_dict = _merge_metrics_dict(metrics_dict, summary_metrics)
        metrics_dict = _merge_metrics_dict(metrics_dict, config_info.get("metrics"))

        cost_estimate = _merge_cost_estimate(
            metrics_dict.get("cost_estimate"),
            summary_metrics.get("cost_estimate") if summary_metrics else None,
        )
        if cost_estimate:
            metrics_dict["cost_estimate"] = cost_estimate

        if config_info.get("project_name") and not project_name:
            project_name = config_info["project_name"]
        if status_info.get("project_name") and not project_name:
            project_name = status_info["project_name"]
        if status_info.get("description") and not requirement:
            requirement = status_info["description"]

        progress_candidates = [progress]

        if summary_generated_at:
            updated_at = _max_datetime(updated_at, summary_generated_at)
        if status_info.get("updated_at"):
            updated_at = _max_datetime(updated_at, status_info["updated_at"])

        progress_info = status_info.get("progress") or {}
        if progress_info.get("percentage") is not None:
            progress_candidates.append(progress_info["percentage"])

        completed_from_status = _coerce_int(progress_info.get("completed"))
        total_from_status = _coerce_int(progress_info.get("total"))

        # Merge stage data from summary and status files.
        for stage_name, updates in summary_stage_updates.items():
            stage_map[stage_name], next_order = _merge_stage_entry(
                stage_map.get(stage_name),
                stage_name,
                updates,
                next_order,
            )

        status_stage_updates = status_info.get("stages") or {}
        for stage_name, updates in status_stage_updates.items():
            stage_map[stage_name], next_order = _merge_stage_entry(
                stage_map.get(stage_name),
                stage_name,
                updates,
                next_order,
            )

        stages = sorted(stage_map.values(), key=lambda stage: (stage.order, stage.name))

        total_stages = len(stages) or snapshot.get("total") or 0
        completed_stages = sum(1 for stage in stages if stage.status == StageStatus.COMPLETED)

        if completed_from_status is not None:
            completed_stages = max(completed_stages, completed_from_status)
        if total_from_status is not None:
            total_stages = max(total_stages, total_from_status)

        if total_stages:
            progress_candidates.append((completed_stages / total_stages) * 100)

        progress = _max_float(progress_candidates)

        allowed_metric_keys = {
            "total_duration_seconds",
            "input_tokens",
            "output_tokens",
            "tool_calls",
            "cost_estimate",
            "total_tools",
        }
        metrics_payload = {k: v for k, v in metrics_dict.items() if k in allowed_metric_keys}
        metrics_model = BuildDashboardMetrics(**metrics_payload) if metrics_payload else None
        latest_task = _extract_task_snapshot(project_record)

        return BuildDashboardData(
            project_id=project_id,
            project_name=project_name,
            status=status,
            progress_percentage=progress if progress is not None else 0.0,
            requirement=requirement,
            stages=stages,
            total_stages=total_stages,
            completed_stages=completed_stages,
            updated_at=updated_at,
            latest_task=latest_task,
            metrics=metrics_model,
            error_info=error_info,
        )

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _resolve_project_directory(self, project_record: Dict[str, Any]) -> Optional[Path]:
        """Best-effort resolution of the project artifacts directory."""

        candidates: list[Path] = []

        metrics = project_record.get("metrics_payload") or project_record.get("metrics")
        if isinstance(metrics, dict):
            report_path = metrics.get("report_path")
            if isinstance(report_path, str) and report_path:
                path_candidate = Path(report_path)
                if path_candidate.is_file():
                    candidates.append(path_candidate.parent)
                else:
                    candidates.append(path_candidate)

        artifacts_path = project_record.get("artifacts_base_path")
        if isinstance(artifacts_path, str) and artifacts_path:
            path_candidate = Path(artifacts_path)
            if not path_candidate.is_absolute():
                path_candidate = self._project_root / artifacts_path
            candidates.append(path_candidate)

        for key in ("project_name", "project_id"):
            value = project_record.get(key)
            if isinstance(value, str) and value:
                candidates.append(self._project_root / value)

        seen = set()
        for candidate in candidates:
            candidate = candidate.resolve()
            if candidate in seen:
                continue
            seen.add(candidate)
            if candidate.exists() and candidate.is_dir():
                return candidate
        return None


# -------------------------------------------------------------------------- #
# Standalone helper functions
# -------------------------------------------------------------------------- #


def _build_stage_model(entry: Dict[str, Any]) -> BuildDashboardStage:
    status_value = entry.get("status") or StageStatus.PENDING.value
    try:
        status = StageStatus(status_value)
    except ValueError:
        status = StageStatus.PENDING

    started_at = _parse_datetime(entry.get("started_at"))
    completed_at = _parse_datetime(entry.get("completed_at"))
    duration = _parse_float(entry.get("duration_seconds"))

    metadata = entry.get("metadata")
    metadata_dict = _normalize(metadata) if isinstance(metadata, (dict, list)) else {}
    if not isinstance(metadata_dict, dict):
        metadata_dict = {}

    # Support both old format (name, display_name, order) and new format (stage_name, stage_name_cn, stage_number)
    name = _coerce_str(entry.get("stage_name") or entry.get("name")) or "unknown"
    display_name = _coerce_str(entry.get("stage_name_cn") or entry.get("display_name"))
    order = _coerce_int(entry.get("stage_number") or entry.get("order")) or 0

    return BuildDashboardStage(
        name=name,
        display_name=display_name,
        order=order,
        status=status,
        started_at=started_at,
        completed_at=completed_at,
        duration_seconds=duration,
        error=_coerce_str(entry.get("error_message") or entry.get("error")),
        input_tokens=_coerce_int(entry.get("input_tokens")),
        output_tokens=_coerce_int(entry.get("output_tokens")),
        tool_calls=_coerce_int(entry.get("tool_calls")),
        metadata=metadata_dict,
    )


def _merge_stage_entry(
    existing: Optional[BuildDashboardStage],
    stage_name: str,
    updates: Dict[str, Any],
    next_order: int,
) -> Tuple[BuildDashboardStage, int]:
    base_data = existing.model_dump() if existing else {"name": stage_name, "status": StageStatus.PENDING, "order": next_order}
    if existing is None:
        next_order += 1

    metadata_updates = updates.pop("metadata", None)
    if metadata_updates:
        existing_metadata = base_data.get("metadata") or {}
        merged = {**existing_metadata, **metadata_updates}
        base_data["metadata"] = merged

    for key, value in updates.items():
        if value is None:
            continue
        if key in {"started_at", "completed_at"}:
            base_data[key] = value if isinstance(value, datetime) else _parse_datetime(value)
        else:
            base_data[key] = value

    if "status" in base_data and not isinstance(base_data["status"], StageStatus):
        try:
            base_data["status"] = StageStatus(base_data["status"])
        except ValueError:
            base_data["status"] = StageStatus.PENDING

    return BuildDashboardStage(**base_data), next_order


def _extract_task_snapshot(project_record: Dict[str, Any]) -> Optional[BuildDashboardTaskSnapshot]:
    task_info = project_record.get("latest_task")
    if not isinstance(task_info, dict) or not task_info.get("task_id"):
        return None

    metadata = task_info.get("metadata")
    normalized_metadata = _normalize(metadata) if isinstance(metadata, (dict, list)) else None
    if normalized_metadata is not None and not isinstance(normalized_metadata, dict):
        normalized_metadata = None

    return BuildDashboardTaskSnapshot(
        task_id=_coerce_str(task_info.get("task_id")) or "",
        status=_coerce_str(task_info.get("status")) or "unknown",
        started_at=_parse_datetime(task_info.get("started_at")),
        finished_at=_parse_datetime(task_info.get("finished_at")),
        error=_coerce_str(task_info.get("error")),
        metadata=normalized_metadata,
    )


def _extract_metrics(project_record: Dict[str, Any]) -> Optional[BuildDashboardMetrics]:
    metrics = project_record.get("metrics_payload") or project_record.get("metrics")
    if not isinstance(metrics, dict):
        return None

    normalized = _normalize(metrics)
    if not isinstance(normalized, dict):
        return None

    return BuildDashboardMetrics(
        total_duration_seconds=_coerce_float(normalized.get("total_duration_seconds")),
        input_tokens=_coerce_int(normalized.get("input_tokens")),
        output_tokens=_coerce_int(normalized.get("output_tokens")),
        tool_calls=_coerce_int(normalized.get("tool_calls")),
        cost_estimate=normalized.get("cost_estimate"),
        total_tools=_coerce_int(normalized.get("total_tools")),
    )


def _merge_metrics_dict(target: Dict[str, Any], source: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not source:
        return target

    for key, value in source.items():
        if value is None:
            continue
        if key == "cost_estimate":
            continue  # handled separately
        target[key] = value

    return target


def _merge_cost_estimate(
    existing: Optional[Dict[str, Any]],
    new_cost: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not existing and not new_cost:
        return None

    result: Dict[str, Any] = {}
    if isinstance(existing, dict):
        result.update(existing)

    if not isinstance(new_cost, dict):
        return result or None

    if "breakdown" in new_cost:
        breakdown = result.get("breakdown", {})
        breakdown.update(new_cost["breakdown"])
        result["breakdown"] = breakdown

    if "rates" in new_cost:
        rates = result.get("rates", {})
        rates.update(new_cost["rates"])
        result["rates"] = rates

    for key, value in new_cost.items():
        if key in {"breakdown", "rates"}:
            continue
        result[key] = value

    return result or None


def _parse_workflow_summary_report(path: Path) -> Tuple[Optional[Dict[str, Any]], Dict[str, Dict[str, Any]], Optional[datetime]]:
    if not path.exists():
        return None, {}, None

    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None, {}, None

    generated_match = re.search(r"\*\*生成时间\*\*:\s*([0-9:\-\s]+)", text)
    generated_at = _parse_datetime(generated_match.group(1)) if generated_match else None

    metrics: Dict[str, Any] = {}

    duration_match = re.search(r"\*\*总执行时间\*\*:\s*([0-9]+(?:\.[0-9]+)?)\s*秒", text)
    if duration_match:
        metrics["total_duration_seconds"] = float(duration_match.group(1))

    input_token_match = re.search(r"\*\*总输入Token\*\*:\s*([0-9.,]+)\s*([KMB]?)", text, flags=re.IGNORECASE)
    if input_token_match:
        metrics["input_tokens"] = _parse_token_string(input_token_match.group(1), input_token_match.group(2))

    output_token_match = re.search(r"\*\*总输出Token\*\*:\s*([0-9.,]+)\s*([KMB]?)", text, flags=re.IGNORECASE)
    if output_token_match:
        metrics["output_tokens"] = _parse_token_string(output_token_match.group(1), output_token_match.group(2))

    tool_calls_match = re.search(r"\*\*总工具调用次数\*\*:\s*([0-9]+)", text)
    if tool_calls_match:
        metrics["tool_calls"] = _coerce_int(tool_calls_match.group(1))

    cost_estimate = _parse_cost_estimate(text)
    if cost_estimate:
        metrics["cost_estimate"] = cost_estimate

    stage_updates = _parse_stage_table(text)

    return (metrics or None), stage_updates, generated_at


def _parse_cost_estimate(text: str) -> Optional[Dict[str, Any]]:
    cost_pattern = re.compile(r"\*\*(输入成本|输出成本|总成本)\*\*:\s*\$([0-9]+(?:\.[0-9]+)?)\s*([A-Z]{3})")
    rate_pattern = re.compile(r"\*\*(输入费率|输出费率)\*\*:\s*\$([0-9]+(?:\.[0-9]+)?)\s*([A-Z]{3})/1K tokens")
    model_pattern = re.compile(r"\*\*定价模型\*\*:\s*(.+)")

    cost_data: Dict[str, Any] = {}
    breakdown: Dict[str, Any] = {}
    currency: Optional[str] = None

    for match in cost_pattern.finditer(text):
        label = match.group(1)
        amount = float(match.group(2))
        currency = currency or match.group(3)
        if label == "总成本":
            cost_data["total"] = amount
        elif label == "输入成本":
            breakdown["input"] = amount
        elif label == "输出成本":
            breakdown["output"] = amount

    if breakdown:
        cost_data["breakdown"] = breakdown

    rates: Dict[str, Any] = {}
    for match in rate_pattern.finditer(text):
        label = match.group(1)
        amount = float(match.group(2))
        currency = currency or match.group(3)
        if label == "输入费率":
            rates["input_per_1k_tokens"] = amount
        elif label == "输出费率":
            rates["output_per_1k_tokens"] = amount

    if rates:
        cost_data["rates"] = rates

    model_match = model_pattern.search(text)
    if model_match:
        cost_data["pricing_model"] = model_match.group(1).strip()

    if currency:
        cost_data["currency"] = currency

    if not cost_data:
        return None

    return cost_data


def _parse_stage_table(text: str) -> Dict[str, Dict[str, Any]]:
    lines = text.splitlines()
    in_section = False
    in_table = False
    stage_updates: Dict[str, Dict[str, Any]] = {}

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## ") and "阶段执行详情" in stripped:
            in_section = True
            in_table = False
            continue
        if in_section and stripped.startswith("## "):
            break
        if not in_section:
            continue
        if not stripped:
            continue
        if stripped.startswith("| 阶段名称"):
            in_table = True
            continue
        if not in_table:
            continue
        if set(stripped) <= {"|", "-", " "}:
            continue
        if not stripped.startswith("|"):
            break

        cells = [cell.strip() for cell in stripped.split("|")[1:-1]]
        if len(cells) < 7:
            continue

        stage_name, status_text, duration_text, input_tokens_text, output_tokens_text, tool_calls_text, efficiency_text = cells[:7]
        status = _status_from_symbol(status_text)
        duration = _parse_float(duration_text)
        input_tokens = _parse_token_string(input_tokens_text)
        output_tokens = _parse_token_string(output_tokens_text)
        tool_calls = _coerce_int(tool_calls_text)
        efficiency = efficiency_text.strip()

        stage_updates[stage_name] = {
            "status": status,
            "duration_seconds": duration,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "tool_calls": tool_calls,
            "metadata": {"efficiency": efficiency} if efficiency else {},
        }

    return stage_updates


def _parse_status_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}

    project_list = data.get("project_info")
    if not isinstance(project_list, list) or not project_list:
        return {}

    project_data = project_list[0]
    pipeline = project_data.get("pipeline") or []
    stages: Dict[str, Dict[str, Any]] = {}

    for entry in pipeline:
        if not isinstance(entry, dict):
            continue
        stage_name = entry.get("stage")
        if not stage_name:
            continue
        status = _status_from_yaml(entry.get("status"))
        updated_at = _parse_datetime(entry.get("updated_date"))
        metadata: Dict[str, Any] = {}
        description = _coerce_str(entry.get("description"))
        if description:
            metadata["description"] = description
        doc_path = _coerce_str(entry.get("doc_path"))
        if doc_path:
            metadata["doc_path"] = doc_path
        artifacts = entry.get("agent_artifact_path")
        if artifacts:
            metadata["artifacts"] = artifacts

        stages[stage_name] = {
            "status": status,
            "completed_at": updated_at if status == StageStatus.COMPLETED else None,
            "metadata": metadata,
        }

    progress_info = None
    progress_data = project_data.get("progress")
    if isinstance(progress_data, list) and progress_data:
        entry = progress_data[0]
        if isinstance(entry, dict):
            completed = _coerce_int(entry.get("completed"))
            total = _coerce_int(entry.get("total"))
            percentage = (completed / total * 100) if completed is not None and total else None
            progress_info = {
                "completed": completed,
                "total": total,
                "percentage": percentage,
            }

    return {
        "stages": stages,
        "progress": progress_info,
        "project_name": _coerce_str(project_data.get("name")),
        "description": _coerce_str(project_data.get("description")),
        "updated_at": _parse_datetime(project_data.get("last_updated")),
    }


def _parse_project_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    total_tools = _coerce_int(data.get("total_tools"))
    project_name = _coerce_str(data.get("project_name"))

    metrics: Dict[str, Any] = {}
    if total_tools is not None:
        metrics["total_tools"] = total_tools

    return {
        "project_name": project_name,
        "metrics": metrics,
    }


def _parse_token_string(value: str, unit: Optional[str] = None) -> Optional[int]:
    if value is None:
        return None
    try:
        numeric, multiplier = _extract_numeric_and_unit(value, unit)
    except ValueError:
        return None

    return int(numeric * multiplier)


def _extract_numeric_and_unit(value: str, explicit_unit: Optional[str] = None) -> Tuple[float, float]:
    cleaned = value.replace(",", "").strip()
    unit = explicit_unit.strip() if explicit_unit else ""
    match = re.match(r"([0-9]+(?:\.[0-9]+)?)\s*([KMB]?)", cleaned, flags=re.IGNORECASE)
    if match:
        number = float(match.group(1))
        unit = unit or match.group(2)
    else:
        number = float(cleaned)

    multiplier = {"": 1.0, "K": 1_000.0, "M": 1_000_000.0, "B": 1_000_000_000.0}
    factor = multiplier.get(unit.upper(), 1.0)
    return number, factor


def _status_from_symbol(value: str) -> StageStatus:
    normalized = value.strip().lower()
    if any(token in normalized for token in ("✅", "✔", "success", "完成", "已完成")):
        return StageStatus.COMPLETED
    if any(token in normalized for token in ("❌", "✖", "失败", "failed", "error")):
        return StageStatus.FAILED
    if any(token in normalized for token in ("⚠", "⚠️", "进行", "running", "in progress", "处理中", "⏳", "等待")):
        return StageStatus.RUNNING
    return StageStatus.PENDING


def _status_from_yaml(value: Any) -> StageStatus:
    if value is None:
        return StageStatus.PENDING
    if isinstance(value, bool):
        return StageStatus.COMPLETED if value else StageStatus.FAILED
    lowered = str(value).lower()
    if lowered in {"completed", "complete", "success", "done", "true"}:
        return StageStatus.COMPLETED
    if lowered in {"failed", "failure", "error", "false"}:
        return StageStatus.FAILED
    if lowered in {"running", "in_progress", "processing"}:
        return StageStatus.RUNNING
    return StageStatus.PENDING


def _parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value)
        except (ValueError, OSError):
            return None
    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None
        candidate = candidate.replace("Z", "+00:00") if candidate.endswith("Z") else candidate
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            return None
    return None


def _coerce_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return str(value)


def _coerce_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, Decimal):
        return int(value)
    if isinstance(value, float):
        return int(value)
    try:
        cleaned = str(value).replace(",", "").strip()
        return int(float(cleaned))
    except (ValueError, TypeError):
        return None


def _parse_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, float):
        return value
    if isinstance(value, int):
        return float(value)
    if isinstance(value, Decimal):
        return float(value)
    try:
        cleaned = str(value).replace(",", "").strip()
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _coerce_float(value: Any) -> float:
    parsed = _parse_float(value)
    return parsed if parsed is not None else 0.0


def _coerce_project_status(value: Any) -> ProjectStatus:
    if isinstance(value, ProjectStatus):
        return value
    if isinstance(value, str):
        try:
            return ProjectStatus(value)
        except ValueError:
            return ProjectStatus.PENDING
    return ProjectStatus.PENDING


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _normalize(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, Decimal):
        return float(value)
    return value


def _max_datetime(current: Optional[datetime], candidate: Optional[datetime]) -> Optional[datetime]:
    if candidate is None:
        return current
    if current is None:
        return candidate
    try:
        if candidate > current:
            return candidate
    except TypeError:
        # Fallback for naive/aware mismatch - prefer candidate.
        return candidate
    return current


def _max_float(values: list[Optional[float]]) -> Optional[float]:
    filtered = [value for value in values if value is not None]
    if not filtered:
        return None
    return max(filtered)
