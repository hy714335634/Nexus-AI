"""
文件同步功能

提供跨 Worker 的文件同步功能，包括文件元数据记录、S3 同步和文件内容 API。

Requirements:
    - 10.1: 文件路径记录
    - 10.2: 文件大小和时间戳记录
    - 10.3: 文件列表查询
    - 10.4: 跨 Worker 文件同步
    - 10.5: 文件内容 API
"""

import logging
import os
import hashlib
import boto3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, BinaryIO
from dataclasses import dataclass, field

from .models import FileMetadata

logger = logging.getLogger(__name__)


def _get_project_root() -> Path:
    """获取项目根目录"""
    current_file = Path(__file__).resolve()
    return current_file.parent.parent.parent


@dataclass
class FileSyncConfig:
    """
    文件同步配置
    
    属性:
        s3_bucket: S3 存储桶名称
        s3_prefix: S3 前缀
        local_base_path: 本地基础路径
        auto_sync: 是否自动同步
    """
    s3_bucket: str = "nexus-ai-workflow-files"
    s3_prefix: str = "workflow-files/"
    local_base_path: str = "projects"
    auto_sync: bool = True
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'FileSyncConfig':
        """从配置字典创建"""
        return cls(
            s3_bucket=config.get('s3_bucket', cls.s3_bucket),
            s3_prefix=config.get('s3_prefix', cls.s3_prefix),
            local_base_path=config.get('local_base_path', cls.local_base_path),
            auto_sync=config.get('auto_sync', cls.auto_sync),
        )


