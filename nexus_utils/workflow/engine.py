"""
工作流引擎

核心工作流引擎类，负责管理和执行 Agent 构建工作流。

Requirements:
    - 1.1: 封装为独立的类
    - 1.2: 支持从任意阶段开始执行
    - 1.3: 验证前置阶段完成状态
    - 1.4: 执行单个阶段
    - 1.5: 从指定阶段执行到完成
    - 1.6: 失败时保存状态，支持重试
    - 3.1: 支持暂停控制
    - 3.2: 支持停止控制
    - 3.3: 支持恢复执行
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field

from .models import (
    WorkflowContext,
    StageOutput,
    StageStatus,
    ControlStatus,
)
from .context import (
    WorkflowContextManager,
    load_workflow_context,
    save_workflow_context,
)
from .executor import StageExecutor, StageExecutionError

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """
    工作流执行结果
    
    属性:
        success: 是否成功完成
        completed_stages: 已完成的阶段列表
        failed_stage: 失败的阶段（如果有）
        error_message: 错误信息
        final_status: 最终状态
        metrics: 执行指标摘要
    """
    success: bool = False
    completed_stages: List[str] = field(default_factory=list)
    failed_stage: Optional[str] = None
    error_message: Optional[str] = None
    final_status: StageStatus = StageStatus.PENDING
    metrics: Dict[str, Any] = field(default_factory=dict)


class WorkflowControlSignal(Exception):
    """
    工作流控制信号
    
    用于在执行过程中传递控制信号。
    """
    PAUSE = "pause"
    STOP = "stop"
    
    def __init__(self, signal_type: str, message: str = ""):
        self.signal_type = signal_type
        super().__init__(f"Control signal: {signal_type} - {message}")


class PrerequisiteError(Exception):
    """
    前置阶段验证错误
    
    当前置阶段未完成时抛出。
    """
    def __init__(self, stage_name: str, missing_prerequisites: List[str]):
        self.stage_name = stage_name
        self.missing_prerequisites = missing_prerequisites
        super().__init__(
            f"Prerequisites not met for stage {stage_name}: "
            f"missing {missing_prerequisites}"
        )


class WorkflowEngine:
    """
    工作流引擎
    
    负责管理和执行 Agent 构建工作流，支持从任意阶段开始执行。
    
    Validates:
        - Requirement 1.1: 封装为独立的类
        - Requirement 1.2: 支持从任意阶段开始执行
        - Requirement 1.3: 验证前置阶段完成状态
        - Requirement 1.4: 执行单个阶段
        - Requirement 1.5: 从指定阶段执行到完成
        - Requirement 1.6: 失败时保存状态，支持重试
        - Requirement 3.1: 支持暂停控制
        - Requirement 3.2: 支持停止控制
        - Requirement 3.3: 支持恢复执行
    """
    
    def __init__(
        self, 
        project_id: str, 
        config: Optional[Dict[str, Any]] = None,
        db_client=None,
    ):
        """
        初始化工作流引擎
        
        参数:
            project_id: 项目唯一标识
            config: 可选的配置覆盖
            db_client: DynamoDB 客户端（可选）
            
        Validates: Requirement 1.1 - 封装为独立的类
        """
        self.project_id = project_id
        self.config = config or {}
        
        # 初始化上下文管理器
        self.context_manager = WorkflowContextManager(db_client)
        
        # 上下文（延迟加载）
        self._context: Optional[WorkflowContext] = None
        
        # 阶段执行器（延迟创建）
        self._executor: Optional[StageExecutor] = None
        
        # 控制标志
        self._pause_requested = False
        self._stop_requested = False
        
        # 回调函数
        self._on_stage_start: Optional[Callable[[str], None]] = None
        self._on_stage_complete: Optional[Callable[[str, StageOutput], None]] = None
        self._on_stage_error: Optional[Callable[[str, Exception], None]] = None
    
    @property
    def context(self) -> WorkflowContext:
        """获取工作流上下文（延迟加载）"""
        if self._context is None:
            self._context = self.load_context()
        return self._context
    
    @property
    def executor(self) -> StageExecutor:
        """获取阶段执行器（延迟创建）"""
        if self._executor is None:
            self._executor = StageExecutor(
                self.context,
                self.context_manager,
                on_stage_start=self._on_stage_start,
                on_stage_complete=self._on_stage_complete,
                on_stage_error=self._on_stage_error,
            )
        return self._executor
    
    def set_callbacks(
        self,
        on_stage_start: Optional[Callable[[str], None]] = None,
        on_stage_complete: Optional[Callable[[str, StageOutput], None]] = None,
        on_stage_error: Optional[Callable[[str, Exception], None]] = None,
    ) -> None:
        """
        设置回调函数
        
        参数:
            on_stage_start: 阶段开始回调
            on_stage_complete: 阶段完成回调
            on_stage_error: 阶段错误回调
        """
        self._on_stage_start = on_stage_start
        self._on_stage_complete = on_stage_complete
        self._on_stage_error = on_stage_error
        
        # 如果执行器已创建，更新其回调
        if self._executor:
            self._executor.on_stage_start = on_stage_start
            self._executor.on_stage_complete = on_stage_complete
            self._executor.on_stage_error = on_stage_error
    
    def load_context(self) -> WorkflowContext:
        """
        从 DynamoDB 加载项目上下文
        
        返回:
            WorkflowContext: 包含项目信息和所有已完成阶段输出的上下文
            
        Validates: Requirement 1.2 - 支持从任意阶段开始执行
        """
        logger.info(f"Loading context for project: {self.project_id}")
        context = self.context_manager.load_from_db(self.project_id)
        logger.info(f"Context loaded, completed stages: {context.get_completed_stages()}")
        return context
    
    def validate_prerequisites(self, stage_name: str) -> bool:
        """
        验证指定阶段的前置阶段是否已完成
        
        参数:
            stage_name: 阶段名称
            
        返回:
            bool: 所有前置阶段是否都已完成
            
        Raises:
            PrerequisiteError: 如果前置阶段未完成
            
        Validates: Requirement 1.3 - 验证前置阶段完成状态
        """
        prerequisites = self.context.get_prerequisite_stages(stage_name)
        completed = set(self.context.get_completed_stages())
        
        missing = [p for p in prerequisites if p not in completed]
        
        if missing:
            logger.warning(
                f"Prerequisites not met for stage {stage_name}: "
                f"missing {missing}"
            )
            raise PrerequisiteError(stage_name, missing)
        
        return True
    
    def execute_single_stage(
        self, 
        stage_name: str,
        input_message: Optional[str] = None,
        state: Optional[Dict[str, Any]] = None,
        skip_validation: bool = False,
    ) -> StageOutput:
        """
        执行单个阶段
        
        参数:
            stage_name: 阶段名称
            input_message: 输入消息（可选）
            state: Agent 状态数据
            skip_validation: 是否跳过前置验证
            
        返回:
            StageOutput: 阶段执行结果
            
        Validates: Requirement 1.4 - 执行单个阶段
        """
        logger.info(f"Executing single stage: {stage_name}")
        
        # 验证前置阶段
        if not skip_validation:
            self.validate_prerequisites(stage_name)
        
        # 在每个阶段开始前检查控制信号（从数据库刷新状态）
        self._check_control_signals()
        
        # 更新当前阶段
        self.context.current_stage = stage_name
        self.context.status = StageStatus.RUNNING
        
        # 保存状态（标记阶段为运行中）
        self._save_context()
        
        # 再次检查控制信号（确保状态更新后仍然可以继续）
        self._check_control_signals()
        
        try:
            # 执行阶段
            output = self.executor.execute_stage(stage_name, input_message, state)
            
            # 执行完成后再次检查控制信号
            self._refresh_control_status()
            
            # 如果控制状态是暂停或停止，不更新阶段为完成，保持当前状态
            if self.context.control_status in [ControlStatus.PAUSED, ControlStatus.STOPPED]:
                logger.info(f"Stage {stage_name} completed but workflow is {self.context.control_status.value}")
                # 仍然保存阶段输出，但不改变项目状态
                self._save_context()
                
                # 抛出控制信号
                if self.context.control_status == ControlStatus.PAUSED:
                    raise WorkflowControlSignal(WorkflowControlSignal.PAUSE, "Pause requested")
                else:
                    raise WorkflowControlSignal(WorkflowControlSignal.STOP, "Stop requested")
            
            # 保存状态
            self._save_context()
            
            return output
            
        except StageExecutionError as e:
            # 保存失败状态
            self.context.status = StageStatus.FAILED
            self._save_context()
            raise
    
    def execute_from_stage(
        self, 
        stage_name: str, 
        to_completion: bool = True,
        state: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """
        从指定阶段开始执行
        
        参数:
            stage_name: 起始阶段名称
            to_completion: 是否执行到完成
            state: Agent 状态数据
            
        返回:
            ExecutionResult: 执行结果
            
        Validates:
            - Requirement 1.2: 支持从任意阶段开始执行
            - Requirement 1.5: 从指定阶段执行到完成
        """
        logger.info(f"Executing from stage: {stage_name}, to_completion: {to_completion}")
        
        result = ExecutionResult()
        
        # 验证前置阶段
        try:
            self.validate_prerequisites(stage_name)
        except PrerequisiteError as e:
            result.error_message = str(e)
            result.final_status = StageStatus.FAILED
            return result
        
        # 获取要执行的阶段列表
        if to_completion:
            pending_stages = self.context.get_pending_stages()
            # 从指定阶段开始
            try:
                start_index = pending_stages.index(stage_name)
                stages_to_execute = pending_stages[start_index:]
            except ValueError:
                # 如果指定阶段不在待执行列表中，只执行该阶段
                stages_to_execute = [stage_name]
        else:
            stages_to_execute = [stage_name]
        
        logger.info(f"Stages to execute: {stages_to_execute}")
        
        # 执行阶段
        for stage in stages_to_execute:
            try:
                # 检查控制信号
                self._check_control_signals()
                
                # 执行阶段
                output = self.execute_single_stage(stage, state=state, skip_validation=True)
                result.completed_stages.append(stage)
                
            except WorkflowControlSignal as e:
                # 处理控制信号
                if e.signal_type == WorkflowControlSignal.PAUSE:
                    logger.info(f"Workflow paused after stage: {stage}")
                    result.final_status = StageStatus.PAUSED
                    return result
                elif e.signal_type == WorkflowControlSignal.STOP:
                    logger.info(f"Workflow stopped after stage: {stage}")
                    result.final_status = StageStatus.FAILED
                    result.error_message = "Workflow stopped by user"
                    return result
                    
            except StageExecutionError as e:
                result.failed_stage = stage
                result.error_message = str(e)
                result.final_status = StageStatus.FAILED
                
                # 保存失败状态
                self._save_context()
                
                logger.error(f"Stage {stage} failed: {e}")
                return result
                
            except Exception as e:
                result.failed_stage = stage
                result.error_message = str(e)
                result.final_status = StageStatus.FAILED
                
                # 保存失败状态
                self._save_context()
                
                logger.error(f"Unexpected error in stage {stage}: {e}")
                return result
        
        # 所有阶段执行完成
        result.success = True
        result.final_status = StageStatus.COMPLETED
        
        # 更新上下文状态
        self.context.status = StageStatus.COMPLETED
        self._save_context()
        
        logger.info(f"Workflow completed successfully")
        return result
    
    def execute_to_completion(
        self,
        state: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """
        从下一个待执行阶段执行到完成
        
        参数:
            state: Agent 状态数据
            
        返回:
            ExecutionResult: 执行结果
        """
        next_stage = self.context.get_next_stage()
        if not next_stage:
            return ExecutionResult(
                success=True,
                final_status=StageStatus.COMPLETED,
                completed_stages=self.context.get_completed_stages(),
            )
        
        return self.execute_from_stage(next_stage, to_completion=True, state=state)
    
    def pause(self) -> bool:
        """
        暂停工作流执行
        
        返回:
            bool: 是否成功设置暂停标志
            
        Validates: Requirement 3.1 - 支持暂停控制
        """
        logger.info(f"Pause requested for project: {self.project_id}")
        self._pause_requested = True
        
        # 更新上下文
        self.context.control_status = ControlStatus.PAUSED
        self.context.pause_requested_at = datetime.now(timezone.utc)
        self._save_context()
        
        return True
    
    def resume(self, from_stage: Optional[str] = None) -> bool:
        """
        恢复工作流执行
        
        参数:
            from_stage: 可选的起始阶段
            
        返回:
            bool: 是否成功恢复
            
        Validates: Requirement 3.3 - 支持恢复执行
        """
        logger.info(f"Resume requested for project: {self.project_id}")
        self._pause_requested = False
        self._stop_requested = False
        
        # 更新上下文
        self.context.control_status = ControlStatus.RUNNING
        self.context.pause_requested_at = None
        self.context.stop_requested_at = None
        
        if from_stage:
            self.context.resume_from_stage = from_stage
        
        self._save_context()
        
        return True
    
    def stop(self) -> bool:
        """
        停止工作流执行
        
        返回:
            bool: 是否成功设置停止标志
            
        Validates: Requirement 3.2 - 支持停止控制
        """
        logger.info(f"Stop requested for project: {self.project_id}")
        self._stop_requested = True
        
        # 更新上下文
        self.context.control_status = ControlStatus.STOPPED
        self.context.stop_requested_at = datetime.now(timezone.utc)
        self._save_context()
        
        return True
    
    def _check_control_signals(self) -> None:
        """
        检查控制信号
        
        Raises:
            WorkflowControlSignal: 如果有控制信号
        """
        # 重新加载上下文以获取最新的控制状态
        self._refresh_control_status()
        
        if self._stop_requested or self.context.control_status == ControlStatus.STOPPED:
            raise WorkflowControlSignal(WorkflowControlSignal.STOP, "Stop requested")
        
        if self._pause_requested or self.context.control_status == ControlStatus.PAUSED:
            raise WorkflowControlSignal(WorkflowControlSignal.PAUSE, "Pause requested")
    
    def _refresh_control_status(self) -> None:
        """刷新控制状态（从数据库重新加载）"""
        try:
            project = self.context_manager.db.get_project(self.project_id)
            if project:
                control_status_str = project.get('control_status', 'running')
                try:
                    self.context.control_status = ControlStatus(control_status_str)
                except ValueError:
                    pass
                
                # 更新本地标志
                if self.context.control_status == ControlStatus.PAUSED:
                    self._pause_requested = True
                elif self.context.control_status == ControlStatus.STOPPED:
                    self._stop_requested = True
        except Exception as e:
            logger.warning(f"Failed to refresh control status: {e}")
    
    def _save_context(self) -> None:
        """保存上下文到 DynamoDB"""
        try:
            self.context_manager.save_to_db(self.context)
        except Exception as e:
            logger.error(f"Failed to save context: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取工作流状态
        
        返回:
            Dict: 状态信息
        """
        return {
            'project_id': self.project_id,
            'status': self.context.status.value,
            'control_status': self.context.control_status.value,
            'current_stage': self.context.current_stage,
            'completed_stages': self.context.get_completed_stages(),
            'pending_stages': self.context.get_pending_stages(),
            'aggregated_metrics': self.context.aggregated_metrics.to_dict(),
        }


