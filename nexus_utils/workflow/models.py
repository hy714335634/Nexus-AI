"""
工作流核心数据模型

定义 Agent 构建工作流的核心数据结构，包括阶段状态、执行指标、阶段输出和工作流上下文。

Requirements:
    - 2.2: Stage_Output 包含执行指标
    - 9.1: Stage_Context 包含基础工作流规则
    - 9.2: Stage_Context 包含所有已完成阶段的输出
    - 9.3: Stage_Context 包含原始用户需求
    - 9.4: Stage_Context 包含编排器阶段的意图分析结果
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any


def _get_stage_sequence(workflow_type: str = "agent_build") -> List[str]:
    """
    从统一配置模块获取阶段顺序
    
    延迟导入以避免循环依赖
    
    参数:
        workflow_type: 工作流类型，默认为 'agent_build'
        
    返回:
        List[str]: 阶段名称列表
    """
    from api.v2.core.stage_config import get_all_stage_names
    return get_all_stage_names(workflow_type)


def _get_stage_order() -> List[str]:
    """
    获取阶段顺序（模块级别导出）
    
    提供模块级别的 STAGE_ORDER 访问，保持向后兼容性
    """
    return _get_stage_sequence("agent_build")


# 模块级别导出 - 延迟初始化以避免循环依赖
# 使用时会从统一配置模块获取最新值
class _LazyStageOrder:
    """
    延迟加载的阶段顺序列表
    
    默认使用 agent_build 工作流的阶段顺序
    """
    _cached: List[str] = None
    
    def __iter__(self):
        if self._cached is None:
            self._cached = _get_stage_sequence("agent_build")
        return iter(self._cached)
    
    def __getitem__(self, index):
        if self._cached is None:
            self._cached = _get_stage_sequence("agent_build")
        return self._cached[index]
    
    def __len__(self):
        if self._cached is None:
            self._cached = _get_stage_sequence("agent_build")
        return len(self._cached)
    
    def __repr__(self):
        if self._cached is None:
            self._cached = _get_stage_sequence("agent_build")
        return repr(self._cached)
    
    def __contains__(self, item):
        if self._cached is None:
            self._cached = _get_stage_sequence("agent_build")
        return item in self._cached
    
    def index(self, item):
        if self._cached is None:
            self._cached = _get_stage_sequence("agent_build")
        return self._cached.index(item)


# 导出模块级别的 STAGE_ORDER
STAGE_ORDER = _LazyStageOrder()


class StageStatus(Enum):
    """
    阶段执行状态枚举
    
    定义工作流中各阶段的执行状态，用于跟踪阶段进度。
    
    属性:
        PENDING: 等待执行
        RUNNING: 正在执行
        COMPLETED: 执行完成
        FAILED: 执行失败
        PAUSED: 已暂停
    """
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class ControlStatus(Enum):
    """
    工作流控制状态枚举
    
    定义工作流的整体控制状态，用于前端控制功能。
    
    属性:
        RUNNING: 正在运行
        PAUSED: 已暂停（完成当前阶段后停止）
        STOPPED: 已停止（完成当前 LLM 调用后停止）
        CANCELLED: 已取消
    """
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    CANCELLED = "cancelled"


@dataclass
class StageMetrics:
    """
    阶段执行指标
    
    记录单个阶段执行过程中的资源消耗和性能指标。
    
    Validates: Requirement 2.2 - Stage_Output 包含执行指标
    
    属性:
        input_tokens: 输入 token 数量
        output_tokens: 输出 token 数量
        execution_time_seconds: 执行时间（秒）
        tool_calls_count: 工具调用次数
        model_id: 使用的模型 ID（可选）
    """
    input_tokens: int = 0
    output_tokens: int = 0
    execution_time_seconds: float = 0.0
    tool_calls_count: int = 0
    model_id: Optional[str] = None
    
    @property
    def total_tokens(self) -> int:
        """
        计算总 token 数量
        
        返回:
            int: 输入和输出 token 的总和
        """
        return self.input_tokens + self.output_tokens
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        
        返回:
            Dict[str, Any]: 包含所有指标的字典
        """
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "execution_time_seconds": self.execution_time_seconds,
            "tool_calls_count": self.tool_calls_count,
            "model_id": self.model_id,
            "total_tokens": self.total_tokens,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StageMetrics":
        """
        从字典创建实例
        
        参数:
            data: 包含指标数据的字典
            
        返回:
            StageMetrics: 新创建的实例
        """
        return cls(
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            execution_time_seconds=data.get("execution_time_seconds", 0.0),
            tool_calls_count=data.get("tool_calls_count", 0),
            model_id=data.get("model_id"),
        )


