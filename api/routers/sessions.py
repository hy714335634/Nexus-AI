"""
Sessions API endpoints

提供通用会话管理的RESTful API
注意：Agent Dialog 相关的会话端点已迁移到 agent_dialog.py

保留的端点：
- GET /sessions/{session_id} - 获取会话详情
- DELETE /sessions/{session_id} - 删除会话

已迁移到 agent_dialog.py 的端点：
- GET /agents/{agent_id}/sessions - 获取会话列表
- POST /agents/{agent_id}/sessions - 创建会话
- GET /agents/{agent_id}/sessions/{session_id}/messages - 获取消息
- POST /agents/{agent_id}/sessions/{session_id}/stream - 流式对话
"""
from fastapi import APIRouter, HTTPException, Path
from typing import Dict, Any
import logging
from datetime import datetime, timezone

from api.core.exceptions import ResourceNotFoundError
from api.services import session_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str = Path(..., description="会话ID")
):
    """
    获取会话详情

    返回指定会话的详细信息
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


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str = Path(..., description="会话ID")
):
    """
    删除会话

    删除会话及其所有关联消息
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
