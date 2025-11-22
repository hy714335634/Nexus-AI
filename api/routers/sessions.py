"""
Sessions API endpoints

提供Agent会话管理的RESTful API，包括创建、查询、消息管理和删除
"""
from fastapi import APIRouter, HTTPException, Query, Path, Body
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime, timezone

from api.models.schemas import APIResponse
from api.core.exceptions import APIException, ResourceNotFoundError
from api.services import SessionService, session_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/agents/{agent_id}/sessions")
async def create_session(
    agent_id: str = Path(..., description="Agent ID"),
    display_name: Optional[str] = Body(None, description="会话显示名称"),
    conversation_mode: str = Body("normal", description="会话模式（normal/debug/eval）"),
    metadata: Optional[Dict[str, Any]] = Body(None, description="会话元数据")
):
    """
    创建新会话

    为指定的Agent创建一个新的对话会话

    Requirements: 6.1
    """
    try:
        session = session_service.create_session(
            agent_id=agent_id,
            display_name=display_name,
            conversation_mode=conversation_mode,
            metadata=metadata
        )

        return {
            "success": True,
            "data": session,
            "message": f"Session created successfully",
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create session for agent {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@router.get("/agents/{agent_id}/sessions")
async def list_agent_sessions(
    agent_id: str = Path(..., description="Agent ID"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    last_key: Optional[str] = Query(None, description="分页游标")
):
    """
    获取Agent的会话列表

    按最后活跃时间降序返回会话列表

    Requirements: 6.3
    """
    try:
        # 处理last_key（简化处理）
        last_evaluated_key = None
        if last_key:
            # 实际应该解析JSON格式的last_key
            # 这里简化处理
            pass

        result = session_service.list_sessions(
            agent_id=agent_id,
            limit=limit,
            last_key=last_evaluated_key
        )

        return {
            "success": True,
            "data": {
                "items": result["items"],
                "last_evaluated_key": result.get("last_evaluated_key"),
                "count": len(result["items"])
            },
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }

    except Exception as e:
        logger.error(f"Failed to list sessions for agent {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str = Path(..., description="会话ID")
):
    """
    获取会话详情

    返回指定会话的详细信息

    Requirements: 6.1
    """
    try:
        session = session_service.get_session(session_id)

        return {
            "success": True,
            "data": session,
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: str = Path(..., description="会话ID"),
    content: str = Body(..., description="消息内容"),
    role: str = Body("user", description="消息角色（user/system）"),
    metadata: Optional[Dict[str, Any]] = Body(None, description="消息元数据")
):
    """
    发送消息

    向会话发送消息并获取Agent的响应

    Requirements: 6.2
    """
    try:
        result = session_service.send_message(
            session_id=session_id,
            content=content,
            role=role,
            metadata=metadata
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
        logger.error(f"Failed to send message to session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")


@router.get("/sessions/{session_id}/messages")
async def list_session_messages(
    session_id: str = Path(..., description="会话ID"),
    limit: int = Query(100, ge=1, le=200, description="每页数量"),
    last_key: Optional[str] = Query(None, description="分页游标")
):
    """
    获取会话消息列表

    按创建时间升序返回会话中的所有消息

    Requirements: 6.4
    """
    try:
        # 处理last_key（简化处理）
        last_evaluated_key = None
        if last_key:
            # 实际应该解析JSON格式的last_key
            pass

        result = session_service.list_messages(
            session_id=session_id,
            limit=limit,
            last_key=last_evaluated_key
        )

        return {
            "success": True,
            "data": {
                "items": result["items"],
                "last_evaluated_key": result.get("last_evaluated_key"),
                "count": len(result["items"])
            },
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }

    except Exception as e:
        logger.error(f"Failed to list messages for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list messages: {str(e)}")


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str = Path(..., description="会话ID")
):
    """
    删除会话

    删除会话及其所有关联消息

    Requirements: 6.5, 10.3
    """
    try:
        session_service.delete_session(session_id)

        return {
            "success": True,
            "message": f"Session {session_id} deleted successfully",
            "data": {
                "session_id": session_id,
                "deleted_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            },
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")
