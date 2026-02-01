"""
工作流相关的 Pydantic schemas

支持多种工作流类型：
- agent_build: Agent 构建工作流
- agent_update: Agent 更新工作流
- tool_build: 工具构建工作流
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from enum import Enum


class WorkflowType(str, Enum):
    """工作流类型"""
    AGENT_BUILD = "agent_build"
    AGENT_UPDATE = "agent_update"
    TOOL_BUILD = "tool_build"
    MAGICIAN = "magician"


class TaskType(str, Enum):
    """任务类型"""
    BUILD_AGENT = "build_agent"
    UPDATE_AGENT = "update_agent"
    BUILD_TOOL = "build_tool"
    DEPLOY_AGENT = "deploy_agent"
    INVOKE_AGENT = "invoke_agent"


# ============== Agent Update Workflow ==============

class UpdateAgentRequest(BaseModel):
    """Agent 更新请求"""
    agent_id: str = Field(..., description="要更新的 Agent ID")
    update_requirement: str = Field(
        ..., 
        min_length=10, 
        max_length=10000, 
        description="更新需求描述"
    )
    user_id: Optional[str] = Field(None, max_length=100, description="用户ID")
    user_name: Optional[str] = Field(None, max_length=100, description="用户名")
    priority: int = Field(3, ge=1, le=5, description="优先级 1-5")
    
    @field_validator('update_requirement')
    @classmethod
    def validate_requirement(cls, v):
        if not v or not v.strip():
            raise ValueError('更新需求描述不能为空')
        return v.strip()


class UpdateAgentResponse(BaseModel):
    """Agent 更新响应"""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None
    request_id: Optional[str] = None


# ============== Tool Build Workflow ==============

class BuildToolRequest(BaseModel):
    """工具构建请求"""
    tool_name: Optional[str] = Field(None, max_length=200, description="工具名称")
    requirement: str = Field(
        ..., 
        min_length=10, 
        max_length=10000, 
        description="工具需求描述"
    )
    category: Optional[str] = Field(None, max_length=100, description="工具类别")
    target_agent: Optional[str] = Field(None, description="目标 Agent（可选）")
    user_id: Optional[str] = Field(None, max_length=100, description="用户ID")
    user_name: Optional[str] = Field(None, max_length=100, description="用户名")
    priority: int = Field(3, ge=1, le=5, description="优先级 1-5")
    tags: Optional[List[str]] = Field(default_factory=list, description="标签列表")
    
    @field_validator('requirement')
    @classmethod
    def validate_requirement(cls, v):
        if not v or not v.strip():
            raise ValueError('工具需求描述不能为空')
        return v.strip()


class BuildToolResponse(BaseModel):
    """工具构建响应"""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None
    request_id: Optional[str] = None


# ============== Workflow Control ==============

class WorkflowControlRequest(BaseModel):
    """工作流控制请求"""
    action: str = Field(..., pattern="^(pause|resume|stop|restart|cancel)$")
    reason: Optional[str] = Field(None, max_length=500)
    from_stage: Optional[str] = Field(None, description="从指定阶段恢复/重启")


class WorkflowStatusResponse(BaseModel):
    """工作流状态响应"""
    project_id: str
    workflow_type: WorkflowType
    status: str
    control_status: str
    current_stage: Optional[str] = None
    completed_stages: List[str] = Field(default_factory=list)
    pending_stages: List[str] = Field(default_factory=list)
    progress: float = 0.0
    error_info: Optional[Dict[str, Any]] = None
