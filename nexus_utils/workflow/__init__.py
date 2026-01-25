"""
工作流模块

提供 Agent 构建工作流的核心数据模型、上下文管理和执行功能。

Requirements:
    - 2.2: Stage_Output 包含执行指标
    - 2.5: Project_Record 包含聚合指标
    - 9.1: Stage_Context 包含基础工作流规则
    - 9.2: Stage_Context 包含所有已完成阶段的输出
    - 9.3: Stage_Context 包含原始用户需求
    - 9.4: Stage_Context 包含意图分析结果
"""

from .models import (
    StageStatus,
    ControlStatus,
    StageMetrics,
    FileMetadata,
    StageOutput,
    WorkflowContext,
    IntentRecognitionResult,
    AggregatedMetrics,
    AgentDefinition,
    MultiAgentArchitecture,
    AgentStageProgress,
)

from .context import (
    WorkflowContextManager,
    workflow_context_manager,
    load_workflow_context,
    save_workflow_context,
    get_stage_context,
    estimate_tokens,
    truncate_to_tokens,
    summarize_stage_output,
    DEFAULT_MAX_CONTEXT_TOKENS,
)

from .executor import (
    StageExecutor,
    StageExecutionError,
    execute_stage,
    STAGE_PROMPT_MAPPING,
)

from .engine import (
    WorkflowEngine,
    ExecutionResult,
    WorkflowControlSignal,
    PrerequisiteError,
    create_workflow_engine,
    run_workflow,
    run_workflow_legacy,
)

from .validator import (
    PromptValidator,
    DocumentValidator,
    ValidationResult,
    ValidationError,
    validate_workflow_prompts,
    validate_tool_path,
    validate_document,
)

from .multi_agent import (
    MultiAgentIterator,
    MultiAgentStageExecutor,
    create_multi_agent_iterator,
    is_multi_agent_project,
    get_multi_agent_progress,
)

from .agent_validator import (
    AgentValidator,
    AgentValidationResult,
    ValidationIssue,
    ValidationLevel,
    validate_agent,
    validate_multiple_agents,
)

from .file_sync import (
    FileMetadataManager,
    FileSyncManager,
    FileSyncConfig,
    scan_and_save_files,
    get_file_content,
    sync_project_files,
)

__all__ = [
    # 数据模型
    'StageStatus',
    'ControlStatus',
    'StageMetrics',
    'FileMetadata',
    'StageOutput',
    'WorkflowContext',
    'IntentRecognitionResult',
    'AggregatedMetrics',
    'AgentDefinition',
    'MultiAgentArchitecture',
    'AgentStageProgress',
    # 上下文管理
    'WorkflowContextManager',
    'workflow_context_manager',
    'load_workflow_context',
    'save_workflow_context',
    'get_stage_context',
    'estimate_tokens',
    'truncate_to_tokens',
    'summarize_stage_output',
    'DEFAULT_MAX_CONTEXT_TOKENS',
    # 阶段执行器
    'StageExecutor',
    'StageExecutionError',
    'execute_stage',
    'STAGE_PROMPT_MAPPING',
    # 工作流引擎
    'WorkflowEngine',
    'ExecutionResult',
    'WorkflowControlSignal',
    'PrerequisiteError',
    'create_workflow_engine',
    'run_workflow',
    'run_workflow_legacy',
    # 验证器
    'PromptValidator',
    'DocumentValidator',
    'ValidationResult',
    'ValidationError',
    'validate_workflow_prompts',
    'validate_tool_path',
    'validate_document',
    # 多 Agent 支持
    'MultiAgentIterator',
    'MultiAgentStageExecutor',
    'create_multi_agent_iterator',
    'is_multi_agent_project',
    'get_multi_agent_progress',
    # Agent 验证
    'AgentValidator',
    'AgentValidationResult',
    'ValidationIssue',
    'ValidationLevel',
    'validate_agent',
    'validate_multiple_agents',
    # 文件同步
    'FileMetadataManager',
    'FileSyncManager',
    'FileSyncConfig',
    'scan_and_save_files',
    'get_file_content',
    'sync_project_files',
]
