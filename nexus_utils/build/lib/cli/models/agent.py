"""Agent data models"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any


@dataclass
class AgentConfig:
    """Agent configuration"""
    name: str
    description: str = ""
    category: str = ""
    version: str = "1.0.0"
    tools_dependencies: List[str] = field(default_factory=list)
    supported_models: List[str] = field(default_factory=list)
    system_prompt: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'version': self.version,
            'tools_dependencies': self.tools_dependencies,
            'supported_models': self.supported_models,
            'system_prompt': self.system_prompt
        }


@dataclass
class Agent:
    """Represents a Nexus-AI agent"""
    name: str
    path: Path
    project: Optional[str] = None
    config: Optional[AgentConfig] = None
    dependencies: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'path': str(self.path),
            'project': self.project,
            'config': self.config.to_dict() if self.config else None,
            'dependencies': self.dependencies,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
