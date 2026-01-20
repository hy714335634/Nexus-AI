"""File system operations adapter"""

import os
import json
import yaml
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from ..models.common import DirectoryTree


class FileSystemAdapter:
    """Handles all file system operations"""
    
    def __init__(self, base_path: str = "."):
        """Initialize with base path"""
        self.base_path = Path(base_path).resolve()
    
    def read_yaml(self, path: str) -> Dict[str, Any]:
        """Read and parse YAML file"""
        full_path = self.base_path / path
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {path}: {e}")
    
    def write_yaml(self, path: str, data: Dict[str, Any]) -> bool:
        """Write data to YAML file"""
        full_path = self.base_path / path
        try:
            # Ensure directory exists
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)
            return True
        except Exception as e:
            raise IOError(f"Failed to write YAML to {path}: {e}")
    
    def read_json(self, path: str) -> Dict[str, Any]:
        """Read and parse JSON file"""
        full_path = self.base_path / path
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {path}: {e}")
    
    def write_json(self, path: str, data: Dict[str, Any]) -> bool:
        """Write data to JSON file"""
        full_path = self.base_path / path
        try:
            # Ensure directory exists
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            raise IOError(f"Failed to write JSON to {path}: {e}")
    
    def read_file(self, path: str) -> str:
        """Read text file"""
        full_path = self.base_path / path
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {path}")
    
    def write_file(self, path: str, content: str) -> bool:
        """Write text file"""
        full_path = self.base_path / path
        try:
            # Ensure directory exists
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            raise IOError(f"Failed to write file {path}: {e}")
    
    def list_directory(self, path: str, pattern: str = "*") -> List[Path]:
        """List directory contents"""
        full_path = self.base_path / path
        if not full_path.exists():
            return []
        if not full_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")
        
        return list(full_path.glob(pattern))
    
    def create_directory(self, path: str) -> bool:
        """Create directory"""
        full_path = self.base_path / path
        try:
            full_path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            raise IOError(f"Failed to create directory {path}: {e}")
    
    def delete_directory(self, path: str) -> bool:
        """Delete directory"""
        full_path = self.base_path / path
        try:
            if full_path.exists():
                shutil.rmtree(full_path)
            return True
        except Exception as e:
            raise IOError(f"Failed to delete directory {path}: {e}")
    
    def delete_file(self, path: str) -> bool:
        """Delete file"""
        full_path = self.base_path / path
        try:
            if full_path.exists():
                full_path.unlink()
            return True
        except Exception as e:
            raise IOError(f"Failed to delete file {path}: {e}")
    
    def copy_directory(self, src: str, dst: str) -> bool:
        """Copy directory"""
        src_path = self.base_path / src
        dst_path = self.base_path / dst
        try:
            shutil.copytree(src_path, dst_path)
            return True
        except Exception as e:
            raise IOError(f"Failed to copy directory from {src} to {dst}: {e}")
    
    def exists(self, path: str) -> bool:
        """Check if path exists"""
        return (self.base_path / path).exists()
    
    def is_directory(self, path: str) -> bool:
        """Check if path is a directory"""
        return (self.base_path / path).is_dir()
    
    def is_file(self, path: str) -> bool:
        """Check if path is a file"""
        return (self.base_path / path).is_file()
    
    def get_directory_tree(self, path: str, max_depth: Optional[int] = None) -> DirectoryTree:
        """Generate directory tree structure"""
        full_path = self.base_path / path
        
        def build_tree(current_path: Path, depth: int = 0) -> DirectoryTree:
            """Recursively build tree"""
            name = current_path.name
            rel_path = str(current_path.relative_to(self.base_path))
            
            if current_path.is_file():
                size = current_path.stat().st_size
                return DirectoryTree(
                    path=rel_path,
                    name=name,
                    type='file',
                    children=[],
                    size=size
                )
            
            # Directory
            children = []
            if max_depth is None or depth < max_depth:
                try:
                    for child in sorted(current_path.iterdir()):
                        children.append(build_tree(child, depth + 1))
                except PermissionError:
                    pass
            
            return DirectoryTree(
                path=rel_path,
                name=name,
                type='directory',
                children=children
            )
        
        if not full_path.exists():
            raise FileNotFoundError(f"Path not found: {path}")
        
        return build_tree(full_path)
    
    def get_file_size(self, path: str) -> int:
        """Get file size in bytes"""
        full_path = self.base_path / path
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return full_path.stat().st_size
    
    def get_modification_time(self, path: str) -> float:
        """Get file modification time"""
        full_path = self.base_path / path
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return full_path.stat().st_mtime
