"""
Agents Management API endpoints

提供Agent实例管理的RESTful API，包括查询、调用、更新和删除
"""
from fastapi import APIRouter, HTTPException, Query, Path, Body
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime, timezone

from api.models.schemas import (
    APIResponse,
    AgentStatus,
)
from api.core.exceptions import APIException, ResourceNotFoundError, ValidationError
from api.services import (
    AgentService,
    agent_service,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/agents/{agent_id}/invoke")
async def invoke_agent(
    agent_id: str = Path(..., description="Agent ID"),
    input_text: str = Body(..., description="输入文本"),
    session_id: Optional[str] = Body(None, description="会话ID（用于多轮对话）"),
    enable_trace: bool = Body(False, description="是否启用追踪"),
    end_session: bool = Body(False, description="是否结束会话"),
    session_state: Optional[Dict[str, Any]] = Body(None, description="会话状态")
):
    """
    调用Agent（仅支持AgentCore部署）

    通过AWS Bedrock AgentCore调用已部署的Agent，支持单轮和多轮对话

    Requirements: 5.1, 5.2, 5.3
    """
    try:
        result = agent_service.invoke_agent(
            agent_id=agent_id,
            input_text=input_text,
            session_id=session_id,
            enable_trace=enable_trace,
            end_session=end_session,
            session_state=session_state
        )

        return {
            "success": True,
            "data": result,
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except APIException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to invoke agent {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to invoke agent: {str(e)}")


@router.get("/agents")
async def list_agents(
    project_id: Optional[str] = Query(None, description="按项目ID过滤"),
    status: Optional[AgentStatus] = Query(None, description="按状态过滤"),
    category: Optional[str] = Query(None, description="按类别过滤"),
    capabilities: Optional[str] = Query(None, description="按能力过滤（逗号分隔）"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    last_key: Optional[str] = Query(None, description="分页游标")
):
    """
    获取Agent列表

    支持按项目ID、状态、类别、能力过滤，支持分页

    Requirements: 4.3
    """
    try:
        # 解析capabilities
        capabilities_list = None
        if capabilities:
            capabilities_list = [c.strip() for c in capabilities.split(",")]

        result = agent_service.list_agents(
            project_id=project_id,
            status=status,
            limit=limit,
            last_key=last_key
        )

        # 应用category和capabilities过滤（在service层之后）
        items = result["items"]
        if category:
            items = [a for a in items if a.get("category") == category]
        if capabilities_list:
            items = [
                a for a in items
                if any(cap in a.get("capabilities", []) for cap in capabilities_list)
            ]

        return {
            "success": True,
            "data": {
                "items": items,
                "last_evaluated_key": result.get("last_evaluated_key"),
                "count": len(items)
            },
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }

    except Exception as e:
        logger.error(f"Failed to list agents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list agents: {str(e)}")


@router.get("/agents/{agent_id}")
async def get_agent(
    agent_id: str = Path(..., description="Agent ID")
):
    """
    获取Agent详情

    返回完整的Agent信息，包括runtime_stats和agentcore_config

    Requirements: 4.2
    """
    try:
        agent = agent_service.get_agent(agent_id)

        return {
            "success": True,
            "data": agent,
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get agent {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get agent: {str(e)}")


@router.put("/agents/{agent_id}")
async def update_agent(
    agent_id: str = Path(..., description="Agent ID"),
    description: Optional[str] = Body(None, description="Agent描述"),
    category: Optional[str] = Body(None, description="Agent类别"),
    version: Optional[str] = Body(None, description="Agent版本"),
    capabilities: Optional[List[str]] = Body(None, description="Agent能力列表")
):
    """
    更新Agent配置

    允许更新Agent的描述、类别、版本和能力等配置信息

    Requirements: 4.4
    """
    try:
        # 获取当前agent
        agent = agent_service.get_agent(agent_id)
        current_status = AgentStatus(agent.get("status", "offline"))

        # 构建更新字段
        update_fields = {}
        if description is not None:
            update_fields["description"] = description
        if category is not None:
            update_fields["category"] = category
        if version is not None:
            update_fields["version"] = version
        if capabilities is not None:
            update_fields["capabilities"] = capabilities

        # 使用update_agent_status传递额外字段
        agent_service.update_agent_status(agent_id, current_status, **update_fields)

        # 返回更新后的agent
        updated_agent = agent_service.get_agent(agent_id)

        return {
            "success": True,
            "data": updated_agent,
            "message": f"Agent {agent_id} updated successfully",
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update agent {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update agent: {str(e)}")


@router.put("/agents/{agent_id}/status")
async def update_agent_status(
    agent_id: str = Path(..., description="Agent ID"),
    status: AgentStatus = Body(..., description="新状态"),
    error_message: Optional[str] = Body(None, description="错误信息（如果状态为offline）")
):
    """
    更新Agent状态

    允许更新Agent的运行状态（running, building, offline）

    Requirements: 4.4
    """
    try:
        # 构建额外字段
        extra_fields = {}
        if error_message:
            extra_fields["error_message"] = error_message

        agent_service.update_agent_status(agent_id, status, **extra_fields)

        # 返回更新后的agent
        updated_agent = agent_service.get_agent(agent_id)

        return {
            "success": True,
            "data": updated_agent,
            "message": f"Agent {agent_id} status updated to {status.value}",
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update agent status {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update agent status: {str(e)}")


@router.delete("/agents/{agent_id}")
async def delete_agent(
    agent_id: str = Path(..., description="Agent ID")
):
    """
    删除Agent

    级联删除Agent及其所有关联数据：
    - Agent记录
    - 所有invocations
    - 所有sessions和messages

    Requirements: 4.5, 10.3
    """
    try:
        agent_service.delete_agent(agent_id)

        return {
            "success": True,
            "message": f"Agent {agent_id} deleted successfully",
            "data": {
                "agent_id": agent_id,
                "deleted_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            },
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete agent {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete agent: {str(e)}")
