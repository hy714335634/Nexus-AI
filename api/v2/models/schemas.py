"""
Pydantic schemas for API v2 request/response models
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum


# ============== Enums ==============

class ProjectStatus(str, Enum):
    """项目状态"""
    PENDING = "pending"      # 等待中
    QUEUED = "queued"        # 已入队
    BUILDING = "building"    # 构建中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败
    PAUSED = "paused"        # 已暂停
    CANCELLED = "cancelled"  # 已取消


class ControlStatus(str, Enum):
    """
    工作流控制状态
    
    用于前端控制工作流执行。
    Validates: Requirement 3.1, 3.2 - 支持暂停和停止控制
    """
    RUNNING = "running"      # 正在运行
    PAUSED = "paused"        # 已暂停（完成当前阶段后停止）
    STOPPED = "stopped"      # 已停止（完成当前 LLM 调用后停止）
    CANCELLED = "cancelled"  # 已取消


class StageStatus(str, Enum):
    """阶段状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentStatus(str, Enum):
    """Agent状态"""
    BUILDING = "building"    # 构建中
    DEPLOYING = "deploying"  # 部署中
    RUNNING = "running"      # 运行中
    OFFLINE = "offline"      # 离线
    ERROR = "error"          # 错误


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """任务类型"""
    BUILD_AGENT = "build_agent"
    DEPLOY_AGENT = "deploy_agent"
    INVOKE_AGENT = "invoke_agent"


class BuildStage(str, Enum):
    """
    构建阶段枚举
    
    注意: 阶段的详细配置（显示名称、序号等）请使用 api.v2.core.stage_config 模块
    
    执行顺序：
    1. orchestrator - 工作流编排
    2. requirements_analysis - 需求分析
    3. system_architecture - 系统架构设计
    4. agent_design - Agent设计
    5. tools_developer - 工具开发（先开发工具）
    6. prompt_engineer - 提示词工程（基于已有工具）
    7. agent_code_developer - 代码开发
    8. agent_developer_manager - 开发管理
    9. agent_deployer - Agent部署
    """
    ORCHESTRATOR = "orchestrator"
    REQUIREMENTS_ANALYSIS = "requirements_analysis"
    SYSTEM_ARCHITECTURE = "system_architecture"
    AGENT_DESIGN = "agent_design"
    TOOLS_DEVELOPER = "tools_developer"
    PROMPT_ENGINEER = "prompt_engineer"
    AGENT_CODE_DEVELOPER = "agent_code_developer"
    AGENT_DEVELOPER_MANAGER = "agent_developer_manager"
    AGENT_DEPLOYER = "agent_deployer"

    @classmethod
    def get_stage_number(cls, stage: 'BuildStage') -> int:
        """
        获取阶段序号 (1-9)
        
        推荐使用: api.v2.core.stage_config.get_stage_number()
        """
        from api.v2.core.stage_config import get_stage_number
        return get_stage_number(stage.value)

    @classmethod
    def get_display_name(cls, stage: 'BuildStage') -> str:
        """
        获取阶段显示名称
        
        推荐使用: api.v2.core.stage_config.get_stage_display_name()
        """
        from api.v2.core.stage_config import get_stage_display_name
        return get_stage_display_name(stage.value)


class ToolSource(str, Enum):
    """工具来源"""
    SYSTEM = "system"
    GENERATED = "generated"
    IMPORTED = "imported"


# ============== Base Models ==============

class TimestampMixin(BaseModel):
    """时间戳混入"""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class APIResponse(BaseModel):
    """API响应基类"""
    success: bool = True
    data: Optional[Any] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None
    request_id: Optional[str] = None


class PaginationMeta(BaseModel):
    """分页元数据"""
    page: int = 1
    limit: int = 20
    total: int = 0
    pages: int = 0
    has_next: bool = False
    has_prev: bool = False


class PaginatedResponse(APIResponse):
    """分页响应基类"""
    pagination: Optional[PaginationMeta] = None


