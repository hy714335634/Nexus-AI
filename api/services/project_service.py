"""
Project Service - 项目生命周期管理

职责:
- 创建项目并初始化阶段
- 查询项目详情和列表
- 更新项目状态
- 删除项目（级联删除）
- 项目控制操作（pause/resume/stop/restart）
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from decimal import Decimal

from api.database.dynamodb_client import db_client
from api.models.schemas import (
    ProjectRecord,
    ProjectStatus,
    BuildStage,
    create_stage_data,
)
from api.services.stage_service import stage_service
from api.core.exceptions import APIException, ResourceNotFoundError

logger = logging.getLogger(__name__)


class ProjectService:
    """项目管理服务"""

    def __init__(self):
        self.db_client = db_client
        self.stage_service = stage_service

    def create_project(
        self,
        project_id: str,
        requirement: str,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        project_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        priority: int = 3,
        agent_name_map: Optional[Dict[BuildStage, Optional[str]]] = None
    ) -> Dict[str, Any]:
        """
        创建项目并初始化阶段

        Args:
            project_id: 项目ID
            requirement: 需求描述
            user_id: 用户ID
            user_name: 用户名
            project_name: 项目名称
            tags: 标签列表
            priority: 优先级 (1-5)
            agent_name_map: 阶段到Agent名称的映射（可选）

        Returns:
            Dict: 创建的项目数据

        Requirements: 3.1
        """
        try:
            # 创建项目记录
            now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

            project_data = ProjectRecord(
                project_id=project_id,
                project_name=project_name or self._extract_project_name(requirement, project_id),
                original_requirement=requirement,
                user_id=user_id or "default",  # user_id is required in ProjectRecord
                user_name=user_name,
                tags=tags or [],
                priority=priority,
                status=ProjectStatus.BUILDING,
                progress_percentage=0.0,
                current_stage=BuildStage.ORCHESTRATOR,
                created_at=now,
                updated_at=now,
                stages_snapshot={}  # 稍后由initialize_stages填充
            )

            self.db_client.create_project(project_data)
            logger.info(f"Created project {project_id}")

            # 初始化6个阶段
            self.stage_service.initialize_stages(project_id, agent_name_map=agent_name_map)
            logger.info(f"Initialized stages for project {project_id}")

            # 重新获取项目（包含stages_snapshot）
            project = self.db_client.get_project(project_id)
            return project

        except Exception as e:
            logger.error(f"Failed to create project {project_id}: {str(e)}")
            raise APIException(f"Failed to create project: {str(e)}")

    def get_project(self, project_id: str) -> Dict[str, Any]:
        """
        查询项目详情（包含完整阶段信息）

        Args:
            project_id: 项目ID

        Returns:
            Dict: 项目详细信息

        Requirements: 3.2
        """
        try:
            project = self.db_client.get_project(project_id)
            if not project:
                raise ResourceNotFoundError("Project", project_id)

            # 确保stages_snapshot存在
            if not project.get("stages_snapshot"):
                logger.warning(f"Project {project_id} missing stages_snapshot, initializing...")
                self.stage_service.initialize_stages(project_id)
                project = self.db_client.get_project(project_id)

            return project

        except ResourceNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get project {project_id}: {str(e)}")
            raise APIException(f"Failed to get project: {str(e)}")

    def list_projects(
        self,
        limit: int = 20,
        last_key: Optional[str] = None,
        user_id: Optional[str] = None,
        status: Optional[ProjectStatus] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        查询项目列表（支持过滤和分页）

        Args:
            limit: 每页数量
            last_key: 分页游标
            user_id: 用户ID过滤
            status: 状态过滤
            tags: 标签过滤

        Returns:
            Dict: 包含items和last_evaluated_key的响应

        Requirements: 3.3
        """
        try:
            # 根据过滤条件选择查询方法
            if user_id:
                result = self.db_client.list_projects_by_user(
                    user_id=user_id,
                    limit=limit,
                    last_key=last_key
                )
            elif status:
                result = self.db_client.list_projects_by_status(
                    status=status,
                    limit=limit,
                    last_key=last_key
                )
            else:
                # Build filters dict for DynamoDB client
                filters = {}
                if status:
                    filters['status'] = status
                if user_id:
                    filters['user_id'] = user_id
                if tags:
                    filters['tags'] = tags

                result = self.db_client.list_projects(
                    limit=limit,
                    last_key=last_key,
                    filters=filters if filters else None
                )

            return result

        except Exception as e:
            logger.error(f"Failed to list projects: {str(e)}")
            raise APIException(f"Failed to list projects: {str(e)}")

    def update_project_status(
        self,
        project_id: str,
        status: ProjectStatus,
        **kwargs
    ) -> None:
        """
        更新项目状态

        Args:
            project_id: 项目ID
            status: 新状态
            **kwargs: 其他字段（error_info, completed_at等）

        Requirements: 3.4, 10.1
        """
        try:
            self.db_client.update_project_status(project_id, status, **kwargs)
            logger.info(f"Updated project {project_id} status to {status.value}")

        except Exception as e:
            logger.error(f"Failed to update project status: {str(e)}")
            raise APIException(f"Failed to update project status: {str(e)}")

    def delete_project(self, project_id: str) -> None:
        """
        删除项目（级联删除所有关联数据）

        级联删除顺序:
        1. AgentInstances (通过project_id)
        2. AgentProjects (项目本身)

        注意: 其他关联数据（sessions, invocations, artifacts）的删除方法将在后续添加

        Args:
            project_id: 项目ID

        Requirements: 3.5, 10.3
        """
        try:
            # 验证项目存在
            project = self.db_client.get_project(project_id)
            if not project:
                raise ResourceNotFoundError("Project", project_id)

            # 1. 查找并删除项目关联的所有agents
            agents = self.db_client.list_agents_by_project(project_id)
            agent_ids = [agent['agent_id'] for agent in agents]

            logger.info(f"Deleting project {project_id} with {len(agent_ids)} agents")

            for agent_id in agent_ids:
                self.db_client.delete_agent_record(agent_id)

            # 2. 最后删除项目本身
            self.db_client.delete_project(project_id)

            logger.info(f"Successfully deleted project {project_id} and {len(agent_ids)} associated agents")

        except ResourceNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to delete project {project_id}: {str(e)}")
            raise APIException(f"Failed to delete project: {str(e)}")

    def control_project(
        self,
        project_id: str,
        action: str,
        reason: Optional[str] = None
    ) -> None:
        """
        控制项目（pause/resume/stop/restart）

        Args:
            project_id: 项目ID
            action: 操作类型 (pause/resume/stop/restart)
            reason: 操作原因

        Requirements: 3.4
        """
        try:
            project = self.db_client.get_project(project_id)
            if not project:
                raise ResourceNotFoundError("Project", project_id)

            current_status = ProjectStatus(project['status'])

            # 状态转换规则
            status_transitions = {
                'pause': {
                    'allowed_from': [ProjectStatus.BUILDING],
                    'new_status': ProjectStatus.PAUSED
                },
                'resume': {
                    'allowed_from': [ProjectStatus.PAUSED],
                    'new_status': ProjectStatus.BUILDING
                },
                'stop': {
                    'allowed_from': [ProjectStatus.BUILDING, ProjectStatus.PAUSED],
                    'new_status': ProjectStatus.FAILED
                },
                'restart': {
                    'allowed_from': [ProjectStatus.FAILED, ProjectStatus.COMPLETED],
                    'new_status': ProjectStatus.BUILDING
                }
            }

            if action not in status_transitions:
                raise ValueError(f"Invalid action: {action}. Must be one of {list(status_transitions.keys())}")

            transition = status_transitions[action]
            if current_status not in transition['allowed_from']:
                raise APIException(
                    f"Cannot {action} project with status {current_status.value}. "
                    f"Allowed statuses: {[s.value for s in transition['allowed_from']]}"
                )

            # 更新状态
            update_data = {}
            if reason:
                update_data['control_reason'] = reason

            self.update_project_status(project_id, transition['new_status'], **update_data)
            logger.info(f"Project {project_id} {action}ed: {current_status.value} -> {transition['new_status'].value}")

        except (ResourceNotFoundError, ValueError):
            raise
        except Exception as e:
            logger.error(f"Failed to control project {project_id}: {str(e)}")
            raise APIException(f"Failed to control project: {str(e)}")

    def _extract_project_name(self, requirement: str, project_id: str) -> str:
        """从需求文本中提取项目名称"""
        if not requirement or not requirement.strip():
            return project_id

        # 取第一行作为项目名称，限制长度
        first_line = requirement.strip().splitlines()[0].strip()
        if not first_line:
            return project_id

        # 限制长度为80字符
        if len(first_line) > 80:
            first_line = first_line[:77].rstrip() + "..."

        return first_line


# Singleton instance
project_service = ProjectService()
