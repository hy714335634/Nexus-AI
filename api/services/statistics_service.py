"""
Statistics Service - 统计数据实时聚合

职责:
- 提供系统总览统计（agent数量、构建统计、调用统计）
- 按日期范围聚合构建统计
- 按日期范围聚合调用统计
- 提供趋势数据

注意: 所有数据通过实时聚合查询获取，不依赖预计算的统计表
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from collections import defaultdict

from api.database.dynamodb_client import db_client
from api.models.schemas import (
    StatisticsOverview,
    BuildStatistics,
    InvocationStatistics,
    TrendData,
    TrendDataPoint,
    AgentStatus,
    ProjectStatus,
)
from api.core.exceptions import APIException

logger = logging.getLogger(__name__)


class StatisticsService:
    """统计服务 - 实时聚合查询"""

    def __init__(self):
        self.db_client = db_client

    def get_overview(self) -> StatisticsOverview:
        """
        获取系统总览统计

        实时聚合:
        - 扫描 AgentInstances 按状态计数
        - 扫描 AgentProjects 计算构建成功率和平均构建时长
        - 查询今日 AgentInvocations 计数

        Returns:
            StatisticsOverview: 总览统计数据

        Requirements: 9.1, 9.2, 9.3
        """
        try:
            # 1. 统计 Agents 按状态分组
            agents_result = self.db_client.list_agents(limit=1000)
            agents = agents_result.get('items', [])

            total_agents = len(agents)
            running_agents = sum(1 for a in agents if a.get('status') == AgentStatus.RUNNING.value)
            building_agents = sum(1 for a in agents if a.get('status') == AgentStatus.BUILDING.value)
            offline_agents = sum(1 for a in agents if a.get('status') == AgentStatus.OFFLINE.value)

            # 2. 统计 Projects 构建成功率和平均构建时长
            projects_result = self.db_client.list_projects(limit=1000)
            projects = projects_result.get('items', [])

            total_builds = len(projects)
            completed_builds = [p for p in projects if p.get('status') == ProjectStatus.COMPLETED.value]
            successful_builds = len(completed_builds)

            success_rate = (successful_builds / total_builds * 100) if total_builds > 0 else 0.0

            # 计算平均构建时长（分钟）
            total_duration_minutes = 0.0
            builds_with_duration = 0

            for project in completed_builds:
                created_at = project.get('created_at')
                completed_at = project.get('completed_at')

                if created_at and completed_at:
                    try:
                        start = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        end = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
                        duration_minutes = (end - start).total_seconds() / 60
                        total_duration_minutes += duration_minutes
                        builds_with_duration += 1
                    except (ValueError, AttributeError):
                        pass

            avg_build_time_minutes = (total_duration_minutes / builds_with_duration) if builds_with_duration > 0 else 0.0

            # 3. 统计今日调用次数
            # 由于没有按日期索引，我们需要扫描 invocations 表（这里简化为返回 0，实际应该添加日期索引）
            today_calls = self._count_today_invocations()

            return StatisticsOverview(
                total_agents=total_agents,
                running_agents=running_agents,
                building_agents=building_agents,
                offline_agents=offline_agents,
                total_builds=total_builds,
                success_rate=round(success_rate, 2),
                avg_build_time_minutes=round(avg_build_time_minutes, 2),
                today_calls=today_calls
            )

        except Exception as e:
            logger.error(f"Failed to get statistics overview: {str(e)}")
            raise APIException(f"Failed to get statistics overview: {str(e)}")

    def get_build_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[BuildStatistics]:
        """
        获取构建统计（按日期范围）

        实时聚合 AgentProjects 表，按日期分组统计

        Args:
            start_date: 开始日期（ISO格式，如 "2024-01-01"）
            end_date: 结束日期（ISO格式）

        Returns:
            List[BuildStatistics]: 按日期分组的构建统计列表

        Requirements: 9.2
        """
        try:
            # 查询所有项目
            projects_result = self.db_client.list_projects(limit=1000)
            projects = projects_result.get('items', [])

            # 按日期过滤
            if start_date or end_date:
                projects = self._filter_by_date_range(projects, start_date, end_date, 'created_at')

            # 按日期分组统计
            stats_by_date = defaultdict(lambda: {
                'total_builds': 0,
                'successful_builds': 0,
                'failed_builds': 0,
                'total_duration_minutes': 0.0,
                'builds_with_duration': 0,
                'builds_by_stage': defaultdict(int)
            })

            for project in projects:
                created_at = project.get('created_at', '')
                date = created_at.split('T')[0] if created_at else 'unknown'

                stats = stats_by_date[date]
                stats['total_builds'] += 1

                status = project.get('status')
                if status == ProjectStatus.COMPLETED.value:
                    stats['successful_builds'] += 1
                elif status == ProjectStatus.FAILED.value:
                    stats['failed_builds'] += 1

                # 计算构建时长
                created_at_full = project.get('created_at')
                completed_at = project.get('completed_at')
                if created_at_full and completed_at:
                    try:
                        start = datetime.fromisoformat(created_at_full.replace('Z', '+00:00'))
                        end = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
                        duration_minutes = (end - start).total_seconds() / 60
                        stats['total_duration_minutes'] += duration_minutes
                        stats['builds_with_duration'] += 1
                    except (ValueError, AttributeError):
                        pass

                # 统计当前阶段
                current_stage = project.get('current_stage')
                if current_stage:
                    stats['builds_by_stage'][current_stage] += 1

            # 转换为 BuildStatistics 列表
            result = []
            for date in sorted(stats_by_date.keys()):
                stats = stats_by_date[date]
                avg_duration = (
                    stats['total_duration_minutes'] / stats['builds_with_duration']
                    if stats['builds_with_duration'] > 0 else 0.0
                )

                result.append(BuildStatistics(
                    date=date,
                    total_builds=stats['total_builds'],
                    successful_builds=stats['successful_builds'],
                    failed_builds=stats['failed_builds'],
                    avg_duration_minutes=round(avg_duration, 2),
                    builds_by_stage=dict(stats['builds_by_stage'])
                ))

            return result

        except Exception as e:
            logger.error(f"Failed to get build statistics: {str(e)}")
            raise APIException(f"Failed to get build statistics: {str(e)}")

    def get_invocation_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[InvocationStatistics]:
        """
        获取调用统计（按日期范围）

        实时聚合 AgentInvocations 表，按日期分组统计

        Args:
            start_date: 开始日期（ISO格式）
            end_date: 结束日期（ISO格式）

        Returns:
            List[InvocationStatistics]: 按日期分组的调用统计列表

        Requirements: 9.3
        """
        try:
            # 由于 DynamoDB 没有直接的扫描全表方法，我们需要通过 agents 来获取所有 invocations
            # 这是一个简化实现，实际生产环境应该使用 GSI 或其他优化方法
            invocations = self._get_all_invocations()

            # 按日期过滤
            if start_date or end_date:
                invocations = self._filter_by_date_range(invocations, start_date, end_date, 'timestamp')

            # 按日期分组统计
            stats_by_date = defaultdict(lambda: {
                'total_invocations': 0,
                'successful_invocations': 0,
                'failed_invocations': 0,
                'total_duration_ms': 0.0,
                'invocations_with_duration': 0
            })

            for invocation in invocations:
                timestamp = invocation.get('timestamp', '')
                date = timestamp.split('T')[0] if timestamp else 'unknown'

                stats = stats_by_date[date]
                stats['total_invocations'] += 1

                status = invocation.get('status')
                if status == 'success':
                    stats['successful_invocations'] += 1
                elif status == 'failed':
                    stats['failed_invocations'] += 1

                # 累计时长
                duration_ms = invocation.get('duration_ms')
                if duration_ms is not None:
                    if isinstance(duration_ms, Decimal):
                        duration_ms = float(duration_ms)
                    stats['total_duration_ms'] += duration_ms
                    stats['invocations_with_duration'] += 1

            # 转换为 InvocationStatistics 列表
            result = []
            for date in sorted(stats_by_date.keys()):
                stats = stats_by_date[date]
                success_rate = (
                    stats['successful_invocations'] / stats['total_invocations'] * 100
                    if stats['total_invocations'] > 0 else 0.0
                )
                avg_duration_ms = (
                    stats['total_duration_ms'] / stats['invocations_with_duration']
                    if stats['invocations_with_duration'] > 0 else 0.0
                )

                result.append(InvocationStatistics(
                    date=date,
                    total_invocations=stats['total_invocations'],
                    successful_invocations=stats['successful_invocations'],
                    failed_invocations=stats['failed_invocations'],
                    success_rate=round(success_rate, 2),
                    avg_duration_ms=round(avg_duration_ms, 2)
                ))

            return result

        except Exception as e:
            logger.error(f"Failed to get invocation statistics: {str(e)}")
            raise APIException(f"Failed to get invocation statistics: {str(e)}")

    def get_trends(
        self,
        metric: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> TrendData:
        """
        获取趋势数据

        支持的指标:
        - "builds": 每日构建数量
        - "invocations": 每日调用数量
        - "success_rate": 每日成功率

        Args:
            metric: 指标名称
            start_date: 开始日期（ISO格式）
            end_date: 结束日期（ISO格式）

        Returns:
            TrendData: 趋势数据

        Requirements: 9.4
        """
        try:
            if metric == "builds":
                build_stats = self.get_build_statistics(start_date, end_date)
                data_points = [
                    TrendDataPoint(date=stat.date, value=float(stat.total_builds))
                    for stat in build_stats
                ]
            elif metric == "invocations":
                invocation_stats = self.get_invocation_statistics(start_date, end_date)
                data_points = [
                    TrendDataPoint(date=stat.date, value=float(stat.total_invocations))
                    for stat in invocation_stats
                ]
            elif metric == "success_rate":
                build_stats = self.get_build_statistics(start_date, end_date)
                data_points = [
                    TrendDataPoint(
                        date=stat.date,
                        value=float(stat.successful_builds / stat.total_builds * 100)
                        if stat.total_builds > 0 else 0.0
                    )
                    for stat in build_stats
                ]
            else:
                raise ValueError(f"Unknown metric: {metric}")

            return TrendData(metric=metric, data_points=data_points)

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to get trends for metric {metric}: {str(e)}")
            raise APIException(f"Failed to get trends: {str(e)}")

    # Helper methods

    def _count_today_invocations(self) -> int:
        """统计今日调用次数"""
        try:
            # 获取所有调用
            invocations = self._get_all_invocations()

            # 获取今日日期
            today = datetime.now(timezone.utc).date()

            count = 0
            for invocation in invocations:
                timestamp = invocation.get('timestamp', '')
                if timestamp:
                    try:
                        inv_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).date()
                        if inv_date == today:
                            count += 1
                    except (ValueError, AttributeError):
                        pass

            return count

        except Exception as e:
            logger.warning(f"Failed to count today's invocations: {str(e)}")
            return 0

    def _get_all_invocations(self) -> List[Dict[str, Any]]:
        """获取所有调用记录（简化实现）"""
        try:
            # 获取所有 agents
            agents_result = self.db_client.list_agents(limit=1000)
            agents = agents_result.get('items', [])

            all_invocations = []
            for agent in agents:
                agent_id = agent.get('agent_id')
                if agent_id:
                    try:
                        invocations_result = self.db_client.list_agent_invocations(agent_id, limit=1000)
                        invocations = invocations_result.get('items', [])
                        all_invocations.extend(invocations)
                    except Exception as e:
                        logger.warning(f"Failed to get invocations for agent {agent_id}: {str(e)}")
                        continue

            return all_invocations

        except Exception as e:
            logger.warning(f"Failed to get all invocations: {str(e)}")
            return []

    def _filter_by_date_range(
        self,
        items: List[Dict[str, Any]],
        start_date: Optional[str],
        end_date: Optional[str],
        date_field: str
    ) -> List[Dict[str, Any]]:
        """按日期范围过滤项目"""
        if not start_date and not end_date:
            return items

        filtered = []
        for item in items:
            timestamp = item.get(date_field, '')
            if not timestamp:
                continue

            try:
                item_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).date()

                if start_date:
                    start = datetime.fromisoformat(start_date).date()
                    if item_date < start:
                        continue

                if end_date:
                    end = datetime.fromisoformat(end_date).date()
                    if item_date > end:
                        continue

                filtered.append(item)

            except (ValueError, AttributeError):
                continue

        return filtered


# Singleton instance
statistics_service = StatisticsService()