class FileMetadataManager:
    """
    文件元数据管理器
    
    负责记录和查询文件元数据。
    
    Validates:
        - Requirement 10.1: 文件路径记录
        - Requirement 10.2: 文件大小和时间戳记录
        - Requirement 10.3: 文件列表查询
    """
    
    def __init__(self, db_client=None):
        """
        初始化元数据管理器
        
        参数:
            db_client: DynamoDB 客户端
        """
        self._db_client = db_client
        self.project_root = _get_project_root()
    
    @property
    def db(self):
        """延迟加载 DynamoDB 客户端"""
        if self._db_client is None:
            from api.v2.database import db_client
            self._db_client = db_client
        return self._db_client
    
    def scan_project_files(
        self, 
        project_id: str, 
        project_name: str
    ) -> List[FileMetadata]:
        """
        扫描项目目录中的所有文件
        
        参数:
            project_id: 项目ID
            project_name: 项目名称
            
        返回:
            List[FileMetadata]: 文件元数据列表
            
        Validates: Requirement 10.1, 10.2 - 文件路径、大小、时间戳记录
        """
        files = []
        
        # 确定项目目录
        project_dir = self.project_root / "projects" / project_name
        if not project_dir.exists():
            project_dir = self.project_root / "projects" / project_id
        
        if not project_dir.exists():
            logger.warning(f"Project directory not found: {project_dir}")
            return files
        
        # 扫描所有文件
        for file_path in project_dir.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith('.'):
                try:
                    # 计算相对路径
                    relative_path = str(file_path.relative_to(project_dir))
                    
                    # 获取文件信息
                    stat = file_path.stat()
                    
                    # 计算校验和
                    checksum = self._calculate_checksum(file_path)
                    
                    files.append(FileMetadata(
                        path=relative_path,
                        size=stat.st_size,
                        checksum=checksum,
                        last_modified=datetime.fromtimestamp(
                            stat.st_mtime, tz=timezone.utc
                        ),
                    ))
                except Exception as e:
                    logger.warning(f"Failed to scan file {file_path}: {e}")
        
        return files
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """计算文件 MD5 校验和"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""
    
    def save_file_metadata(
        self, 
        project_id: str, 
        stage_name: str,
        files: List[FileMetadata]
    ) -> None:
        """
        保存文件元数据到 DynamoDB
        
        参数:
            project_id: 项目ID
            stage_name: 阶段名称
            files: 文件元数据列表
        """
        try:
            files_data = [f.to_dict() for f in files]
            self.db.update_stage(project_id, stage_name, {
                'generated_files': files_data,
            })
            logger.info(f"Saved {len(files)} file metadata for {project_id}/{stage_name}")
        except Exception as e:
            logger.error(f"Failed to save file metadata: {e}")
    
    def get_file_metadata(
        self, 
        project_id: str, 
        stage_name: Optional[str] = None
    ) -> List[FileMetadata]:
        """
        获取文件元数据
        
        参数:
            project_id: 项目ID
            stage_name: 阶段名称（可选，如果不指定则获取所有阶段）
            
        返回:
            List[FileMetadata]: 文件元数据列表
            
        Validates: Requirement 10.3 - 文件列表查询
        """
        files = []
        
        try:
            if stage_name:
                # 获取指定阶段的文件
                stage = self.db.get_stage(project_id, stage_name)
                if stage:
                    files_data = stage.get('generated_files', [])
                    files = [FileMetadata.from_dict(f) for f in files_data]
            else:
                # 获取所有阶段的文件
                stages = self.db.list_stages(project_id)
                for stage in stages:
                    files_data = stage.get('generated_files', [])
                    files.extend([FileMetadata.from_dict(f) for f in files_data])
        except Exception as e:
            logger.error(f"Failed to get file metadata: {e}")
        
        return files
    
    def list_project_files(
        self, 
        project_id: str,
        include_content: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        列出项目的所有文件
        
        参数:
            project_id: 项目ID
            include_content: 是否包含文件内容
            
        返回:
            List[Dict]: 文件信息列表
            
        Validates: Requirement 10.3 - 文件列表查询
        """
        files = self.get_file_metadata(project_id)
        
        result = []
        for f in files:
            file_info = f.to_dict()
            
            if include_content:
                content = self.get_file_content(project_id, f.path)
                file_info['content'] = content
            
            result.append(file_info)
        
        return result
    
    def get_file_content(
        self, 
        project_id: str, 
        file_path: str,
        project_name: Optional[str] = None,
    ) -> Optional[str]:
        """
        获取文件内容
        
        参数:
            project_id: 项目ID
            file_path: 文件相对路径
            project_name: 项目名称（可选）
            
        返回:
            str: 文件内容，如果文件不存在则返回 None
            
        Validates: Requirement 10.5 - 文件内容 API
        """
        # 确定项目目录
        if project_name:
            project_dir = self.project_root / "projects" / project_name
        else:
            project_dir = self.project_root / "projects" / project_id
        
        full_path = project_dir / file_path
        
        if not full_path.exists():
            logger.warning(f"File not found: {full_path}")
            return None
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # 二进制文件，返回 base64 编码
            import base64
            with open(full_path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to read file {full_path}: {e}")
            return None


class FileSyncManager:
    """
    文件同步管理器
    
    负责跨 Worker 的文件同步。
    
    Validates: Requirement 10.4 - 跨 Worker 文件同步
    """
    
    def __init__(self, config: Optional[FileSyncConfig] = None):
        """
        初始化同步管理器
        
        参数:
            config: 同步配置
        """
        self.config = config or FileSyncConfig()
        self.project_root = _get_project_root()
        self._s3_client = None
        self._metadata_manager = FileMetadataManager()
    
    @property
    def s3(self):
        """延迟加载 S3 客户端"""
        if self._s3_client is None:
            self._s3_client = boto3.client('s3')
        return self._s3_client
    
    def sync_to_s3(
        self, 
        project_id: str, 
        project_name: str,
        files: Optional[List[FileMetadata]] = None,
    ) -> int:
        """
        同步文件到 S3
        
        参数:
            project_id: 项目ID
            project_name: 项目名称
            files: 要同步的文件列表（可选，如果不指定则同步所有文件）
            
        返回:
            int: 同步的文件数量
        """
        if files is None:
            files = self._metadata_manager.scan_project_files(project_id, project_name)
        
        if not files:
            return 0
        
        # 确定项目目录
        project_dir = self.project_root / "projects" / project_name
        if not project_dir.exists():
            project_dir = self.project_root / "projects" / project_id
        
        synced_count = 0
        
        for file_meta in files:
            try:
                local_path = project_dir / file_meta.path
                if not local_path.exists():
                    continue
                
                s3_key = f"{self.config.s3_prefix}{project_id}/{file_meta.path}"
                
                with open(local_path, 'rb') as f:
                    self.s3.upload_fileobj(
                        f,
                        self.config.s3_bucket,
                        s3_key,
                        ExtraArgs={
                            'Metadata': {
                                'checksum': file_meta.checksum or '',
                                'project_id': project_id,
                            }
                        }
                    )
                
                synced_count += 1
                logger.debug(f"Synced file to S3: {s3_key}")
                
            except Exception as e:
                logger.error(f"Failed to sync file {file_meta.path}: {e}")
        
        logger.info(f"Synced {synced_count} files to S3 for project {project_id}")
        return synced_count
    
    def sync_from_s3(
        self, 
        project_id: str, 
        project_name: str,
        files: Optional[List[str]] = None,
    ) -> int:
        """
        从 S3 同步文件
        
        参数:
            project_id: 项目ID
            project_name: 项目名称
            files: 要同步的文件路径列表（可选，如果不指定则同步所有文件）
            
        返回:
            int: 同步的文件数量
            
        Validates: Requirement 10.4 - 跨 Worker 文件同步
        """
        # 确定项目目录
        project_dir = self.project_root / "projects" / project_name
        project_dir.mkdir(parents=True, exist_ok=True)
        
        synced_count = 0
        
        try:
            # 列出 S3 中的文件
            prefix = f"{self.config.s3_prefix}{project_id}/"
            
            paginator = self.s3.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.config.s3_bucket,
                Prefix=prefix,
            )
            
            for page in pages:
                for obj in page.get('Contents', []):
                    s3_key = obj['Key']
                    relative_path = s3_key[len(prefix):]
                    
                    # 如果指定了文件列表，只同步指定的文件
                    if files and relative_path not in files:
                        continue
                    
                    local_path = project_dir / relative_path
                    
                    # 检查本地文件是否存在且是最新的
                    if local_path.exists():
                        local_mtime = datetime.fromtimestamp(
                            local_path.stat().st_mtime, tz=timezone.utc
                        )
                        s3_mtime = obj['LastModified']
                        
                        if local_mtime >= s3_mtime:
                            continue  # 本地文件是最新的
                    
                    # 下载文件
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(local_path, 'wb') as f:
                        self.s3.download_fileobj(
                            self.config.s3_bucket,
                            s3_key,
                            f,
                        )
                    
                    synced_count += 1
                    logger.debug(f"Synced file from S3: {relative_path}")
                    
        except Exception as e:
            logger.error(f"Failed to sync from S3: {e}")
        
        logger.info(f"Synced {synced_count} files from S3 for project {project_id}")
        return synced_count
    
    def check_missing_files(
        self, 
        project_id: str, 
        project_name: str,
        required_files: List[str],
    ) -> List[str]:
        """
        检查缺失的文件
        
        参数:
            project_id: 项目ID
            project_name: 项目名称
            required_files: 需要的文件列表
            
        返回:
            List[str]: 缺失的文件路径列表
        """
        # 确定项目目录
        project_dir = self.project_root / "projects" / project_name
        if not project_dir.exists():
            project_dir = self.project_root / "projects" / project_id
        
        missing = []
        for file_path in required_files:
            full_path = project_dir / file_path
            if not full_path.exists():
                missing.append(file_path)
        
        return missing
    
    def ensure_files_available(
        self, 
        project_id: str, 
        project_name: str,
        required_files: List[str],
    ) -> bool:
        """
        确保所需文件可用（如果缺失则从 S3 下载）
        
        参数:
            project_id: 项目ID
            project_name: 项目名称
            required_files: 需要的文件列表
            
        返回:
            bool: 是否所有文件都可用
            
        Validates: Requirement 10.4 - 跨 Worker 文件同步
        """
        missing = self.check_missing_files(project_id, project_name, required_files)
        
        if not missing:
            return True
        
        logger.info(f"Missing {len(missing)} files, syncing from S3...")
        
        # 从 S3 同步缺失的文件
        self.sync_from_s3(project_id, project_name, missing)
        
        # 再次检查
        still_missing = self.check_missing_files(project_id, project_name, required_files)
        
        if still_missing:
            logger.warning(f"Still missing {len(still_missing)} files after sync")
            return False
        
        return True


