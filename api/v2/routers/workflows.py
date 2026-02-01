"""
Workflows API Router

工作流管理相关的 API 端点，支持：
- Agent 更新工作流
- 工具构建工作流
"""
from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional
import logging
from datetime import datetime, timezone
import uuid

from api.v2.models.schemas import APIResponse
from api.v2.models.workflow_schemas import (
    UpdateAgentRequest,
    UpdateAgentResponse,
    BuildToolRequest,
    BuildToolResponse,
    WorkflowStatusResponse,
    WorkflowType,
)
from api.v2.services.workflow_service import workflow_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflows", tags=["Workflows"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _request_id() -> str:
    return str(uuid.uuid4())


# ============== Agent Update Workflow ==============

@router.post("/agent-update", response_model=UpdateAgentResponse)
async def create_agent_update(request: UpdateAgentRequest):
    """
    创建 Agent 更新工作流
    
    根据更新需求，对已有 Agent 进行更新，包括：
    - 更新工具函数
    - 更新提示词模板
    - 更新 Agent 代码
    
    更新进度会实时显示在项目构建模块中。
    """
    try:
        result = workflow_service.create_agent_update_project(
            agent_id=request.agent_id,
            update_requirement=request.update_requirement,
            user_id=request.user_id,
            user_name=request.user_name,
            priority=request.priority,
        )
        
        return UpdateAgentResponse(
            success=True,
            message="Agent 更新任务已创建",
            data=result,
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create agent update: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建 Agent 更新任务失败: {str(e)}")


@router.post("/agents/{agent_id}/update", response_model=UpdateAgentResponse)
async def update_agent(
    agent_id: str = Path(..., description="Agent ID"),
    request: UpdateAgentRequest = None
):
    """
    更新指定 Agent（便捷端点）
    
    在 Agent 详情页点击更新按钮时调用此端点。
    """
    try:
        # 使用路径中的 agent_id
        result = workflow_service.create_agent_update_project(
            agent_id=agent_id,
            update_requirement=request.update_requirement,
            user_id=request.user_id,
            user_name=request.user_name,
            priority=request.priority,
        )
        
        return UpdateAgentResponse(
            success=True,
            message="Agent 更新任务已创建",
            data=result,
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update agent {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新 Agent 失败: {str(e)}")


# ============== Tool Build Workflow ==============

@router.post("/tool-build", response_model=BuildToolResponse)
async def create_tool_build(request: BuildToolRequest):
    """
    创建工具构建工作流
    
    根据需求描述自动构建工具函数，包括：
    - 需求分析
    - 工具设计
    - 代码开发
    - 功能验证
    - 文档生成
    
    构建进度会实时显示在项目构建模块中。
    """
    try:
        result = workflow_service.create_tool_build_project(
            requirement=request.requirement,
            tool_name=request.tool_name,
            category=request.category,
            target_agent=request.target_agent,
            user_id=request.user_id,
            user_name=request.user_name,
            priority=request.priority,
            tags=request.tags,
        )
        
        return BuildToolResponse(
            success=True,
            message="工具构建任务已创建",
            data=result,
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create tool build: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建工具构建任务失败: {str(e)}")


# ============== Workflow Status ==============

@router.get("/{project_id}/status", response_model=APIResponse)
async def get_workflow_status(
    project_id: str = Path(..., description="项目ID")
):
    """
    获取工作流状态
    
    返回工作流的当前状态、进度、已完成阶段等信息。
    """
    try:
        status = workflow_service.get_workflow_status(project_id)
        
        if not status:
            raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")
        
        return APIResponse(
            success=True,
            data=status,
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow status {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取工作流状态失败: {str(e)}")


@router.get("/types", response_model=APIResponse)
async def list_workflow_types():
    """
    获取支持的工作流类型列表
    """
    try:
        from nexus_utils.workflow_config import WorkflowConfigManager
        
        manager = WorkflowConfigManager()
        workflows = manager.get_enabled_workflows()
        
        result = []
        for workflow_type, config in workflows.items():
            result.append({
                'type': workflow_type,
                'name': config.name,
                'display_name': config.display_name,
                'description': config.description,
                'stages_count': len(config.stages),
                'enabled': config.enabled,
            })
        
        return APIResponse(
            success=True,
            data=result,
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except Exception as e:
        logger.error(f"Failed to list workflow types: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取工作流类型失败: {str(e)}")
