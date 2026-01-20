"""
Statistics Service - 统计服务

职责:
- 聚合统计数据
- 提供概览和趋势数据
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta

from api.v2.database import db_client
from api.v2.models.schemas import ProjectStatus, AgentStatus

logger = logging.getLogger(__name__)


class StatisticsService:
    """统计服务"""
    
    def __init__(self):
        self.db = db_client
    
    def get_overview(self) -> Dict[str, Any]:
        """
        获取统计概览
        
        实时聚合计算，适合小规模数据
        大规模数据应考虑预计算或缓存
        """
        # 获取项目统计
        projects_result = self.db.list_projects(limit=1000)
        projects = projects_result.get('items', [])
        
        total_projects = len(projects)
        building_projects = sum(1 for p in projects if p.get('status') == ProjectStatus.BUILDING.value)
        completed_projects = sum(1 for p in projects if p.get('status') == ProjectStatus.COMPLETED.value)
        failed_projects = sum(1 for p in projects if p.get('status') == ProjectStatus.FAILED.value)
        
        # 计算成功率
        finished_projects = completed_projects + failed_projects
        success_rate = (completed_projects / finished_projects * 100) if finished_projects > 0 else 0.0
        
        # 计算平均构建时间
        build_times = []
        for p in projects:
            if p.get('status') == ProjectStatus.COMPLETED.value:
                metrics = p.get('metrics', {})
                if metrics and 'total_duration_seconds' in metrics:
                    build_times.append(metrics['total_duration_seconds'] / 60)  # 转换为分钟
        
        avg_build_time = sum(build_times) / len(build_times) if build_times else 0.0
        
        # 获取 Agent 统计
        agents_result = self.db.list_agents(limit=1000)
        agents = agents_result.get('items', [])
        
        total_agents = len(agents)
        running_agents = sum(1 for a in agents if a.get('status') == AgentStatus.RUNNING.value)
        
        # 计算总调用次数
        total_invocations = sum(a.get('total_invocations', 0) for a in agents)
        
        # 今日调用（简化实现，实际应该查询 invocations 表）
        today_invocations = 0  # TODO: 实现今日调用统计
        
        return {
            'total_projects': total_projects,
            'building_projects': building_projects,
            'completed_projects': completed_projects,
            'failed_projects': failed_projects,
            'total_agents': total_agents,
            'running_agents': running_agents,
            'total_invocations': total_invocations,
            'today_invocations': today_invocations,
            'success_rate': round(success_rate, 2),
            'avg_build_time_minutes': round(avg_build_time, 2)
        }
    
    def get_build_statistics(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        获取构建统计（按天）
        
        简化实现，实际应该使用时间范围查询
        """
        # TODO: 实现按天统计
        return []
    
    def get_invocation_statistics(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        获取调用统计（按天）
        
        简化实现，实际应该使用时间范围查询
        """
        # TODO: 实现按天统计
        return []


# 全局单例
statistics_service = StatisticsService()
