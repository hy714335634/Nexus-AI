"""
Pydantic schemas for request/response models
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
from decimal import Decimal

# Enums
class ProjectStatus(str, Enum):
    PENDING = "pending"
    BUILDING = "building"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class AgentStatus(str, Enum):
    RUNNING = "running"
    BUILDING = "building"
    OFFLINE = "offline"

class BuildStage(str, Enum):
    """Workflow stages following orchestrator-driven pipeline"""
    ORCHESTRATOR = "orchestrator"                        # 0. 编排器
    REQUIREMENTS_ANALYSIS = "requirements_analysis"      # 1. 需求分析
    SYSTEM_ARCHITECTURE = "system_architecture"         # 2. 系统架构设计
    AGENT_DESIGN = "agent_design"                       # 3. Agent设计
    AGENT_DEVELOPER_MANAGER = "agent_developer_manager" # 4. 开发管理
    
    @classmethod
    def get_stage_number(cls, stage: 'BuildStage') -> int:
        """Get stage number (1-8) from stage enum"""
        stage_order = [
            cls.ORCHESTRATOR,
            cls.REQUIREMENTS_ANALYSIS,
            cls.SYSTEM_ARCHITECTURE,
            cls.AGENT_DESIGN,
            cls.AGENT_DEVELOPER_MANAGER,
        ]
        return stage_order.index(stage) + 1
    
    @classmethod
    def get_stage_by_number(cls, stage_number: int) -> 'BuildStage':
        """Get stage enum from stage number (1-8)"""
        stage_order = [
            cls.ORCHESTRATOR,
            cls.REQUIREMENTS_ANALYSIS,
            cls.SYSTEM_ARCHITECTURE,
            cls.AGENT_DESIGN,
            cls.AGENT_DEVELOPER_MANAGER,
        ]
        if 1 <= stage_number <= len(stage_order):
            return stage_order[stage_number - 1]
        raise ValueError(f"Invalid stage number: {stage_number}. Must be between 1 and {len(stage_order)}.")
    
    @classmethod
    def get_stage_name_cn(cls, stage: 'BuildStage') -> str:
        """Get Chinese name for stage"""
        stage_names = {
            cls.ORCHESTRATOR: "工作流编排",
            cls.REQUIREMENTS_ANALYSIS: "需求分析",
            cls.SYSTEM_ARCHITECTURE: "系统架构设计",
            cls.AGENT_DESIGN: "Agent设计",
            cls.AGENT_DEVELOPER_MANAGER: "开发管理",
        }
        return stage_names.get(stage, stage.value)

# Request Models
class CreateAgentRequest(BaseModel):
    requirement: str = Field(..., max_length=5000, description="自然语言需求描述")
    user_id: str = Field(..., min_length=1, max_length=100, description="用户ID")
    user_name: Optional[str] = Field(None, max_length=100, description="用户名称")
    priority: Optional[int] = Field(3, ge=1, le=5, description="优先级 (1-5)")
    tags: Optional[List[str]] = Field(default_factory=list, description="标签列表")
    
    @field_validator('requirement')
    @classmethod
    def validate_requirement(cls, v):
        if not isinstance(v, str):
            raise ValueError('需求描述必须是字符串')
        
        stripped = v.strip()
        if not stripped:
            raise ValueError('需求描述不能为空')
        
        if len(stripped) < 10:
            raise ValueError('需求描述至少需要10个字符')
            
        return stripped

class BuildControlRequest(BaseModel):
    action: str = Field(..., pattern="^(pause|resume|stop|restart)$", description="控制操作")
    reason: Optional[str] = Field(None, max_length=500, description="操作原因")

# Response Models
class APIResponse(BaseModel):
    success: bool
    timestamp: datetime
    request_id: str

class CreateAgentResponse(APIResponse):
    data: Dict[str, Any] = Field(..., description="响应数据")


class TaskStatusData(BaseModel):
    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    date_done: Optional[datetime] = None


class TaskStatusResponse(APIResponse):
    data: TaskStatusData

class ProjectStatusData(BaseModel):
    project_id: str
    project_name: Optional[str] = None
    status: ProjectStatus
    current_stage: Optional[BuildStage] = None
    stage_number: Optional[int] = None  # For backward compatibility
    stage_name: Optional[str] = None
    progress_percentage: float = Field(0.0, ge=0.0, le=100.0)
    started_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    current_agent: Optional[str] = None
    current_work: Optional[str] = None
    error_info: Optional[Dict[str, Any]] = None

class ProjectStatusResponse(APIResponse):
    data: ProjectStatusData

class StageData(BaseModel):
    stage: BuildStage
    stage_number: int = Field(..., ge=1, le=8)
    stage_name: str
    stage_name_cn: str
    status: StageStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    agent_name: Optional[str] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    logs: Optional[List[str]] = None

class StagesResponse(APIResponse):
    data: Dict[str, Any]

class AgentSummary(BaseModel):
    agent_id: str
    project_id: str
    agent_name: str
    category: Optional[str] = None
    status: AgentStatus
    version: Optional[str] = None
    created_at: datetime
    call_count: int = 0
    success_rate: float = Field(0.0, ge=0.0, le=100.0)

class AgentListData(BaseModel):
    agents: List[AgentSummary]
    pagination: Dict[str, Any]

class AgentListResponse(APIResponse):
    data: AgentListData

class AgentDetails(BaseModel):
    agent_id: str
    project_id: str
    agent_name: str
    description: Optional[str] = None
    category: Optional[str] = None
    version: Optional[str] = None
    status: AgentStatus
    script_path: Optional[str] = None
    prompt_path: Optional[str] = None
    tools_count: int = 0
    dependencies: List[str] = Field(default_factory=list)
    supported_models: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    call_count: int = 0
    success_rate: float = Field(0.0, ge=0.0, le=100.0)
    last_called_at: Optional[datetime] = None
    created_at: datetime

class AgentDetailsResponse(APIResponse):
    data: AgentDetails

class StatisticsOverview(BaseModel):
    total_agents: int = 0
    running_agents: int = 0
    building_agents: int = 0
    offline_agents: int = 0
    total_builds: int = 0
    success_rate: float = Field(0.0, ge=0.0, le=100.0)
    avg_build_time_minutes: float = 0.0
    today_calls: int = 0

class StatisticsOverviewResponse(APIResponse):
    data: StatisticsOverview

class BuildStatistics(BaseModel):
    date: str
    total_builds: int = 0
    successful_builds: int = 0
    failed_builds: int = 0
    avg_duration_minutes: float = 0.0
    builds_by_stage: Dict[str, int] = Field(default_factory=dict)

class BuildStatisticsResponse(APIResponse):
    data: List[BuildStatistics]

# Database Models (for internal use)
class ProjectRecord(BaseModel):
    project_id: str
    project_name: Optional[str] = None
    user_id: str
    user_name: Optional[str] = None
    original_requirement: str
    status: ProjectStatus
    current_stage: Optional[BuildStage] = None
    current_stage_number: int = 0  # For DynamoDB storage
    progress_percentage: float = 0.0
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    agent_config: Optional[Dict[str, Any]] = None
    build_summary: Optional[Dict[str, Any]] = None
    error_info: Optional[Dict[str, Any]] = None
    tags: List[str] = Field(default_factory=list)
    priority: int = 3
    stages_snapshot: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

class StageRecord(BaseModel):
    project_id: str
    stage: BuildStage
    stage_number: int  # For DynamoDB sort key
    stage_name: str
    stage_name_cn: str
    status: StageStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    agent_name: Optional[str] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    logs: List[str] = Field(default_factory=list)

class AgentRecord(BaseModel):
    agent_id: str
    project_id: str
    agent_name: str
    category: Optional[str] = None
    description: Optional[str] = None
    version: str = "v1.0.0"
    status: AgentStatus
    script_path: Optional[str] = None
    prompt_path: Optional[str] = None
    tools_count: int = 0
    dependencies: List[str] = Field(default_factory=list)
    supported_models: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    call_count: int = 0
    success_rate: float = 0.0
    last_called_at: Optional[datetime] = None
    created_at: datetime

# Helper functions for stage management
def create_stage_data(stage: BuildStage, status: StageStatus = StageStatus.PENDING, **kwargs) -> StageData:
    """Create StageData with proper stage information"""
    return StageData(
        stage=stage,
        stage_number=BuildStage.get_stage_number(stage),
        stage_name=stage.value,
        stage_name_cn=BuildStage.get_stage_name_cn(stage),
        status=status,
        **kwargs
    )

def create_stage_record(project_id: str, stage: BuildStage, status: StageStatus = StageStatus.PENDING, **kwargs) -> StageRecord:
    """Create StageRecord with proper stage information"""
    return StageRecord(
        project_id=project_id,
        stage=stage,
        stage_number=BuildStage.get_stage_number(stage),
        stage_name=stage.value,
        stage_name_cn=BuildStage.get_stage_name_cn(stage),
        status=status,
        **kwargs
    )

def get_all_stages() -> List[BuildStage]:
    """Get all build stages in order"""
    return [
        BuildStage.ORCHESTRATOR,
        BuildStage.REQUIREMENTS_ANALYSIS,
        BuildStage.SYSTEM_ARCHITECTURE,
        BuildStage.AGENT_DESIGN,
        BuildStage.AGENT_DEVELOPER_MANAGER,
    ]


def build_initial_stage_snapshot(
    include_agent_names: bool = False,
    agent_name_map: Optional[Dict[BuildStage, Optional[str]]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Create the default stages snapshot map for a new project."""
    snapshot: Dict[str, Dict[str, Any]] = {}
    for stage in get_all_stages():
        stage_data = create_stage_data(
            stage,
            status=StageStatus.PENDING,
            logs=[],
        )
        payload = stage_data.model_dump(mode="json")
        if include_agent_names and agent_name_map is not None:
            payload['agent_name'] = agent_name_map.get(stage)
        elif not include_agent_names:
            payload.pop("agent_name", None)
        snapshot[stage.value] = payload
    return snapshot
