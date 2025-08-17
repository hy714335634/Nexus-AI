#!/usr/bin/env python3
"""
项目路径设置工具

统一管理项目路径，避免在每个文件中重复写路径设置代码
"""

import sys
import os
from pathlib import Path

def setup_project_path():
    """
    设置项目路径，确保可以导入项目内部模块
    
    Returns:
        str: 项目根目录路径
    """
    # 获取当前文件的路径
    current_file = Path(__file__).resolve()
    
    # 向上查找项目根目录（包含pyproject.toml的目录）
    project_root = current_file.parent
    while project_root != project_root.parent:
        if (project_root / "pyproject.toml").exists():
            break
        project_root = project_root.parent
    else:
        # 如果没找到pyproject.toml，使用utils的父目录
        project_root = current_file.parent.parent
    
    project_root_str = str(project_root)
    
    # 添加到sys.path（如果还没有的话）
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    
    return project_root_str

# 自动执行路径设置
PROJECT_ROOT = setup_project_path()