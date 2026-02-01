"""
Workflow Service - 统一的工作流管理服务

支持多种工作流类型：
- agent_build: Agent 构建工作流
- agent_update: Agent 更新工作流
- tool_build: 工具构建工作流

职责:
- 创建工作流项目并提交任务到 SQS
- 查询工作流状态
- 工作流控制操作
"""
import uuid
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from api.v2.database import db_client, sqs_client
from api.v2.models.schemas import ProjectStatus, TaskStatus, StageStatus
from api.v2.models.workflow_schemas import WorkflowType, TaskType
from api.v2.config import settings
from api.v2.services.agent_service import agent_service
from nexus_utils.workflow_config import (
    get_workflow_config,
    get_agent_update_workflow,
    get_tool_build_workflow,
)

logger = logging.getLogger(__name__)


class WorkflowService:
    """统一的工作流管理服务"""
    
    def __init__(self):
        self.db = db_client
        self.sqs = sqs_client
    
    def _now(self) -> str:
        """获取当前 UTC 时间的 ISO 格式字符串"""
        return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    def _generate_project_id(self) -> str:
        """生成项目 ID"""
        return str(uuid.uuid4())
    
    def _generate_task_id(self) -> str:
        """生成任务 ID"""
        return str(uuid.uuid4())
    
    def _get_workflow_stages(self, workflow_type: str) -> List[Dict[str, Any]]:
        """
        获取工作流的阶段配置
        
        Args:
            workflow_type: 工作流类型
            
        Returns:
            阶段配置列表
        """
        workflow_config = get_workflow_config(workflow_type)
        if not workflow_config:
            raise ValueError(f"Unknown workflow type: {workflow_type}")
        
        stages = []
        for stage in workflow_config.stages:
            stages.append({
                'stage_name': stage.name,
                'stage_number': stage.order,
                'display_name': stage.display_name,
                'status': StageStatus.PENDING.value,
                'optional': stage.optional,
                'supports_iteration': stage.supports_iteration,
            })
        
        return stages
    
    def _initialize_stages(
        self, 
        project_id: str, 
        workflow_type: str
    ) -> List[Dict[str, Any]]:
        """
        初始化工作流阶段记录
        
        Args:
            project_id: 项目 ID
            workflow_type: 工作流类型
            
        Returns:
            创建的阶段记录列表
        """
        stages = self._get_workflow_stages(workflow_type)
        now = self._now()
        
        created_stages = []
        for stage in stages:
            stage_data = {
                'project_id': project_id,
                'stage_name': stage['stage_name'],
                'stage_number': stage['stage_number'],
                'display_name': stage['display_name'],
                'status': StageStatus.PENDING.value,
                'created_at': now,
            }
            self.db.create_stage(stage_data)
            created_stages.append(stage_data)
        
        return created_stages

    # ============== Agent Update Workflow ==============
    
    def create_agent_update_project(
        self,
        agent_id: str,
        update_requirement: str,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        priority: int = 3,
    ) -> Dict[str, Any]:
        """
        创建 Agent 更新项目
        
        Args:
            agent_id: 要更新的 Agent ID
            update_requirement: 更新需求描述
            user_id: 用户 ID
            user_name: 用户名
            priority: 优先级
            
        Returns:
            创建的项目信息
        """
        # 使用 agent_service 验证 Agent 存在（支持本地和数据库）
        agent = agent_service.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        project_id = self._generate_project_id()
        task_id = self._generate_task_id()
        now = self._now()
        
        # 从 Agent 获取关联的项目信息
        original_project_id = agent.get('project_id')
        agent_name = agent.get('agent_name', agent_id)
        
        # 创建项目记录
        project_data = {
            'project_id': project_id,
            'project_name': f"update_{agent_name}_{now[:10]}",
            'workflow_type': WorkflowType.AGENT_UPDATE.value,
            'status': ProjectStatus.QUEUED.value,
            'requirement': update_requirement,
            'user_id': user_id,
            'user_name': user_name,
            'priority': priority,
            'progress': 0.0,
            'control_status': 'running',
            'metadata': {
                'agent_id': agent_id,
                'agent_name': agent_name,
                'original_project_id': original_project_id,
            },
            'created_at': now,
            'updated_at': now,
        }
        
        self.db.create_project(project_data)
        
        # 初始化阶段
        stages = self._initialize_stages(project_id, WorkflowType.AGENT_UPDATE.value)
        
        # 创建任务记录
        task_data = {
            'task_id': task_id,
            'task_type': TaskType.UPDATE_AGENT.value,
            'project_id': project_id,
            'status': TaskStatus.QUEUED.value,
            'priority': priority,
            'payload': {
                'agent_id': agent_id,
                'update_requirement': update_requirement,
            },
            'created_at': now,
            'updated_at': now,
        }
        self.db.create_task(task_data)
        
        # 发送到 SQS
        self.sqs.send_message(
            queue_name=settings.SQS_BUILD_QUEUE_NAME,
            message_body={
                'task_id': task_id,
                'project_id': project_id,
                'task_type': TaskType.UPDATE_AGENT.value,
                'workflow_type': WorkflowType.AGENT_UPDATE.value,
                'agent_id': agent_id,
                'requirement': update_requirement,
                'user_id': user_id,
                'priority': priority,
                'action': 'execute',
                'execute_to_completion': True,
            },
            message_attributes={
                'task_type': TaskType.UPDATE_AGENT.value,
                'workflow_type': WorkflowType.AGENT_UPDATE.value,
                'priority': str(priority),
            }
        )
        
        logger.info(f"Created agent update project {project_id} for agent {agent_id}")
        
        return {
            'project_id': project_id,
            'task_id': task_id,
            'agent_id': agent_id,
            'workflow_type': WorkflowType.AGENT_UPDATE.value,
            'status': ProjectStatus.QUEUED.value,
            'stages': [s['stage_name'] for s in stages],
        }
    
    # ============== Tool Build Workflow ==============
    
    def create_tool_build_project(
        self,
        requirement: str,
        tool_name: Optional[str] = None,
        category: Optional[str] = None,
        target_agent: Optional[str] = None,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        priority: int = 3,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        创建工具构建项目
        
        Args:
            requirement: 工具需求描述
            tool_name: 工具名称（可选，会自动生成）
            category: 工具类别
            target_agent: 目标 Agent（可选）
            user_id: 用户 ID
            user_name: 用户名
            priority: 优先级
            tags: 标签列表
            
        Returns:
            创建的项目信息
        """
        project_id = self._generate_project_id()
        task_id = self._generate_task_id()
        now = self._now()
        
        # 生成工具名称（如果未提供）
        if not tool_name:
            tool_name = f"tool_{project_id[:8]}"
        
        # 创建项目记录
        project_data = {
            'project_id': project_id,
            'project_name': tool_name,
            'workflow_type': WorkflowType.TOOL_BUILD.value,
            'status': ProjectStatus.QUEUED.value,
            'requirement': requirement,
            'user_id': user_id,
            'user_name': user_name,
            'priority': priority,
            'tags': tags or [],
            'progress': 0.0,
            'control_status': 'running',
            'metadata': {
                'tool_name': tool_name,
                'category': category,
                'target_agent': target_agent,
            },
            'created_at': now,
            'updated_at': now,
        }
        
        self.db.create_project(project_data)
        
        # 初始化阶段
        stages = self._initialize_stages(project_id, WorkflowType.TOOL_BUILD.value)
        
        # 创建任务记录
        task_data = {
            'task_id': task_id,
            'task_type': TaskType.BUILD_TOOL.value,
            'project_id': project_id,
            'status': TaskStatus.QUEUED.value,
            'priority': priority,
            'payload': {
                'tool_name': tool_name,
                'requirement': requirement,
                'category': category,
                'target_agent': target_agent,
            },
            'created_at': now,
            'updated_at': now,
        }
        self.db.create_task(task_data)
        
        # 发送到 SQS
        self.sqs.send_message(
            queue_name=settings.SQS_BUILD_QUEUE_NAME,
            message_body={
                'task_id': task_id,
                'project_id': project_id,
                'task_type': TaskType.BUILD_TOOL.value,
                'workflow_type': WorkflowType.TOOL_BUILD.value,
                'tool_name': tool_name,
                'requirement': requirement,
                'category': category,
                'target_agent': target_agent,
                'user_id': user_id,
                'priority': priority,
                'action': 'execute',
                'execute_to_completion': True,
            },
            message_attributes={
                'task_type': TaskType.BUILD_TOOL.value,
                'workflow_type': WorkflowType.TOOL_BUILD.value,
                'priority': str(priority),
            }
        )
        
        logger.info(f"Created tool build project {project_id} for tool {tool_name}")
        
        return {
            'project_id': project_id,
            'task_id': task_id,
            'tool_name': tool_name,
            'workflow_type': WorkflowType.TOOL_BUILD.value,
            'status': ProjectStatus.QUEUED.value,
            'stages': [s['stage_name'] for s in stages],
        }
    
    # ============== Workflow Status ==============
    
    def get_workflow_status(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        获取工作流状态
        
        Args:
            project_id: 项目 ID
            
        Returns:
            工作流状态信息
        """
        project = self.db.get_project(project_id)
        if not project:
            return None
        
        stages = self.db.list_stages(project_id)
        
        completed_stages = [
            s['stage_name'] for s in stages 
            if s.get('status') == StageStatus.COMPLETED.value
        ]
        pending_stages = [
            s['stage_name'] for s in stages 
            if s.get('status') == StageStatus.PENDING.value
        ]
        
        return {
            'project_id': project_id,
            'workflow_type': project.get('workflow_type', WorkflowType.AGENT_BUILD.value),
            'status': project.get('status'),
            'control_status': project.get('control_status', 'running'),
            'current_stage': project.get('current_stage'),
            'completed_stages': completed_stages,
            'pending_stages': pending_stages,
            'progress': project.get('progress', 0.0),
            'error_info': project.get('error_info'),
            'metadata': project.get('metadata'),
        }


# 全局服务实例
workflow_service = WorkflowService()
