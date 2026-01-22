"""
Artifact Manager - 管理Agent文件的S3同步和版本控制

提供CLI层面的artifact同步、版本查询等功能。
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from .base import ResourceManager


@dataclass
class ArtifactInfo:
    """Artifact信息"""
    agent_name: str
    version_count: int = 0
    latest_version: str = ""
    latest_created_at: str = ""
    workspace_uuid: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'agent_name': self.agent_name,
            'version_count': self.version_count,
            'latest_version': self.latest_version,
            'latest_created_at': self.latest_created_at,
            'workspace_uuid': self.workspace_uuid
        }


@dataclass
class VersionInfo:
    """版本信息"""
    agent_name: str
    version_uuid: str
    version_tag: str
    workspace_uuid: str
    s3_paths: Dict[str, str]
    notes: str = ""
    created_at: str = ""
    created_by: str = ""
    file_count: int = 0
    total_size: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'agent_name': self.agent_name,
            'version_uuid': self.version_uuid,
            'version_tag': self.version_tag,
            'workspace_uuid': self.workspace_uuid,
            's3_paths': self.s3_paths,
            'notes': self.notes,
            'created_at': self.created_at,
            'created_by': self.created_by,
            'file_count': self.file_count,
            'total_size': self.total_size
        }
    
    def format_size(self) -> str:
        """格式化文件大小"""
        # 转换为float以处理DynamoDB返回的Decimal类型
        size = float(self.total_size) if self.total_size else 0.0
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


@dataclass
class SyncResult:
    """同步结果"""
    success: bool
    agent_name: str
    version_uuid: str = ""
    workspace_uuid: str = ""
    s3_paths: Dict[str, str] = field(default_factory=dict)
    files_synced: int = 0
    total_size: int = 0
    duration_seconds: float = 0.0
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'success': self.success,
            'agent_name': self.agent_name,
            'version_uuid': self.version_uuid,
            'workspace_uuid': self.workspace_uuid,
            's3_paths': self.s3_paths,
            'files_synced': self.files_synced,
            'total_size': self.total_size,
            'duration_seconds': self.duration_seconds,
            'error': self.error
        }
    
    def format_size(self) -> str:
        """格式化文件大小"""
        # 转换为float以处理DynamoDB返回的Decimal类型
        size = float(self.total_size) if self.total_size else 0.0
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


class ArtifactManager(ResourceManager):
    """
    Artifact管理器
    
    封装nexus_utils.artifact_sync模块，提供CLI友好的接口。
    """
    
    def __init__(self, fs_adapter, config_loader):
        """
        初始化Artifact管理器
        
        Args:
            fs_adapter: 文件系统适配器
            config_loader: 配置加载器
        """
        super().__init__(fs_adapter, config_loader)
        self._sync_manager = None
    
    @property
    def sync_manager(self):
        """获取同步管理器（延迟初始化）"""
        if self._sync_manager is None:
            # 导入artifact_sync模块
            from nexus_utils.artifact_sync import ArtifactSyncManager
            self._sync_manager = ArtifactSyncManager(str(self.fs.base_path))
        return self._sync_manager
    
    def sync_agent(
        self,
        agent_name: str,
        version_tag: str = "",
        notes: str = "",
        categories: Optional[List[str]] = None
    ) -> SyncResult:
        """
        同步Agent到S3
        
        Args:
            agent_name: Agent名称
            version_tag: 版本标签
            notes: 备注
            categories: 要同步的类别
            
        Returns:
            SyncResult: 同步结果
        """
        result = self.sync_manager.sync_agent(
            agent_name=agent_name,
            version_tag=version_tag,
            notes=notes,
            categories=categories
        )
        
        return SyncResult(
            success=result.success,
            agent_name=result.agent_name,
            version_uuid=result.version_uuid,
            workspace_uuid=result.workspace_uuid,
            s3_paths=result.s3_paths,
            files_synced=result.files_synced,
            total_size=result.total_size,
            duration_seconds=result.duration_seconds,
            error=result.error
        )
    
    def sync_backup(
        self,
        agent_name: str,
        backup_path: str,
        notes: str = ""
    ) -> SyncResult:
        """
        同步备份文件到S3
        
        Args:
            agent_name: Agent名称
            backup_path: 备份文件路径
            notes: 备注
            
        Returns:
            SyncResult: 同步结果
        """
        result = self.sync_manager.sync_backup(
            agent_name=agent_name,
            backup_path=Path(backup_path),
            notes=notes
        )
        
        return SyncResult(
            success=result.success,
            agent_name=result.agent_name,
            version_uuid=result.version_uuid,
            workspace_uuid=result.workspace_uuid,
            s3_paths=result.s3_paths,
            files_synced=result.files_synced,
            total_size=result.total_size,
            duration_seconds=result.duration_seconds,
            error=result.error
        )
    
    def list_synced_agents(self) -> List[ArtifactInfo]:
        """
        列出所有已同步的Agent（按Agent分组汇总）
        
        Returns:
            List[ArtifactInfo]: Agent列表
        """
        agents_data = self.sync_manager.list_all_agents()
        
        result = []
        for data in agents_data:
            result.append(ArtifactInfo(
                agent_name=data['agent_name'],
                version_count=data['version_count'],
                latest_version=data.get('latest_version', ''),
                latest_created_at=data.get('latest_created_at', ''),
                workspace_uuid=self.sync_manager.get_workspace_uuid()
            ))
        
        return sorted(result, key=lambda x: x.agent_name)
    
    def list_all_versions(self) -> List[VersionInfo]:
        """
        列出所有已同步的版本（不分组，显示每个版本）
        
        Returns:
            List[VersionInfo]: 所有版本列表，按创建时间倒序
        """
        versions = self.sync_manager.list_all_versions()
        
        result = []
        for v in versions:
            result.append(VersionInfo(
                agent_name=v.agent_name,
                version_uuid=v.version_uuid,
                version_tag=v.version_tag,
                workspace_uuid=v.workspace_uuid,
                s3_paths=v.s3_paths,
                notes=v.notes,
                created_at=v.created_at,
                created_by=v.created_by,
                file_count=v.file_count,
                total_size=v.total_size
            ))
        
        return result
    
    def list_versions(self, agent_name: str) -> List[VersionInfo]:
        """
        列出Agent的所有版本
        
        Args:
            agent_name: Agent名称
            
        Returns:
            List[VersionInfo]: 版本列表
        """
        versions = self.sync_manager.list_agent_versions(agent_name)
        
        result = []
        for v in versions:
            result.append(VersionInfo(
                agent_name=v.agent_name,
                version_uuid=v.version_uuid,
                version_tag=v.version_tag,
                workspace_uuid=v.workspace_uuid,
                s3_paths=v.s3_paths,
                notes=v.notes,
                created_at=v.created_at,
                created_by=v.created_by,
                file_count=v.file_count,
                total_size=v.total_size
            ))
        
        return result
    
    def get_version_detail(self, agent_name: str, version_uuid: str) -> Optional[VersionInfo]:
        """
        获取版本详情
        
        Args:
            agent_name: Agent名称
            version_uuid: 版本UUID
            
        Returns:
            VersionInfo: 版本信息
        """
        v = self.sync_manager.get_version_detail(agent_name, version_uuid)
        
        if not v:
            return None
        
        return VersionInfo(
            agent_name=v.agent_name,
            version_uuid=v.version_uuid,
            version_tag=v.version_tag,
            workspace_uuid=v.workspace_uuid,
            s3_paths=v.s3_paths,
            notes=v.notes,
            created_at=v.created_at,
            created_by=v.created_by,
            file_count=v.file_count,
            total_size=v.total_size
        )
    
    def delete_version(
        self,
        agent_name: str,
        version_uuid: str,
        delete_s3: bool = False
    ) -> bool:
        """
        删除版本
        
        Args:
            agent_name: Agent名称
            version_uuid: 版本UUID
            delete_s3: 是否同时删除S3文件
            
        Returns:
            bool: 是否成功
        """
        return self.sync_manager.delete_version(agent_name, version_uuid, delete_s3)
    
    def get_workspace_uuid(self) -> str:
        """
        获取工作空间UUID
        
        Returns:
            str: 工作空间UUID
        """
        return self.sync_manager.get_workspace_uuid()
    
    def get_bucket_name(self) -> str:
        """
        获取S3桶名称
        
        Returns:
            str: S3桶名称
        """
        return self.sync_manager.bucket_name
