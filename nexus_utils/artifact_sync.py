#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Artifact Sync Module

用于将Agent相关文件同步到S3存储桶，并管理版本信息。
支持agents、projects、tools、prompts的同步和备份。
"""

import os
import uuid
import json
import hashlib
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
import logging

import boto3
from botocore.exceptions import ClientError

from .config_loader import get_config

logger = logging.getLogger(__name__)


@dataclass
class ArtifactVersion:
    """Artifact版本信息"""
    agent_name: str
    version_uuid: str
    workspace_uuid: str
    s3_paths: Dict[str, str]
    version_tag: str = ""
    notes: str = ""
    created_at: str = ""
    created_by: str = ""
    file_count: int = 0
    total_size: int = 0
    checksum: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArtifactVersion':
        """从字典创建"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class SyncResult:
    """同步结果"""
    success: bool
    agent_name: str
    version_uuid: str
    workspace_uuid: str
    s3_paths: Dict[str, str] = field(default_factory=dict)
    files_synced: int = 0
    total_size: int = 0
    duration_seconds: float = 0.0
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class ArtifactSyncManager:
    """
    Artifact同步管理器
    
    负责将本地Agent文件同步到S3，并在DynamoDB中记录版本信息。
    """
    
    # 本地目录映射
    LOCAL_PATHS = {
        'agents': 'agents/generated_agents',
        'projects': 'projects',
        'tools': 'tools/generated_tools',
        'prompts': 'prompts/generated_agents_prompts'
    }
    
    # DynamoDB表名
    TABLE_NAME = 'nexus_artifacts'
    
    def __init__(self, base_path: str = "."):
        """
        初始化同步管理器
        
        Args:
            base_path: 项目根目录路径
        """
        self.base_path = Path(base_path).resolve()
        self.config = get_config()
        
        # 获取配置
        self._bucket_name = self.config.get_nested(
            'nexus_ai', 'artifacts_s3_bucket',
            default='nexus-ai-artifacts'
        )
        self._aws_region = self.config.get_nested(
            'aws', 'aws_region_name',
            default='us-west-2'
        )
        self._table_prefix = 'nexus_'
        
        # 初始化AWS客户端
        self._s3_client = None
        self._dynamodb_client = None
        self._dynamodb_resource = None
        
        # 工作空间UUID（延迟初始化）
        self._workspace_uuid = None
    
    @property
    def bucket_name(self) -> str:
        """获取S3桶名称"""
        return self._bucket_name
    
    @property
    def s3_client(self):
        """获取S3客户端（延迟初始化）"""
        if self._s3_client is None:
            self._s3_client = boto3.client('s3', region_name=self._aws_region)
        return self._s3_client
    
    @property
    def dynamodb_client(self):
        """获取DynamoDB客户端（延迟初始化）"""
        if self._dynamodb_client is None:
            self._dynamodb_client = boto3.client('dynamodb', region_name=self._aws_region)
        return self._dynamodb_client
    
    @property
    def dynamodb_resource(self):
        """获取DynamoDB资源（延迟初始化）"""
        if self._dynamodb_resource is None:
            self._dynamodb_resource = boto3.resource('dynamodb', region_name=self._aws_region)
        return self._dynamodb_resource
    
    @property
    def table_name(self) -> str:
        """获取完整表名"""
        return f"{self._table_prefix}{self.TABLE_NAME}"
    
    def get_workspace_uuid(self) -> str:
        """
        获取或创建工作空间UUID
        
        首次调用时从DynamoDB获取或创建新的UUID
        """
        if self._workspace_uuid:
            return self._workspace_uuid
        
        # 尝试从本地配置文件读取
        workspace_file = self.base_path / '.nexus_workspace_id'
        if workspace_file.exists():
            self._workspace_uuid = workspace_file.read_text().strip()
            return self._workspace_uuid
        
        # 创建新的UUID
        self._workspace_uuid = str(uuid.uuid4())
        
        # 保存到本地
        workspace_file.write_text(self._workspace_uuid)
        
        logger.info(f"创建新的工作空间UUID: {self._workspace_uuid}")
        return self._workspace_uuid
    
    def ensure_bucket_exists(self) -> bool:
        """
        确保S3桶存在
        
        Returns:
            bool: 桶是否存在或创建成功
        """
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                # 桶不存在，尝试创建
                try:
                    if self._aws_region == 'us-east-1':
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': self._aws_region}
                        )
                    logger.info(f"创建S3桶: {self.bucket_name}")
                    return True
                except ClientError as create_error:
                    logger.error(f"创建S3桶失败: {create_error}")
                    return False
            else:
                logger.error(f"检查S3桶失败: {e}")
                return False
    
    def ensure_table_exists(self) -> bool:
        """
        确保DynamoDB表存在
        
        Returns:
            bool: 表是否存在或创建成功
        """
        try:
            self.dynamodb_client.describe_table(TableName=self.table_name)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                # 表不存在，创建
                try:
                    self.dynamodb_client.create_table(
                        TableName=self.table_name,
                        KeySchema=[
                            {'AttributeName': 'agent_name', 'KeyType': 'HASH'},
                            {'AttributeName': 'version_uuid', 'KeyType': 'RANGE'}
                        ],
                        AttributeDefinitions=[
                            {'AttributeName': 'agent_name', 'AttributeType': 'S'},
                            {'AttributeName': 'version_uuid', 'AttributeType': 'S'},
                            {'AttributeName': 'workspace_uuid', 'AttributeType': 'S'},
                            {'AttributeName': 'created_at', 'AttributeType': 'S'}
                        ],
                        GlobalSecondaryIndexes=[
                            {
                                'IndexName': 'WorkspaceIndex',
                                'KeySchema': [
                                    {'AttributeName': 'workspace_uuid', 'KeyType': 'HASH'},
                                    {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                                ],
                                'Projection': {'ProjectionType': 'ALL'}
                            }
                        ],
                        BillingMode='PAY_PER_REQUEST'
                    )
                    
                    # 等待表创建完成
                    waiter = self.dynamodb_client.get_waiter('table_exists')
                    waiter.wait(TableName=self.table_name)
                    
                    logger.info(f"创建DynamoDB表: {self.table_name}")
                    return True
                except ClientError as create_error:
                    logger.error(f"创建DynamoDB表失败: {create_error}")
                    return False
            else:
                logger.error(f"检查DynamoDB表失败: {e}")
                return False
    
    def _get_local_path(self, category: str, agent_name: str) -> Path:
        """获取本地目录路径"""
        base = self.LOCAL_PATHS.get(category, category)
        return self.base_path / base / agent_name
    
    def _get_s3_prefix(self, category: str, agent_name: str, version_uuid: str) -> str:
        """获取S3前缀路径"""
        workspace_uuid = self.get_workspace_uuid()
        return f"{workspace_uuid}/{category}/{agent_name}/{version_uuid}"
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """计算文件SHA256校验和"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _upload_directory(self, local_dir: Path, s3_prefix: str) -> Tuple[int, int]:
        """
        上传目录到S3
        
        Args:
            local_dir: 本地目录路径
            s3_prefix: S3前缀
            
        Returns:
            Tuple[int, int]: (文件数, 总大小)
        """
        file_count = 0
        total_size = 0
        
        if not local_dir.exists():
            return file_count, total_size
        
        for file_path in local_dir.rglob('*'):
            if file_path.is_file():
                # 跳过__pycache__和.pyc文件
                if '__pycache__' in str(file_path) or file_path.suffix == '.pyc':
                    continue
                
                relative_path = file_path.relative_to(local_dir)
                s3_key = f"{s3_prefix}/{relative_path}"
                
                try:
                    self.s3_client.upload_file(
                        str(file_path),
                        self.bucket_name,
                        s3_key
                    )
                    file_count += 1
                    total_size += file_path.stat().st_size
                    logger.debug(f"上传文件: {s3_key}")
                except ClientError as e:
                    logger.error(f"上传文件失败 {file_path}: {e}")
        
        return file_count, total_size
    
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
            version_tag: 版本标签（可选）
            notes: 备注（可选）
            categories: 要同步的类别列表，默认全部
            
        Returns:
            SyncResult: 同步结果
        """
        import time
        start_time = time.time()
        
        # 生成版本UUID
        version_uuid = str(uuid.uuid4())
        workspace_uuid = self.get_workspace_uuid()
        
        # 默认同步所有类别
        if categories is None:
            categories = list(self.LOCAL_PATHS.keys())
        
        # 确保基础设施存在
        if not self.ensure_bucket_exists():
            return SyncResult(
                success=False,
                agent_name=agent_name,
                version_uuid=version_uuid,
                workspace_uuid=workspace_uuid,
                error="S3桶不存在且无法创建"
            )
        
        if not self.ensure_table_exists():
            return SyncResult(
                success=False,
                agent_name=agent_name,
                version_uuid=version_uuid,
                workspace_uuid=workspace_uuid,
                error="DynamoDB表不存在且无法创建"
            )
        
        # 同步各类别
        s3_paths = {}
        total_files = 0
        total_size = 0
        
        for category in categories:
            local_path = self._get_local_path(category, agent_name)
            if local_path.exists():
                s3_prefix = self._get_s3_prefix(category, agent_name, version_uuid)
                files, size = self._upload_directory(local_path, s3_prefix)
                if files > 0:
                    s3_paths[category] = f"s3://{self.bucket_name}/{s3_prefix}"
                    total_files += files
                    total_size += size
                    logger.info(f"同步 {category}: {files} 文件, {size} 字节")
        
        if total_files == 0:
            return SyncResult(
                success=False,
                agent_name=agent_name,
                version_uuid=version_uuid,
                workspace_uuid=workspace_uuid,
                error=f"未找到Agent '{agent_name}' 的任何文件"
            )
        
        # 记录版本信息到DynamoDB
        version_info = ArtifactVersion(
            agent_name=agent_name,
            version_uuid=version_uuid,
            workspace_uuid=workspace_uuid,
            s3_paths=s3_paths,
            version_tag=version_tag or f"v{datetime.now().strftime('%Y%m%d%H%M%S')}",
            notes=notes,
            created_at=datetime.utcnow().isoformat() + 'Z',
            created_by=os.environ.get('USER', 'unknown'),
            file_count=total_files,
            total_size=total_size
        )
        
        try:
            table = self.dynamodb_resource.Table(self.table_name)
            table.put_item(Item=version_info.to_dict())
        except ClientError as e:
            logger.error(f"保存版本信息失败: {e}")
            return SyncResult(
                success=False,
                agent_name=agent_name,
                version_uuid=version_uuid,
                workspace_uuid=workspace_uuid,
                s3_paths=s3_paths,
                files_synced=total_files,
                total_size=total_size,
                error=f"保存版本信息失败: {e}"
            )
        
        duration = time.time() - start_time
        
        return SyncResult(
            success=True,
            agent_name=agent_name,
            version_uuid=version_uuid,
            workspace_uuid=workspace_uuid,
            s3_paths=s3_paths,
            files_synced=total_files,
            total_size=total_size,
            duration_seconds=duration
        )
    
    def sync_backup(
        self,
        agent_name: str,
        backup_path: Path,
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
        import time
        start_time = time.time()
        
        workspace_uuid = self.get_workspace_uuid()
        version_uuid = str(uuid.uuid4())
        
        if not backup_path.exists():
            return SyncResult(
                success=False,
                agent_name=agent_name,
                version_uuid=version_uuid,
                workspace_uuid=workspace_uuid,
                error=f"备份文件不存在: {backup_path}"
            )
        
        # 确保S3桶存在
        if not self.ensure_bucket_exists():
            return SyncResult(
                success=False,
                agent_name=agent_name,
                version_uuid=version_uuid,
                workspace_uuid=workspace_uuid,
                error="S3桶不存在且无法创建"
            )
        
        # 上传备份文件
        s3_key = f"{workspace_uuid}/backups/{agent_name}/{backup_path.name}"
        
        try:
            self.s3_client.upload_file(
                str(backup_path),
                self.bucket_name,
                s3_key
            )
        except ClientError as e:
            return SyncResult(
                success=False,
                agent_name=agent_name,
                version_uuid=version_uuid,
                workspace_uuid=workspace_uuid,
                error=f"上传备份失败: {e}"
            )
        
        file_size = backup_path.stat().st_size
        duration = time.time() - start_time
        
        s3_paths = {'backups': f"s3://{self.bucket_name}/{s3_key}"}
        
        # 记录到DynamoDB（可选）
        if self.ensure_table_exists():
            version_info = ArtifactVersion(
                agent_name=agent_name,
                version_uuid=version_uuid,
                workspace_uuid=workspace_uuid,
                s3_paths=s3_paths,
                version_tag=f"backup-{backup_path.stem}",
                notes=notes or f"Backup: {backup_path.name}",
                created_at=datetime.utcnow().isoformat() + 'Z',
                created_by=os.environ.get('USER', 'unknown'),
                file_count=1,
                total_size=file_size
            )
            
            try:
                table = self.dynamodb_resource.Table(self.table_name)
                table.put_item(Item=version_info.to_dict())
            except ClientError as e:
                logger.warning(f"保存备份版本信息失败: {e}")
        
        return SyncResult(
            success=True,
            agent_name=agent_name,
            version_uuid=version_uuid,
            workspace_uuid=workspace_uuid,
            s3_paths=s3_paths,
            files_synced=1,
            total_size=file_size,
            duration_seconds=duration
        )
    
    def list_agent_versions(self, agent_name: str) -> List[ArtifactVersion]:
        """
        列出Agent的所有版本
        
        Args:
            agent_name: Agent名称
            
        Returns:
            List[ArtifactVersion]: 版本列表
        """
        if not self.ensure_table_exists():
            return []
        
        try:
            table = self.dynamodb_resource.Table(self.table_name)
            response = table.query(
                KeyConditionExpression='agent_name = :name',
                ExpressionAttributeValues={':name': agent_name},
                ScanIndexForward=False  # 按时间倒序
            )
            
            versions = []
            for item in response.get('Items', []):
                versions.append(ArtifactVersion.from_dict(item))
            
            return versions
        except ClientError as e:
            logger.error(f"查询版本失败: {e}")
            return []
    
    def list_all_agents(self) -> List[Dict[str, Any]]:
        """
        列出所有已同步的Agent（按Agent分组汇总）
        
        Returns:
            List[Dict]: Agent列表，包含名称和版本数
        """
        if not self.ensure_table_exists():
            return []
        
        try:
            table = self.dynamodb_resource.Table(self.table_name)
            response = table.scan(
                ProjectionExpression='agent_name, version_uuid, created_at, version_tag'
            )
            
            # 按agent_name分组
            agents = {}
            for item in response.get('Items', []):
                name = item['agent_name']
                if name not in agents:
                    agents[name] = {
                        'agent_name': name,
                        'version_count': 0,
                        'latest_version': None,
                        'latest_created_at': None
                    }
                agents[name]['version_count'] += 1
                
                created_at = item.get('created_at', '')
                if not agents[name]['latest_created_at'] or created_at > agents[name]['latest_created_at']:
                    agents[name]['latest_created_at'] = created_at
                    agents[name]['latest_version'] = item.get('version_tag', item['version_uuid'][:8])
            
            return list(agents.values())
        except ClientError as e:
            logger.error(f"查询Agent列表失败: {e}")
            return []
    
    def list_all_versions(self) -> List[ArtifactVersion]:
        """
        列出所有已同步的版本（不分组，显示每个版本）
        
        Returns:
            List[ArtifactVersion]: 所有版本列表，按创建时间倒序
        """
        if not self.ensure_table_exists():
            return []
        
        try:
            table = self.dynamodb_resource.Table(self.table_name)
            response = table.scan()
            
            versions = []
            for item in response.get('Items', []):
                versions.append(ArtifactVersion.from_dict(item))
            
            # 按创建时间倒序排序
            versions.sort(key=lambda v: v.created_at or '', reverse=True)
            
            return versions
        except ClientError as e:
            logger.error(f"查询所有版本失败: {e}")
            return []
    
    def get_version_detail(self, agent_name: str, version_uuid: str) -> Optional[ArtifactVersion]:
        """
        获取特定版本的详细信息
        
        Args:
            agent_name: Agent名称
            version_uuid: 版本UUID
            
        Returns:
            ArtifactVersion: 版本信息，不存在返回None
        """
        if not self.ensure_table_exists():
            return None
        
        try:
            table = self.dynamodb_resource.Table(self.table_name)
            response = table.get_item(
                Key={
                    'agent_name': agent_name,
                    'version_uuid': version_uuid
                }
            )
            
            item = response.get('Item')
            if item:
                return ArtifactVersion.from_dict(item)
            return None
        except ClientError as e:
            logger.error(f"获取版本详情失败: {e}")
            return None
    
    def delete_version(self, agent_name: str, version_uuid: str, delete_s3: bool = False) -> bool:
        """
        删除特定版本
        
        Args:
            agent_name: Agent名称
            version_uuid: 版本UUID
            delete_s3: 是否同时删除S3文件
            
        Returns:
            bool: 是否成功
        """
        # 获取版本信息
        version = self.get_version_detail(agent_name, version_uuid)
        if not version:
            return False
        
        # 删除S3文件（如果需要）
        if delete_s3 and version.s3_paths:
            for category, s3_path in version.s3_paths.items():
                # 解析S3路径
                if s3_path.startswith('s3://'):
                    path_parts = s3_path[5:].split('/', 1)
                    if len(path_parts) == 2:
                        bucket, prefix = path_parts
                        try:
                            # 列出并删除所有对象
                            paginator = self.s3_client.get_paginator('list_objects_v2')
                            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                                objects = page.get('Contents', [])
                                if objects:
                                    delete_keys = [{'Key': obj['Key']} for obj in objects]
                                    self.s3_client.delete_objects(
                                        Bucket=bucket,
                                        Delete={'Objects': delete_keys}
                                    )
                        except ClientError as e:
                            logger.error(f"删除S3文件失败: {e}")
        
        # 删除DynamoDB记录
        try:
            table = self.dynamodb_resource.Table(self.table_name)
            table.delete_item(
                Key={
                    'agent_name': agent_name,
                    'version_uuid': version_uuid
                }
            )
            return True
        except ClientError as e:
            logger.error(f"删除版本记录失败: {e}")
            return False


# 便捷函数
def get_artifact_sync_manager(base_path: str = ".") -> ArtifactSyncManager:
    """
    获取ArtifactSyncManager实例
    
    Args:
        base_path: 项目根目录
        
    Returns:
        ArtifactSyncManager: 管理器实例
    """
    return ArtifactSyncManager(base_path)


def sync_agent_to_s3(
    agent_name: str,
    version_tag: str = "",
    notes: str = "",
    base_path: str = "."
) -> SyncResult:
    """
    便捷函数：同步Agent到S3
    
    Args:
        agent_name: Agent名称
        version_tag: 版本标签
        notes: 备注
        base_path: 项目根目录
        
    Returns:
        SyncResult: 同步结果
    """
    manager = get_artifact_sync_manager(base_path)
    return manager.sync_agent(agent_name, version_tag, notes)


if __name__ == "__main__":
    # 测试代码
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python artifact_sync.py <agent_name> [version_tag] [notes]")
        sys.exit(1)
    
    agent_name = sys.argv[1]
    version_tag = sys.argv[2] if len(sys.argv) > 2 else ""
    notes = sys.argv[3] if len(sys.argv) > 3 else ""
    
    result = sync_agent_to_s3(agent_name, version_tag, notes)
    
    if result.success:
        print(f"✓ 同步成功!")
        print(f"  Agent: {result.agent_name}")
        print(f"  版本UUID: {result.version_uuid}")
        print(f"  文件数: {result.files_synced}")
        print(f"  总大小: {result.total_size} 字节")
        print(f"  耗时: {result.duration_seconds:.2f} 秒")
        print(f"  S3路径:")
        for category, path in result.s3_paths.items():
            print(f"    {category}: {path}")
    else:
        print(f"✗ 同步失败: {result.error}")
        sys.exit(1)
