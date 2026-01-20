"""
Statistics API Router

统计数据相关的 API 端点
"""
from fastapi import APIRouter, HTTPException, Query
import logging
from datetime import datetime, timezone
import uuid

from api.v2.models.schemas import (
    StatisticsOverviewResponse,
    BuildStatisticsResponse,
    InvocationStatisticsResponse,
)
from api.v2.services import statistics_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/statistics", tags=["Statistics"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _request_id() -> str:
    return str(uuid.uuid4())


@router.get("/overview", response_model=StatisticsOverviewResponse)
async def get_overview():
    """
    获取统计概览
    
    返回项目、Agent、调用等的汇总统计数据
    """
    try:
        overview = statistics_service.get_overview()
        
        return StatisticsOverviewResponse(
            success=True,
            data=overview,
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except Exception as e:
        logger.error(f"Failed to get statistics overview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取统计概览失败: {str(e)}")


@router.get("/builds", response_model=BuildStatisticsResponse)
async def get_build_statistics(
    days: int = Query(7, ge=1, le=30, description="统计天数")
):
    """
    获取构建统计
    
    返回按天统计的构建数据
    """
    try:
        stats = statistics_service.get_build_statistics(days=days)
        
        return BuildStatisticsResponse(
            success=True,
            data=stats,
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except Exception as e:
        logger.error(f"Failed to get build statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取构建统计失败: {str(e)}")


@router.get("/invocations", response_model=InvocationStatisticsResponse)
async def get_invocation_statistics(
    days: int = Query(7, ge=1, le=30, description="统计天数")
):
    """
    获取调用统计
    
    返回按天统计的 Agent 调用数据
    """
    try:
        stats = statistics_service.get_invocation_statistics(days=days)
        
        return InvocationStatisticsResponse(
            success=True,
            data=stats,
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except Exception as e:
        logger.error(f"Failed to get invocation statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取调用统计失败: {str(e)}")
