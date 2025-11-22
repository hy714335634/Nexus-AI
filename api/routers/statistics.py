"""
Statistics API endpoints

提供系统统计数据的RESTful API，包括总览、构建统计、调用统计和趋势数据
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging
import uuid
from datetime import datetime, timezone

from api.models.schemas import (
    StatisticsOverviewResponse,
    BuildStatisticsResponse,
    InvocationStatisticsResponse,
    TrendDataResponse,
)
from api.core.exceptions import APIException, ValidationError
from api.services import StatisticsService, statistics_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/statistics/overview", response_model=StatisticsOverviewResponse)
async def get_statistics_overview():
    """
    获取系统总览统计

    返回实时聚合的系统统计数据：
    - Agent数量（总数、运行中、构建中、离线）
    - 构建统计（总数、成功率、平均时长）
    - 今日调用次数

    Requirements: 9.1, 9.2, 9.3
    """
    try:
        overview = statistics_service.get_overview()

        return StatisticsOverviewResponse(
            success=True,
            data=overview,
            timestamp=datetime.now(timezone.utc),
            request_id=str(uuid.uuid4())
        )

    except Exception as e:
        logger.error(f"Failed to get statistics overview: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics overview: {str(e)}")


@router.get("/statistics/builds", response_model=BuildStatisticsResponse)
async def get_build_statistics(
    start_date: Optional[str] = Query(None, description="开始日期（ISO格式，如 2024-01-01）"),
    end_date: Optional[str] = Query(None, description="结束日期（ISO格式）")
):
    """
    获取构建统计数据

    按日期范围查询构建统计，包括：
    - 每日构建数量
    - 成功/失败构建数
    - 平均构建时长
    - 按阶段分组的构建数

    Requirements: 9.2
    """
    try:
        # 验证日期格式
        if start_date:
            try:
                datetime.fromisoformat(start_date)
            except ValueError:
                raise ValidationError(f"Invalid start_date format: {start_date}. Use ISO format (YYYY-MM-DD)")

        if end_date:
            try:
                datetime.fromisoformat(end_date)
            except ValueError:
                raise ValidationError(f"Invalid end_date format: {end_date}. Use ISO format (YYYY-MM-DD)")

        build_stats = statistics_service.get_build_statistics(
            start_date=start_date,
            end_date=end_date
        )

        return BuildStatisticsResponse(
            success=True,
            data=build_stats,
            timestamp=datetime.now(timezone.utc),
            request_id=str(uuid.uuid4())
        )

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get build statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get build statistics: {str(e)}")


@router.get("/statistics/invocations", response_model=InvocationStatisticsResponse)
async def get_invocation_statistics(
    start_date: Optional[str] = Query(None, description="开始日期（ISO格式）"),
    end_date: Optional[str] = Query(None, description="结束日期（ISO格式）")
):
    """
    获取调用统计数据

    按日期范围查询Agent调用统计，包括：
    - 每日调用数量
    - 成功/失败调用数
    - 成功率
    - 平均调用时长

    Requirements: 9.3
    """
    try:
        # 验证日期格式
        if start_date:
            try:
                datetime.fromisoformat(start_date)
            except ValueError:
                raise ValidationError(f"Invalid start_date format: {start_date}. Use ISO format (YYYY-MM-DD)")

        if end_date:
            try:
                datetime.fromisoformat(end_date)
            except ValueError:
                raise ValidationError(f"Invalid end_date format: {end_date}. Use ISO format (YYYY-MM-DD)")

        invocation_stats = statistics_service.get_invocation_statistics(
            start_date=start_date,
            end_date=end_date
        )

        return InvocationStatisticsResponse(
            success=True,
            data=invocation_stats,
            timestamp=datetime.now(timezone.utc),
            request_id=str(uuid.uuid4())
        )

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get invocation statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get invocation statistics: {str(e)}")


@router.get("/statistics/trends", response_model=TrendDataResponse)
async def get_trends(
    metric: str = Query(..., description="指标名称：builds, invocations, success_rate"),
    start_date: Optional[str] = Query(None, description="开始日期（ISO格式）"),
    end_date: Optional[str] = Query(None, description="结束日期（ISO格式）")
):
    """
    获取趋势数据

    按日期范围查询指定指标的趋势数据

    支持的指标:
    - builds: 每日构建数量
    - invocations: 每日调用数量
    - success_rate: 每日成功率

    Requirements: 9.4
    """
    try:
        # 验证metric
        valid_metrics = ["builds", "invocations", "success_rate"]
        if metric not in valid_metrics:
            raise ValidationError(f"Invalid metric: {metric}. Must be one of {valid_metrics}")

        # 验证日期格式
        if start_date:
            try:
                datetime.fromisoformat(start_date)
            except ValueError:
                raise ValidationError(f"Invalid start_date format: {start_date}. Use ISO format (YYYY-MM-DD)")

        if end_date:
            try:
                datetime.fromisoformat(end_date)
            except ValueError:
                raise ValidationError(f"Invalid end_date format: {end_date}. Use ISO format (YYYY-MM-DD)")

        trend_data = statistics_service.get_trends(
            metric=metric,
            start_date=start_date,
            end_date=end_date
        )

        return TrendDataResponse(
            success=True,
            data=trend_data,
            timestamp=datetime.now(timezone.utc),
            request_id=str(uuid.uuid4())
        )

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get trends: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get trends: {str(e)}")
