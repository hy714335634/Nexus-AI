"""Common data models for Nexus-AI CLI"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path


@dataclass
class Dependency:
    """Represents a dependency (tool, package, agent, etc.)"""
    name: str
    type: str  # agent, tool, template, prompt, package
    version: Optional[str] = None
    required: bool = True
    available: bool = False
    path: Optional[str] = None


@dataclass
class DirectoryTree:
    """Represents a directory tree structure"""
    path: str
    name: str
    type: str  # file, directory
    children: List['DirectoryTree'] = field(default_factory=list)
    size: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'path': self.path,
            'name': self.name,
            'type': self.type,
            'children': [child.to_dict() for child in self.children],
            'size': self.size
        }


@dataclass
class ValidationResult:
    """Result of a validation operation"""
    success: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    
    def add_error(self, message: str):
        """Add an error message"""
        self.errors.append(message)
        self.success = False
    
    def add_warning(self, message: str):
        """Add a warning message"""
        self.warnings.append(message)
    
    def add_suggestion(self, message: str):
        """Add a suggestion"""
        self.suggestions.append(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'success': self.success,
            'errors': self.errors,
            'warnings': self.warnings,
            'suggestions': self.suggestions
        }
