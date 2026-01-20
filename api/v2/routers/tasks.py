"""
Tasks API Router

任务状态查询相关的 API 端点
"""
from fastapi import APIRouter, HTTPException, Path
import logging
from datetime import datetime, timezone
import uuid

from api.v2.models.schemas import TaskStatusResponse
from api.v2.services import task_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["Tasks"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _request_id() -> str:
    return str(uuid.uuid4())


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str = Path(..., description="任务ID")
):
    """
    获取任务状态
    
    用于查询构建任务、部署任务等的执行状态
    """
    try:
        task = task_service.get_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
        
        return TaskStatusResponse(
            success=True,
            data=task,
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取任务状态失败: {str(e)}")