# ============== Stage Models ==============

class StageMetricsSchema(BaseModel):
    """
    阶段执行指标 Schema
    
    记录单个阶段执行过程中的资源消耗和性能指标。
    Validates: Requirement 2.2 - Stage_Output 包含执行指标
    """
    input_tokens: int = 0
    output_tokens: int = 0
    execution_time_seconds: float = 0.0
    tool_calls_count: int = 0
    model_id: Optional[str] = None
    
    @property
    def total_tokens(self) -> int:
        """计算总 token 数量"""
        return self.input_tokens + self.output_tokens


class FileMetadataSchema(BaseModel):
    """
    生成文件的元数据 Schema
    
    记录阶段执行过程中生成的文件信息。
    Validates: Requirement 2.3 - Stage_Output 包含生成文件路径列表
    """
    path: str
    size: int = 0
    checksum: Optional[str] = None
    last_modified: Optional[str] = None


class DesignDocumentSchema(BaseModel):
    """
    设计文档 Schema
    
    存储阶段产生的设计文档内容。
    Validates: Requirement 2.4 - 阶段完成时存储完整设计文档内容
    """
    content: str = ""
    format: str = "markdown"  # json/markdown
    version: str = "1.0"


class AggregatedMetricsSchema(BaseModel):
    """
    项目聚合指标 Schema
    
    存储项目级别的聚合执行指标。
    Validates: Requirement 2.5 - Project_Record 包含聚合指标
    """
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    total_execution_time: float = 0.0
    total_tool_calls: int = 0


# ============== Project Models ==============

class CreateProjectRequest(BaseModel):
    """创建项目请求"""
    requirement: str = Field(..., min_length=10, max_length=10000, description="需求描述")
    project_name: Optional[str] = Field(None, max_length=200, description="项目名称")
    user_id: Optional[str] = Field(None, max_length=100, description="用户ID")
    user_name: Optional[str] = Field(None, max_length=100, description="用户名")
    priority: int = Field(3, ge=1, le=5, description="优先级 1-5")
    tags: Optional[List[str]] = Field(default_factory=list, description="标签列表")

    @field_validator('requirement')
    @classmethod
    def validate_requirement(cls, v):
        if not v or not v.strip():
            raise ValueError('需求描述不能为空')
        return v.strip()


class ProjectRecord(TimestampMixin):
    """
    项目记录
    
    存储项目的完整信息，包括控制状态和聚合指标。
    
    Validates:
        - Requirement 2.5: 包含聚合指标
        - Requirement 3.1, 3.2: 包含控制状态字段
    """
    project_id: str
    project_name: Optional[str] = None
    status: ProjectStatus = ProjectStatus.PENDING
    requirement: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    priority: int = 3
    tags: List[str] = Field(default_factory=list)
    progress: float = 0.0
    current_stage: Optional[str] = None
    error_info: Optional[Dict[str, Any]] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    
    # 新增字段 - 控制状态（Requirement 3.1, 3.2）
    control_status: Optional[ControlStatus] = Field(
        default=ControlStatus.RUNNING,
        description="工作流控制状态"
    )
    pause_requested_at: Optional[str] = Field(
        None,
        description="暂停请求时间"
    )
    stop_requested_at: Optional[str] = Field(
        None,
        description="停止请求时间"
    )
    resume_from_stage: Optional[str] = Field(
        None,
        description="恢复起始阶段"
    )
    last_control_action: Optional[str] = Field(
        None,
        description="最后控制操作"
    )
    control_action_by: Optional[str] = Field(
        None,
        description="操作用户"
    )
    
    # 新增字段 - 聚合指标（Requirement 2.5）
    aggregated_metrics: Optional[AggregatedMetricsSchema] = Field(
        None,
        description="项目聚合指标"
    )


class ProjectSummary(BaseModel):
    """项目摘要"""
    project_id: str
    project_name: Optional[str] = None
    status: ProjectStatus
    progress: float = 0.0
    current_stage: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ProjectDetail(ProjectRecord):
    """项目详情"""
    stages: Optional[List['StageRecord']] = None
    agent_count: int = 0


