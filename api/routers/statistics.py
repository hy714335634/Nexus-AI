"""
Statistics and monitoring API endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import uuid
import logging
from datetime import datetime, timedelta

from api.models.schemas import (
    StatisticsOverviewResponse, BuildStatisticsResponse, APIResponse
)
from api.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/statistics/overview", response_model=StatisticsOverviewResponse)
async def get_statistics_overview():
    """
    获取系统概览统计
    
    返回总代理数、运行状态、构建统计等关键指标
    """
    try:
        # TODO: Implement actual statistics retrieval logic
        # This will be implemented in task 6.1
        
        from api.models.schemas import StatisticsOverview
        
        # Mock data for now
        overview_data = StatisticsOverview(
            total_agents=0,
            running_agents=0,
            building_agents=0,
            offline_agents=0,
            total_builds=0,
            success_rate=0.0,
            avg_build_time_minutes=0.0,
            today_calls=0
        )
        
        return StatisticsOverviewResponse(
            success=True,
            data=overview_data,
            timestamp=datetime.utcnow(),
            request_id=str(uuid.uuid4())
        )
        
    except Exception as e:
        logger.error(f"Error getting statistics overview: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statistics/builds", response_model=BuildStatisticsResponse)
async def get_build_statistics(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    group_by: Optional[str] = Query("day", pattern="^(day|week|month)$", description="分组方式")
):
    """
    获取构建统计数据
    
    支持按时间范围和分组方式查询构建趋势
    """
    try:
        # TODO: Implement actual build statistics retrieval logic
        # This will be implemented in task 6.2
        
        from api.models.schemas import BuildStatistics
        
        # Validate date parameters
        if start_date:
            try:
                datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                raise ValidationError("Invalid start_date format. Use YYYY-MM-DD")
        
        if end_date:
            try:
                datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                raise ValidationError("Invalid end_date format. Use YYYY-MM-DD")
        
        # Mock data for now
        build_stats = []
        
        return BuildStatisticsResponse(
            success=True,
            data=build_stats,
            timestamp=datetime.utcnow(),
            request_id=str(uuid.uuid4())
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "VALIDATION_ERROR",
                "message": str(e),
                "details": "请检查输入参数格式",
                "suggestion": "确保日期格式为 YYYY-MM-DD"
            }
        )
    except Exception as e:
        logger.error(f"Error getting build statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))