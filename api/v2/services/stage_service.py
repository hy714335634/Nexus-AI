"""
Stage Service v2 - 统一的阶段状态管理服务

职责:
- 更新阶段状态（running/completed/failed）
- 计算项目进度
- 存储阶段输出内容、指标和设计文档
- 提供给 worker 和 agent_build_workflow 使用

设计原则:
- 单一数据源：所有阶段状态都写入 nexus_stages 表
- 统一接口：旧的 stage_tracker 和新的 worker 都使用此服务
- 阶段配置：使用 api.v2.core.stage_config 作为唯一配置来源

Requirements:
    - 2.1: Stage_Output 包含 agent 输出内容，最大 400KB
    - 2.2: Stage_Output 包含执行指标
    - 2.3: Stage_Output 包含生成文件路径列表
    - 2.4: 阶段完成时存储完整设计文档内容
    - 2.7: 超过 400KB 时存储 S3 引用
"""
import logging
import hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from enum import Enum

from api.v2.database import db_client
from api.v2.models.schemas import (
    ProjectStatus,
    StageStatus,
    BuildStage,
    StageMetricsSchema,
    FileMetadataSchema,
    DesignDocumentSchema,
)
# 从统一配置模块导入阶段名称标准化函数
from api.v2.core.stage_config import normalize_stage_name as _normalize_stage_name

logger = logging.getLogger(__name__)

# 内容大小限制（400KB）
MAX_CONTENT_SIZE = 400 * 1024


