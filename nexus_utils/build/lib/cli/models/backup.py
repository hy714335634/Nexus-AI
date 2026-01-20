"""
Backup data models for Nexus-AI CLI
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class BackupManifest:
    """Backup manifest containing metadata and checksums"""
    version: str
    project_name: str
    created_at: datetime
    nexus_version: str
    resources: Dict[str, List[str]]  # resource_type -> list of paths
    checksums: Dict[str, str]  # file_path -> checksum (SHA-256)
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'version': self.version,
            'project_name': self.project_name,
            'created_at': self.created_at.isoformat(),
            'nexus_version': self.nexus_version,
            'resources': self.resources,
            'checksums': self.checksums,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'BackupManifest':
        """Create from dictionary"""
        return cls(
            version=data['version'],
            project_name=data['project_name'],
            created_at=datetime.fromisoformat(data['created_at']),
            nexus_version=data['nexus_version'],
            resources=data['resources'],
            checksums=data['checksums'],
            metadata=data.get('metadata', {})
        )


@dataclass
class Backup:
    """Backup information"""
    name: str
    path: Path
    project_name: str
    created_at: datetime
    size: int  # Size in bytes
    format: str  # tar.gz or zip
    manifest: Optional[BackupManifest] = None
    checksum: Optional[str] = None  # Overall backup file checksum
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'path': str(self.path),
            'project_name': self.project_name,
            'created_at': self.created_at.isoformat(),
            'size': self.size,
            'size_mb': round(self.size / (1024 * 1024), 2),
            'format': self.format,
            'checksum': self.checksum,
            'manifest': self.manifest.to_dict() if self.manifest else None
        }
    
    @property
    def size_mb(self) -> float:
        """Get size in megabytes"""
        return round(self.size / (1024 * 1024), 2)
    
    @property
    def size_human(self) -> str:
        """Get human-readable size"""
        size = self.size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
