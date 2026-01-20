"""
Agents API Router

Agent 管理相关的 API 端点
"""
from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional
import logging
from datetime import datetime, timezone
import uuid

from api.v2.models.schemas import (
    AgentListResponse,
    AgentDetailResponse,
    InvokeAgentRequest,
    InvokeAgentResponse,
    APIResponse,
    AgentStatus,
    AgentContextResponse,
    AgentRuntimeHealthResponse,
)
from api.v2.services import agent_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["Agents"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _request_id() -> str:
    return str(uuid.uuid4())


@router.get("", response_model=AgentListResponse)
async def list_agents(
    status: Optional[str] = Query(None, description="按状态筛选"),
    category: Optional[str] = Query(None, description="按类别筛选"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量")
):
    """
    获取 Agent 列表
    """
    try:
        result = agent_service.list_agents(
            status=status,
            category=category,
            page=page,
            limit=limit
        )
        
        return AgentListResponse(
            success=True,
            data=result.get('items', []),
            pagination=result.get('pagination'),
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except Exception as e:
        logger.error(f"Failed to list agents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取 Agent 列表失败: {str(e)}")


@router.get("/{agent_id}", response_model=AgentDetailResponse)
async def get_agent(
    agent_id: str = Path(..., description="Agent ID")
):
    """
    获取 Agent 详情
    """
    try:
        agent = agent_service.get_agent(agent_id)
        
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} 不存在")
        
        return AgentDetailResponse(
            success=True,
            data=agent,
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取 Agent 详情失败: {str(e)}")


@router.get("/{agent_id}/context", response_model=APIResponse)
async def get_agent_context(
    agent_id: str = Path(..., description="Agent ID")
):
    """
    获取 Agent 上下文信息
    
    返回 Agent 的配置信息，包括提示词路径、代码路径、工具路径等
    """
    try:
        agent = agent_service.get_agent(agent_id)
        
        if not agent:
            # 返回空上下文而不是404
            return APIResponse(
                success=True,
                data=AgentContextResponse(agent_id=agent_id).model_dump(),
                timestamp=_now(),
                request_id=_request_id()
            )
        
        tags = agent.get("tags") or (agent.get("metadata") or {}).get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        
        context = AgentContextResponse(
            agent_id=agent_id,
            display_name=agent.get("display_name") or agent.get("agent_name"),
            system_prompt_path=agent.get("prompt_path"),
            code_path=agent.get("code_path"),
            tools_path=agent.get("tools_path"),
            description=agent.get("description"),
            tags=list(tags),
            runtime_model_id=agent.get("runtime_model_id"),
            agentcore_runtime_arn=agent.get("agentcore_runtime_arn") or agent.get("agentcore_arn"),
            agentcore_runtime_alias=agent.get("agentcore_runtime_alias") or agent.get("agentcore_alias"),
            agentcore_region=agent.get("agentcore_region") or agent.get("region"),
        )
        
        return APIResponse(
            success=True,
            data=context.model_dump(),
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except Exception as e:
        logger.error(f"Failed to get agent context {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取 Agent 上下文失败: {str(e)}")


@router.get("/{agent_id}/runtime/health", response_model=APIResponse)
async def check_agent_runtime_health(
    agent_id: str = Path(..., description="Agent ID")
):
    """
    检查 Agent 运行时健康状态
    """
    try:
        agent = agent_service.get_agent(agent_id)
        
        if not agent:
            return APIResponse(
                success=False,
                data=None,
                message=f"Agent '{agent_id}' not found in database",
                timestamp=_now(),
                request_id=_request_id()
            )
        
        runtime_arn = agent.get("agentcore_runtime_arn") or agent.get("agentcore_arn")
        entrypoint = agent.get("entrypoint") or agent.get("code_path")
        
        health_status = AgentRuntimeHealthResponse(
            agent_id=agent_id,
            agent_name=agent.get("agent_name"),
            status=agent.get("status"),
            has_agentcore_arn=bool(runtime_arn),
            has_entrypoint=bool(entrypoint),
            runtime_type="agentcore" if runtime_arn else "local_http",
            agentcore_arn=runtime_arn if runtime_arn else None,
            entrypoint=entrypoint if entrypoint else None,
            is_ready=bool(runtime_arn or entrypoint),
        )
        
        return APIResponse(
            success=True,
            data=health_status.model_dump(),
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except Exception as e:
        logger.error(f"Failed to check agent runtime health {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"检查 Agent 运行时健康状态失败: {str(e)}")


@router.post("/{agent_id}/invoke", response_model=InvokeAgentResponse)
async def invoke_agent(
    agent_id: str = Path(..., description="Agent ID"),
    request: InvokeAgentRequest = None
):
    """
    调用 Agent
    
    发送输入文本，获取 Agent 响应
    """
    try:
        agent = agent_service.get_agent(agent_id)
        
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} 不存在")
        
        if agent.get('status') != AgentStatus.RUNNING.value:
            raise HTTPException(status_code=400, detail=f"Agent {agent_id} 当前不可用")
        
        # TODO: 实现实际的 Agent 调用逻辑
        # 这里需要根据 deployment_type 调用不同的后端
        # - local: 调用本地 Agent
        # - agentcore: 调用 AWS Bedrock AgentCore
        
        # 模拟响应
        result = {
            'invocation_id': f"inv_{uuid.uuid4().hex[:12]}",
            'session_id': request.session_id,
            'output': "这是一个模拟响应。实际实现需要调用 Agent 后端。",
            'duration_ms': 100,
            'status': 'success'
        }
        
        return InvokeAgentResponse(
            success=True,
            data=result,
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to invoke agent {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"调用 Agent 失败: {str(e)}")


@router.put("/{agent_id}/status", response_model=APIResponse)
async def update_agent_status(
    agent_id: str = Path(..., description="Agent ID"),
    status: str = Query(..., description="新状态"),
    error_message: Optional[str] = Query(None, description="错误信息")
):
    """
    更新 Agent 状态
    """
    try:
        agent = agent_service.get_agent(agent_id)
        
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} 不存在")
        
        try:
            agent_status = AgentStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的状态: {status}")
        
        agent_service.update_agent_status(agent_id, agent_status, error_message)
        
        return APIResponse(
            success=True,
            message="Agent 状态更新成功",
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update agent status {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新 Agent 状态失败: {str(e)}")


@router.delete("/{agent_id}", response_model=APIResponse)
async def delete_agent(
    agent_id: str = Path(..., description="Agent ID")
):
    """
    删除 Agent
    """
    try:
        success = agent_service.delete_agent(agent_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} 不存在")
        
        return APIResponse(
            success=True,
            message="Agent 删除成功",
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete agent {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除 Agent 失败: {str(e)}")
