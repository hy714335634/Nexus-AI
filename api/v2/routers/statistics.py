"""
Statistics API Router

统计数据相关的 API 端点
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
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


# 额外的响应模型
class CategoryDistributionResponse(BaseModel):
    """Agent 分类分布响应"""
    success: bool
    data: List[Dict[str, Any]]
    timestamp: str
    request_id: str


class TopAgentsResponse(BaseModel):
    """热门 Agent 响应"""
    success: bool
    data: List[Dict[str, Any]]
    timestamp: str
    request_id: str


class RecentActivitiesResponse(BaseModel):
    """最近活动响应"""
    success: bool
    data: List[Dict[str, Any]]
    timestamp: str
    request_id: str


class SystemHealthResponse(BaseModel):
    """系统健康状态响应"""
    success: bool
    data: Dict[str, Any]
    timestamp: str
    request_id: str


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
    days: int = Query(7, ge=1, le=90, description="统计天数")
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
    days: int = Query(7, ge=1, le=90, description="统计天数")
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


@router.get("/agent-categories", response_model=CategoryDistributionResponse)
async def get_agent_category_distribution():
    """
    获取 Agent 分类分布
    
    返回各分类的 Agent 数量统计
    """
    try:
        distribution = statistics_service.get_agent_category_distribution()
        
        return CategoryDistributionResponse(
            success=True,
            data=distribution,
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except Exception as e:
        logger.error(f"Failed to get agent category distribution: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取分类分布失败: {str(e)}")


@router.get("/top-agents", response_model=TopAgentsResponse)
async def get_top_agents(
    limit: int = Query(10, ge=1, le=50, description="返回数量")
):
    """
    获取热门 Agent
    
    返回调用次数最多的 Agent 列表
    """
    try:
        top_agents = statistics_service.get_top_agents(limit=limit)
        
        return TopAgentsResponse(
            success=True,
            data=top_agents,
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except Exception as e:
        logger.error(f"Failed to get top agents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取热门 Agent 失败: {str(e)}")


@router.get("/recent-activities", response_model=RecentActivitiesResponse)
async def get_recent_activities(
    limit: int = Query(10, ge=1, le=50, description="返回数量")
):
    """
    获取最近活动
    
    返回最近的项目和 Agent 活动记录
    """
    try:
        activities = statistics_service.get_recent_activities(limit=limit)
        
        return RecentActivitiesResponse(
            success=True,
            data=activities,
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except Exception as e:
        logger.error(f"Failed to get recent activities: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取最近活动失败: {str(e)}")


@router.get("/system-health", response_model=SystemHealthResponse)
async def get_system_health():
    """
    获取系统健康状态
    
    返回系统各组件的健康状态
    """
    try:
        health = statistics_service.get_system_health()
        
        return SystemHealthResponse(
            success=True,
            data=health,
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except Exception as e:
        logger.error(f"Failed to get system health: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取系统健康状态失败: {str(e)}")