# 便捷函数
def scan_and_save_files(
    project_id: str, 
    project_name: str, 
    stage_name: str
) -> List[FileMetadata]:
    """
    扫描并保存文件元数据
    
    参数:
        project_id: 项目ID
        project_name: 项目名称
        stage_name: 阶段名称
        
    返回:
        List[FileMetadata]: 文件元数据列表
    """
    manager = FileMetadataManager()
    files = manager.scan_project_files(project_id, project_name)
    manager.save_file_metadata(project_id, stage_name, files)
    return files


def get_file_content(
    project_id: str, 
    file_path: str,
    project_name: Optional[str] = None,
) -> Optional[str]:
    """
    获取文件内容
    
    参数:
        project_id: 项目ID
        file_path: 文件相对路径
        project_name: 项目名称
        
    返回:
        str: 文件内容
    """
    manager = FileMetadataManager()
    return manager.get_file_content(project_id, file_path, project_name)


def sync_project_files(
    project_id: str, 
    project_name: str,
    direction: str = "to_s3",
) -> int:
    """
    同步项目文件
    
    参数:
        project_id: 项目ID
        project_name: 项目名称
        direction: 同步方向 ("to_s3" 或 "from_s3")
        
    返回:
        int: 同步的文件数量
    """
    manager = FileSyncManager()
    
    if direction == "to_s3":
        return manager.sync_to_s3(project_id, project_name)
    else:
        return manager.sync_from_s3(project_id, project_name)
