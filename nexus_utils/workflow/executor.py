"""
阶段执行器

负责执行单个工作流阶段，创建 Agent 并管理执行过程。

Requirements:
    - 1.4: 执行单个阶段
    - 1.5: 从指定阶段执行到完成
    - 2.2: 收集执行指标
    - 2.3: 记录生成的文件
    - 6.2: agent_designer 阶段迭代处理
    - 6.3: tool_developer 阶段迭代处理
    - 6.4: prompt_engineer 阶段迭代处理
    - 6.5: agent_code_developer 阶段迭代处理
"""

import logging
import time
import os
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, TYPE_CHECKING

from .models import (
    WorkflowContext,
    StageOutput,
    StageMetrics,
    FileMetadata,
    StageStatus,
)
from .context import WorkflowContextManager, get_stage_context

if TYPE_CHECKING:
    from .multi_agent import MultiAgentIterator, MultiAgentStageExecutor

logger = logging.getLogger(__name__)


def _get_project_root() -> Path:
    """获取项目根目录"""
    current_file = Path(__file__).resolve()
    return current_file.parent.parent.parent


# 阶段到提示词模板路径的映射
STAGE_PROMPT_MAPPING = {
    "orchestrator": "system_agents_prompts/agent_build_workflow/orchestrator",
    "requirements_analyzer": "system_agents_prompts/agent_build_workflow/requirements_analyzer",
    "system_architect": "system_agents_prompts/agent_build_workflow/system_architect",
    "agent_designer": "system_agents_prompts/agent_build_workflow/agent_designer",
    "tool_developer": "system_agents_prompts/agent_build_workflow/tool_developer",
    "prompt_engineer": "system_agents_prompts/agent_build_workflow/prompt_engineer",
    "agent_code_developer": "system_agents_prompts/agent_build_workflow/agent_code_developer",
    "agent_developer_manager": "system_agents_prompts/agent_build_workflow/agent_developer_manager",
    "agent_deployer": "system_agents_prompts/agent_build_workflow/agent_deployer",
}


class StageExecutionError(Exception):
    """
    阶段执行错误
    
    属性:
        stage_name: 阶段名称
        message: 错误信息
        recoverable: 是否可恢复
    """
    def __init__(self, stage_name: str, message: str, recoverable: bool = True):
        self.stage_name = stage_name
        self.message = message
        self.recoverable = recoverable
        super().__init__(f"Stage {stage_name} failed: {message}")


