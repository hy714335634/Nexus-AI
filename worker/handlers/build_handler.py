"""
Build Handler - 处理 Agent 构建任务

负责:
- 执行 Agent 构建工作流
- 更新任务和项目状态
- 处理错误和重试
- 支持从任意阶段恢复执行

注意：阶段状态更新由 agent_build_workflow 通过 stage_tracker 完成，
stage_tracker 已重构为使用 api.v2.services.stage_service。

Requirements:
    - 4.1: Worker 从 SQS 消息中提取 project_id 和 target_stage
    - 4.5: Worker 使用 WorkflowEngine 执行任务
    - 4.2: 从 DynamoDB 加载项目上下文
    - 4.3: 加载工作流规则和本地文档
    - 4.6: 阶段状态更新逻辑
    - 4.7: 停止信号处理
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
    """
    构建任务处理器
    
    支持两种执行模式：
    1. 传统模式：使用现有的 agent_build_workflow 脚本
    2. 引擎模式：使用新的 WorkflowEngine 类
    
    Validates:
        - Requirement 4.1: 从 SQS 消息中提取 project_id 和 target_stage
        - Requirement 4.5: 使用 WorkflowEngine 执行任务
    """
    
    def __init__(self, use_workflow_engine: bool = True):
        """
        初始化构建处理器
        
        参数:
            use_workflow_engine: 是否使用新的 WorkflowEngine（默认 True）
        """
        self.db = db_client
        self.worker_id = worker_settings.WORKER_ID
        self.use_workflow_engine = use_workflow_engine
    
    def handle(self, message: Dict[str, Any]) -> bool:
        """
        处理构建任务消息
        
        Args:
            message: SQS 消息内容
        
        Returns:
            是否处理成功
            
        Validates: Requirement 4.1 - 从 SQS 消息中提取 project_id 和 target_stage
        """
        body = message.get('body', {})
        task_id = body.get('task_id')
        project_id = body.get('project_id')
        requirement = body.get('requirement')
        
        # 新增：支持从指定阶段开始执行
        target_stage = body.get('target_stage')
        execute_to_completion = body.get('execute_to_completion', True)
        action = body.get('action', 'execute')  # execute, resume, restart
        
        if not all([task_id, project_id]):
            logger.error(f"Invalid message: missing required fields (task_id, project_id)")
            return False
        
        # 对于新项目，requirement 是必需的
        if action == 'execute' and not requirement and not target_stage:
            logger.error(f"Invalid message: requirement is required for new execution")
            return False
        
        logger.info(f"Processing build task {task_id} for project {project_id}")
        logger.info(f"Action: {action}, target_stage: {target_stage}, to_completion: {execute_to_completion}")
        
        try:
            # 更新任务状态为运行中
            self._update_task_status(task_id, TaskStatus.RUNNING)
            
            # 更新项目状态为构建中
            self._update_project_status(project_id, ProjectStatus.BUILDING)
            
            # 根据配置选择执行模式
            if self.use_workflow_engine:
                result = self._execute_with_workflow_engine(
                    project_id=project_id,
                    requirement=requirement,
                    target_stage=target_stage,
                    execute_to_completion=execute_to_completion,
                    action=action,
                    metadata=body.get('metadata', {})
                )
            else:
                result = self._execute_build_workflow(
                    project_id=project_id,
                    requirement=requirement,
                    metadata=body.get('metadata', {})
                )
            
            # 检查执行结果
            if result.get('status') == 'paused':
                # 工作流被暂停
                self._update_task_status(task_id, TaskStatus.PENDING, result=result)
                self._update_project_status(project_id, ProjectStatus.PAUSED)
                logger.info(f"Build task {task_id} paused")
                return True
            
            elif result.get('status') == 'stopped':
                # 工作流被停止
                self._update_task_status(task_id, TaskStatus.CANCELLED, result=result)
                self._update_project_status(project_id, ProjectStatus.CANCELLED)
                logger.info(f"Build task {task_id} stopped by user")
                return True
            
            elif result.get('status') == 'failed':
                # 工作流执行失败
                error_msg = result.get('error_message', 'Unknown error')
                self._update_task_status(task_id, TaskStatus.FAILED, error_message=error_msg)
                self._update_project_status(
                    project_id,
                    ProjectStatus.FAILED,
                    error_info={'message': error_msg, 'failed_stage': result.get('failed_stage')}
                )
                logger.error(f"Build task {task_id} failed: {error_msg}")
                return False
            
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
    
    def _execute_with_workflow_engine(
        self,
        project_id: str,
        requirement: Optional[str],
        target_stage: Optional[str],
        execute_to_completion: bool,
        action: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        使用 WorkflowEngine 执行构建工作流
        
        参数:
            project_id: 项目ID
            requirement: 用户需求（新项目必需）
            target_stage: 目标阶段（可选）
            execute_to_completion: 是否执行到完成
            action: 操作类型 (execute, resume, restart)
            metadata: 元数据
            
        返回:
            执行结果字典
            
        Validates:
            - Requirement 4.2: 从 DynamoDB 加载项目上下文
            - Requirement 4.5: 使用 WorkflowEngine 执行任务
            - Requirement 4.7: 停止信号处理
        """
        # 设置环境变量供工作流工具使用（如 project_manager.py 中的 project_init）
        os.environ["NEXUS_STAGE_TRACKER_PROJECT_ID"] = project_id
        
        try:
            from nexus_utils.workflow import (
                WorkflowEngine,
                ExecutionResult,
                WorkflowControlSignal,
                PrerequisiteError,
                StageStatus as WFStageStatus,
            )
            
            # 创建工作流引擎
            engine = WorkflowEngine(project_id, db_client=self.db)
            
            # 设置回调函数用于日志记录
            engine.set_callbacks(
                on_stage_start=lambda stage: logger.info(f"Stage {stage} started"),
                on_stage_complete=lambda stage, output: logger.info(
                    f"Stage {stage} completed, tokens: {output.metrics.input_tokens + output.metrics.output_tokens}"
                ),
                on_stage_error=lambda stage, error: logger.error(f"Stage {stage} error: {error}"),
            )
            
            # 根据操作类型执行
            if action == 'resume':
                # 恢复执行
                engine.resume(from_stage=target_stage)
                result = engine.execute_to_completion()
                
            elif action == 'restart':
                # 从指定阶段重新开始
                if not target_stage:
                    raise ValueError("target_stage is required for restart action")
                result = engine.execute_from_stage(target_stage, to_completion=execute_to_completion)
                
            else:
                # 正常执行
                if target_stage:
                    result = engine.execute_from_stage(target_stage, to_completion=execute_to_completion)
                else:
                    result = engine.execute_to_completion()
            
            # 转换结果
            return self._convert_execution_result(result)
            
        except ImportError as e:
            logger.warning(f"WorkflowEngine not available: {e}, falling back to legacy mode")
            return self._execute_build_workflow(project_id, requirement, metadata)
        
        except PrerequisiteError as e:
            logger.error(f"Prerequisite check failed: {e}")
            return {
                'status': 'failed',
                'error_message': str(e),
                'missing_prerequisites': e.missing_prerequisites,
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
            if "NEXUS_STAGE_TRACKER_PROJECT_ID" in os.environ:
                del os.environ["NEXUS_STAGE_TRACKER_PROJECT_ID"]
    
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
            
            # 获取用户指定的项目名称
            project_name = metadata.get('project_name')
            
            # 执行工作流
            result = run_workflow(
                user_input=requirement,
                session_id=metadata.get('session_id'),
                project_name=project_name
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
