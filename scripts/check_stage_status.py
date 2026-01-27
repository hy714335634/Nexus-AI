#!/usr/bin/env python3
"""
检查数据库中阶段状态的脚本

用于调试前端不显示"运行中"状态的问题
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.v2.database import db_client


def check_stage_status(project_id: str = None):
    """
    检查阶段状态
    
    参数:
        project_id: 项目ID，如果为 None 则列出所有项目
    """
    if project_id:
        # 检查特定项目
        print(f"\n检查项目: {project_id}")
        print("=" * 60)
        
        project = db_client.get_project(project_id)
        if not project:
            print(f"项目 {project_id} 不存在")
            return
        
        print(f"项目状态: {project.get('status')}")
        print(f"当前阶段: {project.get('current_stage')}")
        print(f"控制状态: {project.get('control_status')}")
        
        stages = db_client.list_stages(project_id)
        print(f"\n阶段列表 ({len(stages)} 个):")
        print("-" * 60)
        
        for stage in stages:
            stage_name = stage.get('stage_name', 'unknown')
            status = stage.get('status', 'unknown')
            started_at = stage.get('started_at', 'N/A')
            completed_at = stage.get('completed_at', 'N/A')
            duration = stage.get('duration_seconds', 'N/A')
            
            print(f"  {stage_name}:")
            print(f"    status: '{status}' (type: {type(status).__name__})")
            print(f"    started_at: {started_at}")
            print(f"    completed_at: {completed_at}")
            print(f"    duration_seconds: {duration}")
            print()
    else:
        # 列出所有项目
        print("\n列出所有项目:")
        print("=" * 60)
        
        result = db_client.list_projects(limit=10)
        projects = result.get('items', [])
        
        for project in projects:
            project_id = project.get('project_id')
            status = project.get('status')
            current_stage = project.get('current_stage')
            print(f"  {project_id}: status={status}, current_stage={current_stage}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        check_stage_status(sys.argv[1])
    else:
        check_stage_status()
        print("\n提示: 使用 'python scripts/check_stage_status.py <project_id>' 查看特定项目的阶段状态")
