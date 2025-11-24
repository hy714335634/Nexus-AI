"""Base resource manager"""

from typing import List, Optional
from ..models.common import Dependency, ValidationResult
from ..adapters.filesystem import FileSystemAdapter
from ..adapters.config_loader import ConfigLoader


class ResourceManager:
    """Base class for all resource managers"""
    
    def __init__(self, fs_adapter: FileSystemAdapter, config_loader: ConfigLoader):
        """Initialize with adapters"""
        self.fs = fs_adapter
        self.config = config_loader
    
    def validate_resource(self, resource: any) -> ValidationResult:
        """Validate a resource"""
        result = ValidationResult(success=True)
        # Base validation - can be overridden
        return result
    
    def check_dependencies(self, resource: any) -> List[Dependency]:
        """Check dependencies for a resource"""
        # Base implementation - can be overridden
        return []
    
    def ensure_hierarchy_integrity(self, resource: any) -> bool:
        """Ensure hierarchy integrity"""
        # Base implementation - can be overridden
        return True