@dataclass
class FileMetadata:
    """
    生成文件的元数据
    
    记录阶段执行过程中生成的文件信息。
    
    属性:
        path: 文件相对路径（相对于 projects/<agent_name>/）
        size: 文件大小（字节）
        checksum: MD5 校验和（可选）
        last_modified: 最后修改时间（可选）
    """
    path: str
    size: int = 0
    checksum: Optional[str] = None
    last_modified: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        
        返回:
            Dict[str, Any]: 包含文件元数据的字典
        """
        return {
            "path": self.path,
            "size": self.size,
            "checksum": self.checksum,
            "last_modified": self.last_modified.isoformat() if self.last_modified else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FileMetadata":
        """
        从字典创建实例
        
        参数:
            data: 包含文件元数据的字典
            
        返回:
            FileMetadata: 新创建的实例
        """
        last_modified = None
        if data.get("last_modified"):
            last_modified = datetime.fromisoformat(data["last_modified"])
        
        return cls(
            path=data.get("path", ""),
            size=data.get("size", 0),
            checksum=data.get("checksum"),
            last_modified=last_modified,
        )


@dataclass
class StageOutput:
    """
    阶段输出数据
    
    存储单个阶段执行完成后的所有输出信息，包括内容、指标和生成的文件。
    
    Validates: Requirement 2.2 - Stage_Output 包含执行指标
    
    属性:
        stage_name: 阶段名称
        content: Agent 输出内容（最大 400KB，超出存储 S3 引用）
        metrics: 执行指标
        generated_files: 生成的文件列表
        document_content: 设计文档内容（JSON 或 Markdown 格式）
        document_format: 文档格式（json/markdown）
        completed_at: 完成时间
        status: 阶段状态
        error_message: 错误信息（失败时）
        s3_content_ref: S3 内容引用（内容超过 400KB 时使用）
    """
    stage_name: str
    content: str = ""
    metrics: StageMetrics = field(default_factory=StageMetrics)
    generated_files: List[FileMetadata] = field(default_factory=list)
    document_content: str = ""
    document_format: str = "markdown"
    completed_at: Optional[datetime] = None
    status: StageStatus = StageStatus.PENDING
    error_message: Optional[str] = None
    s3_content_ref: Optional[str] = None
    
    # 内容大小限制（400KB）
    MAX_CONTENT_SIZE = 400 * 1024
    
    @property
    def is_completed(self) -> bool:
        """
        检查阶段是否已完成
        
        返回:
            bool: 阶段是否处于完成状态
        """
        return self.status == StageStatus.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        """
        检查阶段是否失败
        
        返回:
            bool: 阶段是否处于失败状态
        """
        return self.status == StageStatus.FAILED
    
    @property
    def content_exceeds_limit(self) -> bool:
        """
        检查内容是否超过大小限制
        
        返回:
            bool: 内容是否超过 400KB
        """
        return len(self.content.encode('utf-8')) > self.MAX_CONTENT_SIZE
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式（用于 DynamoDB 存储）
        
        返回:
            Dict[str, Any]: 包含所有输出数据的字典
        """
        return {
            "stage_name": self.stage_name,
            "content": self.content if not self.s3_content_ref else "",
            "s3_content_ref": self.s3_content_ref,
            "metrics": self.metrics.to_dict(),
            "generated_files": [f.to_dict() for f in self.generated_files],
            "document_content": self.document_content,
            "document_format": self.document_format,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status.value,
            "error_message": self.error_message,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StageOutput":
        """
        从字典创建实例
        
        参数:
            data: 包含阶段输出数据的字典
            
        返回:
            StageOutput: 新创建的实例
        """
        completed_at = None
        if data.get("completed_at"):
            completed_at = datetime.fromisoformat(data["completed_at"])
        
        # 解析状态
        status_value = data.get("status", "pending")
        status = StageStatus(status_value) if isinstance(status_value, str) else status_value
        
        # 解析生成的文件
        generated_files = [
            FileMetadata.from_dict(f) for f in data.get("generated_files", [])
        ]
        
        # 解析指标
        metrics_data = data.get("metrics", {})
        metrics = StageMetrics.from_dict(metrics_data) if metrics_data else StageMetrics()
        
        return cls(
            stage_name=data.get("stage_name", ""),
            content=data.get("content", ""),
            metrics=metrics,
            generated_files=generated_files,
            document_content=data.get("document_content", ""),
            document_format=data.get("document_format", "markdown"),
            completed_at=completed_at,
            status=status,
            error_message=data.get("error_message"),
            s3_content_ref=data.get("s3_content_ref"),
        )


@dataclass
class IntentRecognitionResult:
    """
    意图识别结果
    
    存储编排器阶段对用户需求的意图分析结果。
    
    Validates: Requirement 9.4 - Stage_Context 包含意图分析结果
    
    属性:
        agent_name: 识别出的 Agent 名称
        agent_description: Agent 描述
        workflow_type: 工作流类型（single_agent/multi_agent）
        complexity: 复杂度评估（low/medium/high）
        estimated_stages: 预计需要的阶段列表
        key_features: 关键功能列表
        tool_requirements: 工具需求列表
        raw_analysis: 原始分析内容
    """
    agent_name: str = ""
    agent_description: str = ""
    workflow_type: str = "single_agent"
    complexity: str = "medium"
    estimated_stages: List[str] = field(default_factory=list)
    key_features: List[str] = field(default_factory=list)
    tool_requirements: List[str] = field(default_factory=list)
    raw_analysis: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        
        返回:
            Dict[str, Any]: 包含意图识别结果的字典
        """
        return {
            "agent_name": self.agent_name,
            "agent_description": self.agent_description,
            "workflow_type": self.workflow_type,
            "complexity": self.complexity,
            "estimated_stages": self.estimated_stages,
            "key_features": self.key_features,
            "tool_requirements": self.tool_requirements,
            "raw_analysis": self.raw_analysis,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IntentRecognitionResult":
        """
        从字典创建实例
        
        参数:
            data: 包含意图识别结果的字典
            
        返回:
            IntentRecognitionResult: 新创建的实例
        """
        return cls(
            agent_name=data.get("agent_name", ""),
            agent_description=data.get("agent_description", ""),
            workflow_type=data.get("workflow_type", "single_agent"),
            complexity=data.get("complexity", "medium"),
            estimated_stages=data.get("estimated_stages", []),
            key_features=data.get("key_features", []),
            tool_requirements=data.get("tool_requirements", []),
            raw_analysis=data.get("raw_analysis", ""),
        )


@dataclass
class AgentDefinition:
    """
    Agent 定义
    
    存储多 Agent 架构中单个 Agent 的定义信息。
    
    Validates: Requirement 6.1 - 多 Agent 架构记录
    
    属性:
        name: Agent 名称
        agent_type: Agent 类型（main/sub/tool）
        description: Agent 描述
        orchestration_pattern: 编排模式（agent_as_tool/swarm/graph）
        dependencies: 依赖的其他 Agent 列表
        tools: 需要的工具列表
        status: 当前状态
    """
    name: str
    agent_type: str = "main"  # main, sub, tool
    description: str = ""
    orchestration_pattern: str = "agent_as_tool"  # agent_as_tool, swarm, graph
    dependencies: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    status: StageStatus = StageStatus.PENDING
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "name": self.name,
            "agent_type": self.agent_type,
            "description": self.description,
            "orchestration_pattern": self.orchestration_pattern,
            "dependencies": self.dependencies,
            "tools": self.tools,
            "status": self.status.value,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentDefinition":
        """从字典创建实例"""
        status_value = data.get("status", "pending")
        status = StageStatus(status_value) if isinstance(status_value, str) else status_value
        
        return cls(
            name=data.get("name", ""),
            agent_type=data.get("agent_type", "main"),
            description=data.get("description", ""),
            orchestration_pattern=data.get("orchestration_pattern", "agent_as_tool"),
            dependencies=data.get("dependencies", []),
            tools=data.get("tools", []),
            status=status,
        )


@dataclass
class MultiAgentArchitecture:
    """
    多 Agent 架构
    
    存储多 Agent 项目的架构信息，包括所有 Agent 定义和编排模式。
    
    Validates: Requirement 6.1 - 多 Agent 架构记录
    
    属性:
        agents: Agent 定义列表
        orchestration_pattern: 整体编排模式
        main_agent: 主 Agent 名称
        agent_count: Agent 数量
    """
    agents: List[AgentDefinition] = field(default_factory=list)
    orchestration_pattern: str = "agent_as_tool"
    main_agent: str = ""
    
    @property
    def agent_count(self) -> int:
        """获取 Agent 数量"""
        return len(self.agents)
    
    @property
    def agent_names(self) -> List[str]:
        """获取所有 Agent 名称"""
        return [agent.name for agent in self.agents]
    
    def get_agent(self, name: str) -> Optional[AgentDefinition]:
        """获取指定名称的 Agent"""
        for agent in self.agents:
            if agent.name == name:
                return agent
        return None
    
    def add_agent(self, agent: AgentDefinition) -> None:
        """添加 Agent"""
        self.agents.append(agent)
        if agent.agent_type == "main" and not self.main_agent:
            self.main_agent = agent.name
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "agents": [agent.to_dict() for agent in self.agents],
            "orchestration_pattern": self.orchestration_pattern,
            "main_agent": self.main_agent,
            "agent_count": self.agent_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MultiAgentArchitecture":
        """从字典创建实例"""
        agents = [AgentDefinition.from_dict(a) for a in data.get("agents", [])]
        return cls(
            agents=agents,
            orchestration_pattern=data.get("orchestration_pattern", "agent_as_tool"),
            main_agent=data.get("main_agent", ""),
        )


@dataclass
class AgentStageProgress:
    """
    Agent 阶段进度
    
    跟踪多 Agent 项目中每个 Agent 在各阶段的进度。
    
    Validates: Requirement 6.7 - 多 Agent 进度跟踪
    
    属性:
        agent_name: Agent 名称
        stage_statuses: 各阶段状态（键为阶段名称）
        current_stage: 当前阶段
        completed_stages: 已完成阶段数
        total_stages: 总阶段数
    """
    agent_name: str
    stage_statuses: Dict[str, StageStatus] = field(default_factory=dict)
    current_stage: str = ""
    
    # Agent 开发相关的阶段
    AGENT_STAGES: List[str] = field(default_factory=lambda: [
        "agent_design",
        "tool_development",
        "prompt_engineering",
        "code_development",
        "testing",
    ])
    
    @property
    def completed_stages(self) -> int:
        """获取已完成阶段数"""
        return sum(1 for status in self.stage_statuses.values() 
                   if status == StageStatus.COMPLETED)
    
    @property
    def total_stages(self) -> int:
        """获取总阶段数"""
        return len(self.AGENT_STAGES)
    
    @property
    def progress_percentage(self) -> float:
        """获取进度百分比"""
        if self.total_stages == 0:
            return 0.0
        return (self.completed_stages / self.total_stages) * 100
    
    def update_stage_status(self, stage_name: str, status: StageStatus) -> None:
        """更新阶段状态"""
        self.stage_statuses[stage_name] = status
        if status == StageStatus.RUNNING:
            self.current_stage = stage_name
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "agent_name": self.agent_name,
            "stage_statuses": {k: v.value for k, v in self.stage_statuses.items()},
            "current_stage": self.current_stage,
            "completed_stages": self.completed_stages,
            "total_stages": self.total_stages,
            "progress_percentage": self.progress_percentage,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentStageProgress":
        """从字典创建实例"""
        stage_statuses = {}
        for stage, status_value in data.get("stage_statuses", {}).items():
            stage_statuses[stage] = StageStatus(status_value) if isinstance(status_value, str) else status_value
        
        return cls(
            agent_name=data.get("agent_name", ""),
            stage_statuses=stage_statuses,
            current_stage=data.get("current_stage", ""),
        )


@dataclass
class AggregatedMetrics:
    """
    聚合指标
    
    存储项目级别的聚合执行指标。
    
    Validates: Requirement 2.5 - Project_Record 包含聚合指标
    
    属性:
        total_input_tokens: 总输入 token 数
        total_output_tokens: 总输出 token 数
        total_tokens: 总 token 数
        total_cost: 总成本（美元）
        total_execution_time: 总执行时间（秒）
        total_tool_calls: 总工具调用次数
    """
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    total_execution_time: float = 0.0
    total_tool_calls: int = 0
    
    def add_stage_metrics(self, metrics: StageMetrics) -> None:
        """
        添加阶段指标到聚合指标
        
        参数:
            metrics: 要添加的阶段指标
        """
        self.total_input_tokens += metrics.input_tokens
        self.total_output_tokens += metrics.output_tokens
        self.total_tokens = self.total_input_tokens + self.total_output_tokens
        self.total_execution_time += metrics.execution_time_seconds
        self.total_tool_calls += metrics.tool_calls_count
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        
        返回:
            Dict[str, Any]: 包含聚合指标的字典
        """
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "total_execution_time": self.total_execution_time,
            "total_tool_calls": self.total_tool_calls,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AggregatedMetrics":
        """
        从字典创建实例
        
        参数:
            data: 包含聚合指标的字典
            
        返回:
            AggregatedMetrics: 新创建的实例
        """
        return cls(
            total_input_tokens=data.get("total_input_tokens", 0),
            total_output_tokens=data.get("total_output_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
            total_cost=data.get("total_cost", 0.0),
            total_execution_time=data.get("total_execution_time", 0.0),
            total_tool_calls=data.get("total_tool_calls", 0),
        )


@dataclass
class WorkflowContext:
    """
    工作流上下文
    
    管理工作流执行过程中的所有状态和数据，包括项目信息、规则、阶段输出等。
    
    Validates:
        - Requirement 9.1: 包含基础工作流规则
        - Requirement 9.2: 包含所有已完成阶段的输出
        - Requirement 9.3: 包含原始用户需求
        - Requirement 9.4: 包含意图分析结果
    
    属性:
        project_id: 项目唯一标识
        project_name: 项目名称
        requirement: 原始用户需求
        intent_result: 意图识别结果
        stage_outputs: 各阶段输出（键为阶段名称）
        rules: 工作流规则内容
        current_stage: 当前执行阶段
        status: 工作流控制状态
        aggregated_metrics: 聚合指标
        created_at: 创建时间
        updated_at: 更新时间
        control_status: 控制状态
        pause_requested_at: 暂停请求时间
        stop_requested_at: 停止请求时间
        resume_from_stage: 恢复起始阶段
        workflow_type: 工作流类型
    """
    project_id: str
    project_name: str = ""
    requirement: str = ""
    intent_result: Optional[IntentRecognitionResult] = None
    stage_outputs: Dict[str, StageOutput] = field(default_factory=dict)
    rules: str = ""
    current_stage: str = ""
    status: StageStatus = StageStatus.PENDING
    aggregated_metrics: AggregatedMetrics = field(default_factory=AggregatedMetrics)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    control_status: ControlStatus = ControlStatus.RUNNING
    pause_requested_at: Optional[datetime] = None
    stop_requested_at: Optional[datetime] = None
    resume_from_stage: Optional[str] = None
    workflow_type: str = "agent_build"
    
    # 工作流阶段顺序定义 - 延迟初始化
    _stage_order: List[str] = field(default_factory=list, repr=False)
    
    @property
    def STAGE_ORDER(self) -> List[str]:
        """
        获取工作流阶段顺序
        
        根据 workflow_type 动态获取对应的阶段顺序
        """
        if not self._stage_order:
            self._stage_order = _get_stage_sequence(self.workflow_type)
        return self._stage_order
    
    def set_workflow_type(self, workflow_type: str) -> None:
        """
        设置工作流类型并更新阶段顺序
        
        参数:
            workflow_type: 工作流类型
        """
        self.workflow_type = workflow_type
        self._stage_order = _get_stage_sequence(workflow_type)
    
    def get_completed_stages(self) -> List[str]:
        """
        获取所有已完成的阶段列表
        
        返回:
            List[str]: 已完成阶段名称列表（按执行顺序）
        """
        completed = []
        for stage_name in self.STAGE_ORDER:
            if stage_name in self.stage_outputs:
                output = self.stage_outputs[stage_name]
                if output.is_completed:
                    completed.append(stage_name)
        return completed
    
    def get_pending_stages(self) -> List[str]:
        """
        获取所有待执行的阶段列表
        
        返回:
            List[str]: 待执行阶段名称列表（按执行顺序）
        """
        completed = set(self.get_completed_stages())
        return [s for s in self.STAGE_ORDER if s not in completed]
    
    def get_next_stage(self) -> Optional[str]:
        """
        获取下一个待执行的阶段
        
        返回:
            Optional[str]: 下一个阶段名称，如果所有阶段都已完成则返回 None
        """
        pending = self.get_pending_stages()
        return pending[0] if pending else None
    
    def get_stage_output(self, stage_name: str) -> Optional[StageOutput]:
        """
        获取指定阶段的输出
        
        参数:
            stage_name: 阶段名称
            
        返回:
            Optional[StageOutput]: 阶段输出，如果不存在则返回 None
        """
        return self.stage_outputs.get(stage_name)
    
    def update_stage_output(self, stage_name: str, output: StageOutput) -> None:
        """
        更新阶段输出
        
        参数:
            stage_name: 阶段名称
            output: 阶段输出对象
        """
        self.stage_outputs[stage_name] = output
        self.updated_at = datetime.now()
        
        # 更新聚合指标
        if output.is_completed:
            self.aggregated_metrics.add_stage_metrics(output.metrics)
    
    def get_prerequisite_stages(self, stage_name: str) -> List[str]:
        """
        获取指定阶段的前置阶段列表
        
        参数:
            stage_name: 阶段名称
            
        返回:
            List[str]: 前置阶段名称列表
        """
        if stage_name not in self.STAGE_ORDER:
            return []
        
        stage_index = self.STAGE_ORDER.index(stage_name)
        return self.STAGE_ORDER[:stage_index]
    
    def are_prerequisites_completed(self, stage_name: str) -> bool:
        """
        检查指定阶段的所有前置阶段是否已完成
        
        参数:
            stage_name: 阶段名称
            
        返回:
            bool: 所有前置阶段是否都已完成
        """
        prerequisites = self.get_prerequisite_stages(stage_name)
        completed = set(self.get_completed_stages())
        return all(prereq in completed for prereq in prerequisites)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式（用于 DynamoDB 存储）
        
        返回:
            Dict[str, Any]: 包含所有上下文数据的字典
        """
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "requirement": self.requirement,
            "intent_result": self.intent_result.to_dict() if self.intent_result else None,
            "stage_outputs": {
                name: output.to_dict() for name, output in self.stage_outputs.items()
            },
            "rules": self.rules,
            "current_stage": self.current_stage,
            "status": self.status.value,
            "aggregated_metrics": self.aggregated_metrics.to_dict(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "control_status": self.control_status.value,
            "pause_requested_at": self.pause_requested_at.isoformat() if self.pause_requested_at else None,
            "stop_requested_at": self.stop_requested_at.isoformat() if self.stop_requested_at else None,
            "resume_from_stage": self.resume_from_stage,
            "workflow_type": self.workflow_type,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowContext":
        """
        从字典创建实例
        
        参数:
            data: 包含上下文数据的字典
            
        返回:
            WorkflowContext: 新创建的实例
        """
        # 解析时间字段
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        
        updated_at = None
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"])
        
        pause_requested_at = None
        if data.get("pause_requested_at"):
            pause_requested_at = datetime.fromisoformat(data["pause_requested_at"])
        
        stop_requested_at = None
        if data.get("stop_requested_at"):
            stop_requested_at = datetime.fromisoformat(data["stop_requested_at"])
        
        # 解析意图识别结果
        intent_result = None
        if data.get("intent_result"):
            intent_result = IntentRecognitionResult.from_dict(data["intent_result"])
        
        # 解析阶段输出
        stage_outputs = {}
        for name, output_data in data.get("stage_outputs", {}).items():
            stage_outputs[name] = StageOutput.from_dict(output_data)
        
        # 解析状态
        status_value = data.get("status", "pending")
        status = StageStatus(status_value) if isinstance(status_value, str) else status_value
        
        # 解析控制状态
        control_status_value = data.get("control_status", "running")
        control_status = ControlStatus(control_status_value) if isinstance(control_status_value, str) else control_status_value
        
        # 解析聚合指标
        aggregated_metrics_data = data.get("aggregated_metrics", {})
        aggregated_metrics = AggregatedMetrics.from_dict(aggregated_metrics_data) if aggregated_metrics_data else AggregatedMetrics()
        
        # 获取工作流类型
        workflow_type = data.get("workflow_type", "agent_build")
        
        return cls(
            project_id=data.get("project_id", ""),
            project_name=data.get("project_name", ""),
            requirement=data.get("requirement", ""),
            intent_result=intent_result,
            stage_outputs=stage_outputs,
            rules=data.get("rules", ""),
            current_stage=data.get("current_stage", ""),
            status=status,
            aggregated_metrics=aggregated_metrics,
            created_at=created_at,
            updated_at=updated_at,
            control_status=control_status,
            pause_requested_at=pause_requested_at,
            stop_requested_at=stop_requested_at,
            resume_from_stage=data.get("resume_from_stage"),
            workflow_type=workflow_type,
        )
