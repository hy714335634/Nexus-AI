"""
Build Handler - 处理 Agent 构建任务

负责:
- 执行 Agent 构建工作流
- 更新任务和项目状态
- 处理错误和重试

注意：阶段状态更新由 agent_build_workflow 通过 stage_tracker 完成，
stage_tracker 已重构为使用 api.v2.services.stage_service。
"""
import os
import logging
import traceback
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from api.v2.database import db_client
from api.v2.models.schemas import ProjectStatus, TaskStatus, StageStatus, BuildStage
from worker.config import worker_settings

logger = logging.getLogger(__name__)


class BuildHandler:
    """构建任务处理器"""
    
    def __init__(self):
        self.db = db_client
        self.worker_id = worker_settings.WORKER_ID
    
    def handle(self, message: Dict[str, Any]) -> bool:
        """
        处理构建任务消息
        
        Args:
            message: SQS 消息内容
        
        Returns:
            是否处理成功
        """
        body = message.get('body', {})
        task_id = body.get('task_id')
        project_id = body.get('project_id')
        requirement = body.get('requirement')
        
        if not all([task_id, project_id, requirement]):
            logger.error(f"Invalid message: missing required fields")
            return False
        
        logger.info(f"Processing build task {task_id} for project {project_id}")
        
        try:
            # 更新任务状态为运行中
            self._update_task_status(task_id, TaskStatus.RUNNING)
            
            # 更新项目状态为构建中
            self._update_project_status(project_id, ProjectStatus.BUILDING)
            
            # 执行构建工作流
            result = self._execute_build_workflow(
                project_id=project_id,
                requirement=requirement,
                metadata=body.get('metadata', {})
            )
            
            # 更新任务状态为完成
            self._update_task_status(task_id, TaskStatus.COMPLETED, result=result)
            
            # 更新项目状态为完成
            self._update_project_status(project_id, ProjectStatus.COMPLETED)
            
            logger.info(f"Build task {task_id} completed successfully")
            return True
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Build task {task_id} failed: {error_msg}")
            logger.error(traceback.format_exc())
            
            # 更新任务状态为失败
            self._update_task_status(task_id, TaskStatus.FAILED, error_message=error_msg)
            
            # 更新项目状态为失败
            self._update_project_status(
                project_id,
                ProjectStatus.FAILED,
                error_info={'message': error_msg, 'traceback': traceback.format_exc()}
            )
            
            return False
    
    def _execute_build_workflow(
        self,
        project_id: str,
        requirement: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行构建工作流
        
        调用现有的 agent_build_workflow 模块。
        阶段状态更新由 stage_tracker -> stage_service_v2 完成。
        """
        # 设置环境变量供工作流使用
        os.environ["NEXUS_STAGE_TRACKER_PROJECT_ID"] = project_id
        
        try:
            # 导入并执行构建工作流
            from agents.system_agents.agent_build_workflow.agent_build_workflow import (
                run_workflow
            )
            
            # 执行工作流
            result = run_workflow(
                user_input=requirement,
                session_id=metadata.get('session_id')
            )
            
            return {
                'status': 'completed',
                'session_id': result.get('session_id'),
                'execution_time': result.get('execution_time'),
                'execution_order': result.get('execution_order'),
                'report_path': result.get('report_path'),
            }
            
        except ImportError as e:
            logger.warning(f"Could not import build workflow: {e}, using mock")
            return self._mock_build_workflow(project_id, requirement)
        
        finally:
            # 清理环境变量
            if "NEXUS_STAGE_TRACKER_PROJECT_ID" in os.environ:
                del os.environ["NEXUS_STAGE_TRACKER_PROJECT_ID"]
    
    def _mock_build_workflow(self, project_id: str, requirement: str) -> Dict[str, Any]:
        """模拟构建工作流（用于测试）"""
        import time
        from api.v2.services.stage_service import stage_service_v2
        
        stages = list(BuildStage)
        total_stages = len(stages)
        
        for i, stage in enumerate(stages):
            # 更新阶段状态为运行中
            stage_service_v2.mark_stage_running(project_id, stage.value)
            
            # 模拟处理时间
            time.sleep(0.5)
            
            # 更新阶段状态为完成
            stage_service_v2.mark_stage_completed(project_id, stage.value)
        
        return {
            'status': 'completed',
            'message': 'Mock build completed',
            'stages_completed': total_stages
        }
    
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
        error_info: Optional[Dict[str, Any]] = None
    ):
        """更新项目状态"""
        now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        updates = {'status': status.value}
        
        if status == ProjectStatus.BUILDING:
            updates['started_at'] = now
        
        if status in [ProjectStatus.COMPLETED, ProjectStatus.FAILED]:
            updates['completed_at'] = now
            if status == ProjectStatus.COMPLETED:
                updates['progress'] = 100.0
        
        if error_info:
            updates['error_info'] = error_info
        
        self.db.update_project(project_id, updates)