# 便捷函数
def create_workflow_engine(
    project_id: str,
    config: Optional[Dict[str, Any]] = None,
) -> WorkflowEngine:
    """
    创建工作流引擎实例
    
    参数:
        project_id: 项目ID
        config: 配置
        
    返回:
        WorkflowEngine: 工作流引擎实例
    """
    return WorkflowEngine(project_id, config)


def run_workflow(
    project_id: str,
    from_stage: Optional[str] = None,
    to_completion: bool = True,
    state: Optional[Dict[str, Any]] = None,
) -> ExecutionResult:
    """
    运行工作流（向后兼容接口）
    
    参数:
        project_id: 项目ID
        from_stage: 起始阶段（可选）
        to_completion: 是否执行到完成
        state: Agent 状态
        
    返回:
        ExecutionResult: 执行结果
        
    Validates: Requirement 1.7 - 保持现有 run_workflow() 函数接口
    """
    engine = WorkflowEngine(project_id)
    
    if from_stage:
        return engine.execute_from_stage(from_stage, to_completion, state)
    else:
        return engine.execute_to_completion(state)


def run_workflow_legacy(
    user_input: str,
    session_id: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    运行工作流（传统接口，兼容 agent_build_workflow.py）
    
    此函数提供与原有 agent_build_workflow.run_workflow() 相同的接口，
    内部使用新的 WorkflowEngine 实现。
    
    参数:
        user_input: 用户输入内容
        session_id: 可选的 session_id
        project_id: 可选的项目ID（如果未提供则自动生成）
        
    返回:
        Dict: 执行结果，包含 session_id, execution_time, execution_order 等
        
    Validates: Requirement 1.7 - 保持现有 run_workflow() 函数接口
    """
    import uuid
    import time
    
    # 生成或使用 project_id
    if project_id is None:
        project_id = str(uuid.uuid4())
    
    # 生成或使用 session_id
    if session_id is None:
        session_id = str(uuid.uuid4())
    
    start_time = time.time()
    
    try:
        # 创建工作流引擎
        engine = WorkflowEngine(project_id)
        
        # 初始化上下文（如果是新项目）
        if not engine.context.requirement:
            engine.context.requirement = user_input
        
        # 执行工作流
        result = engine.execute_to_completion()
        
        execution_time = time.time() - start_time
        
        return {
            'status': 'completed' if result.success else 'failed',
            'session_id': session_id,
            'project_id': project_id,
            'execution_time': execution_time,
            'execution_order': result.completed_stages,
            'failed_stage': result.failed_stage,
            'error_message': result.error_message,
            'metrics': result.metrics,
        }
        
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Workflow execution failed: {e}")
        
        return {
            'status': 'failed',
            'session_id': session_id,
            'project_id': project_id,
            'execution_time': execution_time,
            'execution_order': [],
            'error_message': str(e),
        }