class CreateProjectResponse(APIResponse):
    """创建项目响应"""
    data: Optional[Dict[str, Any]] = None


class ProjectListResponse(PaginatedResponse):
    """项目列表响应"""
    data: Optional[List[ProjectSummary]] = None


class ProjectDetailResponse(APIResponse):
    """项目详情响应"""
    data: Optional[ProjectDetail] = None


class ProjectControlRequest(BaseModel):
    """项目控制请求"""
    action: str = Field(..., pattern="^(pause|resume|stop|restart|cancel)$")
    reason: Optional[str] = Field(None, max_length=500)


class StageRecord(BaseModel):
    """
    阶段记录
    
    存储单个阶段的完整执行信息，包括状态、输出、指标和生成的文件。
    
    Validates:
        - Requirement 2.1: agent_output_content 最大 400KB
        - Requirement 2.2: 包含执行指标
        - Requirement 2.3: 包含生成文件路径列表
        - Requirement 2.4: 包含设计文档内容
    """
    project_id: str
    stage_name: str
    stage_number: int
    display_name: str
    status: StageStatus = StageStatus.PENDING
    agent_name: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    
    # 现有字段（保持兼容）
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    tool_calls: Optional[int] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    logs: Optional[List[str]] = None
    doc_path: Optional[str] = None
    
    # 新增字段 - Agent 输出内容
    agent_output_content: Optional[str] = Field(
        None, 
        description="Agent 输出内容，最大 400KB"
    )
    agent_output_s3_ref: Optional[str] = Field(
        None, 
        description="超大输出的 S3 引用"
    )
    
    # 新增字段 - 执行指标
    metrics: Optional[StageMetricsSchema] = Field(
        None, 
        description="阶段执行指标"
    )
    
    # 新增字段 - 生成的文件列表
    generated_files: Optional[List[FileMetadataSchema]] = Field(
        default_factory=list, 
        description="生成的文件列表"
    )
    
    # 新增字段 - 设计文档
    design_document: Optional[DesignDocumentSchema] = Field(
        None, 
        description="设计文档内容"
    )


class StageOutputRequest(BaseModel):
    """
    阶段输出更新请求
    
    用于更新阶段完成时的输出数据。
    """
    agent_output_content: Optional[str] = None
    metrics: Optional[StageMetricsSchema] = None
    generated_files: Optional[List[FileMetadataSchema]] = None
    design_document: Optional[DesignDocumentSchema] = None
    doc_path: Optional[str] = None


class StageListResponse(APIResponse):
    """阶段列表响应"""
    data: Optional[List[StageRecord]] = None


class StageDetailResponse(APIResponse):
    """阶段详情响应"""
    data: Optional[StageRecord] = None


class StageOutputResponse(APIResponse):
    """阶段输出响应"""
    data: Optional[Dict[str, Any]] = None


# ============== Agent Models ==============

class AgentCoreConfig(BaseModel):
    """AgentCore配置"""
    agent_arn: Optional[str] = None
    agent_alias_id: Optional[str] = None
    agent_alias_arn: Optional[str] = None


class AgentRecord(TimestampMixin):
    """Agent记录"""
    agent_id: str
    project_id: Optional[str] = None
    agent_name: str
    description: Optional[str] = None
    category: Optional[str] = None
    version: str = "1.0.0"
    status: AgentStatus = AgentStatus.OFFLINE
    deployment_type: str = "local"
    agentcore_config: Optional[AgentCoreConfig] = None
    capabilities: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    prompt_path: Optional[str] = None
    code_path: Optional[str] = None
    deployed_at: Optional[str] = None
    # AgentCore Runtime 信息 (从DynamoDB获取)
    agentcore_runtime_arn: Optional[str] = None
    agentcore_runtime_alias: Optional[str] = None
    agentcore_region: Optional[str] = None
    # Runtime stats
    total_invocations: int = 0
    successful_invocations: int = 0
    failed_invocations: int = 0
    avg_duration_ms: float = 0.0
    last_invoked_at: Optional[str] = None


