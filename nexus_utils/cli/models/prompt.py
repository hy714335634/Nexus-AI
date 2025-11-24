"""Prompt data models"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Any


@dataclass
class Prompt:
    """Represents a prompt"""
    name: str
    path: Path
    project: Optional[str] = None
    content: str = ""
    version: str = "1.0.0"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'path': str(self.path),
            'project': self.project,
            'content': self.content,
            'version': self.version,
            'metadata': self.metadata
        }
