"""
Stage Tracker - 构建阶段状态跟踪

此模块已重构为使用 API v2 的 stage_service。
所有阶段状态更新都写入 nexus_stages 表。

兼容性说明:
- 保持原有函数签名不变
- 内部实现改为调用 api.v2.services.stage_service
"""
from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# 阶段序列（保留用于兼容性）
STAGE_SEQUENCE: List[Tuple[str, str]] = [
    ("orchestrator", "工作流编排"),
    ("requirements_analyzer", "需求分析"),
    ("system_architect", "系统架构设计"),
    ("agent_designer", "Agent设计"),
    ("tools_developer", "工具开发"),
    ("prompt_engineer", "提示词工程"),
    ("agent_code_developer", "代码开发"),
    ("agent_developer_manager", "开发管理"),
    ("agent_deployer", "Agent部署"),
]


class WorkflowPausedError(Exception):
    """工作流已暂停异常"""
    pass


class WorkflowStoppedError(Exception):
    """工作流已停止异常"""
    pass


def _get_stage_service():
    """延迟导入 v2 stage service，避免循环依赖"""
    from api.v2.services.stage_service import stage_service_v2
    return stage_service_v2


def _get_db_client():
    """延迟导入数据库客户端"""
    from api.v2.database import db_client
    return db_client


def check_control_status(project_id: str) -> str:
    """
    检查项目控制状态
    
    Args:
        project_id: 项目ID
        
    Returns:
        控制状态字符串: 'running', 'paused', 'stopped'
        
    Raises:
        WorkflowPausedError: 如果项目已暂停
        WorkflowStoppedError: 如果项目已停止
    """
    try:
        db = _get_db_client()
        project = db.get_project(project_id)
        if not project:
            return 'running'
        
        control_status = project.get('control_status', 'running')
        
        if control_status == 'paused':
            logger.info(f"Project {project_id} is paused")
            raise WorkflowPausedError(f"Project {project_id} is paused")
        elif control_status == 'stopped':
            logger.info(f"Project {project_id} is stopped")
            raise WorkflowStoppedError(f"Project {project_id} is stopped")
        
        return control_status
    except (WorkflowPausedError, WorkflowStoppedError):
        raise
    except Exception as e:
        logger.warning(f"Failed to check control status: {e}")
        return 'running'


def initialize_project_record(
    project_id: str,
    *,
    requirement: str = "",
    user_id: Optional[str] = None,
    user_name: Optional[str] = None,
    project_name: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> None:
    """
    初始化项目记录
    
    注意：在 v2 架构中，项目和阶段的初始化由 project_service 完成。
    此函数保留用于兼容性，但实际上不再需要调用。
    """
    logger.info(f"initialize_project_record: {project_id} (v2 handled by project_service)")


def mark_stage_running(project_id: str, stage_name: str) -> None:
    """
    标记阶段为运行中
    
    Args:
        project_id: 项目ID
        stage_name: 阶段名称（支持工作流名称和枚举值）
    """
    try:
        service = _get_stage_service()
        service.mark_stage_running(project_id, stage_name)
    except Exception as e:
        logger.error(f"Failed to mark stage running: {e}")
        raise


def mark_stage_completed(
    project_id: str,
    stage_name: str,
    output_data: Optional[Dict] = None,
    doc_path: Optional[str] = None
) -> None:
    """
    标记阶段为完成
    
    Args:
        project_id: 项目ID
        stage_name: 阶段名称
        output_data: 阶段输出数据（可选）
        doc_path: 阶段文档路径（可选）
    """
    try:
        service = _get_stage_service()
        service.mark_stage_completed(project_id, stage_name, output_data, doc_path=doc_path)
    except Exception as e:
        logger.error(f"Failed to mark stage completed: {e}")
        raise


def mark_stage_failed(project_id: str, stage_name: str, error_message: str) -> None:
    """
    标记阶段为失败
    
    Args:
        project_id: 项目ID
        stage_name: 阶段名称
        error_message: 错误信息
    """
    try:
        service = _get_stage_service()
        service.mark_stage_failed(project_id, stage_name, error_message)
    except Exception as e:
        logger.error(f"Failed to mark stage failed: {e}")
        raise


def mark_project_completed(project_id: str) -> None:
    """标记项目为完成"""
    try:
        service = _get_stage_service()
        stages = service.list_stages(project_id)
        
        for stage in stages:
            if stage.get('status') != 'completed':
                service.mark_stage_completed(project_id, stage.get('stage_name'))
        
        from api.v2.database import db_client
        from api.v2.models.schemas import ProjectStatus
        from datetime import datetime, timezone
        
        now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        db_client.update_project(project_id, {
            'status': ProjectStatus.COMPLETED.value,
            'progress': 100.0,
            'completed_at': now
        })
        
        logger.info(f"Project {project_id} marked as completed")
    except Exception as e:
        logger.error(f"Failed to mark project completed: {e}")
        raise


def mark_sub_stage_running(project_id: str, sub_stage_name: str) -> None:
    """标记子阶段为运行中"""
    logger.info(f"Sub-stage {sub_stage_name} running for project {project_id}")


def mark_sub_stage_completed(
    project_id: str,
    sub_stage_name: str,
    artifacts: Optional[List[str]] = None
) -> None:
    """标记子阶段为完成"""
    logger.info(f"Sub-stage {sub_stage_name} completed for project {project_id}")


def mark_sub_stage_failed(
    project_id: str,
    sub_stage_name: str,
    error_message: str
) -> None:
    """标记子阶段为失败"""
    logger.error(f"Sub-stage {sub_stage_name} failed: {error_message}")


__all__ = [
    "STAGE_SEQUENCE",
    "initialize_project_record",
    "mark_stage_running",
    "mark_stage_completed",
    "mark_stage_failed",
    "mark_project_completed",
    "mark_sub_stage_running",
    "mark_sub_stage_completed",
    "mark_sub_stage_failed",
]