class AgentSummary(BaseModel):
    """Agent摘要"""
    agent_id: str
    agent_name: str
    status: AgentStatus
    category: Optional[str] = None
    version: Optional[str] = None
    deployment_type: str = "local"
    total_invocations: int = 0
    created_at: Optional[str] = None


class AgentListResponse(PaginatedResponse):
    """Agent列表响应"""
    data: Optional[List[AgentSummary]] = None


class AgentDetailResponse(APIResponse):
    """Agent详情响应"""
    data: Optional[AgentRecord] = None


class AgentContextResponse(BaseModel):
    """Agent上下文响应"""
    agent_id: str
    display_name: Optional[str] = None
    system_prompt_path: Optional[str] = None
    code_path: Optional[str] = None
    tools_path: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    runtime_model_id: Optional[str] = None
    agentcore_runtime_arn: Optional[str] = None
    agentcore_runtime_alias: Optional[str] = None
    agentcore_region: Optional[str] = None


class AgentRuntimeHealthResponse(BaseModel):
    """Agent运行时健康状态响应"""
    agent_id: str
    agent_name: Optional[str] = None
    status: Optional[str] = None
    has_agentcore_arn: bool = False
    has_entrypoint: bool = False
    runtime_type: str = "unknown"
    agentcore_arn: Optional[str] = None
    entrypoint: Optional[str] = None
    is_ready: bool = False


class FileUploadResponse(BaseModel):
    """文件上传响应"""
    files: List[Dict[str, Any]] = Field(default_factory=list)
    count: int = 0
    session_id: str


class InvokeAgentRequest(BaseModel):
    """调用Agent请求"""
    input_text: str = Field(..., min_length=1, max_length=50000)
    session_id: Optional[str] = None
    enable_trace: bool = False
    metadata: Optional[Dict[str, Any]] = None


class InvokeAgentResponse(APIResponse):
    """调用Agent响应"""
    data: Optional[Dict[str, Any]] = None


# ============== Session Models ==============

class SessionRecord(TimestampMixin):
    """会话记录"""
    session_id: str
    agent_id: str
    user_id: Optional[str] = None
    display_name: Optional[str] = None
    status: str = "active"
    message_count: int = 0
    last_active_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class CreateSessionRequest(BaseModel):
    """创建会话请求"""
    display_name: Optional[str] = Field(None, max_length=200)
    user_id: Optional[str] = Field(None, max_length=100)
    metadata: Optional[Dict[str, Any]] = None


class SessionListResponse(APIResponse):
    """会话列表响应"""
    data: Optional[List[SessionRecord]] = None


class SessionDetailResponse(APIResponse):
    """会话详情响应"""
    data: Optional[SessionRecord] = None


# ============== Message Models ==============

class MessageRecord(BaseModel):
    """消息记录"""
    session_id: str
    message_id: str
    role: str  # user/assistant/system
    content: str
    created_at: str
    metadata: Optional[Dict[str, Any]] = None


class FileData(BaseModel):
    """文件数据"""
    filename: str
    content_type: str = "application/octet-stream"
    data: str  # base64 encoded
    file_id: Optional[str] = None
    size: Optional[int] = None


class SendMessageRequest(BaseModel):
    """发送消息请求"""
    content: str = Field(..., min_length=1, max_length=50000)
    role: str = Field("user", pattern="^(user|assistant|system)$")
    metadata: Optional[Dict[str, Any]] = None
    files: Optional[List[FileData]] = Field(default=None, description="上传的文件列表")


class MessageListResponse(APIResponse):
    """消息列表响应"""
    data: Optional[List[MessageRecord]] = None


class SendMessageResponse(APIResponse):
    """发送消息响应"""
    data: Optional[MessageRecord] = None


