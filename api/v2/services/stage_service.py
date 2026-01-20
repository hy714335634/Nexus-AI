"""
Stage Service v2 - 统一的阶段状态管理服务

职责:
- 更新阶段状态（running/completed/failed）
- 计算项目进度
- 提供给 worker 和 agent_build_workflow 使用

设计原则:
- 单一数据源：所有阶段状态都写入 nexus_stages 表
- 统一接口：旧的 stage_tracker 和新的 worker 都使用此服务
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from enum import Enum

from api.v2.database import db_client
from api.v2.models.schemas import (
    ProjectStatus,
    StageStatus,
    BuildStage,
)

logger = logging.getLogger(__name__)


# 阶段名称映射：支持多种命名方式
STAGE_NAME_MAPPING = {
    # 工作流中使用的名称 -> BuildStage 枚举
    "orchestrator": BuildStage.ORCHESTRATOR,
    "requirements_analyzer": BuildStage.REQUIREMENTS_ANALYSIS,
    "requirements_analysis": BuildStage.REQUIREMENTS_ANALYSIS,
    "system_architect": BuildStage.SYSTEM_ARCHITECTURE,
    "system_architecture": BuildStage.SYSTEM_ARCHITECTURE,
    "agent_designer": BuildStage.AGENT_DESIGN,
    "agent_design": BuildStage.AGENT_DESIGN,
    "prompt_engineer": BuildStage.PROMPT_ENGINEER,
    "tools_developer": BuildStage.TOOLS_DEVELOPER,
    "tool_developer": BuildStage.TOOLS_DEVELOPER,
    "agent_code_developer": BuildStage.AGENT_CODE_DEVELOPER,
    "agent_developer_manager": BuildStage.AGENT_DEVELOPER_MANAGER,
    "agent_deployer": BuildStage.AGENT_DEPLOYER,
}


class StageServiceV2:
    """阶段管理服务 v2"""
    
    def __init__(self):
        self.db = db_client
    
    def _normalize_stage_name(self, stage_name: str) -> Optional[str]:
        """
        将各种阶段名称标准化为 BuildStage 枚举值
        
        Args:
            stage_name: 阶段名称（可以是工作流名称或枚举值）
        
        Returns:
            标准化的阶段名称（BuildStage.value）或 None
        """
        # 先尝试直接匹配
        stage = STAGE_NAME_MAPPING.get(stage_name.lower())
        if stage:
            return stage.value
        
        # 尝试作为 BuildStage 枚举值
        try:
            return BuildStage(stage_name).value
        except ValueError:
            pass
        
        return None
    
    def _now(self) -> str:
        """获取当前 UTC 时间的 ISO 格式字符串"""
        return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    def mark_stage_running(self, project_id: str, stage_name: str) -> bool:
        """
        标记阶段为运行中
        
        Args:
            project_id: 项目ID
            stage_name: 阶段名称
        
        Returns:
            是否成功
        """
        normalized_name = self._normalize_stage_name(stage_name)
        if not normalized_name:
            logger.warning(f"Unknown stage name: {stage_name}")
            return False
        
        try:
            now = self._now()
            
            # 更新阶段状态
            self.db.update_stage(project_id, normalized_name, {
                'status': StageStatus.RUNNING.value,
                'started_at': now
            })
            
            # 更新项目当前阶段和状态
            self.db.update_project(project_id, {
                'current_stage': normalized_name,
                'status': ProjectStatus.BUILDING.value
            })
            
            logger.info(f"Stage {normalized_name} marked as running for project {project_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to mark stage {stage_name} as running: {e}")
            return False
    
    def mark_stage_completed(
        self,
        project_id: str,
        stage_name: str,
        output_data: Optional[Dict[str, Any]] = None,
        doc_path: Optional[str] = None
    ) -> bool:
        """
        标记阶段为完成
        
        Args:
            project_id: 项目ID
            stage_name: 阶段名称
            output_data: 阶段输出数据
            doc_path: 阶段文档路径
        
        Returns:
            是否成功
        """
        normalized_name = self._normalize_stage_name(stage_name)
        if not normalized_name:
            logger.warning(f"Unknown stage name: {stage_name}")
            return False
        
        try:
            now = self._now()
            
            # 获取阶段记录计算耗时
            stage_record = self.db.get_stage(project_id, normalized_name)
            duration_seconds = None
            if stage_record and stage_record.get('started_at'):
                try:
                    start = datetime.fromisoformat(
                        stage_record['started_at'].replace('Z', '+00:00')
                    )
                    end = datetime.fromisoformat(now.replace('Z', '+00:00'))
                    duration_seconds = (end - start).total_seconds()
                except Exception:
                    pass
            
            # 构建更新数据
            updates = {
                'status': StageStatus.COMPLETED.value,
                'completed_at': now
            }
            if duration_seconds is not None:
                updates['duration_seconds'] = duration_seconds
            if output_data:
                updates['output_data'] = output_data
            if doc_path:
                updates['doc_path'] = doc_path
            
            # 更新阶段
            self.db.update_stage(project_id, normalized_name, updates)
            
            # 更新项目进度
            self._update_project_progress(project_id)
            
            logger.info(f"Stage {normalized_name} marked as completed for project {project_id}, doc_path={doc_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to mark stage {stage_name} as completed: {e}")
            return False
    
    def mark_stage_failed(
        self,
        project_id: str,
        stage_name: str,
        error_message: str
    ) -> bool:
        """
        标记阶段为失败
        
        Args:
            project_id: 项目ID
            stage_name: 阶段名称
            error_message: 错误信息
        
        Returns:
            是否成功
        """
        normalized_name = self._normalize_stage_name(stage_name)
        if not normalized_name:
            logger.warning(f"Unknown stage name: {stage_name}")
            return False
        
        try:
            now = self._now()
            
            # 更新阶段状态
            self.db.update_stage(project_id, normalized_name, {
                'status': StageStatus.FAILED.value,
                'completed_at': now,
                'error_message': error_message
            })
            
            logger.info(f"Stage {normalized_name} marked as failed for project {project_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to mark stage {stage_name} as failed: {e}")
            return False
    
    def _update_project_progress(self, project_id: str):
        """更新项目进度百分比"""
        try:
            stages = self.db.list_stages(project_id)
            total = len(stages)
            if total == 0:
                return
            
            completed = sum(
                1 for s in stages 
                if s.get('status') == StageStatus.COMPLETED.value
            )
            progress = (completed / total) * 100
            
            self.db.update_project(project_id, {'progress': progress})
        except Exception as e:
            logger.error(f"Failed to update project progress: {e}")
    
    def get_stage(self, project_id: str, stage_name: str) -> Optional[Dict[str, Any]]:
        """获取阶段详情"""
        normalized_name = self._normalize_stage_name(stage_name)
        if not normalized_name:
            return None
        return self.db.get_stage(project_id, normalized_name)
    
    def list_stages(self, project_id: str) -> List[Dict[str, Any]]:
        """列出项目所有阶段"""
        return self.db.list_stages(project_id)
    
    def calculate_progress(self, project_id: str) -> float:
        """计算项目进度"""
        stages = self.db.list_stages(project_id)
        total = len(stages)
        if total == 0:
            return 0.0
        
        completed = sum(
            1 for s in stages 
            if s.get('status') == StageStatus.COMPLETED.value
        )
        return (completed / total) * 100


# 全局单例
stage_service_v2 = StageServiceV2()


# ============== 兼容旧 stage_tracker 的函数接口 ==============
# 这些函数可以直接被 agent_build_workflow 导入使用

def mark_stage_running(project_id: str, stage_name: str) -> None:
    """标记阶段为运行中（兼容旧接口）"""
    stage_service_v2.mark_stage_running(project_id, stage_name)


def mark_stage_completed(
    project_id: str,
    stage_name: str,
    output_data: Optional[Dict[str, Any]] = None,
    doc_path: Optional[str] = None
) -> None:
    """标记阶段为完成（兼容旧接口）"""
    stage_service_v2.mark_stage_completed(project_id, stage_name, output_data, doc_path=doc_path)


def mark_stage_failed(project_id: str, stage_name: str, error_message: str) -> None:
    """标记阶段为失败（兼容旧接口）"""
    stage_service_v2.mark_stage_failed(project_id, stage_name, error_message)
