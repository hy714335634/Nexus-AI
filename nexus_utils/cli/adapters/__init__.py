"""Data access adapters for Nexus-AI CLI"""

from .filesystem import FileSystemAdapter
from .config_loader import ConfigLoader

__all__ = ['FileSystemAdapter', 'ConfigLoader']
