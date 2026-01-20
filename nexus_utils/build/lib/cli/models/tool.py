"""Tool data models"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Any


@dataclass
class Tool:
    """Represents a tool"""
    name: str
    path: Path
    project: Optional[str] = None
    function_name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'path': str(self.path),
            'project': self.project,
            'function_name': self.function_name,
            'description': self.description,
            'parameters': self.parameters
        }
