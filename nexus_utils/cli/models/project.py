"""Project data models"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any


@dataclass
class ProjectConfig:
    """Project configuration"""
    name: str
    description: str = ""
    version: str = "1.0.0"
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'dependencies': self.dependencies,
            'metadata': self.metadata
        }


@dataclass
class ProjectStatus:
    """Project status information"""
    overall_status: str  # pending, in_progress, completed, failed
    stages: Dict[str, str] = field(default_factory=dict)
    progress: float = 0.0  # 0.0 to 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'overall_status': self.overall_status,
            'stages': self.stages,
            'progress': self.progress
        }


@dataclass
class Project:
    """Represents a Nexus-AI project"""
    name: str
    path: Path
    config: ProjectConfig
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    agents: List[str] = field(default_factory=list)
    templates: List[str] = field(default_factory=list)
    prompts: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    
    @property
    def agent_count(self) -> int:
        """Get count of agents"""
        return len(self.agents)
    
    @property
    def template_count(self) -> int:
        """Get count of templates"""
        return len(self.templates)
    
    @property
    def prompt_count(self) -> int:
        """Get count of prompts"""
        return len(self.prompts)
    
    @property
    def tool_count(self) -> int:
        """Get count of tools"""
        return len(self.tools)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'path': str(self.path),
            'config': self.config.to_dict(),
            'status': self.status.to_dict(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'agents': self.agents,
            'agent_count': self.agent_count,
            'templates': self.templates,
            'template_count': self.template_count,
            'prompts': self.prompts,
            'prompt_count': self.prompt_count,
            'tools': self.tools,
            'tool_count': self.tool_count
        }