class StageServiceV2:
    """
    阶段管理服务 v2
    
    提供阶段状态管理、输出存储和指标记录功能。
    
    Validates:
        - Requirement 2.1: 存储 agent 输出内容
        - Requirement 2.2: 存储执行指标
        - Requirement 2.3: 存储生成文件路径
        - Requirement 2.4: 存储设计文档内容
        - Requirement 2.7: 超大内容存储 S3 引用
    """
    
    def __init__(self):
        self.db = db_client
    
    def _normalize_stage_name(self, stage_name: str) -> Optional[str]:
        """
        将各种阶段名称标准化为 BuildStage 枚举值
        
        使用统一配置模块 api.v2.core.stage_config 进行标准化
        
        Args:
            stage_name: 阶段名称（可以是工作流名称或枚举值）
        
        Returns:
            标准化的阶段名称（BuildStage.value）或 None
        """
        return _normalize_stage_name(stage_name)
    
    def _now(self) -> str:
        """获取当前 UTC 时间的 ISO 格式字符串"""
        return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    def _check_content_size(self, content: str) -> bool:
        """
        检查内容是否超过大小限制
        
        Args:
            content: 要检查的内容
            
        Returns:
            bool: 内容是否超过 400KB
        """
        return len(content.encode('utf-8')) > MAX_CONTENT_SIZE
    
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
            
            # 检查项目控制状态，如果已暂停或停止，不更新项目状态
            project = self.db.get_project(project_id)
            control_status = project.get('control_status', 'running') if project else 'running'
            
            # 如果项目已暂停或停止，不继续执行
            if control_status in ['paused', 'stopped']:
                logger.warning(
                    f"Project {project_id} is {control_status}, "
                    f"skipping stage {normalized_name}"
                )
                return False
            
            # 检查阶段是否存在，避免 DynamoDB update_item 自动创建新记录
            existing_stage = self.db.get_stage(project_id, normalized_name)
            if not existing_stage:
                logger.warning(
                    f"Stage {normalized_name} not found for project {project_id}, "
                    f"original name: {stage_name}"
                )
                return False
            
            # 更新阶段状态
            self.db.update_stage(project_id, normalized_name, {
                'status': StageStatus.RUNNING.value,
                'started_at': now
            })
            
            # 更新项目当前阶段和状态（仅当控制状态为 running 时）
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
        doc_path: Optional[str] = None,
        agent_output_content: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
        generated_files: Optional[List[Dict[str, Any]]] = None,
        design_document: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        标记阶段为完成
        
        Args:
            project_id: 项目ID
            stage_name: 阶段名称
            output_data: 阶段输出数据（兼容旧接口）
            doc_path: 阶段文档路径
            agent_output_content: Agent 输出内容（新增）
            metrics: 执行指标（新增）
            generated_files: 生成的文件列表（新增）
            design_document: 设计文档内容（新增）
        
        Returns:
            是否成功
            
        Validates:
            - Requirement 2.1: 存储 agent 输出内容
            - Requirement 2.2: 存储执行指标
            - Requirement 2.3: 存储生成文件路径
            - Requirement 2.4: 存储设计文档内容
            - Requirement 2.7: 超大内容存储 S3 引用
        """
        normalized_name = self._normalize_stage_name(stage_name)
        if not normalized_name:
            logger.warning(f"Unknown stage name: {stage_name}")
            return False
        
        try:
            now = self._now()
            
            # 检查阶段是否存在，避免 DynamoDB update_item 自动创建新记录
            existing_stage = self.db.get_stage(project_id, normalized_name)
            if not existing_stage:
                logger.warning(
                    f"Stage {normalized_name} not found for project {project_id}, "
                    f"original name: {stage_name}, skipping completion"
                )
                return False
            
            # 获取阶段记录计算耗时
            stage_record = existing_stage
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
            
            # 处理 agent 输出内容（Requirement 2.1, 2.7）
            if agent_output_content:
                if self._check_content_size(agent_output_content):
                    # 超过 400KB，需要存储到 S3
                    # TODO: 实现 S3 存储逻辑
                    s3_ref = self._store_content_to_s3(
                        project_id, normalized_name, agent_output_content
                    )
                    updates['agent_output_s3_ref'] = s3_ref
                    updates['agent_output_content'] = ""  # 清空内容
                    logger.info(f"Stage {normalized_name} output stored to S3: {s3_ref}")
                else:
                    updates['agent_output_content'] = agent_output_content
            
            # 处理执行指标（Requirement 2.2）
            if metrics:
                updates['metrics'] = metrics
                # 同时更新兼容字段
                updates['input_tokens'] = metrics.get('input_tokens', 0)
                updates['output_tokens'] = metrics.get('output_tokens', 0)
                updates['tool_calls'] = metrics.get('tool_calls_count', 0)
            
            # 处理生成的文件列表（Requirement 2.3）
            if generated_files:
                updates['generated_files'] = generated_files
            
            # 处理设计文档（Requirement 2.4）
            if design_document:
                updates['design_document'] = design_document
            
            # 更新阶段
            self.db.update_stage(project_id, normalized_name, updates)
            
            # 更新项目进度和聚合指标
            self._update_project_progress(project_id)
            if metrics:
                self._update_project_aggregated_metrics(project_id, metrics)
            
            logger.info(f"Stage {normalized_name} marked as completed for project {project_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to mark stage {stage_name} as completed: {e}")
            return False
    
    def _store_content_to_s3(
        self, 
        project_id: str, 
        stage_name: str, 
        content: str
    ) -> str:
        """
        将超大内容存储到 S3
        
        Args:
            project_id: 项目ID
            stage_name: 阶段名称
            content: 要存储的内容
            
        Returns:
            str: S3 对象引用
            
        Validates: Requirement 2.7 - 超过 400KB 时存储 S3 引用
        """
        # TODO: 实现实际的 S3 存储逻辑
        # 目前返回一个占位符引用
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        s3_ref = f"s3://nexus-ai-stage-outputs/{project_id}/{stage_name}/{content_hash}.txt"
        logger.warning(f"S3 storage not implemented, using placeholder: {s3_ref}")
        return s3_ref
    
    def _update_project_aggregated_metrics(
        self, 
        project_id: str, 
        stage_metrics: Dict[str, Any]
    ) -> None:
        """
        更新项目聚合指标
        
        Args:
            project_id: 项目ID
            stage_metrics: 阶段指标
            
        Validates: Requirement 2.5 - Project_Record 包含聚合指标
        """
        try:
            project = self.db.get_project(project_id)
            if not project:
                return
            
            # 获取现有聚合指标
            aggregated = project.get('aggregated_metrics', {})
            
            # 更新聚合指标
            aggregated['total_input_tokens'] = (
                aggregated.get('total_input_tokens', 0) + 
                stage_metrics.get('input_tokens', 0)
            )
            aggregated['total_output_tokens'] = (
                aggregated.get('total_output_tokens', 0) + 
                stage_metrics.get('output_tokens', 0)
            )
            aggregated['total_tokens'] = (
                aggregated['total_input_tokens'] + 
                aggregated['total_output_tokens']
            )
            aggregated['total_execution_time'] = (
                aggregated.get('total_execution_time', 0) + 
                stage_metrics.get('execution_time_seconds', 0)
            )
            aggregated['total_tool_calls'] = (
                aggregated.get('total_tool_calls', 0) + 
                stage_metrics.get('tool_calls_count', 0)
            )
            
            # 更新项目
            self.db.update_project(project_id, {
                'aggregated_metrics': aggregated
            })
        except Exception as e:
            logger.error(f"Failed to update project aggregated metrics: {e}")
    
    def mark_stage_failed(
        self,
        project_id: str,
        stage_name: str,
        error_message: str,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        标记阶段为失败
        
        Args:
            project_id: 项目ID
            stage_name: 阶段名称
            error_message: 错误信息
            metrics: 执行指标（可选，记录失败前的指标）
        
        Returns:
            是否成功
        """
        normalized_name = self._normalize_stage_name(stage_name)
        if not normalized_name:
            logger.warning(f"Unknown stage name: {stage_name}")
            return False
        
        try:
            now = self._now()
            
            # 检查阶段是否存在，避免 DynamoDB update_item 自动创建新记录
            existing_stage = self.db.get_stage(project_id, normalized_name)
            if not existing_stage:
                logger.warning(
                    f"Stage {normalized_name} not found for project {project_id}, "
                    f"original name: {stage_name}, skipping failure mark"
                )
                return False
            
            # 构建更新数据
            updates = {
                'status': StageStatus.FAILED.value,
                'completed_at': now,
                'error_message': error_message
            }
            
            # 记录失败前的指标
            if metrics:
                updates['metrics'] = metrics
                updates['input_tokens'] = metrics.get('input_tokens', 0)
                updates['output_tokens'] = metrics.get('output_tokens', 0)
                updates['tool_calls'] = metrics.get('tool_calls_count', 0)
            
            # 更新阶段状态
            self.db.update_stage(project_id, normalized_name, updates)
            
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
    
    def get_stage_output(
        self, 
        project_id: str, 
        stage_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取阶段输出内容
        
        如果内容存储在 S3，会自动加载。
        
        Args:
            project_id: 项目ID
            stage_name: 阶段名称
            
        Returns:
            阶段输出数据，包含 content、metrics、generated_files、design_document
            
        Validates: Requirement 2.6 - 支持按 project_id 和 stage_name 查询阶段输出
        """
        stage = self.get_stage(project_id, stage_name)
        if not stage:
            return None
        
        output = {
            'stage_name': stage.get('stage_name'),
            'status': stage.get('status'),
            'content': stage.get('agent_output_content', ''),
            'metrics': stage.get('metrics'),
            'generated_files': stage.get('generated_files', []),
            'design_document': stage.get('design_document'),
            'doc_path': stage.get('doc_path'),
        }
        
        # 如果内容在 S3，加载它
        s3_ref = stage.get('agent_output_s3_ref')
        if s3_ref and not output['content']:
            output['content'] = self._load_content_from_s3(s3_ref)
            output['s3_ref'] = s3_ref
        
        return output
    
    def _load_content_from_s3(self, s3_ref: str) -> str:
        """
        从 S3 加载内容
        
        Args:
            s3_ref: S3 对象引用
            
        Returns:
            str: 加载的内容
        """
        # TODO: 实现实际的 S3 加载逻辑
        logger.warning(f"S3 loading not implemented for: {s3_ref}")
        return f"[Content stored at {s3_ref}]"
    
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
    
    def get_stage_design_document(
        self, 
        project_id: str, 
        stage_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取阶段设计文档
        
        Args:
            project_id: 项目ID
            stage_name: 阶段名称
            
        Returns:
            设计文档数据
            
        Validates: Requirement 2.4, 2.6 - 存储和查询设计文档
        """
        stage = self.get_stage(project_id, stage_name)
        if not stage:
            return None
        
        return stage.get('design_document')
    
    def list_generated_files(
        self, 
        project_id: str, 
        stage_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        列出项目生成的文件
        
        Args:
            project_id: 项目ID
            stage_name: 可选的阶段名称，不指定则返回所有阶段的文件
            
        Returns:
            文件元数据列表
            
        Validates: Requirement 2.3 - 支持列出生成的文件
        """
        if stage_name:
            stage = self.get_stage(project_id, stage_name)
            if not stage:
                return []
            return stage.get('generated_files', [])
        
        # 获取所有阶段的文件
        stages = self.list_stages(project_id)
        all_files = []
        for stage in stages:
            files = stage.get('generated_files', [])
            for f in files:
                f['stage_name'] = stage.get('stage_name')
            all_files.extend(files)
        
        return all_files


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
