#!/usr/bin/env python3
"""
调试脚本：检查项目阶段记录

用于诊断阶段重复问题
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.v2.database import db_client
from api.v2.models.schemas import BuildStage


def debug_project_stages(project_id: str):
    """检查项目的阶段记录"""
    print(f"\n{'='*60}")
    print(f"项目ID: {project_id}")
    print(f"{'='*60}")
    
    # 获取项目信息
    project = db_client.get_project(project_id)
    if not project:
        print(f"❌ 项目不存在: {project_id}")
        return
    
    print(f"\n📋 项目状态:")
    print(f"  - 名称: {project.get('project_name')}")
    print(f"  - 状态: {project.get('status')}")
    print(f"  - 进度: {project.get('progress')}%")
    print(f"  - 当前阶段: {project.get('current_stage')}")
    print(f"  - 控制状态: {project.get('control_status')}")
    
    # 获取所有阶段
    stages = db_client.list_stages(project_id)
    
    print(f"\n📊 阶段记录 (共 {len(stages)} 条):")
    print(f"{'='*60}")
    
    # 检查 BuildStage 枚举定义
    print(f"\n🔧 BuildStage 枚举定义:")
    for stage in BuildStage:
        print(f"  - {stage.name} = '{stage.value}'")
    
    print(f"\n📝 数据库中的阶段记录:")
    stage_names = set()
    duplicates = []
    
    for i, stage in enumerate(stages):
        stage_name = stage.get('stage_name')
        stage_number = stage.get('stage_number', 'N/A')
        status = stage.get('status', 'unknown')
        display_name = stage.get('display_name', 'N/A')
        
        # 检查重复
        if stage_name in stage_names:
            duplicates.append(stage_name)
            marker = "⚠️ 重复!"
        else:
            stage_names.add(stage_name)
            marker = ""
        
        print(f"\n  [{i+1}] stage_name: '{stage_name}' {marker}")
        print(f"      stage_number: {stage_number}")
        print(f"      display_name: {display_name}")
        print(f"      status: {status}")
        print(f"      started_at: {stage.get('started_at', 'N/A')}")
        print(f"      completed_at: {stage.get('completed_at', 'N/A')}")
    
    # 检查是否有不在枚举中的阶段名称
    print(f"\n🔍 阶段名称验证:")
    valid_stage_values = {s.value for s in BuildStage}
    
    for stage_name in stage_names:
        if stage_name in valid_stage_values:
            print(f"  ✅ '{stage_name}' - 有效的 BuildStage 值")
        else:
            print(f"  ❌ '{stage_name}' - 不在 BuildStage 枚举中!")
    
    if duplicates:
        print(f"\n⚠️ 发现重复的阶段名称: {duplicates}")
    else:
        print(f"\n✅ 没有发现重复的阶段名称")
    
    # 检查阶段数量是否正确
    expected_count = len(BuildStage)
    actual_count = len(stages)
    
    print(f"\n📈 阶段数量检查:")
    print(f"  - 预期阶段数: {expected_count}")
    print(f"  - 实际阶段数: {actual_count}")
    
    if actual_count != expected_count:
        print(f"  ⚠️ 阶段数量不匹配!")
        
        # 找出缺失或多余的阶段
        missing = valid_stage_values - stage_names
        extra = stage_names - valid_stage_values
        
        if missing:
            print(f"  - 缺失的阶段: {missing}")
        if extra:
            print(f"  - 多余的阶段: {extra}")
    else:
        print(f"  ✅ 阶段数量正确")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/debug_project_stages.py <project_id>")
        print("示例: python scripts/debug_project_stages.py proj_123330210f3e")
        sys.exit(1)
    
    project_id = sys.argv[1]
    debug_project_stages(project_id)
