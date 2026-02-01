"""
Workflow Handler - 统一的工作流任务处理器

支持多种工作流类型：
- agent_build: Agent 构建工作流
- agent_update: Agent 更新工作流
- tool_build: 工具构建工作流

负责:
- 根据工作流类型分发任务
- 使用 WorkflowEngine 执行工作流
- 更新任务和项目状态
- 处理错误和重试
"""
import os
import logging
import traceback
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from api.v2.database import db_client
from api.v2.models.schemas import ProjectStatus, TaskStatus, StageStatus
from worker.config import worker_settings

logger = logging.getLogger(__name__)


class WorkflowHandler:
    """
    统一的工作流任务处理器
    
    根据消息中的 workflow_type 字段分发到对应的工作流执行器
    """
    
    # 支持的工作流类型
    SUPPORTED_WORKFLOWS = ['agent_build', 'agent_update', 'tool_build']
    
    def __init__(self):
        """初始化工作流处理器"""
        self.db = db_client
        self.worker_id = worker_settings.WORKER_ID
    
    def handle(self, message: Dict[str, Any]) -> bool:
        """
        处理工作流任务消息
        
        根据 workflow_type 分发到对应的处理方法
        
        参数:
            message: SQS 消息内容
            
        返回:
            是否处理成功
        """
        body = message.get('body', {})
        task_id = body.get('task_id')
        project_id = body.get('project_id')
        workflow_type = body.get('workflow_type', 'agent_build')
        task_type = body.get('task_type', 'build_agent')
        
        if not all([task_id, project_id]):
            logger.error("Invalid message: missing required fields (task_id, project_id)")
            return False
        
        logger.info(f"Processing {workflow_type} task {task_id} for project {project_id}")
        
        # 根据工作流类型分发
        if workflow_type == 'agent_update':
            return self._handle_agent_update(message)
        elif workflow_type == 'tool_build':
            return self._handle_tool_build(message)
        else:
            # 默认使用 agent_build 处理器
            return self._handle_agent_build(message)
    
    def _handle_agent_build(self, message: Dict[str, Any]) -> bool:
        """
        处理 Agent 构建任务
        
        委托给现有的 BuildHandler
        """
        from worker.handlers.build_handler import BuildHandler
        handler = BuildHandler()
        return handler.handle(message)
    
    def _handle_agent_update(self, message: Dict[str, Any]) -> bool:
        """
        处理 Agent 更新任务
        
        参数:
            message: SQS 消息内容
            
        返回:
            是否处理成功
        """
        body = message.get('body', {})
        task_id = body.get('task_id')
        project_id = body.get('project_id')
        agent_id = body.get('agent_id')
        requirement = body.get('requirement')
        
        if not agent_id:
            logger.error("Invalid agent update message: missing agent_id")
            return False
        
        logger.info(f"Processing agent update task {task_id} for agent {agent_id}")
        
        try:
            # 更新任务状态为运行中
            self._update_task_status(task_id, TaskStatus.RUNNING)
            
            # 更新项目状态为构建中
            self._update_project_status(project_id, ProjectStatus.BUILDING, clear_error=True)
            
            # 执行 Agent 更新工作流
            result = self._execute_agent_update_workflow(
                project_id=project_id,
                agent_id=agent_id,
                requirement=requirement,
                metadata=body.get('metadata', {})
            )
            
            # 处理执行结果
            return self._handle_execution_result(task_id, project_id, result)
            
        except Exception as e:
            return self._handle_execution_error(task_id, project_id, e)
    
    def _handle_tool_build(self, message: Dict[str, Any]) -> bool:
        """
        处理工具构建任务
        
        参数:
            message: SQS 消息内容
            
        返回:
            是否处理成功
        """
        body = message.get('body', {})
        task_id = body.get('task_id')
        project_id = body.get('project_id')
        tool_name = body.get('tool_name')
        requirement = body.get('requirement')
        
        logger.info(f"Processing tool build task {task_id} for tool {tool_name}")
        
        try:
            # 更新任务状态为运行中
            self._update_task_status(task_id, TaskStatus.RUNNING)
            
            # 更新项目状态为构建中
            self._update_project_status(project_id, ProjectStatus.BUILDING, clear_error=True)
            
            # 执行工具构建工作流
            result = self._execute_tool_build_workflow(
                project_id=project_id,
                tool_name=tool_name,
                requirement=requirement,
                category=body.get('category'),
                target_agent=body.get('target_agent'),
                metadata=body.get('metadata', {})
            )
            
            # 处理执行结果
            return self._handle_execution_result(task_id, project_id, result)
            
        except Exception as e:
            return self._handle_execution_error(task_id, project_id, e)

    def _execute_agent_update_workflow(
        self,
        project_id: str,
        agent_id: str,
        requirement: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行 Agent 更新工作流
        
        参数:
            project_id: 项目ID
            agent_id: Agent ID
            requirement: 更新需求
            metadata: 元数据
            
        返回:
            执行结果字典
        """
        # 设置环境变量
        os.environ["NEXUS_STAGE_TRACKER_PROJECT_ID"] = project_id
        os.environ["NEXUS_UPDATE_AGENT_ID"] = agent_id
        
        try:
            from nexus_utils.workflow import (
                WorkflowEngine,
                WorkflowControlSignal,
                PrerequisiteError,
                StageStatus as WFStageStatus,
            )
            from nexus_utils.workflow_config import WorkflowType
            
            # 创建工作流引擎，指定工作流类型
            engine = WorkflowEngine(
                project_id, 
                db_client=self.db,
                config={'workflow_type': WorkflowType.AGENT_UPDATE.value}
            )
            
            # 设置回调函数
            engine.set_callbacks(
                on_stage_start=lambda stage: logger.info(f"[Agent Update] Stage {stage} started"),
                on_stage_complete=lambda stage, output: logger.info(
                    f"[Agent Update] Stage {stage} completed"
                ),
                on_stage_error=lambda stage, error: logger.error(
                    f"[Agent Update] Stage {stage} error: {error}"
                ),
            )
            
            # 执行工作流
            logger.info(f"Executing agent update workflow for agent {agent_id}")
            result = engine.execute_to_completion()
            
            return self._convert_execution_result(result)
            
        except ImportError as e:
            logger.error(f"WorkflowEngine import failed: {e}")
            return {
                'status': 'failed',
                'error_message': f"WorkflowEngine not available: {e}",
            }
        
        except PrerequisiteError as e:
            logger.error(f"Prerequisite check failed: {e}")
            return {
                'status': 'failed',
                'error_message': str(e),
            }
        
        except WorkflowControlSignal as e:
            if e.signal_type == WorkflowControlSignal.PAUSE:
                return {'status': 'paused', 'message': 'Workflow paused by user'}
            elif e.signal_type == WorkflowControlSignal.STOP:
                return {'status': 'stopped', 'message': 'Workflow stopped by user'}
            else:
                return {'status': 'failed', 'error_message': str(e)}
        
        finally:
            # 清理环境变量
            for key in ["NEXUS_STAGE_TRACKER_PROJECT_ID", "NEXUS_UPDATE_AGENT_ID"]:
                if key in os.environ:
                    del os.environ[key]
    
    def _execute_tool_build_workflow(
        self,
        project_id: str,
        tool_name: str,
        requirement: str,
        category: Optional[str],
        target_agent: Optional[str],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行工具构建工作流
        
        参数:
            project_id: 项目ID
            tool_name: 工具名称
            requirement: 工具需求
            category: 工具类别
            target_agent: 目标 Agent
            metadata: 元数据
            
        返回:
            执行结果字典
        """
        # 设置环境变量
        os.environ["NEXUS_STAGE_TRACKER_PROJECT_ID"] = project_id
        os.environ["NEXUS_TOOL_NAME"] = tool_name or ""
        if target_agent:
            os.environ["NEXUS_TARGET_AGENT"] = target_agent
        
        try:
            from nexus_utils.workflow import (
                WorkflowEngine,
                WorkflowControlSignal,
                PrerequisiteError,
                StageStatus as WFStageStatus,
            )
            from nexus_utils.workflow_config import WorkflowType
            
            # 创建工作流引擎，指定工作流类型
            engine = WorkflowEngine(
                project_id, 
                db_client=self.db,
                config={'workflow_type': WorkflowType.TOOL_BUILD.value}
            )
            
            # 设置回调函数
            engine.set_callbacks(
                on_stage_start=lambda stage: logger.info(f"[Tool Build] Stage {stage} started"),
                on_stage_complete=lambda stage, output: logger.info(
                    f"[Tool Build] Stage {stage} completed"
                ),
                on_stage_error=lambda stage, error: logger.error(
                    f"[Tool Build] Stage {stage} error: {error}"
                ),
            )
            
            # 执行工作流
            logger.info(f"Executing tool build workflow for tool {tool_name}")
            result = engine.execute_to_completion()
            
            return self._convert_execution_result(result)
            
        except ImportError as e:
            logger.error(f"WorkflowEngine import failed: {e}")
            return {
                'status': 'failed',
                'error_message': f"WorkflowEngine not available: {e}",
            }
        
        except PrerequisiteError as e:
            logger.error(f"Prerequisite check failed: {e}")
            return {
                'status': 'failed',
                'error_message': str(e),
            }
        
        except WorkflowControlSignal as e:
            if e.signal_type == WorkflowControlSignal.PAUSE:
                return {'status': 'paused', 'message': 'Workflow paused by user'}
            elif e.signal_type == WorkflowControlSignal.STOP:
                return {'status': 'stopped', 'message': 'Workflow stopped by user'}
            else:
                return {'status': 'failed', 'error_message': str(e)}
        
        finally:
            # 清理环境变量
            for key in ["NEXUS_STAGE_TRACKER_PROJECT_ID", "NEXUS_TOOL_NAME", "NEXUS_TARGET_AGENT"]:
                if key in os.environ:
                    del os.environ[key]
    
    def _convert_execution_result(self, result) -> Dict[str, Any]:
        """
        转换 ExecutionResult 为字典格式
        
        参数:
            result: ExecutionResult 对象
            
        返回:
            字典格式的结果
        """
        from nexus_utils.workflow import StageStatus as WFStageStatus
        
        # 映射状态
        status_map = {
            WFStageStatus.COMPLETED: 'completed',
            WFStageStatus.FAILED: 'failed',
            WFStageStatus.PAUSED: 'paused',
            WFStageStatus.PENDING: 'pending',
            WFStageStatus.RUNNING: 'running',
        }
        
        return {
            'status': status_map.get(result.final_status, 'unknown'),
            'success': result.success,
            'completed_stages': result.completed_stages,
            'failed_stage': result.failed_stage,
            'error_message': result.error_message,
            'metrics': result.metrics,
        }
    
    def _handle_execution_result(
        self, 
        task_id: str, 
        project_id: str, 
        result: Dict[str, Any]
    ) -> bool:
        """
        处理工作流执行结果
        
        参数:
            task_id: 任务ID
            project_id: 项目ID
            result: 执行结果
            
        返回:
            是否成功
        """
        status = result.get('status', 'unknown')
        
        if status == 'paused':
            self._update_task_status(task_id, TaskStatus.PENDING, result=result)
            self._update_project_status(project_id, ProjectStatus.PAUSED)
            logger.info(f"Task {task_id} paused")
            return True
        
        elif status == 'stopped':
            self._update_task_status(task_id, TaskStatus.CANCELLED, result=result)
            self._update_project_status(project_id, ProjectStatus.CANCELLED)
            logger.info(f"Task {task_id} stopped by user")
            return True
        
        elif status == 'failed':
            error_msg = result.get('error_message', 'Unknown error')
            self._update_task_status(task_id, TaskStatus.FAILED, error_message=error_msg)
            self._update_project_status(
                project_id,
                ProjectStatus.FAILED,
                error_info={'message': error_msg, 'failed_stage': result.get('failed_stage')}
            )
            logger.error(f"Task {task_id} failed: {error_msg}")
            return False
        
        # 成功完成
        self._update_task_status(task_id, TaskStatus.COMPLETED, result=result)
        self._update_project_status(project_id, ProjectStatus.COMPLETED)
        logger.info(f"Task {task_id} completed successfully")
        return True
    
    def _handle_execution_error(
        self, 
        task_id: str, 
        project_id: str, 
        error: Exception
    ) -> bool:
        """
        处理工作流执行错误
        
        参数:
            task_id: 任务ID
            project_id: 项目ID
            error: 异常对象
            
        返回:
            False（表示失败）
        """
        error_msg = str(error)
        logger.error(f"Task {task_id} failed: {error_msg}")
        logger.error(traceback.format_exc())
        
        self._update_task_status(task_id, TaskStatus.FAILED, error_message=error_msg)
        self._update_project_status(
            project_id,
            ProjectStatus.FAILED,
            error_info={'message': error_msg, 'traceback': traceback.format_exc()}
        )
        
        return False
    
    def _update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ):
        """更新任务状态"""
        now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        updates = {
            'status': status.value,
            'worker_id': self.worker_id
        }
        
        if status == TaskStatus.RUNNING:
            updates['started_at'] = now
        
        if status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            updates['completed_at'] = now
        
        if result:
            updates['result'] = result
        
        if error_message:
            updates['error_message'] = error_message
        
        self.db.update_task(task_id, updates)
    
    def _update_project_status(
        self,
        project_id: str,
        status: ProjectStatus,
        error_info: Optional[Dict[str, Any]] = None,
        clear_error: bool = False
    ):
        """更新项目状态"""
        now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        updates = {'status': status.value}
        
        if status == ProjectStatus.BUILDING:
            updates['started_at'] = now
            updates['control_status'] = 'running'
        
        if status in [ProjectStatus.COMPLETED, ProjectStatus.FAILED]:
            updates['completed_at'] = now
            if status == ProjectStatus.COMPLETED:
                updates['progress'] = 100.0
        
        if error_info:
            updates['error_info'] = error_info
        elif clear_error:
            updates['error_info'] = None
        
        self.db.update_project(project_id, updates)
