"""
Stage Service - 阶段状态管理和查询

职责:
- 初始化项目的6个阶段
- 更新阶段状态（原子操作）
- 更新子阶段状态（Developer Manager）
- 查询阶段详情和列表
- 计算项目进度百分比
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from decimal import Decimal

from api.database.dynamodb_client import db_client
from api.models.schemas import (
    BuildStage,
    StageStatus,
    StageData,
    create_stage_data,
    build_initial_stage_snapshot,
)
from api.core.exceptions import APIException, ResourceNotFoundError

logger = logging.getLogger(__name__)


class StageService:
    """阶段管理服务"""

    def __init__(self):
        self.db_client = db_client

    def initialize_stages(self, project_id: str, agent_name_map: Optional[Dict[BuildStage, Optional[str]]] = None) -> None:
        """
        初始化项目的6个阶段到stages_snapshot

        Args:
            project_id: 项目ID
            agent_name_map: 阶段到Agent名称的映射（可选）

        Requirements: 3.1, 7.1
        """
        try:
            self.db_client.initialize_project_stages(
                project_id,
                agent_name_map=agent_name_map
            )
            logger.info(f"Initialized 6 stages for project {project_id}")
        except Exception as e:
            logger.error(f"Failed to initialize stages for project {project_id}: {str(e)}")
            raise APIException(f"Failed to initialize project stages: {str(e)}")

    def update_stage_status(
        self,
        project_id: str,
        stage: BuildStage,
        status: StageStatus,
        **kwargs
    ) -> float:
        """
        原子更新阶段状态并重新计算进度

        Args:
            project_id: 项目ID
            stage: 阶段枚举
            status: 新状态
            **kwargs: 其他字段（started_at, completed_at, output_data, error_message, logs等）

        Returns:
            float: 更新后的进度百分比

        Requirements: 7.2, 7.3, 7.4, 10.1, 10.4
        """
        try:
            stage_number = BuildStage.get_stage_number(stage)

            # 更新阶段状态
            self.db_client.update_stage_status(
                project_id=project_id,
                stage_number=stage_number,
                status=status,
                **kwargs
            )

            # 重新计算进度
            progress = self.calculate_project_progress(project_id)

            # 更新项目进度
            self.db_client.update_project_progress(
                project_id=project_id,
                progress_percentage=progress,
                current_stage=stage
            )

            logger.info(f"Updated stage {stage.value} for project {project_id} to {status.value}, progress: {progress}%")
            return progress

        except Exception as e:
            logger.error(f"Failed to update stage status: {str(e)}")
            raise APIException(f"Failed to update stage status: {str(e)}")

    def update_sub_stage_status(
        self,
        project_id: str,
        sub_stage_name: str,
        status: StageStatus,
        artifacts: Optional[List[str]] = None,
        **kwargs
    ) -> float:
        """
        更新子阶段状态（仅限agent_developer_manager阶段）

        Args:
            project_id: 项目ID
            sub_stage_name: 子阶段名称（tool_developer, prompt_engineer, agent_code_developer）
            status: 新状态
            artifacts: 产物文件列表
            **kwargs: 其他字段（started_at, completed_at等）

        Returns:
            float: 更新后的进度百分比

        Requirements: 7.2, 7.3
        """
        # 验证子阶段名称（在try块外，这样ValueError会直接抛出）
        valid_sub_stages = ["tool_developer", "prompt_engineer", "agent_code_developer"]
        if sub_stage_name not in valid_sub_stages:
            raise ValueError(f"Invalid sub_stage_name: {sub_stage_name}. Must be one of {valid_sub_stages}")

        try:

            # 获取项目当前的stages_snapshot
            project = self.db_client.get_project(project_id)
            if not project:
                raise ResourceNotFoundError("Project", project_id)

            stages_snapshot = project.get("stages_snapshot", {})
            if not isinstance(stages_snapshot, dict):
                raise APIException(f"Invalid stages_snapshot format for project {project_id}")

            stages_list = stages_snapshot.get("stages", [])

            # 查找agent_developer_manager阶段并更新子阶段
            updated = False
            for stage in stages_list:
                if stage.get("stage_name") == "agent_developer_manager":
                    if "sub_stages" not in stage:
                        stage["sub_stages"] = {
                            "tool_developer": {"status": "pending", "started_at": None, "completed_at": None, "artifacts": []},
                            "prompt_engineer": {"status": "pending", "started_at": None, "completed_at": None, "artifacts": []},
                            "agent_code_developer": {"status": "pending", "started_at": None, "completed_at": None, "artifacts": []}
                        }

                    # 更新子阶段
                    sub_stage = stage["sub_stages"].get(sub_stage_name, {})
                    sub_stage["status"] = status.value if isinstance(status, StageStatus) else status

                    if artifacts is not None:
                        sub_stage["artifacts"] = artifacts

                    # 更新时间戳
                    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                    if status == StageStatus.RUNNING and "started_at" not in kwargs:
                        sub_stage["started_at"] = now
                    elif status == StageStatus.COMPLETED and "completed_at" not in kwargs:
                        sub_stage["completed_at"] = now

                    for key, value in kwargs.items():
                        if value is not None:
                            if isinstance(value, datetime):
                                value = value.isoformat().replace('+00:00', 'Z')
                            sub_stage[key] = value

                    stage["sub_stages"][sub_stage_name] = sub_stage
                    updated = True
                    break

            if not updated:
                raise APIException(f"agent_developer_manager stage not found in project {project_id}")

            # 更新stages_snapshot到数据库
            import json
            serialized_snapshot = json.dumps(stages_snapshot, default=str)
            self.db_client.projects_table.update_item(
                Key={'project_id': project_id},
                UpdateExpression="SET stages_snapshot = :snapshot, updated_at = :updated_at",
                ExpressionAttributeValues={
                    ':snapshot': serialized_snapshot,
                    ':updated_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                }
            )

            # 重新计算进度
            progress = self.calculate_project_progress(project_id)
            self.db_client.update_project_progress(
                project_id=project_id,
                progress_percentage=progress
            )

            logger.info(f"Updated sub-stage {sub_stage_name} for project {project_id} to {status.value}, progress: {progress}%")
            return progress

        except (ResourceNotFoundError, APIException):
            # 让ResourceNotFoundError和APIException直接抛出，不包装
            raise
        except Exception as e:
            logger.error(f"Failed to update sub-stage status: {str(e)}")
            raise APIException(f"Failed to update sub-stage status: {str(e)}")

    def get_stage(self, project_id: str, stage_name: str) -> Dict[str, Any]:
        """
        获取特定阶段的详细信息

        Args:
            project_id: 项目ID
            stage_name: 阶段名称

        Returns:
            Dict: 阶段详细信息

        Requirements: 7.5
        """
        try:
            stages = self.list_stages(project_id)

            for stage in stages:
                if stage.get("stage_name") == stage_name:
                    return stage

            raise ResourceNotFoundError("Stage", stage_name)

        except ResourceNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get stage {stage_name} for project {project_id}: {str(e)}")
            raise APIException(f"Failed to get stage: {str(e)}")

    def list_stages(self, project_id: str) -> List[Dict[str, Any]]:
        """
        列出项目的所有阶段

        Args:
            project_id: 项目ID

        Returns:
            List[Dict]: 阶段列表

        Requirements: 7.5
        """
        try:
            return self.db_client.list_project_stages(project_id)
        except Exception as e:
            logger.error(f"Failed to list stages for project {project_id}: {str(e)}")
            raise APIException(f"Failed to list project stages: {str(e)}")

    def calculate_project_progress(self, project_id: str) -> float:
        """
        根据stages_snapshot计算项目进度百分比

        算法:
        - 各阶段权重: orchestrator(5%), requirements(10%), architecture(15%),
                     design(15%), developer_manager(45%), deployer(10%)
        - developer_manager的子阶段权重: tool(40%), prompt(30%), code(30%)
        - running状态的阶段计为50%完成（或子阶段加权）

        Args:
            project_id: 项目ID

        Returns:
            float: 进度百分比 (0.0 - 100.0)

        Requirements: 3.2, 7.3
        """
        try:
            stages = self.list_stages(project_id)
            return self.calculate_progress_from_stages(stages)
        except Exception as e:
            logger.error(f"Failed to calculate progress for project {project_id}: {str(e)}")
            raise APIException(f"Failed to calculate project progress: {str(e)}")

    def calculate_progress_from_stages(self, stages: List[Dict[str, Any]]) -> float:
        """
        从阶段列表计算进度百分比（静态方法，可用于测试）

        Args:
            stages: 阶段列表

        Returns:
            float: 进度百分比 (0.0 - 100.0)

        Requirements: 3.2
        """
        # 阶段权重
        STAGE_WEIGHTS = {
            "orchestrator": 5.0,
            "requirements_analysis": 10.0,
            "system_architecture": 15.0,
            "agent_design": 15.0,
            "agent_developer_manager": 45.0,
            "agent_deployer": 10.0
        }

        # developer_manager子阶段权重
        SUB_STAGE_WEIGHTS = {
            "tool_developer": 0.40,
            "prompt_engineer": 0.30,
            "agent_code_developer": 0.30
        }

        total_progress = 0.0

        for stage in stages:
            stage_name = stage.get("stage_name", "")
            status = stage.get("status", "pending")
            weight = STAGE_WEIGHTS.get(stage_name, 0.0)

            if status == "completed":
                # 已完成阶段贡献100%权重
                total_progress += weight
            elif status == "running":
                # 正在运行的阶段
                if stage_name == "agent_developer_manager":
                    # 计算子阶段进度
                    sub_stages = stage.get("sub_stages", {})
                    sub_progress = 0.0

                    for sub_name, sub_weight in SUB_STAGE_WEIGHTS.items():
                        sub_stage = sub_stages.get(sub_name, {})
                        sub_status = sub_stage.get("status", "pending")

                        if sub_status == "completed":
                            sub_progress += sub_weight
                        elif sub_status == "running":
                            sub_progress += sub_weight * 0.5

                    total_progress += weight * sub_progress
                else:
                    # 其他阶段running状态计为50%
                    total_progress += weight * 0.5

        # 确保进度在0-100之间
        return max(0.0, min(100.0, total_progress))


# Singleton instance
stage_service = StageService()
