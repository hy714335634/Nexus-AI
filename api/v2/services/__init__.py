"""
API v2 Services
"""
from .project_service import ProjectService, project_service
from .agent_service import AgentService, agent_service
from .task_service import TaskService, task_service
from .session_service import SessionService, session_service
from .statistics_service import StatisticsService, statistics_service
from .stage_service import (
    StageServiceV2,
    stage_service_v2,
    mark_stage_running,
    mark_stage_completed,
    mark_stage_failed,
)
from .agent_cli_workflow_service import AgentCLIBuildService, AgentWorkflowOutput
from .agent_deployment_service import (
    AgentDeploymentService,
    AgentDeploymentError,
    DeploymentResult,
)

__all__ = [
    'ProjectService', 'project_service',
    'AgentService', 'agent_service',
    'TaskService', 'task_service',
    'SessionService', 'session_service',
    'StatisticsService', 'statistics_service',
    'StageServiceV2', 'stage_service_v2',
    'mark_stage_running', 'mark_stage_completed', 'mark_stage_failed',
    'AgentCLIBuildService', 'AgentWorkflowOutput',
    'AgentDeploymentService', 'AgentDeploymentError', 'DeploymentResult',
]