class StageExecutor:
    """
    阶段执行器
    
    负责创建和执行单个阶段的 Agent，收集执行指标和生成的文件。
    支持多 Agent 项目的迭代处理。
    
    Validates:
        - Requirement 1.4: 执行单个阶段
        - Requirement 2.2: 收集执行指标
        - Requirement 2.3: 记录生成的文件
        - Requirement 6.2: agent_designer 阶段迭代处理
        - Requirement 6.3: tool_developer 阶段迭代处理
        - Requirement 6.4: prompt_engineer 阶段迭代处理
        - Requirement 6.5: agent_code_developer 阶段迭代处理
    """
    
    # 需要迭代处理的阶段
    ITERATIVE_STAGES = [
        "agent_designer",
        "tool_developer",
        "prompt_engineer",
        "agent_code_developer",
    ]
    
    def __init__(
        self, 
        context: WorkflowContext,
        context_manager: Optional[WorkflowContextManager] = None,
        on_stage_start: Optional[Callable[[str], None]] = None,
        on_stage_complete: Optional[Callable[[str, StageOutput], None]] = None,
        on_stage_error: Optional[Callable[[str, Exception], None]] = None,
        enable_multi_agent: bool = True,
    ):
        """
        初始化阶段执行器
        
        参数:
            context: 工作流上下文
            context_manager: 上下文管理器（可选）
            on_stage_start: 阶段开始回调
            on_stage_complete: 阶段完成回调
            on_stage_error: 阶段错误回调
            enable_multi_agent: 是否启用多 Agent 迭代处理
        """
        self.context = context
        self.context_manager = context_manager or WorkflowContextManager()
        self.on_stage_start = on_stage_start
        self.on_stage_complete = on_stage_complete
        self.on_stage_error = on_stage_error
        self.enable_multi_agent = enable_multi_agent
        
        # 执行过程中的指标收集
        self._current_metrics = StageMetrics()
        self._generated_files: List[FileMetadata] = []
        
        # 多 Agent 支持（延迟初始化）
        self._multi_agent_iterator: Optional['MultiAgentIterator'] = None
        self._multi_agent_executor: Optional['MultiAgentStageExecutor'] = None
    
    @property
    def multi_agent_iterator(self) -> 'MultiAgentIterator':
        """获取多 Agent 迭代器（延迟初始化）"""
        if self._multi_agent_iterator is None:
            from .multi_agent import MultiAgentIterator
            self._multi_agent_iterator = MultiAgentIterator(self.context)
        return self._multi_agent_iterator
    
    @property
    def multi_agent_executor(self) -> 'MultiAgentStageExecutor':
        """获取多 Agent 阶段执行器（延迟初始化）"""
        if self._multi_agent_executor is None:
            from .multi_agent import MultiAgentStageExecutor
            self._multi_agent_executor = MultiAgentStageExecutor(
                self.context,
                self.multi_agent_iterator,
            )
        return self._multi_agent_executor
    
    def should_iterate(self, stage_name: str) -> bool:
        """
        检查指定阶段是否需要迭代处理
        
        参数:
            stage_name: 阶段名称
            
        返回:
            bool: 是否需要迭代处理
        """
        if not self.enable_multi_agent:
            return False
        
        return (
            stage_name in self.ITERATIVE_STAGES and
            self.multi_agent_iterator.is_multi_agent
        )
    
    def create_agent(self, stage_name: str, state: Optional[Dict[str, Any]] = None):
        """
        创建阶段对应的 Agent
        
        参数:
            stage_name: 阶段名称
            state: Agent 状态数据
            
        返回:
            Agent: 创建的 Agent 实例
            
        Raises:
            StageExecutionError: 如果无法创建 Agent
        """
        from nexus_utils.agent_factory import create_agent_from_prompt_template
        
        # 获取提示词模板路径
        prompt_path = STAGE_PROMPT_MAPPING.get(stage_name)
        if not prompt_path:
            raise StageExecutionError(
                stage_name, 
                f"Unknown stage: {stage_name}", 
                recoverable=False
            )
        
        # 准备 Agent 状态
        agent_state = state or {}
        
        # 添加项目信息到状态
        agent_state['project_id'] = self.context.project_id
        agent_state['project_name'] = self.context.project_name
        
        # 创建 Agent
        try:
            agent = create_agent_from_prompt_template(
                agent_name=prompt_path,
                env="production",
                enable_logging=True,
                state=agent_state,
            )
            
            if not agent:
                raise StageExecutionError(
                    stage_name,
                    f"Failed to create agent from template: {prompt_path}",
                    recoverable=False
                )
            
            return agent
            
        except Exception as e:
            raise StageExecutionError(
                stage_name,
                f"Error creating agent: {str(e)}",
                recoverable=False
            )
    
    def format_context(self, stage_name: str) -> str:
        """
        格式化阶段执行上下文
        
        参数:
            stage_name: 阶段名称
            
        返回:
            str: 格式化的上下文字符串
        """
        return get_stage_context(
            self.context, 
            stage_name,
            include_rules=True,
            include_local_docs=True,
        )
    
    def execute_stage(
        self, 
        stage_name: str,
        input_message: Optional[str] = None,
        state: Optional[Dict[str, Any]] = None,
    ) -> StageOutput:
        """
        执行指定阶段
        
        参数:
            stage_name: 阶段名称
            input_message: 输入消息（可选，默认使用格式化的上下文）
            state: Agent 状态数据
            
        返回:
            StageOutput: 阶段执行结果
            
        Validates:
            - Requirement 1.4: 执行单个阶段
            - Requirement 2.2: 收集执行指标
            - Requirement 2.3: 记录生成的文件
            - Requirement 6.2-6.5: 多 Agent 迭代处理
        """
        logger.info(f"Starting execution of stage: {stage_name}")
        
        # 检查是否需要多 Agent 迭代处理
        if self.should_iterate(stage_name):
            logger.info(f"Stage {stage_name} requires multi-agent iteration")
            return self._execute_iterative_stage(stage_name, input_message, state)
        
        # 单 Agent 执行
        return self._execute_single_agent_stage(stage_name, input_message, state)
    
    def _execute_iterative_stage(
        self,
        stage_name: str,
        input_message: Optional[str] = None,
        state: Optional[Dict[str, Any]] = None,
    ) -> StageOutput:
        """
        执行迭代阶段（多 Agent）
        
        参数:
            stage_name: 阶段名称
            input_message: 输入消息
            state: Agent 状态
            
        返回:
            StageOutput: 合并的阶段输出
        """
        # 准备基础上下文
        base_context = input_message or self.format_context(stage_name)
        
        # 使用多 Agent 执行器
        return self.multi_agent_executor.execute_iterative_stage(
            stage_name,
            self,  # 传递自身作为基础执行器
            base_context,
            state,
        )
    
    def _execute_single_agent_stage(
        self,
        stage_name: str,
        input_message: Optional[str] = None,
        state: Optional[Dict[str, Any]] = None,
    ) -> StageOutput:
        """
        执行单 Agent 阶段
        
        参数:
            stage_name: 阶段名称
            input_message: 输入消息
            state: Agent 状态
            
        返回:
            StageOutput: 阶段输出
        """
        
        # 重置指标收集器
        self._current_metrics = StageMetrics()
        self._generated_files = []
        
        # 触发开始回调
        if self.on_stage_start:
            self.on_stage_start(stage_name)
        
        # 记录开始时间
        start_time = time.time()
        
        try:
            # 创建 Agent
            agent = self.create_agent(stage_name, state)
            
            # 准备输入消息
            if input_message is None:
                input_message = self.format_context(stage_name)
            
            # 执行 Agent
            logger.info(f"Invoking agent for stage: {stage_name}")
            result = agent(input_message)
            
            # 计算执行时间
            execution_time = time.time() - start_time
            
            # 收集指标
            metrics = self._collect_metrics(agent, execution_time)
            
            # 扫描生成的文件
            generated_files = self._scan_generated_files(stage_name)
            
            # 提取输出内容
            output_content = self._extract_output_content(result)
            
            # 提取设计文档（如果有）
            document_content, document_format = self._extract_design_document(
                stage_name, output_content
            )
            
            # 创建阶段输出
            output = StageOutput(
                stage_name=stage_name,
                content=output_content,
                metrics=metrics,
                generated_files=generated_files,
                document_content=document_content,
                document_format=document_format,
                completed_at=datetime.now(timezone.utc),
                status=StageStatus.COMPLETED,
            )
            
            # 更新上下文
            self.context.update_stage_output(stage_name, output)
            
            # 触发完成回调
            if self.on_stage_complete:
                self.on_stage_complete(stage_name, output)
            
            logger.info(f"Stage {stage_name} completed successfully")
            return output
            
        except StageExecutionError:
            raise
        except Exception as e:
            # 计算执行时间
            execution_time = time.time() - start_time
            
            # 创建失败输出
            output = StageOutput(
                stage_name=stage_name,
                content="",
                metrics=StageMetrics(execution_time_seconds=execution_time),
                completed_at=datetime.now(timezone.utc),
                status=StageStatus.FAILED,
                error_message=str(e),
            )
            
            # 更新上下文
            self.context.update_stage_output(stage_name, output)
            
            # 触发错误回调
            if self.on_stage_error:
                self.on_stage_error(stage_name, e)
            
            logger.error(f"Stage {stage_name} failed: {e}")
            raise StageExecutionError(stage_name, str(e), recoverable=True)
    
    def _collect_metrics(self, agent, execution_time: float) -> StageMetrics:
        """
        从 Agent 收集执行指标
        
        参数:
            agent: Agent 实例
            execution_time: 执行时间（秒）
            
        返回:
            StageMetrics: 收集的指标
            
        Validates: Requirement 2.2 - 收集执行指标
        """
        metrics = StageMetrics(
            execution_time_seconds=execution_time,
        )
        
        # 尝试从 Agent 获取 token 使用情况
        try:
            if hasattr(agent, 'model') and hasattr(agent.model, 'usage'):
                usage = agent.model.usage
                if hasattr(usage, 'input_tokens'):
                    metrics.input_tokens = usage.input_tokens
                if hasattr(usage, 'output_tokens'):
                    metrics.output_tokens = usage.output_tokens
            
            # 尝试获取模型 ID
            if hasattr(agent, 'model') and hasattr(agent.model, 'model_id'):
                metrics.model_id = agent.model.model_id
            
            # 尝试获取工具调用次数
            if hasattr(agent, 'tool_calls_count'):
                metrics.tool_calls_count = agent.tool_calls_count
            elif hasattr(agent, 'state') and hasattr(agent.state, 'get'):
                tool_calls = agent.state.get('tool_calls_count', 0)
                if tool_calls:
                    metrics.tool_calls_count = tool_calls
                    
        except Exception as e:
            logger.warning(f"Failed to collect some metrics: {e}")
        
        return metrics
    
    def _scan_generated_files(self, stage_name: str) -> List[FileMetadata]:
        """
        扫描阶段生成的文件
        
        参数:
            stage_name: 阶段名称
            
        返回:
            List[FileMetadata]: 生成的文件列表
            
        Validates: Requirement 2.3 - 记录生成的文件
        """
        files = []
        project_root = _get_project_root()
        
        # 确定项目目录
        project_dir = project_root / "projects" / self.context.project_name
        if not project_dir.exists():
            project_dir = project_root / "projects" / self.context.project_id
        
        if not project_dir.exists():
            return files
        
        # 扫描项目目录中的文件
        try:
            for file_path in project_dir.rglob("*"):
                if file_path.is_file() and not file_path.name.startswith('.'):
                    # 计算相对路径
                    relative_path = str(file_path.relative_to(project_dir))
                    
                    # 获取文件信息
                    stat = file_path.stat()
                    
                    # 计算校验和
                    checksum = None
                    try:
                        with open(file_path, 'rb') as f:
                            checksum = hashlib.md5(f.read()).hexdigest()
                    except:
                        pass
                    
                    files.append(FileMetadata(
                        path=relative_path,
                        size=stat.st_size,
                        checksum=checksum,
                        last_modified=datetime.fromtimestamp(
                            stat.st_mtime, tz=timezone.utc
                        ),
                    ))
        except Exception as e:
            logger.warning(f"Failed to scan generated files: {e}")
        
        return files
    
    def _extract_output_content(self, result) -> str:
        """
        从 Agent 结果中提取输出内容
        
        参数:
            result: Agent 执行结果
            
        返回:
            str: 提取的输出内容
        """
        if result is None:
            return ""
        
        if isinstance(result, str):
            return result
        
        # 尝试从结果对象中提取内容
        if hasattr(result, 'content'):
            return str(result.content)
        
        if hasattr(result, 'message'):
            return str(result.message)
        
        if hasattr(result, 'text'):
            return str(result.text)
        
        # 尝试转换为字符串
        try:
            return str(result)
        except:
            return ""
    
    def _extract_design_document(
        self, 
        stage_name: str, 
        output_content: str
    ) -> tuple:
        """
        从输出内容中提取设计文档
        
        参数:
            stage_name: 阶段名称
            output_content: 输出内容
            
        返回:
            tuple: (document_content, document_format)
        """
        # 某些阶段产生设计文档
        design_stages = {
            "requirements_analyzer": "markdown",
            "system_architect": "json",
            "agent_designer": "markdown",
        }
        
        if stage_name not in design_stages:
            return "", "markdown"
        
        document_format = design_stages[stage_name]
        
        # 对于 system_architect，尝试提取 JSON
        if document_format == "json":
            import json
            try:
                # 尝试找到 JSON 块
                import re
                json_match = re.search(r'```json\s*([\s\S]*?)\s*```', output_content)
                if json_match:
                    json_content = json_match.group(1)
                    # 验证是有效的 JSON
                    json.loads(json_content)
                    return json_content, "json"
            except:
                pass
        
        # 默认返回整个输出作为文档
        return output_content, document_format


# 便捷函数
def execute_stage(
    context: WorkflowContext,
    stage_name: str,
    input_message: Optional[str] = None,
    state: Optional[Dict[str, Any]] = None,
) -> StageOutput:
    """
    执行单个阶段
    
    参数:
        context: 工作流上下文
        stage_name: 阶段名称
        input_message: 输入消息
        state: Agent 状态
        
    返回:
        StageOutput: 阶段执行结果
    """
    executor = StageExecutor(context)
    return executor.execute_stage(stage_name, input_message, state)