# ============== Task Models ==============

class TaskRecord(TimestampMixin):
    """任务记录"""
    task_id: str
    task_type: TaskType
    project_id: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 3
    payload: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    worker_id: Optional[str] = None


class TaskStatusResponse(APIResponse):
    """任务状态响应"""
    data: Optional[TaskRecord] = None


# ============== Tool Models ==============

class ToolSchema(BaseModel):
    """工具Schema"""
    name: str
    description: str
    parameters: Optional[Dict[str, Any]] = None


class ToolRecord(TimestampMixin):
    """工具记录"""
    tool_id: str
    tool_name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    source: ToolSource = ToolSource.SYSTEM
    version: str = "1.0.0"
    code_path: Optional[str] = None
    schema_def: Optional[ToolSchema] = None
    dependencies: List[str] = Field(default_factory=list)
    usage_count: int = 0


class ToolListResponse(PaginatedResponse):
    """工具列表响应"""
    data: Optional[List[ToolRecord]] = None


class ToolDetailResponse(APIResponse):
    """工具详情响应"""
    data: Optional[ToolRecord] = None


# ============== Statistics Models ==============

class StatisticsOverview(BaseModel):
    """统计概览"""
    total_projects: int = 0
    building_projects: int = 0
    completed_projects: int = 0
    failed_projects: int = 0
    total_agents: int = 0
    running_agents: int = 0
    total_invocations: int = 0
    today_invocations: int = 0
    success_rate: float = 0.0
    avg_build_time_minutes: float = 0.0


class StatisticsOverviewResponse(APIResponse):
    """统计概览响应"""
    data: Optional[StatisticsOverview] = None


class BuildStatistics(BaseModel):
    """构建统计"""
    date: str
    total_builds: int = 0
    successful_builds: int = 0
    failed_builds: int = 0
    avg_duration_minutes: float = 0.0


class BuildStatisticsResponse(APIResponse):
    """构建统计响应"""
    data: Optional[List[BuildStatistics]] = None


class InvocationStatistics(BaseModel):
    """调用统计"""
    date: str
    total_invocations: int = 0
    successful_invocations: int = 0
    failed_invocations: int = 0
    avg_duration_ms: float = 0.0


class InvocationStatisticsResponse(APIResponse):
    """调用统计响应"""
    data: Optional[List[InvocationStatistics]] = None


# ============== Build Dashboard Models ==============

class BuildDashboardStage(BaseModel):
    """构建仪表板阶段"""
    name: str
    display_name: str
    order: int
    status: StageStatus
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    error: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    tool_calls: Optional[int] = None
    efficiency_rating: Optional[str] = None
    doc_path: Optional[str] = None
    artifact_paths: Optional[List[str]] = None


class BuildDashboardMetrics(BaseModel):
    """构建仪表板指标"""
    total_duration_seconds: Optional[float] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    tool_calls: Optional[int] = None
    total_tools: Optional[int] = None
    # 成本估算
    cost_input_usd: Optional[float] = None
    cost_output_usd: Optional[float] = None
    cost_total_usd: Optional[float] = None
    pricing_model: Optional[str] = None
    # 阶段统计
    successful_stages: Optional[int] = None
    failed_stages: Optional[int] = None


class BuildDashboardData(BaseModel):
    """构建仪表板数据"""
    project_id: str
    project_name: Optional[str] = None
    local_project_dir: Optional[str] = None
    status: ProjectStatus
    progress: float = 0.0
    requirement: Optional[str] = None
    stages: List[BuildDashboardStage] = Field(default_factory=list)
    total_stages: int = 9
    completed_stages: int = 0
    updated_at: Optional[str] = None
    metrics: Optional[BuildDashboardMetrics] = None
    config_summary: Optional[Dict[str, Any]] = None
    error_info: Optional[Dict[str, Any]] = None


class BuildDashboardResponse(APIResponse):
    """构建仪表板响应"""
    data: Optional[BuildDashboardData] = None
